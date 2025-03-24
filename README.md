# Protected Planet Administrative Coverage Analysis

> ⚠️ *Note:*  
> I am currently working on getting the ADM0 results to match the ADM0 totals shown on the [Protected Planet website](https://www.protectedplanet.net/) — for India, Bangladesh, and Pakistan.  
> I believe the mismatch is related to **disputed or independent territories** not being returned when you use the search api with the country parameter.  The number of protected areas does match what is on the website.
> This issue hopefully **should not impact ADM1 or ADM2 calculations**, but I'm actively investigating to ensure consistency at all levels. 

This repository contains a Python script that retrieves protected area data from the Protected Planet API, processes it alongside local administrative boundary data (ADM0, ADM1, and ADM2) from GADM, calculates the percentage of area protected at each level, and exports the results as both shapefiles and CSV files.

## Overview

The script performs the following main tasks:

1. **Fetch Protected Areas from the API:**  
   It uses the `/v3/protected_areas/search` endpoint to obtain protected area records for a given country (using the three-letter ISO code). The script handles pagination (up to 50 records per page) to ensure all data are fetched.

2. **Buffering of Point Geometries:**  
   Some protected areas are provided as point features. In those cases, the script calculates a buffer around the point. The buffer radius is computed from the reported area using the formula:  
   ```
   radius (m) = sqrt(reported_area (km²) / π) * 1000
   ```
   To ensure accurate buffering (in meters), the point is reprojected into the Mollweide projection (an equal‑area projection), buffered, and then reprojected back to EPSG:4326.

3. **Loading Administrative Boundaries:**  
   Local shapefiles containing ADM0, ADM1, and ADM2 boundaries are loaded from a structured directory (one folder per country).

4. **Flattening Protected Areas:**  
   To remove overlaps, the script dissolves (flattens) all protected area geometries into one non‑overlapping geometry.

5. **Calculating Protected Area Coverage:**  
   - **ADM0 (Country-Level):**  
     Instead of using a spatial union (which may miss independent territories), the script sums the areas of all admin boundary features to form the denominator and sums the areas of all protected areas (from the flattened dataset) for the numerator. All area calculations are done in the Mollweide projection.
   - **ADM1 & ADM2:**  
     For subnational levels, the script uses an overlay (intersection) approach to calculate the protected area within each administrative unit.

6. **Exporting Results:**  
   - **Shapefiles:** The script writes the resulting coverage layers for ADM0, ADM1, and ADM2 to separate shapefiles.
   - **CSV Files:** It also accumulates key fields (country code, administrative level, names, and protected percentage) into CSV files. After processing all countries, three global CSV files are generated:
     - `all_adm0_export.csv`
     - `all_adm1_export.csv`
     - `all_adm2_export.csv`

7. **Using the Mollweide Projection:**  
   The script reprojects data to the Mollweide projection (`+proj=moll +lon_0=0 +datum=WGS84 +units=m +no_defs`) for accurate area measurements and buffer calculations.

## Detailed Code Breakdown

### 1. Fetching Protected Areas

- **Function:** `fetch_api_protected_areas(country_code)`
- **Process:**  
  - Uses a loop with pagination (50 records per page) to call the Protected Planet API.
  - Extracts geometries from the returned JSON.
  - For point features, it calculates a buffer based on the reported area.
- **Output:** A GeoDataFrame with protected area features in EPSG:4326.

### 2. Loading Administrative Boundaries

- **Function:** `load_shapefile(file_path)`
- **Process:**  
  - Temporarily changes the working directory to reliably load a shapefile.
- **Output:** A GeoDataFrame containing the administrative boundaries.

### 3. Fixing and Converting Geometries

- **Function:** `fix_invalid_geometries(gdf)`  
  Fixes any invalid geometries using a zero‑width buffer.
- **Function:** `convert_geometry(geom)`  
  Converts GeometryCollections into MultiPolygons if they contain only polygonal parts.

### 4. Filtering Protected Areas

- **Function:** `filter_api_protected_areas(protected_areas)`  
  Filters out records where the protected area designation or legal status is “Proposed.”
  
### 5. Flattening Protected Areas

- **Function:** `flatten_protected_areas(protected_areas)`  
  Fixes invalid geometries and dissolves overlapping protected area features into one unified geometry.

### 6. Calculating Protected Area Coverage

- **Function:** `calculate_protected_area_coverage(admin_boundaries, protected_areas, id_field, name_field=None, level='country')`
- **For ADM0 (Country-Level):**  
  - Instead of a spatial union (which might miss independent territories), the script sums the areas of all admin boundary features (denom.) and the areas of all protected areas (numerator) using the Mollweide projection.
  - Additional print statements display the total area, protected area, and the resulting protected percentage.
- **For ADM1/ADM2:**  
  - Uses a spatial overlay (intersection) approach to calculate areas within each administrative unit.

### 7. Saving Shapefiles

- **Function:** `save_results(gdf, output_path, change_dir=True)`  
  Saves a GeoDataFrame to a shapefile at the specified output path.

### 8. Processing Each Country

- **Function:** `process_country(country_code, project_dir, output_dir)`
- **Steps:**  
  1. Fetch and process protected area data.
  2. Filter and flatten the protected area geometries.
  3. Load the administrative boundary shapefiles.
  4. For ADM0, combine all territories using `unary_union` (or, as an alternative, sum their areas).
  5. Calculate protected area coverage for ADM0, ADM1, and ADM2.
  6. Save the resulting shapefiles.
  7. Build CSV rows with the following columns:
     - `country_wb`: Three-letter ISO country code.
     - `geo_level`: 0 (ADM0), 1 (ADM1), or 2 (ADM2).
     - `level0_name`: Country name (from ADM0 data).
     - `level1_name`: ADM1 name (if applicable).
     - `level2_name`: ADM2 name (if applicable).
     - `value`: Protected area percentage.
  8. Append these rows to global accumulators.

### 9. Exporting Global CSV Files

- **In the `main()` function:**  
  After processing all countries, the global CSV accumulators are concatenated and exported as three CSV files:
  - `all_adm0_export.csv`
  - `all_adm1_export.csv`
  - `all_adm2_export.csv`

## How to Use the Script

1. **Project Structure:**  
   Organize your administrative boundary shapefiles in a folder structure like:
   ```
   [Project_Dir]/
       [CountryCode]_shapefiles/
           [CountryCode]_shp_0/  (ADM0 shapefiles)
           [CountryCode]_shp_1/  (ADM1 shapefiles)
           [CountryCode]_shp_2/  (ADM2 shapefiles)
   ```

2. **Configure Your API Token:**  
   Replace the placeholder API token in the script with your actual Protected Planet API token.

3. **Run the Script:**  
   From the command line, run:
   ```
   python testingProtectedPlanet.py
   ```

4. **Review the Output:**  
   - The script creates country-specific folders under an `output` directory containing the shapefiles.
   - Three global CSV files (`all_adm0_export.csv`, `all_adm1_export.csv`, `all_adm2_export.csv`) are created in the output directory.
   - Additional print statements display the intermediate calculations (total area, protected area, and protected percentage) for ADM0.

## Additional Notes

- **Buffering Points:**  
  For point-type protected areas, the script buffers them based on the reported area. This allows you to combine these with polygon data.

- **Projection:**  
  Reprojection to the Mollweide projection is necessary for accurate area and buffer calculations because EPSG:4326 (WGS84) uses degrees, which are not linear units.

- **Field Name Truncation:**  
  You might see warnings about field names being truncated when saving shapefiles. This is expected with the ESRI Shapefile format.

- **Independent Territories:**  
  The ADM0 calculation for country-level coverage sums the areas of all admin boundary features (including independent territories) and all protected areas, ensuring that nothing is omitted.

## References

- **Protected Planet API Documentation:** https://api.protectedplanet.net
- **Mollweide Projection:** https://proj.org/operations/projections/moll.html
- **Buffering & Area Calculation in GIS:** Visconti et al. (2013), Venter et al. (2014), Butchart et al. (2015), and the 2018 Protected Planet Report.
