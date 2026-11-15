import zipfile
import io
import json
import requests
import pandas as pd

# --- KONFIGURÁCIA ---
STOP_ID = "000000023400001" # Líščie nivy
GTFS_URL = "https://www.arcgis.com/sharing/rest/content/items/aba12fd2cbac4843bc7406151bc66106/data"
OUTPUT_FILE = "odchody.json"

def main():
    print("Sťahujem GTFS dáta...")
    response = requests.get(GTFS_URL)
    response.raise_for_status()

    print("Rozbaľujem a spracovávam dáta...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        stop_times = pd.read_csv(z.open('stop_times.txt'), dtype=str)
        trips = pd.read_csv(z.open('trips.txt'), dtype=str)
        routes = pd.read_csv(z.open('routes.txt'), dtype=str)

    print(f"Hľadám spoje pre zastávku {STOP_ID}...")
    
    # 1. Nájdeme všetky spoje pre našu zastávku
    my_stop_times = stop_times[stop_times['stop_id'] == STOP_ID].copy()
    
    if my_stop_times.empty:
        print("Pre túto zastávku neboli nájdené žiadne spoje.")
        return

    # 2. Vyfiltrujeme len časy medzi 07:00 a 21:00
    # Keďže sú časy uložené ako stringy (napr. "07:15:00"), môžeme ich porovnávať abecedne
    my_stop_times = my_stop_times[
        (my_stop_times['departure_time'] >= '07:00:00') & 
        (my_stop_times['departure_time'] <= '21:00:00')
    ]

    # 3. Spojíme s informáciami o linke a smere
    my_trips = pd.merge(my_stop_times, trips, on='trip_id', how='left')
    my_trips = pd.merge(my_trips, routes, on='route_id', how='left')

    # 4. Zoradíme podľa času odchodu
    my_trips = my_trips.sort_values(by='departure_time')

    # 5. Vytvoríme zoznam výsledkov
    vysledky = []
    for _, row in my_trips.iterrows():
        vysledky.append({
            "linka": row['route_short_name'],
            "smer": row['trip_headsign'],
            "cas": row['departure_time'] # napr. "14:35:00"
        })

    # Uložíme do JSON súboru
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(vysledky, f, ensure_ascii=False, indent=2)

    print(f"Hotovo! Uložených {len(vysledky)} odchodov do {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
