import requests
import json
import time

API_KEY = "15514395b80ee101b6bcdee785a6445a"
BASE_URL = "https://api.protectedplanet.net/v3/protected_areas"
OUTPUT_FILE = "all_protected_areas_with_geojson135.json"
## don't run unless you want all the data to be returned. It takes like an hour.

def fetch_all_protected_areas():
    all_data = []
    page = 135
    per_page = 50

    while True:
        print(f"📦 Fetching page {page}...")
        params = {
            "with_geometry": "true",
            "per_page": per_page,
            "page": page,
            "token": API_KEY
        }

        response = requests.get(BASE_URL, params=params)
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}")
            print(response.text)
            break

        page_data = response.json().get("protected_areas", [])
        if not page_data:
            break

        all_data.extend(page_data)
        if len(page_data) < per_page:
            break

        page += 1
        time.sleep(0.5)  # Be kind to the API

    print(f"\n✅ Downloaded {len(all_data)} protected areas.")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"📁 Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_all_protected_areas()
