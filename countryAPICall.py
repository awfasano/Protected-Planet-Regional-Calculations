import requests

API_KEY = "15514395b80ee101b6bcdee785a6445a"

def get_country_statistics(country_iso="IND"):
    url = f"https://api.protectedplanet.net/v3/countries/{country_iso}"
    params = {
        "with_geometry": "false",
        "token": API_KEY
    }
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print("Error:", response.status_code)
        print(response.text)
        return

    country = response.json().get("country", {})
    stats = country.get("statistics", {})

    print(f"\n📍 Country: {country.get('name')} ({country.get('iso_3')})")
    print(f"🌍 Land Area: {stats.get('land_area')} km²")
    print(f"🌊 Marine Area: {stats.get('marine_area')} km²")
    print(f"🛡️ Protected Land Area: {stats.get('pa_land_area')} km² ({stats.get('percentage_pa_land_cover')}%)")
    print(f"🛡️ Protected Marine Area: {stats.get('pa_marine_area')} km² ({stats.get('percentage_pa_marine_cover')}%)")
    print(f"🧾 Total Protected Areas: {country.get('pas_count')}")
    print(f"  - Polygon PAs: {stats.get('protected_area_polygon_count')}")
    print(f"  - Point PAs: {stats.get('protected_area_point_count')}")

get_country_statistics("IND")
