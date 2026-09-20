import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("data/uber_rides.db")
CSV_PATH = Path("data/uber_rides_cleaned.csv")

# Load the verified cleaned CSV
df = pd.read_csv(CSV_PATH)

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