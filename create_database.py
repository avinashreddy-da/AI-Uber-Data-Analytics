import os
import sqlite3
import pandas as pd

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

CSV_PATH = os.path.join(
    "data",
    "fairfare_ride_demand_dataset.csv",
)

DB_PATH = os.path.join(
    "data",
    "mobilitylens.db",
)

TABLE_NAME = "rides"


# ------------------------------------------------------------
# Load CSV
# ------------------------------------------------------------

if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"FairFare CSV not found: {CSV_PATH}"
    )

df = pd.read_csv(CSV_PATH)

print(f"Loaded CSV: {df.shape[0]:,} rows, {df.shape[1]} columns")


# ------------------------------------------------------------
# Basic cleaning
# ------------------------------------------------------------

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce",
)

df["Event"] = (
    df["Event"]
    .fillna("No Event Recorded")
    .astype(str)
    .str.strip()
)

df["Weather"] = (
    df["Weather"]
    .fillna("Unknown")
    .astype(str)
    .str.strip()
)

df["City"] = (
    df["City"]
    .astype(str)
    .str.strip()
)

df["Day_of_Week"] = (
    df["Day_of_Week"]
    .astype(str)
    .str.strip()
)

df["Ride_Type"] = (
    df["Ride_Type"]
    .astype(str)
    .str.strip()
)


# ------------------------------------------------------------
# Create derived column
# ------------------------------------------------------------

df["Fare_Per_KM"] = (
    df["Final_Fare"]
    / df["Ride_Distance_KM"]
)

df.loc[
    df["Ride_Distance_KM"] <= 0,
    "Fare_Per_KM"
] = None


# ------------------------------------------------------------
# Create database folder if needed
# ------------------------------------------------------------

os.makedirs(
    os.path.dirname(DB_PATH),
    exist_ok=True,
)


# ------------------------------------------------------------
# Create SQLite database
# ------------------------------------------------------------

connection = sqlite3.connect(DB_PATH)

df.to_sql(
    TABLE_NAME,
    connection,
    if_exists="replace",
    index=False,
)


# ------------------------------------------------------------
# Verify
# ------------------------------------------------------------

row_count = connection.execute(
    f"SELECT COUNT(*) FROM {TABLE_NAME}"
).fetchone()[0]

city_count = connection.execute(
    f"SELECT COUNT(DISTINCT City) FROM {TABLE_NAME}"
).fetchone()[0]

cities = connection.execute(
    f"""
    SELECT City, COUNT(*) AS Records
    FROM {TABLE_NAME}
    GROUP BY City
    ORDER BY City
    """
).fetchall()

connection.close()


print()
print("Database created successfully.")
print(f"Database: {DB_PATH}")
print(f"Table: {TABLE_NAME}")
print(f"Rows: {row_count:,}")
print(f"Cities: {city_count}")
print()
print("City record counts:")

for city, records in cities:
    print(f"  {city}: {records:,}")