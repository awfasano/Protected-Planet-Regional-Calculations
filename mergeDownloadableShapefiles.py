#!/usr/bin/env python

import os
import glob
import pandas as pd
import geopandas as gpd


def list_folder_contents(folder):
    """Prints the contents of a folder for debugging."""
    print(f"Contents of '{folder}':")
    for item in sorted(os.listdir(folder)):
        print("   ", item)


def merge_shapefiles(base_folder, subfolder_pattern, shp_filename, output_filename):
    """
    Searches for shapefiles within subfolders and merges them into a single GeoDataFrame.
    Prints out paths and folder contents to help verify the folder locations.

    Parameters:
        base_folder (str): The absolute path to the folder containing the subfolders.
        subfolder_pattern (str): The pattern matching the subfolder names (e.g., "AFG_shp_*").
        shp_filename (str): The name of the shapefile (e.g., "WDPA_WDOECM_Mar2025_Public_AFG_shp-polygons.shp").
        output_filename (str): The filename for the merged shapefile.
    """
    # Print the current working directory
    cwd = os.getcwd()
    print("Current working directory:", cwd)

    # Convert base folder to an absolute path and check if it exists
    base_folder_abs = os.path.abspath(base_folder)
    print("Looking for base folder at:", base_folder_abs)
    if not os.path.exists(base_folder_abs):
        raise Exception(f"Base folder '{base_folder_abs}' does not exist. Please check the folder path.")

    # Construct a search pattern for the shapefiles in the subfolders
    search_pattern = os.path.join(base_folder_abs, subfolder_pattern, shp_filename)
    print("Using search pattern:", search_pattern)

    shapefile_paths = glob.glob(search_pattern)

    if not shapefile_paths:
        print("No shapefiles were found. Please ensure that:")
        print(f"  1. The base folder '{base_folder_abs}' is correct.")
        print(f"  2. The subfolder names match the pattern '{subfolder_pattern}'.")
        print(f"  3. Each subfolder contains a file named '{shp_filename}'.")
        return

    print("Found the following shapefiles:")
    for path in shapefile_paths:
        absolute_path = os.path.abspath(path)
        print("  -", absolute_path)

        # List contents of the subfolder for debugging
        subfolder = os.path.dirname(absolute_path)
        list_folder_contents(subfolder)

    # Read each shapefile into a GeoDataFrame and collect them in a list
    gdf_list = []
    for shp_path in shapefile_paths:
        abs_shp_path = os.path.abspath(shp_path)
        print("Loading shapefile:", abs_shp_path)

        # Check if the .shp file exists (it should, since we found it)
        if not os.path.exists(abs_shp_path):
            print(f"ERROR: File {abs_shp_path} does not exist!")
            continue

        # Change to the directory containing the shapefile before reading it
        # This is the key fix - we'll work with local paths relative to the current directory
        original_dir = os.getcwd()
        shapefile_dir = os.path.dirname(abs_shp_path)
        shapefile_name = os.path.basename(abs_shp_path)

        try:
            # Change to the directory containing the shapefile
            os.chdir(shapefile_dir)
            print(f"Changed directory to: {os.getcwd()}")

            # Now read the file using just the filename (not the full path)
            try:
                gdf = gpd.read_file(shapefile_name, engine="pyogrio")
                print(f"Successfully loaded {shapefile_name} with pyogrio")
            except Exception as e:
                print(f"pyogrio read_file failed for {shapefile_name} with error: {e}")
                print("Trying with the 'fiona' engine...")
                try:
                    gdf = gpd.read_file(shapefile_name, engine="fiona")
                    print(f"Successfully loaded {shapefile_name} with fiona")
                except Exception as e2:
                    print(f"Fiona engine also failed for {shapefile_name} with error: {e2}")
                    os.chdir(original_dir)  # Make sure to change back
                    continue  # Skip this shapefile if it can't be read

            # Add to our list of GeoDataFrames
            gdf_list.append(gdf)

        finally:
            # Always change back to the original directory
            os.chdir(original_dir)
            print(f"Changed back to original directory: {os.getcwd()}")

    if not gdf_list:
        print("No shapefiles could be loaded. Exiting.")
        return

    # Merge all the GeoDataFrames into one using pd.concat
    print(f"Merging {len(gdf_list)} GeoDataFrames...")
    merged_gdf = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True), crs=gdf_list[0].crs)

    # Write the merged GeoDataFrame to a new shapefile
    # For the to_file method, changing directory is the safest approach with pyogrio/fiona
    output_dir = os.path.dirname(output_filename)
    output_basename = os.path.basename(output_filename)
    original_dir = os.getcwd()

    try:
        # First ensure we're in the right directory before writing
        print(f"Changing to output directory: {output_dir}")
        os.chdir(output_dir)
        print(f"Current directory (for writing): {os.getcwd()}")
        print(f"Writing merged shapefile as: {output_basename}")

        # Now write the file using just the basename
        merged_gdf.to_file(output_basename)
        print(f"Merged shapefile successfully written to: {os.path.join(output_dir, output_basename)}")
    finally:
        # Always return to original directory
        os.chdir(original_dir)
        print(f"Changed back to original directory: {os.getcwd()}")


if __name__ == "__main__":
    # Update this base folder path to where your AFG_shapefiles folder actually is.
    base_folder = "/Users/awfasano/PycharmProjects/ProtectPlanetADM!/AFG_shapefiles"

    # Subfolder names are of the pattern "AFG_shp_0", "AFG_shp_1", "AFG_shp_2"
    subfolder_pattern = "AFG_shp_*"

    # The name of the shapefile in each subfolder (all subfolders have a file with the same name)
    shp_filename = "WDPA_WDOECM_Mar2025_Public_AFG_shp-polygons.shp"

    # Define output directory - use the project base folder instead of current directory
    # This ensures we're writing to a known, accessible location
    project_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up from .venv
    output_dir = os.path.join(project_base, "output")

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir)

    # Output filename for the merged shapefile (in the output directory)
    output_filename = os.path.join(output_dir, "merged_polygons.shp")

    merge_shapefiles(base_folder, subfolder_pattern, shp_filename, output_filename)