import os
import pandas as pd

def clean_uber_data(raw_csv_path: str, output_csv_path: str = None) -> pd.DataFrame:
    """
    Concise automated cleaning pipeline for Uber rides dataset.
    Leaves raw CSV completely untouched.
    """
    # 1. Load the raw dataset
    df = pd.read_csv(raw_csv_path)

    # 2. Strip wrapping quotes from identifier columns
    df['Booking ID'] = df['Booking ID'].astype(str).str.strip('\"\'')
    df['Customer ID'] = df['Customer ID'].astype(str).str.strip('\"\'')

    # 3. Create unified datetime from Date + Time
    df['Pickup_DateTime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%d-%m-%Y %H:%M:%S')

    # 4. Extract operational temporal dimensions for Demand & Cancellation Intelligence
    df['Hour'] = df['Pickup_DateTime'].dt.hour
    df['Day_Name'] = df['Pickup_DateTime'].dt.day_name()
    df['Is_Weekend'] = df['Pickup_DateTime'].dt.dayofweek.isin([5, 6]).astype(int)

    # 5. Compute earnings opportunity metric (Rs/km) for Completed rides
    df['Value_Per_Km'] = (df['Booking Value'] / df['Ride Distance']).where(df['Booking Status'] == 'Completed')

    # 6. Drop redundant indicator flags and raw Date/Time strings
    cols_to_drop = [
        'Cancelled Rides by Customer',
        'Cancelled Rides by Driver',
        'Incomplete Rides',
        'Date',
        'Time'
    ]
    df.drop(columns=cols_to_drop, inplace=True)

    # 7. Save cleaned copy if output path is provided
    if output_csv_path:
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        df.to_csv(output_csv_path, index=False)
        print(f"Cleaned dataset successfully saved to: {output_csv_path}")

    return df

if __name__ == '__main__':
    base_dir = os.path.dirname(__file__)
    raw_path = os.path.join(base_dir, 'data', 'uber_rides_raw.csv')
    cleaned_path = os.path.join(base_dir, 'data', 'uber_rides_cleaned.csv')

    print("Executing cleaning pipeline...")
    cleaned_df = clean_uber_data(raw_path, cleaned_path)
    
    print("\n--- VALIDATION ---")
    print(f"Total Rows: {len(cleaned_df):,}")
    print(f"Total Columns: {len(cleaned_df.columns)}")
    print("Final Column List:")
    for idx, col in enumerate(cleaned_df.columns, 1):
        print(f"  {idx}. {col} ({cleaned_df[col].dtype})")
