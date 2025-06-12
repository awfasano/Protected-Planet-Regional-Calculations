### Summary

This code calculates protected area coverage at national (ADM0), state (ADM1), and district (ADM2) levels by combining data from the Protected Planet API and GADM administrative boundaries. It fetches, processes, and buffers geometries, handles overlaps, and uses the Mollweide projection for accurate area measurement before exporting results as shapefiles and CSVs.  

World Bank National Indicator and Methodology
https://scorecard.worldbank.org/en/data/indicator-detail/ER_LND_HEAL?orgCode=ALL&refareatype=REGION&refareacode=ACW&age=_T&disability=_T&sex=_T


### File Descriptions

- `regionProtectedPlanetDraft.py`  
  Main script that retrieves protected area data from the Protected Planet API, processes it with GADM boundary shapefiles (ADM0–ADM2), and calculates protected area coverage. Outputs shapefiles and CSVs.

- `testingProtectedPlanet.py`  
  Entry point script that calls `process_country()` for each country, manages output structure, and exports global CSV files (`all_adm0_export.csv`, `all_adm1_export.csv`, `all_adm2_export.csv`).

- `output/`  
  Folder containing country-specific subfolders with shapefiles and CSVs of protected area coverage results at ADM0, ADM1, and ADM2 levels.

- `output/all_adm0_export.csv`  
  Aggregated CSV showing national-level (ADM0) protected area percentages for all processed countries.

- `output/all_adm1_export.csv`  
  Aggregated CSV showing state/province-level (ADM1) protected area percentages.

- `output/all_adm2_export.csv`  
  Aggregated CSV showing district-level (ADM2) protected area percentages.

- `[CountryCode]_shapefiles/`  
  Directory containing administrative boundary shapefiles for each country:
  - `[CountryCode]_shp_0/` – ADM0 (national) boundaries
  - `[CountryCode]_shp_1/` – ADM1 (state/province) boundaries
  - `[CountryCode]_shp_2/` – ADM2 (district) boundaries
