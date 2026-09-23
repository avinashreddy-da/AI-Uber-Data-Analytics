import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/uber_rides.db")
CSV_PATH = Path("data/uber_rides_cleaned.csv")

# Load the verified cleaned CSV
df = pd.read_csv(CSV_PATH)

# ---------------------------------------------------------
# Add 2024 Indian festival features
# ---------------------------------------------------------

festivals = {
    "2024-01-15": "Makar Sankranti",
    "2024-03-25": "Holi",
    "2024-04-11": "Eid al-Fitr",
    "2024-08-19": "Raksha Bandhan",
    "2024-08-26": "Janmashtami",
    "2024-09-07": "Ganesh Chaturthi",
    "2024-10-12": "Dussehra",
    "2024-10-31": "Diwali",
    "2024-11-15": "Guru Nanak Jayanti",
    "2024-12-25": "Christmas",
}

df["Pickup_DateTime"] = pd.to_datetime(
    df["Pickup_DateTime"]
)

df["Date"] = df["Pickup_DateTime"].dt.strftime(
    "%Y-%m-%d"
)

df["Festival_Name"] = df["Date"].map(festivals)

df["Is_Festival"] = df["Festival_Name"].notna().astype(int)

print(
    f"Festival rides: {df['Is_Festival'].sum():,}"
)

print(f"Cleaned CSV rows: {len(df):,}")
print(f"Cleaned CSV columns: {len(df.columns)}")

# Delete the incorrect/duplicated database
if DB_PATH.exists():
    DB_PATH.unlink()
    print("Old database deleted.")

# Create fresh database
conn = sqlite3.connect(DB_PATH)

# Load cleaned data into rides table
df.to_sql("rides", conn, if_exists="replace", index=False)

# Recreate indexes
conn.execute("""
    CREATE INDEX idx_rides_booking_id
    ON rides ("Booking ID")
""")

conn.execute("""
    CREATE INDEX idx_rides_pickup_location
    ON rides ("Pickup Location")
""")

# Verify row count
row_count = conn.execute(
    "SELECT COUNT(*) FROM rides"
).fetchone()[0]

print(f"\nDatabase rows: {row_count:,}")

# Verify booking status counts
print("\nBooking status counts:")

status_counts = conn.execute("""
    SELECT "Booking Status", COUNT(*)
    FROM rides
    GROUP BY "Booking Status"
    ORDER BY COUNT(*) DESC
""").fetchall()

for status, count in status_counts:
    print(f"{status}: {count:,}")

conn.close()

print("\nDatabase rebuild completed.")