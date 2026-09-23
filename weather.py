import os
import json
import time
from datetime import date, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("VISUAL_CROSSING_API_KEY")

LOCATION = "Delhi,India"

START_DATE = date(2024, 1, 1)
END_DATE = date(2024, 12, 30)

OUTPUT_FILE = "data/weather/delhi_weather_2024.csv"
PROGRESS_FILE = "data/weather/weather_progress.json"

SAFE_DAILY_LIMIT = 900


def get_historical_weather(start_date, end_date):
    url = (
        "https://weather.visualcrossing.com/"
        "VisualCrossingWebServices/rest/services/timeline/"
        f"{LOCATION}/{start_date}/{end_date}"
    )

    params = {
        "unitGroup": "metric",
        "include": "hours",
        "elements": "datetime,temp,precip,humidity,windspeed,conditions",
        "key": API_KEY,
        "contentType": "json"
    }

    response = requests.get(url, params=params, timeout=60)

    if response.status_code == 429:
        print("429: Visual Crossing rejected the request because of a usage/rate limit.")
        print("No new weather data was saved.")
        return None

    if response.status_code != 200:
        print(f"Weather API error: {response.status_code}")
        print(response.text[:500])
        return None

    return response.json()


def weather_to_dataframe(weather_data):
    rows = []

    for day in weather_data["days"]:
        weather_date = day["datetime"]

        for hour in day["hours"]:
            rows.append({
                "date": weather_date,
                "hour": hour["datetime"],
                "temp": hour.get("temp"),
                "precip": hour.get("precip"),
                "humidity": hour.get("humidity"),
                "windspeed": hour.get("windspeed"),
                "conditions": hour.get("conditions")
            })

    return pd.DataFrame(rows)


def save_weather_data(weather_df):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(OUTPUT_FILE)

        combined_df = pd.concat(
            [existing_df, weather_df],
            ignore_index=True
        )

        combined_df = combined_df.drop_duplicates(
            subset=["date", "hour"]
        )

        combined_df.to_csv(OUTPUT_FILE, index=False)

    else:
        weather_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved: {OUTPUT_FILE}")


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as file:
            return json.load(file)

    return {
        "records_used_today": 0,
        "completed_months": []
    }


def save_progress(progress):
    os.makedirs(os.path.dirname(PROGRESS_FILE), exist_ok=True)

    with open(PROGRESS_FILE, "w") as file:
        json.dump(progress, file, indent=4)


def get_month_end(start):
    next_month = start.replace(day=28) + timedelta(days=4)
    month_end = next_month - timedelta(days=next_month.day)

    return min(month_end, END_DATE)


def download_weather():
    progress = load_progress()

    records_used_today = progress["records_used_today"]
    completed_months = progress["completed_months"]

    current_date = START_DATE

    while current_date <= END_DATE:

        month_end = get_month_end(current_date)

        month_name = current_date.strftime("%Y-%m")

        if month_name in completed_months:
            print(f"{month_name} already completed. Skipping.")
            current_date = month_end + timedelta(days=1)
            continue

        days_in_chunk = (month_end - current_date).days + 1
        estimated_records = days_in_chunk * 24

        print()
        print(f"Next chunk: {current_date} → {month_end}")
        print(f"Estimated records: {estimated_records}")
        print(f"Today's tracked records: {records_used_today}")

        if records_used_today + estimated_records > SAFE_DAILY_LIMIT:
            print()
            print("Safe daily limit reached.")
            print("Stopping before making another API request.")
            print("Run the script again after the daily limit resets.")
            return

        weather_data = get_historical_weather(
            current_date.isoformat(),
            month_end.isoformat()
        )

        if weather_data is None:
            print()
            print("Download stopped.")
            print("Existing CSV data has NOT been deleted.")
            return

        actual_query_cost = weather_data.get(
            "queryCost",
            estimated_records
        )

        print(f"Actual API query cost: {actual_query_cost}")

        if records_used_today + actual_query_cost > SAFE_DAILY_LIMIT:
            print("API cost would exceed the safe limit.")
            print("Stopping without saving this chunk.")
            return

        weather_df = weather_to_dataframe(weather_data)

        save_weather_data(weather_df)

        records_used_today += actual_query_cost
        completed_months.append(month_name)

        progress["records_used_today"] = records_used_today
        progress["completed_months"] = completed_months

        save_progress(progress)

        print(
            f"{month_name} completed successfully."
        )

        current_date = month_end + timedelta(days=1)

        # Small pause between successful requests
        time.sleep(2)

        # For the free plan, stop after one month.
        # This makes it easy to resume the next day.
        print()
        print("One monthly chunk completed.")
        print("Stopping safely for today.")
        return


if __name__ == "__main__":
    download_weather()