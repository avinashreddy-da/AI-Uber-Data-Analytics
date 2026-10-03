import os
import re
import sqlite3
import pandas as pd
from math import radians, sin, cos, sqrt, atan2

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

CSV_PATH = os.path.join("data", "fairfare_ride_demand_dataset.csv")
ZONES_PATH = os.path.join("data", "mobilitylens_zones.csv")
DB_PATH = os.path.join("data", "mobilitylens.db")
MAIN_PATH = "main.py"
DATABASE_PATH = "database.py"

# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

df = pd.read_csv(CSV_PATH)
zones = pd.read_csv(ZONES_PATH)

print("\n" + "=" * 70)
print("1. DAY_OF_WEEK VALUES")
print("=" * 70)
print(df["Day_of_Week"].value_counts(dropna=False).sort_index())

print("\n" + "=" * 70)
print("2. DATE + DAY_OF_WEEK SAMPLE")
print("=" * 70)
print(df[["Date", "Day_of_Week"]].head(15).to_string(index=False))

print("\n" + "=" * 70)
print("3. HYDERABAD — HOUR 18 — DAY_OF_WEEK COUNTS")
print("=" * 70)

hyd_18 = df[
    (df["City"].astype(str).str.strip().str.lower() == "hyderabad")
    & (pd.to_numeric(df["Hour_of_Day"], errors="coerce") == 18)
]

print(
    hyd_18["Day_of_Week"]
    .value_counts(dropna=False)
    .sort_index()
)

print("\nTotal Hyderabad records at hour 18:", len(hyd_18))

print("\n" + "=" * 70)
print("4. DEMAND_LEVEL VALUES")
print("=" * 70)
print(df["Demand_Level"].value_counts(dropna=False))

# ------------------------------------------------------------
# Read exact zone settings from main.py WITHOUT importing it
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("5. MAIN.PY ZONE SETTINGS")
print("=" * 70)

main_text = open(MAIN_PATH, "r", encoding="utf-8").read()

match = re.search(
    r"ZONE_MAX_DISTANCE_KM\s*=\s*([0-9.]+)",
    main_text
)

if match:
    zone_limit = float(match.group(1))
    print("ZONE_MAX_DISTANCE_KM =", zone_limit)
else:
    zone_limit = 6.0
    print("Could not find ZONE_MAX_DISTANCE_KM in main.py")

bounds_match = re.search(
    r"CITY_BOUNDS\s*=\s*\{(.*?)\n\}",
    main_text,
    re.DOTALL
)

if bounds_match:
    bounds_text = bounds_match.group(1)
    hyd_match = re.search(
        r'["\']Hyderabad["\']\s*:\s*\(([^)]*)\)',
        bounds_text
    )

    if hyd_match:
        print("Hyderabad CITY_BOUNDS =", hyd_match.group(1))
    else:
        print("Could not extract Hyderabad CITY_BOUNDS")
else:
    print("Could not find CITY_BOUNDS in main.py")

# ------------------------------------------------------------
# Haversine
# ------------------------------------------------------------

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0

    lat1, lon1, lat2, lon2 = map(
        radians,
        [lat1, lon1, lat2, lon2]
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )

    return 2 * R * atan2(sqrt(a), sqrt(1 - a))

# ------------------------------------------------------------
# Madhapur zone
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("6. MADHAPUR ZONE / NEARBY RIDE CHECK")
print("=" * 70)

print("\nHyderabad zones containing 'Madhapur':")

madhapur_zones = zones[
    zones["zone"].astype(str).str.contains(
        "Madhapur",
        case=False,
        na=False
    )
]

print(madhapur_zones.to_string(index=False))

hyd = df[
    df["City"].astype(str).str.strip().str.lower() == "hyderabad"
].copy()

hyd["Latitude"] = pd.to_numeric(hyd["Latitude"], errors="coerce")
hyd["Longitude"] = pd.to_numeric(hyd["Longitude"], errors="coerce")

hyd = hyd.dropna(subset=["Latitude", "Longitude"])

print("\nHyderabad records with valid coordinates:", len(hyd))

if not madhapur_zones.empty:

    mz = madhapur_zones.iloc[0]

    distances = hyd.apply(
        lambda row: haversine_km(
            row["Latitude"],
            row["Longitude"],
            float(mz["lat"]),
            float(mz["lon"])
        ),
        axis=1
    )

    print("\nMadhapur zone coordinates:")
    print("Latitude :", mz["lat"])
    print("Longitude:", mz["lon"])

    print("\nClosest Hyderabad rides to Madhapur:")

    closest = hyd.copy()
    closest["Distance_KM_To_Madhapur"] = distances

    print(
        closest[
            [
                "City",
                "Latitude",
                "Longitude",
                "Hour_of_Day",
                "Day_of_Week",
                "Ride_Type",
                "Demand_Level",
                "Distance_KM_To_Madhapur",
            ]
        ]
        .sort_values("Distance_KM_To_Madhapur")
        .head(15)
        .to_string(index=False)
    )

    print(
        "\nHyderabad rides within",
        zone_limit,
        "km of Madhapur:",
        int((distances <= zone_limit).sum())
    )

# ------------------------------------------------------------
# Zone assignment approximation
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("7. HYDERABAD ZONE ASSIGNMENT COUNTS")
print("=" * 70)

hyd_zones = zones[
    zones["city"].astype(str).str.strip().str.lower() == "hyderabad"
].copy()

print("Number of Hyderabad demo zones:", len(hyd_zones))

if not hyd_zones.empty:

    assigned = []

    for _, row in hyd.iterrows():

        distances = hyd_zones.apply(
            lambda z: haversine_km(
                row["Latitude"],
                row["Longitude"],
                float(z["lat"]),
                float(z["lon"])
            ),
            axis=1
        )

        idx = distances.idxmin()
        nearest_distance = float(distances.loc[idx])

        if nearest_distance <= zone_limit:
            assigned.append(hyd_zones.loc[idx, "zone"])
        else:
            assigned.append(None)

    hyd["Assigned_Zone_Diagnostic"] = assigned

    print("\nAssigned Hyderabad rides by zone:")

    print(
        hyd["Assigned_Zone_Diagnostic"]
        .value_counts(dropna=False)
        .to_string()
    )

# ------------------------------------------------------------
# database.py functions
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("8. DATABASE.PY FUNCTIONS")
print("=" * 70)

database_text = open(DATABASE_PATH, "r", encoding="utf-8").read()

functions = re.findall(
    r"^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
    database_text,
    re.MULTILINE
)

for f in functions:
    print("-", f)

required = [
    "get_zone_context_sql",
    "get_city_context_sql",
    "read_sql",
    "get_connection",
    "database_available",
    "zoned_database_available",
]

print("\nRequired function check:")

for f in required:
    print(f"{f}: {'FOUND' if re.search(rf'^\s*def\s+{f}\s*\(', database_text, re.MULTILINE) else 'MISSING'}")

# ------------------------------------------------------------
# Database / zones timestamps
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("9. FILE TIMESTAMPS")
print("=" * 70)

for path in [ZONES_PATH, DB_PATH, CSV_PATH, MAIN_PATH, DATABASE_PATH]:

    if os.path.exists(path):

        stat = os.stat(path)

        print(
            f"{path:<45} "
            f"modified = {pd.to_datetime(stat.st_mtime, unit='s')}"
        )

    else:
        print(path, "NOT FOUND")

# ------------------------------------------------------------
# SQLite basic check
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("10. SQLITE CHECK")
print("=" * 70)

if os.path.exists(DB_PATH):

    conn = sqlite3.connect(DB_PATH)

    tables = pd.read_sql(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        conn
    )

    print("Tables:")
    print(tables.to_string(index=False))

    conn.close()

else:
    print("mobilitylens.db NOT FOUND")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE")
print("=" * 70)