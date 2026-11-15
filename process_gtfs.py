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
        calendar_dates = pd.read_csv(z.open('calendar_dates.txt'), dtype=str)

    # 1. ZISTÍME DNEŠNÝ DÁTUM A DEŇ V TÝŽDNI
    dnes_datum = datetime.now().strftime('%Y%m%d')  # napr. '20261117'
    dnes_den = datetime.now().strftime('%A').lower() # napr. 'tuesday'
    print(f"Dnes je {dnes_den} ({dnes_datum}). Filtrujem spoje.")

    # 2. ZÁKLADNÝ ZOZNAM SLUŽIEB Z CALENDAR.TXT
    # Vyberieme služby, ktoré podľa týždenného kalendára dnes majú ísť
    # a zároveň ich platnosť (start_date, end_date) zahŕňa dnešný dátum
    zakladne_sluzby = calendar[
        (calendar[dnes_den] == '1') &
        (calendar['start_date'] <= dnes_datum) &
        (calendar['end_date'] >= dnes_datum)
    ]['service_id'].tolist()

    # 3. APLIKUJEME VÝNIMKY Z CALENDAR_DATES.TXT
    # Výnimky pre dnešný dátum
    dnesne_vyimky = calendar_dates[calendar_dates['date'] == dnes_datum]

    # Služby, ktoré dnes NEJDÚ (exception_type == '2')
    odstavene_sluzby = dnesne_vyimky[dnesne_vyimky['exception_type'] == '2']['service_id'].tolist()

    # Služby, ktoré dnes IDÚ (exception_type == '1')
    pridane_sluzby = dnesne_vyimky[dnesne_vyimky['exception_type'] == '1']['service_id'].tolist()

    # Výsledný zoznam aktívnych služieb
    aktivne_sluzby = set(zakladne_sluzby) - set(odstavene_sluzby) | set(pridane_sluzby)

    if not aktivne_sluzby:
        print("Dnes nepremáva žiadna služba.")
        return

    # 4. VYFILTRUJEME SPOJE (TRIPS) LEN PRE AKTÍVNE SLUŽBY
    dnesne_trips = trips[trips['service_id'].isin(aktivne_sluzby)].copy()

    print(f"Hľadám spoje pre zastávky: {STOP_IDS}...")
    # 5. Nájdeme odchody pre naše zastávky
    my_stop_times = stop_times[stop_times['stop_id'].isin(STOP_IDS)].copy()
    
    # 6. Vyfiltrujeme len časy medzi 07:00 a 21:00
    my_stop_times = my_stop_times[
        (my_stop_times['departure_time'] >= '07:00:00') & 
        (my_stop_times['departure_time'] <= '21:00:00')
    ]

    # 7. Spojíme to dokopy
    my_trips = pd.merge(my_stop_times, dnesne_trips, on='trip_id', how='inner')
    my_trips = pd.merge(my_trips, routes, on='route_id', how='left')

    # 8. Odstránime duplicity
    my_trips = my_trips.drop_duplicates(subset=['route_short_name', 'trip_headsign', 'departure_time'])

    # 9. Zoradíme podľa času
    my_trips = my_trips.sort_values(by='departure_time')

    # 10. Vytvoríme JSON
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
