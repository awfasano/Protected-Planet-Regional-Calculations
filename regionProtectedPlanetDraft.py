#!/usr/bin/env python

import os
import requests
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import shape, MultiPolygon

# --- API functions ---
API_BASE_URL = "https://api.protectedplanet.net/v3"
API_KEY = "15514395b80ee101b6bcdee785a6445a"  # Replace with your API token


def fetch_api_protected_areas(country_code):
    """
    Fetches WDPA protected areas for the given country using the /protected_areas/search endpoint.
    Uses pagination (per_page=50) to retrieve all pages.
    For features that are Points, creates a buffer based on the reported area.
    Reprojects everything to the Mollweide projection (same as used in national calculations).
    """
    all_features = []
    page = 1
    per_page = 50
    while True:
        endpoint = (f"{API_BASE_URL}/protected_areas/search?country={country_code}"
                    f"&with_geometry=true&token={API_KEY}&page={page}&per_page={per_page}")
        print("Requesting API endpoint:", endpoint)
        response = requests.get(endpoint)
        if response.status_code != 200:
            print(f"Error fetching API data for {country_code} on page {page}: {response.status_code}")
            print(response.text)
            break
        data = response.json()
        features = data.get("protected_areas", [])
        if not features:
            break
        all_features.extend(features)
        if len(features) < per_page:
            break
        page += 1
    print(f"Successfully fetched {len(all_features)} protected areas from API for {country_code}.")

    processed_features = []
    for area in all_features:
        geojson_data = area.get("geojson")
        if not (geojson_data and "type" in geojson_data):
            print("Skipping area without valid geojson geometry")
            continue

        geom = None
        geom_type = geojson_data["type"]
        if geom_type == "Feature":
            geom = shape(geojson_data["geometry"])
            actual_type = geom.geom_type
        else:
            actual_type = geojson_data["type"]
            if actual_type in ["Polygon", "MultiPolygon"]:
                geom = shape(geojson_data)
            elif actual_type == "Point":
                try:
                    rep_area = float(area.get("reported_area")) if area.get("reported_area") is not None else np.nan
                except Exception:
                    rep_area = np.nan
                if not np.isnan(rep_area) and rep_area > 0:
                    radius = (rep_area / 3.14159) ** 0.5 * 1000  # in meters
                else:
                    radius = 1000  # default buffer size in meters
                point_geom = shape(geojson_data)
                gdf_point = gpd.GeoDataFrame(geometry=[point_geom], crs="EPSG:4326")
                gdf_point = gdf_point.to_crs('+proj=moll +lon_0=0 +datum=WGS84 +units=m +no_defs')
                buffered_geom = gdf_point.buffer(radius).iloc[0]
                buffered_geom = gpd.GeoSeries([buffered_geom],
                                              crs='+proj=moll +lon_0=0 +datum=WGS84 +units=m +no_defs').to_crs(
                    "EPSG:4326").iloc[0]
                geom = buffered_geom
            else:
                print(f"Skipping area with unknown geometry type: {actual_type}")
                continue

        processed_features.append({
            "id": area.get("id"),
            "name": area.get("name"),
            "wdpa_id": area.get("wdpa_id"),
            "reported_area": area.get("reported_area"),
            "designation": area.get("designation"),
            "legal_status": area.get("legal_status"),
            "geometry": geom
        })

    if processed_features:
        gdf = gpd.GeoDataFrame(processed_features, geometry="geometry", crs="EPSG:4326")
        return gdf
    else:
        print("No features found in API response.")
        return None


def load_shapefile(file_path):
    """
    Loads a shapefile by temporarily changing to its directory.
    """
    print(f"Loading shapefile: {file_path}")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    original_dir = os.getcwd()
    try:
        shapefile_dir = os.path.dirname(file_path)
        shapefile_name = os.path.basename(file_path)
        os.chdir(shapefile_dir)
        print(f"Changed directory to: {os.getcwd()}")
        gdf = gpd.read_file(shapefile_name)
        print(f"Successfully loaded {len(gdf)} features from {file_path}")
        return gdf
    finally:
        os.chdir(original_dir)
        print(f"Changed back to original directory: {os.getcwd()}")


def fix_invalid_geometries(gdf):
    """
    Fixes invalid geometries using a zero-width buffer.
    """
    gdf["geometry"] = gdf.geometry.apply(lambda geom: geom if geom.is_valid else geom.buffer(0))
    return gdf


def convert_geometry(geom):
    """
    Converts a GeometryCollection into a MultiPolygon if possible.
    """
    if geom is None:
        return None
    if geom.geom_type == "GeometryCollection":
        polygons = [g for g in geom.geoms if g.geom_type in ["Polygon", "MultiPolygon"]]
        if not polygons:
            return None
        elif len(polygons) == 1:
            return polygons[0]
        else:
            return MultiPolygon(polygons)
    return geom


def filter_api_protected_areas(protected_areas):
    """
    Filters out records where the designation or legal_status name is "Proposed".
    """
    print("Filtering API protected areas based on designation and legal_status...")
    original_count = len(protected_areas)
    protected_areas["designation_name"] = protected_areas["designation"].apply(
        lambda d: d.get("name") if isinstance(d, dict) else None)
    protected_areas["legal_status_name"] = protected_areas["legal_status"].apply(
        lambda d: d.get("name") if isinstance(d, dict) else None)
    filtered = protected_areas[
        (protected_areas["designation_name"] != "Proposed") &
        (protected_areas["legal_status_name"] != "Proposed")
        ]
    print(f"Filtered protected areas: {original_count} -> {len(filtered)}")
    return filtered


def filter_protected_areas(protected_areas):
    return filter_api_protected_areas(protected_areas)


def flatten_protected_areas(protected_areas):
    """
    Dissolves (flattens) the protected areas to eliminate overlaps.
    """
    print("Fixing invalid geometries if necessary...")
    protected_areas = fix_invalid_geometries(protected_areas)
    print("Flattening protected areas to eliminate overlaps...")
    protected_areas['dissolve_id'] = 1
    flat_pas = protected_areas.dissolve(by='dissolve_id')
    print(f"Flattened {len(protected_areas)} features into {len(flat_pas)} non-overlapping geometries")
    flat_pas["geometry"] = flat_pas.geometry.apply(convert_geometry)
    return flat_pas


def calculate_protected_area_coverage(admin_boundaries, protected_areas, id_field, name_field=None, level='country'):
    """
    Calculates the percentage of each administrative unit covered by protected areas.

    For ADM0 (level=='country'): Sums the area of all admin boundaries and all protected areas
    using the Mollweide projection.

    For ADM1/ADM2, a spatial overlay (intersection) is used.
    """
    proj_moll = '+proj=moll +lon_0=0 +datum=WGS84 +units=m +no_defs'
    if level == 'country':
        print("Calculating country-level (ADM0) coverage by summing areas using Mollweide projection.")
        total_area = admin_boundaries.to_crs(proj_moll).area.sum() / 1_000_000
        protected_area = protected_areas.to_crs(proj_moll).area.sum() / 1_000_000
        protected_percentage = (protected_area / total_area) * 100
        print(f"Total area (km²): {total_area:.2f}")
        print(f"Protected area (km²): {protected_area:.2f}")
        print(f"Protected percentage: {round(protected_percentage, 2)}%")
        data = {
            id_field: [admin_boundaries.iloc[0][id_field] if id_field in admin_boundaries.columns else ""]
        }
        if name_field in admin_boundaries.columns:
            data[name_field] = [admin_boundaries.iloc[0][name_field]]
        else:
            data[name_field] = [""]
        data.update({
            "total_area_km2": [total_area],
            "protected_area_km2": [protected_area],
            "protected_percentage": [round(protected_percentage, 2)]
        })
        country_boundary = admin_boundaries.unary_union
        result = gpd.GeoDataFrame(data, geometry=[country_boundary], crs=admin_boundaries.crs)
        summary = result.copy()
        return result, summary
    else:
        print(f"Calculating protected area coverage for {len(admin_boundaries)} {level} boundaries using overlay.")
        result = admin_boundaries.copy()
        if protected_areas.crs != result.crs:
            result = result.to_crs(protected_areas.crs)
        result['total_area_km2'] = result.geometry.to_crs(proj_moll).area / 1_000_000
        intersections = gpd.overlay(result, protected_areas, how='intersection')
        intersections['protected_area_km2'] = intersections.geometry.to_crs(proj_moll).area / 1_000_000
        if id_field in intersections.columns:
            protected_totals = intersections.groupby(id_field)['protected_area_km2'].sum().reset_index()
            result = result.merge(protected_totals, on=id_field, how='left')
        else:
            result['protected_area_km2'] = 0
        result['protected_area_km2'] = result['protected_area_km2'].fillna(0)
        result['protected_percentage'] = (result['protected_area_km2'] / result['total_area_km2']) * 100
        result['protected_percentage'] = result['protected_percentage'].round(2)
        if name_field and name_field in result.columns:
            summary_fields = [id_field, name_field, 'total_area_km2', 'protected_area_km2', 'protected_percentage']
        else:
            summary_fields = [id_field, 'total_area_km2', 'protected_area_km2', 'protected_percentage']
        summary = result[summary_fields].sort_values(by='protected_percentage', ascending=False)
        return result, summary


def save_results(gdf, output_path, change_dir=True):
    """
    Saves a GeoDataFrame as a shapefile.
    """
    print(f"Saving results to: {output_path}")
    if change_dir:
        original_dir = os.getcwd()
        try:
            output_dir = os.path.dirname(output_path)
            output_filename = os.path.basename(output_path)
            os.makedirs(output_dir, exist_ok=True)
            os.chdir(output_dir)
            gdf.to_file(output_filename)
            print(f"Successfully saved to {output_path}")
        finally:
            os.chdir(original_dir)
            print(f"Changed back to original directory: {os.getcwd()}")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        gdf.to_file(output_path)
        print(f"Successfully saved to {output_path}")


# Global accumulators for CSV rows from all countries
global_adm0 = []
global_adm1 = []
global_adm2 = []


def process_country(country_code, project_dir, output_dir):
    """
    Processes one country:
      1) Fetch API protected areas (all pages),
      2) Filter and flatten,
      3) Load admin boundaries,
      4) For ADM0: combine all admin boundaries using unary_union,
      5) Calculate coverage,
      6) Save shapefiles and accumulate CSV rows.
    """
    print("\n" + "=" * 60)
    print(f"Processing country: {country_code}")
    print("=" * 60)

    # STEP 1: Fetch API protected areas
    api_protected_areas = fetch_api_protected_areas(country_code)
    if api_protected_areas is None or api_protected_areas.empty:
        print(f"No protected area data available from API for {country_code}. Skipping...")
        return

    # STEP 2: Filter API data
    filtered_pas = filter_protected_areas(api_protected_areas)

    # STEP 3: Flatten protected areas
    flat_pas = flatten_protected_areas(filtered_pas)
    country_output_dir = os.path.join(output_dir, country_code)
    os.makedirs(country_output_dir, exist_ok=True)
    flat_pas_file = os.path.join(country_output_dir, "flattened_protected_areas.shp")
    save_results(flat_pas, flat_pas_file)

    # STEP 4: Load admin boundaries
    adm_folder = os.path.join(project_dir, f"{country_code}_shapefiles")
    adm0_file = os.path.join(adm_folder, f"{country_code}_shp_0", f"gadm41_{country_code}_0.shp")
    adm1_file = os.path.join(adm_folder, f"{country_code}_shp_1", f"gadm41_{country_code}_1.shp")
    adm2_file = os.path.join(adm_folder, f"{country_code}_shp_2", f"gadm41_{country_code}_2.shp")
    print(f"Loading admin boundaries for {country_code} from {adm_folder}")
    try:
        adm0 = load_shapefile(adm0_file)
        adm1 = load_shapefile(adm1_file)
        adm2 = load_shapefile(adm2_file)
    except FileNotFoundError as e:
        print(f"Error loading admin boundaries for {country_code}: {e}")
        return

    # STEP 4b: For ADM0, combine all territories using unary_union.
    country_boundary = adm0.unary_union
    # Use the country code as the level0_code and (if available) the country name from a NAME_0 field.
    country_name = adm0.iloc[0]["NAME_0"] if "NAME_0" in adm0.columns else ""
    adm0 = gpd.GeoDataFrame({
        "GID_0": [country_code]
    }, geometry=[country_boundary], crs=adm0.crs)
    # We add the country name as an extra field for later use.
    adm0["NAME_0"] = country_name

    # STEP 5: Calculate coverage at each admin level
    adm0_id_field = "GID_0"
    adm0_name_field = "NAME_0"
    adm1_id_field = "GID_1"  # from overlay for provinces
    adm1_name_field = "NAME_1"
    adm2_id_field = "GID_2"  # from overlay for districts
    adm2_name_field = "NAME_2"

    adm0_result, adm0_summary = calculate_protected_area_coverage(adm0, flat_pas, adm0_id_field, adm0_name_field,
                                                                  level='country')
    adm1_result, adm1_summary = calculate_protected_area_coverage(adm1, flat_pas, adm1_id_field, adm1_name_field,
                                                                  level='province')
    adm2_result, adm2_summary = calculate_protected_area_coverage(adm2, flat_pas, adm2_id_field, adm2_name_field,
                                                                  level='district')

    # STEP 5b: Save the coverage shapefiles
    save_results(adm0_result, os.path.join(country_output_dir, "adm0_protected_areas.shp"))
    save_results(adm1_result, os.path.join(country_output_dir, "adm1_protected_areas.shp"))
    save_results(adm2_result, os.path.join(country_output_dir, "adm2_protected_areas.shp"))

    # STEP 6: Build CSV rows with the following columns:
    # country_wb, geo_level, level0_code, level0_name, level1_code, level1_name, level2_code, level2_name, indicator, indicator_label, value, year

    # ADM0 (Country)
    adm0_rows = pd.DataFrame({
        "country_wb": [country_code],
        "geo_level": [0],
        "level0_code": [country_code],
        "level0_name": [country_name],
        "level1_code": [""],
        "level1_name": [""],
        "level2_code": [""],
        "level2_name": [""],
        "indicator": [""],
        "indicator_label": [""],
        "value": [adm0_result.iloc[0]["protected_percentage"]],
        "year": [""]
    })
    global global_adm0
    global_adm0.append(adm0_rows)

    # ADM1 (Province) – use overlay result columns
    adm1_rows = adm1_result.copy()
    # Create new columns using the overlay fields
    adm1_rows = adm1_rows.assign(
        country_wb=country_code,
        geo_level=1,
        level0_code=adm1_rows["GID_0"],
        level0_name=country_name,
        level1_code=adm1_rows["GID_1"],
        level1_name=adm1_rows["NAME_1"],
        level2_code="",
        level2_name="",
        indicator="",
        indicator_label="",
        value=adm1_rows["protected_percentage"],
        year=""
    )
    # Select only the required columns
    adm1_rows = adm1_rows[["country_wb", "geo_level", "level0_code", "level0_name",
                           "level1_code", "level1_name", "level2_code", "level2_name",
                           "indicator", "indicator_label", "value", "year"]]
    global global_adm1
    global_adm1.append(adm1_rows)

    # ADM2 (District) – use overlay result columns
    adm2_rows = adm2_result.copy()
    adm2_rows = adm2_rows.assign(
        country_wb=country_code,
        geo_level=2,
        level0_code=adm2_rows["GID_0"],
        level0_name=country_name,
        level1_code=adm2_rows["GID_1"],
        level1_name=adm2_rows["NAME_1"],
        level2_code=adm2_rows["GID_2"],
        level2_name=adm2_rows["NAME_2"],
        indicator="",
        indicator_label="",
        value=adm2_rows["protected_percentage"],
        year=""
    )
    adm2_rows = adm2_rows[["country_wb", "geo_level", "level0_code", "level0_name",
                           "level1_code", "level1_name", "level2_code", "level2_name",
                           "indicator", "indicator_label", "value", "year"]]
    global global_adm2
    global_adm2.append(adm2_rows)

    print(f"Finished processing {country_code}.\n")


def main():
    project_dir = "/Users/awfasano/PycharmProjects/Protected-Planet-Regional-Calculations"
    output_dir = os.path.join(project_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    countries = ["AFG", "BGD", "BTN", "IND", "LKA", "MDV", "NPL", "PAK"]

    for country in countries:
        process_country(country, project_dir, output_dir)

    if global_adm0:
        df_adm0 = pd.concat(global_adm0, ignore_index=True)
        adm0_csv_path = os.path.join(output_dir, "all_adm0_export.csv")
        df_adm0.to_csv(adm0_csv_path, index=False)
        print(f"Exported ADM0 CSV to: {adm0_csv_path}")

    if global_adm1:
        df_adm1 = pd.concat(global_adm1, ignore_index=True)
        adm1_csv_path = os.path.join(output_dir, "all_adm1_export.csv")
        df_adm1.to_csv(adm1_csv_path, index=False)
        print(f"Exported ADM1 CSV to: {adm1_csv_path}")

    if global_adm2:
        df_adm2 = pd.concat(global_adm2, ignore_index=True)
        adm2_csv_path = os.path.join(output_dir, "all_adm2_export.csv")
        df_adm2.to_csv(adm2_csv_path, index=False)
        print(f"Exported ADM2 CSV to: {adm2_csv_path}")

    print("Analysis complete for all countries. Check the output directory for results.")


if __name__ == "__main__":
    main()
