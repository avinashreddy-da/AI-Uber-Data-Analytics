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

# Safety limit below the assumed 1,000-record daily allowance.
SAFE_DAILY_LIMIT = 900


def get_historical_weather(start_date, end_date):
    """Fetch one controlled historical weather range."""

    url = (
        "https://weather.visualcrossing.com/"
        "VisualCrossingWebServices/rest/services/timeline/"
        f"{LOCATION}/{start_date}/{end_date}"
    )

    params = {
        "unitGroup": "metric",
        "include": "hours",
        "elements": (
            "datetime,temp,feelslike,humidity,precip,"
            "preciptype,windspeed,visibility,conditions"
        ),
        "key": API_KEY,
        "contentType": "json",
    }

    response = requests.get(
        url,
        params=params,
        timeout=60,
    )

    if response.status_code == 429:
        print("429: Visual Crossing usage/rate limit reached.")
        print("No new weather data was saved.")
        return None

    if response.status_code != 200:
        print(f"Weather API error: {response.status_code}")
        print(response.text[:500])
        return None

    return response.json()


def weather_to_dataframe(weather_data):
    """Convert Visual Crossing hourly data into a clean dataframe."""

    rows = []

    timezone = weather_data.get("timezone")

    for day in weather_data.get("days", []):
        weather_date = day["datetime"]

        for hour in day.get("hours", []):
            hour_time = hour["datetime"]

            rows.append(
                {
                    "Weather_DateTime": (
                        f"{weather_date} {hour_time}"
                    ),
                    "Temp_C": hour.get("temp"),
                    "FeelsLike_C": hour.get("feelslike"),
                    "Humidity": hour.get("humidity"),
                    "Precip_mm": hour.get("precip"),
                    "Precip_Type": hour.get("preciptype"),
                    "WindSpeed_kmh": hour.get("windspeed"),
                    "Visibility_km": hour.get("visibility"),
                    "Conditions": hour.get("conditions"),
                }
            )

    weather_df = pd.DataFrame(rows)

    if not weather_df.empty:
        weather_df["Weather_DateTime"] = pd.to_datetime(
            weather_df["Weather_DateTime"]
        )

        weather_df = weather_df.drop_duplicates(
            subset=["Weather_DateTime"]
        )

        weather_df = weather_df.sort_values(
            "Weather_DateTime"
        ).reset_index(drop=True)

    print(f"Timezone returned by API: {timezone}")
    print(f"Weather records extracted: {len(weather_df)}")

    return weather_df


def save_weather_data(weather_df):
    """Append new weather data without creating duplicate hours."""

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True,
    )

    if os.path.exists(OUTPUT_FILE):
        existing_df = pd.read_csv(
            OUTPUT_FILE,
            parse_dates=["Weather_DateTime"],
        )

        combined_df = pd.concat(
            [existing_df, weather_df],
            ignore_index=True,
        )

        combined_df = combined_df.drop_duplicates(
            subset=["Weather_DateTime"],
            keep="first",
        )

        combined_df = combined_df.sort_values(
            "Weather_DateTime"
        ).reset_index(drop=True)

    else:
        combined_df = weather_df.copy()

    combined_df.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(f"Saved: {OUTPUT_FILE}")
    print(f"Total weather records in file: {len(combined_df)}")


def load_progress():
    """Load progress and reset the daily counter on a new date."""

    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as file:
            progress = json.load(file)
    else:
        progress = {
            "usage_date": str(date.today()),
            "records_used_today": 0,
            "completed_months": [],
        }

    today = str(date.today())

    if progress.get("usage_date") != today:
        progress["usage_date"] = today
        progress["records_used_today"] = 0

    progress.setdefault("completed_months", [])
    progress.setdefault("records_used_today", 0)

    return progress


def save_progress(progress):
    """Save download progress."""

    os.makedirs(
        os.path.dirname(PROGRESS_FILE),
        exist_ok=True,
    )

    with open(PROGRESS_FILE, "w") as file:
        json.dump(
            progress,
            file,
            indent=4,
        )


def get_month_end(start):
    """Return the last date of the current month."""

    next_month = start.replace(day=28) + timedelta(days=4)

    month_end = (
        next_month
        - timedelta(days=next_month.day)
    )

    return min(month_end, END_DATE)


def download_weather():
    """Download one monthly weather chunk per run."""

    if not API_KEY:
        print("ERROR: VISUAL_CROSSING_API_KEY is missing.")
        return

    progress = load_progress()

    records_used_today = progress[
        "records_used_today"
    ]

    completed_months = progress[
        "completed_months"
    ]

    current_date = START_DATE

    while current_date <= END_DATE:

        month_end = get_month_end(current_date)

        month_name = current_date.strftime(
            "%Y-%m"
        )

        if month_name in completed_months:
            print(
                f"{month_name} already completed. "
                "Skipping."
            )

            current_date = (
                month_end + timedelta(days=1)
            )

            continue

        days_in_chunk = (
            month_end - current_date
        ).days + 1

        estimated_records = days_in_chunk * 24

        print()
        print("=" * 60)
        print(
            f"Next weather chunk: "
            f"{current_date} → {month_end}"
        )
        print(
            f"Estimated records: "
            f"{estimated_records}"
        )
        print(
            f"Records used today: "
            f"{records_used_today}"
        )
        print("=" * 60)

        if (
            records_used_today
            + estimated_records
            > SAFE_DAILY_LIMIT
        ):
            print()
            print(
                "Safety limit reached before "
                "making the API request."
            )
            print(
                "Stopping without making another request."
            )
            return

        weather_data = get_historical_weather(
            current_date.isoformat(),
            month_end.isoformat(),
        )

        if weather_data is None:
            print()
            print("Download stopped.")
            print(
                "Existing weather data was not deleted."
            )
            return

        actual_query_cost = weather_data.get(
            "queryCost"
        )

        if actual_query_cost is None:
            print(
                "ERROR: Visual Crossing response "
                "did not contain queryCost."
            )
            print(
                "Stopping without saving this chunk."
            )
            return

        print(
            f"Actual API query cost: "
            f"{actual_query_cost}"
        )

        if (
            records_used_today
            + actual_query_cost
            > SAFE_DAILY_LIMIT
        ):
            print()
            print(
                "Actual API cost exceeds our "
                "safety limit."
            )
            print(
                "Stopping without saving this chunk."
            )
            return

        weather_df = weather_to_dataframe(
            weather_data
        )

        if weather_df.empty:
            print(
                "No weather records returned."
            )
            print(
                "Stopping without marking "
                "the month complete."
            )
            return

        save_weather_data(weather_df)

        records_used_today += actual_query_cost

        completed_months.append(month_name)

        progress["records_used_today"] = (
            records_used_today
        )

        progress["completed_months"] = (
            completed_months
        )

        save_progress(progress)

        print()
        print(
            f"{month_name} completed successfully."
        )
        print(
            f"Today's tracked API usage: "
            f"{records_used_today}"
        )

        current_date = (
            month_end + timedelta(days=1)
        )

        # Small pause after a successful request.
        time.sleep(2)

        # IMPORTANT:
        # Only one monthly request per script run.
        print()
        print(
            "One monthly chunk completed."
        )
        print(
            "Stopping safely for today."
        )

        return


if __name__ == "__main__":
    download_weather()