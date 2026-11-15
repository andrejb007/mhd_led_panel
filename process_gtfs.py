import zipfile
import io
import json
import requests
import pandas as pd
from datetime import datetime

# --- KONFIGURÁCIA ---
STOP_IDS = [
    "000000023400003", # zastavka C
    "000000023400001", # zastavka A
]
GTFS_URL = "https://www.arcgis.com/sharing/rest/content/items/aba12fd2cbac4843bc7406151bc66106/data"
OUTPUT_FILE = "odchody.json"

def main():
    print("Sťahujem GTFS dáta...")
    response = requests.get(GTFS_URL)
    response.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        stop_times = pd.read_csv(z.open('stop_times.txt'), dtype=str)
        trips = pd.read_csv(z.open('trips.txt'), dtype=str)
        routes = pd.read_csv(z.open('routes.txt'), dtype=str)
        calendar = pd.read_csv(z.open('calendar.txt'), dtype=str)

    # 1. ZISTÍME AKTUÁLNY DEŇ
    # Zistíme, aký je dnes deň (napr. 'monday', 'tuesday' atď.)
    dnes = datetime.now().strftime('%A').lower()
    print(f"Dnes je {dnes}. Filtrujem spoje len pre tento deň.")

    # 2. NÁJDEME SLUŽBY (SERVICE_ID), KTORÉ DNES PREMÁVAJÚ
    # V súbore calendar.txt hľadáme riadky, kde je pre dnešný deň jednotka ('1')
    dnesne_sluzby = calendar[calendar[dnes] == '1']['service_id'].tolist()
    
    # 3. VYFILTRUJEME SPOJE (TRIPS) LEN PRE DNEŠNÉ SLUŽBY
    dnesne_trips = trips[trips['service_id'].isin(dnesne_sluzby)].copy()

    print("Hľadám spoje pre zastávky...")
    # 4. Nájdeme odchody pre naše zastávky
    my_stop_times = stop_times[stop_times['stop_id'].isin(STOP_IDS)].copy()
    
    # 5. Vyfiltrujeme len časy medzi 07:00 a 21:00
    my_stop_times = my_stop_times[
        (my_stop_times['departure_time'] >= '07:00:00') & 
        (my_stop_times['departure_time'] <= '21:00:00')
    ]

    # 6. Spojíme to dokopy (a aplikujeme filter dnešných spojov)
    my_trips = pd.merge(my_stop_times, dnesne_trips, on='trip_id', how='inner')
    my_trips = pd.merge(my_trips, routes, on='route_id', how='left')

    # 7. Odstránime duplicity
    my_trips = my_trips.drop_duplicates(subset=['route_short_name', 'trip_headsign', 'departure_time'])

    # 8. Zoradíme podľa času
    my_trips = my_trips.sort_values(by='departure_time')

    # 9. Vytvoríme JSON
    vysledky = []
    for _, row in my_trips.iterrows():
        vysledky.append({
            "linka": row['route_short_name'],
            "smer": row['trip_headsign'],
            "cas": row['departure_time']
        })

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(vysledky, f, ensure_ascii=False, indent=2)

    print(f"Hotovo! Uložených {len(vysledky)} odchodov pre dnešný deň do {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
