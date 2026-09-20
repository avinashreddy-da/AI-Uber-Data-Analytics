import os
import sqlite3
import pandas as pd

def build_sqlite_database(csv_path: str, db_path: str) -> None:
    """
    Creates an SQLite database from the cleaned Uber rides CSV:
    - Loads all 150,000 records from uber_rides_cleaned.csv.
    - Writes records to the 'rides' table.
    - Creates indexes on 'Booking ID' and 'Pickup Location' for fast queries.
    - Verifies row count.
    """
    print(f"Reading cleaned dataset from: {csv_path}")
    df = pd.read_csv(csv_path)

    print(f"Connecting to SQLite database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Writing records to 'rides' table...")
    df.to_sql(name="rides", con=conn, if_exists="replace", index=False)

    print("Creating indexes on 'Booking ID' and 'Pickup Location'...")
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rides_booking_id ON rides("Booking ID");')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rides_pickup_location ON rides("Pickup Location");')
    conn.commit()

    # Verification: Count rows
    cursor.execute("SELECT COUNT(*) FROM rides;")
    total_rows = cursor.fetchone()[0]

    # Verification: Check indexes created
    cursor.execute("PRAGMA index_list(rides);")
    indexes = cursor.fetchall()

    conn.close()

    print("\n--- DATABASE VERIFICATION ---")
    print(f"Total Rows in 'rides' table: {total_rows:,}")
    print(f"Indexes on 'rides' table: {len(indexes)}")
    for idx in indexes:
        print(f"  - Index Name: {idx[1]} (Unique: {bool(idx[2])})")


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    cleaned_csv = os.path.join(base_dir, "data", "uber_rides_cleaned.csv")
    database_file = os.path.join(base_dir, "data", "uber_rides.db")

    build_sqlite_database(cleaned_csv, database_file)
