import os
import json

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from dotenv import load_dotenv
from google import genai
from google.genai import types

import analytics as an


# ==============================================================================
# CONFIG
# ==============================================================================

load_dotenv()

st.set_page_config(
    page_title="RideIntel | Historical Mobility Analytics",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==============================================================================
# GLOBAL CSS
# ==============================================================================

st.markdown(
    """
    <style>

    /* ============================================================
       APP
       ============================================================ */

    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }

    [data-testid="stHeader"] {
        background-color: #0f172a;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }


    /* ============================================================
       SIDEBAR
       ============================================================ */

    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important;
        border-right: 1px solid #334155;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 4px;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    label {
        color: #e2e8f0 !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        padding: 9px 12px !important;
        margin: 2px 0 !important;
        border-radius: 8px !important;
        transition:
            background-color 0.15s ease,
            color 0.15s ease;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    label:hover {
        background-color: rgba(56, 189, 248, 0.08) !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    label:has(input:checked) {
        background-color: rgba(56, 189, 248, 0.14) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-left: 3px solid #38bdf8 !important;
        padding-left: 9px !important;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    label p {
        color: inherit !important;
        font-weight: inherit !important;
        margin: 0 !important;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    label span {
        font-size: 1.05rem !important;
        margin-right: 9px !important;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    input {
        display: none !important;
    }


    /* ============================================================
       SELECTBOX
       ============================================================ */

    div[data-testid="stSelectbox"] label {
        color: #f8fafc !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }

    div[data-testid="stSelectbox"] label p {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        border: 1px solid #475569 !important;
        color: #f8fafc !important;
        border-radius: 8px !important;
    }

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] span {
        color: #f8fafc !important;
    }

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] input {
        color: #f8fafc !important;
    }

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] svg {
        fill: #cbd5e1 !important;
    }

    div[data-baseweb="popover"] {
        background-color: #1e293b !important;
        border: 1px solid #475569 !important;
    }

    div[data-baseweb="popover"] ul {
        background-color: #1e293b !important;
    }

    div[data-baseweb="popover"] li {
        background-color: #1e293b !important;
        color: #f8fafc !important;
    }

    div[data-baseweb="popover"] li:hover {
        background-color: #334155 !important;
        color: #ffffff !important;
    }

    div[data-baseweb="popover"] li[aria-selected="true"] {
        background-color: #334155 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
    }


    /* ============================================================
       MULTISELECT
       ============================================================ */

    div[data-testid="stMultiSelect"] label {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMultiSelect"]
    div[data-baseweb="select"] {
        background-color: #1e293b !important;
    }

    div[data-testid="stMultiSelect"]
    div[data-baseweb="select"] span {
        color: #f8fafc !important;
    }


    /* ============================================================
       SLIDER
       ============================================================ */

    div[data-testid="stSlider"] label {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stSlider"] label p {
        color: #f8fafc !important;
    }


    /* ============================================================
       METRIC
       ============================================================ */

    div[data-testid="stMetric"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px;
    }

    div[data-testid="stMetricLabel"] {
        color: #f8fafc !important;
    }

    div[data-testid="stMetricLabel"] p {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
    }

    div[data-testid="stMetricDelta"] {
        color: #f8fafc !important;
    }


    /* ============================================================
       BUTTON
       ============================================================ */

    .stButton > button {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    .stButton > button:hover {
        background-color: #334155 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }


    /* ============================================================
       CHAT INPUT
       ============================================================ */

    div[data-testid="stChatInput"] {
        border-color: #334155 !important;
    }


    /* ============================================================
       EXPANDER
       ============================================================ */

    details {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }

    details summary {
        color: #f8fafc !important;
    }


    /* ============================================================
       DATAFRAME / TABLE TEXT
       ============================================================ */

    div[data-testid="stDataFrame"] * {
        color: #f8fafc !important;
    }

    div[data-testid="stDataFrame"] {
        color: #f8fafc !important;
    }


    /* ============================================================
       GENERAL TEXT
       ============================================================ */

    div[data-testid="stCaptionContainer"] {
        color: #f8fafc !important;
    }

    div[data-testid="stCaptionContainer"] p {
        color: #f8fafc !important;
    }

    /* ============================================================
       PAGE TEXT / LABELS / FILTER VALUES
       Keep app UI text white. Chart-internal labels are controlled
       separately by Altair and are intentionally not overridden here.
       ============================================================ */

    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
    }

    div[data-testid="stMarkdownContainer"] p,
    div[data-testid="stMarkdownContainer"] span,
    div[data-testid="stMarkdownContainer"] strong,
    div[data-testid="stText"] p,
    div[data-testid="stText"] span {
        color: #f8fafc !important;
    }

    div[data-testid="stSelectbox"] label,
    div[data-testid="stSelectbox"] label *,
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stMultiSelect"] label *,
    div[data-testid="stSlider"] label,
    div[data-testid="stSlider"] label * {
        color: #f8fafc !important;
    }

    div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div * {
        color: #f8fafc !important;
    }

    div[data-testid="stMultiSelect"] [data-baseweb="tag"],
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] * {
        color: #f8fafc !important;
        background-color: #334155 !important;
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div * {
        color: #f8fafc !important;
    }

    div[data-baseweb="popover"],
    div[data-baseweb="popover"] *,
    div[data-baseweb="popover"] li,
    div[data-baseweb="popover"] li * {
        color: #f8fafc !important;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *,
    div[data-testid="stMetricDelta"],
    div[data-testid="stMetricDelta"] * {
        color: #f8fafc !important;
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stDataFrame"] * {
        color: #f8fafc !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# DATA
# ==============================================================================

DATA_PATH = os.path.join(
    "data",
    "uber_rides_cleaned.csv",
)


@st.cache_data
def load_and_clean_data(file_path):

    if not os.path.exists(file_path):
        return None

    df = pd.read_csv(file_path)

    rename_map = {
        "Pickup Location": "Pickup_Location",
        "Vehicle Type": "Vehicle_Type",
        "Booking Status": "Booking_Status",
        "Booking Value": "Booking_Value",
        "Ride Distance": "Ride_Distance",
        "Day Name": "Day_Name",
        "Value Per Km": "Value_Per_Km",
        "Value_Per_Km": "Value_Per_Km",
    }

    df = df.rename(columns=rename_map)

    if "Pickup_DateTime" not in df.columns:

        if "Date" in df.columns and "Time" in df.columns:

            df["Pickup_DateTime"] = pd.to_datetime(
                df["Date"].astype(str)
                + " "
                + df["Time"].astype(str),
                errors="coerce",
            )

    if "Hour" not in df.columns:

        df["Hour"] = (
            df["Pickup_DateTime"]
            .dt
            .hour
        )

    if "Day_Name" not in df.columns:

        df["Day_Name"] = (
            df["Pickup_DateTime"]
            .dt
            .day_name()
        )

    for column in [
        "Booking_Value",
        "Ride_Distance",
        "Value_Per_Km",
    ]:

        if column in df.columns:

            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    if "Value_Per_Km" not in df.columns:

        df["Value_Per_Km"] = np.where(
            df["Ride_Distance"] > 0,
            df["Booking_Value"]
            / df["Ride_Distance"],
            np.nan,
        )

    return df



# ==============================================================================
# HISTORICAL WEATHER - LOCAL CSV ONLY
# ==============================================================================

WEATHER_PATH = os.path.join(
    "data",
    "weather",
    "delhi_weather_2024.csv",
)


@st.cache_data
def load_historical_weather(file_path):

    if not os.path.exists(file_path):
        return None

    weather = pd.read_csv(file_path)

    if "Weather_DateTime" not in weather.columns:
        return None

    weather["Weather_DateTime"] = pd.to_datetime(
        weather["Weather_DateTime"],
        errors="coerce",
    )

    weather = weather.dropna(
        subset=["Weather_DateTime"]
    ).copy()

    # The app uses the January 2024 dataset already downloaded locally.
    weather = weather[
        weather["Weather_DateTime"].dt.month == 1
    ].copy()

    weather["Hour"] = weather[
        "Weather_DateTime"
    ].dt.hour

    weather["Day_Name"] = weather[
        "Weather_DateTime"
    ].dt.day_name()

    return weather


def get_historical_weather_context(
    weather,
    day_name,
    hour,
):

    if weather is None or weather.empty:
        return None

    match = weather[
        (weather["Day_Name"] == day_name)
        & (weather["Hour"] == hour)
    ].copy()

    if match.empty:
        return None

    summary = {}

    numeric_columns = [
        "Temp_C",
        "FeelsLike_C",
        "Humidity",
        "Precip_mm",
        "WindSpeed_kmh",
        "Visibility_km",
    ]

    for column in numeric_columns:
        if column in match.columns:
            values = pd.to_numeric(
                match[column],
                errors="coerce",
            )
            value = values.mean()
            if pd.notna(value):
                summary[column] = float(value)

    if "Conditions" in match.columns:
        conditions = (
            match["Conditions"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        if not conditions.empty:
            summary["Conditions"] = (
                conditions.mode().iloc[0]
            )

    summary["records"] = len(match)

    return summary

df_main = load_and_clean_data(DATA_PATH)

historical_weather = load_historical_weather(WEATHER_PATH)


# ==============================================================================
# HELPERS
# ==============================================================================

def normalize_analytics_result(result):

    if isinstance(result, pd.DataFrame):

        if result.empty:
            return {}

        return result.iloc[0].to_dict()

    if isinstance(result, pd.Series):

        return result.to_dict()

    if isinstance(result, dict):

        return result

    return {}


def display_data_error():

    st.error(
        "Ride dataset not found. Make sure "
        "`data/uber_rides_cleaned.csv` exists."
    )


def show_metric_cards(
    metrics
):

    columns = st.columns(
        len(metrics)
    )

    for column, metric in zip(
        columns,
        metrics,
    ):

        with column:

            st.metric(
                label=metric["label"],
                value=metric["value"],
                help=metric.get("help"),
            )


# ==============================================================================
# GEMINI
# ==============================================================================

def get_gemini_client():

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        return None

    try:

        return genai.Client(
            api_key=api_key
        )

    except Exception:

        return None


def _ai_filter_dataframe(
    pickup_location=None,
    vehicle_type=None,
    hour=None,
    day_name=None,
):

    filtered = df_main.copy()

    if pickup_location:
        filtered = filtered[
            filtered["Pickup_Location"] == pickup_location
        ]

    if vehicle_type and vehicle_type != "All Vehicle Types":
        filtered = filtered[
            filtered["Vehicle_Type"] == vehicle_type
        ]

    if hour is not None:
        filtered = filtered[
            filtered["Hour"] == int(hour)
        ]

    if day_name:
        filtered = filtered[
            filtered["Day_Name"].str.lower()
            == str(day_name).lower()
        ]

    return filtered


def ai_historical_context(
    pickup_location,
    hour,
    day_name,
    vehicle_type="All Vehicle Types",
):

    data = _ai_filter_dataframe(
        pickup_location=pickup_location,
        vehicle_type=vehicle_type,
        hour=hour,
        day_name=day_name,
    )

    if data.empty:
        return {
            "found": False,
            "message": "No recorded rides match this historical context.",
        }

    completed = data[
        data["Booking_Status"] == "Completed"
    ]

    customer_cancel = int(
        (data["Booking_Status"] == "Cancelled by Customer").sum()
    )
    driver_cancel = int(
        (data["Booking_Status"] == "Cancelled by Driver").sum()
    )

    return {
        "found": True,
        "pickup_location": pickup_location,
        "hour": int(hour),
        "day_name": day_name,
        "vehicle_type": vehicle_type,
        "total_bookings": int(len(data)),
        "completed_rides": int(len(completed)),
        "completion_rate": round(len(completed) / len(data) * 100, 2),
        "avg_booking_value": round(float(completed["Booking_Value"].mean()), 2) if not completed.empty else None,
        "avg_ride_distance": round(float(completed["Ride_Distance"].mean()), 2) if not completed.empty else None,
        "avg_value_per_km": round(float(completed["Value_Per_Km"].mean()), 2) if not completed.empty else None,
        "customer_cancellation_rate": round(customer_cancel / len(data) * 100, 2),
        "driver_cancellation_rate": round(driver_cancel / len(data) * 100, 2),
        "combined_cancellation_rate": round((customer_cancel + driver_cancel) / len(data) * 100, 2),
        "festival_bookings": int(data.get("Is_Festival", pd.Series(False, index=data.index)).fillna(False).astype(bool).sum())
        if "Is_Festival" in data.columns else 0,
    }


def ai_cancellation_patterns(
    pickup_location=None,
    vehicle_type="All Vehicle Types",
):

    data = _ai_filter_dataframe(
        pickup_location=pickup_location,
        vehicle_type=vehicle_type,
    )

    if data.empty:
        return {
            "found": False,
            "message": "No recorded rides match the cancellation context.",
        }

    grouped = data.groupby("Pickup_Location").size().reset_index(name="total_bookings")
    customer = (
        data[data["Booking_Status"] == "Cancelled by Customer"]
        .groupby("Pickup_Location")
        .size()
        .rename("customer_cancellations")
    )
    driver = (
        data[data["Booking_Status"] == "Cancelled by Driver"]
        .groupby("Pickup_Location")
        .size()
        .rename("driver_cancellations")
    )

    grouped = grouped.set_index("Pickup_Location")
    grouped["customer_cancellations"] = customer
    grouped["driver_cancellations"] = driver
    grouped = grouped.fillna(0).reset_index()
    grouped["customer_rate"] = grouped["customer_cancellations"] / grouped["total_bookings"] * 100
    grouped["driver_rate"] = grouped["driver_cancellations"] / grouped["total_bookings"] * 100
    grouped["combined_rate"] = (
        grouped["customer_cancellations"] + grouped["driver_cancellations"]
    ) / grouped["total_bookings"] * 100

    grouped = grouped.sort_values(
        ["combined_rate", "total_bookings"],
        ascending=[False, False],
    )

    return {
        "found": True,
        "filter_location": pickup_location or "All Locations",
        "filter_vehicle": vehicle_type,
        "rows": grouped.head(10).round(2).to_dict(orient="records"),
    }


def ai_earnings_patterns(
    pickup_location=None,
    vehicle_type="All Vehicle Types",
    hour=None,
    day_name=None,
):

    data = _ai_filter_dataframe(
        pickup_location=pickup_location,
        vehicle_type=vehicle_type,
        hour=hour,
        day_name=day_name,
    )

    completed = data[
        data["Booking_Status"] == "Completed"
    ]

    if completed.empty:
        return {
            "found": False,
            "message": "No completed historical rides match the earnings context.",
        }

    summary = {
        "found": True,
        "filter_location": pickup_location or "All Locations",
        "filter_vehicle": vehicle_type,
        "filter_hour": hour,
        "filter_day": day_name or "All Days",
        "completed_rides": int(len(completed)),
        "avg_booking_value": round(float(completed["Booking_Value"].mean()), 2),
        "avg_ride_distance": round(float(completed["Ride_Distance"].mean()), 2),
        "avg_value_per_km": round(float(completed["Value_Per_Km"].mean()), 2),
    }

    by_location = (
        completed.groupby("Pickup_Location")
        .agg(
            completed_rides=("Booking_Status", "size"),
            avg_value_per_km=("Value_Per_Km", "mean"),
            avg_booking_value=("Booking_Value", "mean"),
        )
        .reset_index()
        .sort_values("avg_value_per_km", ascending=False)
        .head(10)
    )

    summary["by_location"] = by_location.round(2).to_dict(orient="records")
    return summary


def ai_demand_patterns(
    pickup_location=None,
    vehicle_type="All Vehicle Types",
    hour=None,
    day_name=None,
):

    data = _ai_filter_dataframe(
        pickup_location=pickup_location,
        vehicle_type=vehicle_type,
        hour=hour,
        day_name=day_name,
    )

    completed = data[
        data["Booking_Status"] == "Completed"
    ]

    if completed.empty:
        return {
            "found": False,
            "message": "No completed historical rides match the demand context.",
        }

    by_hour = (
        completed.groupby("Hour")
        .size()
        .reset_index(name="completed_rides")
        .sort_values("completed_rides", ascending=False)
        .head(10)
    )

    by_day = (
        completed.groupby("Day_Name")
        .size()
        .reset_index(name="completed_rides")
        .sort_values("completed_rides", ascending=False)
    )

    return {
        "found": True,
        "filter_location": pickup_location or "All Locations",
        "filter_vehicle": vehicle_type,
        "filter_hour": hour,
        "filter_day": day_name or "All Days",
        "completed_rides": int(len(completed)),
        "top_hours": by_hour.to_dict(orient="records"),
        "rides_by_day": by_day.to_dict(orient="records"),
    }


ANALYTICS_TOOLS = {
    "ai_historical_context": ai_historical_context,
    "ai_cancellation_patterns": ai_cancellation_patterns,
    "ai_earnings_patterns": ai_earnings_patterns,
    "ai_demand_patterns": ai_demand_patterns,
}


SYSTEM_INSTRUCTION = """
You are RideIntel AI, an analytical assistant for ride-hailing/gig workers
using the Delhi NCR historical ride dataset.

Your job is to explain what the recorded historical data shows.

Rules:

1. Use analytics tools whenever the user asks about a specific location,
hour, day, vehicle type, earnings, demand, or cancellations.

2. For questions that connect multiple topics, use MULTIPLE relevant
analytics tools before answering. Examples:
- earnings + cancellations -> use earnings and cancellation tools
- demand + earnings -> use demand and earnings tools
- a specific location/hour/day/vehicle situation -> use historical context,
and use additional tools when the question asks about earnings, demand,
or cancellations within that situation.

3. Combine the tool results into one explanation. Do not simply repeat one
tool result and ignore the others.

4. Never make predictions.

5. Never tell drivers where to go or what they should do.

6. Never claim expected demand, predicted earnings, guaranteed outcomes,
or future performance.

7. Use phrases such as historical pattern, recorded activity, historical
completion rate, observed in the dataset, and recorded completed rides.

8. When the sample size is small, explicitly mention that the historical
comparison is based on a small number of recorded rides.

9. Keep answers concise, practical, and driver-focused.
"""


gemini_tools = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="ai_historical_context",
                description=(
                    "Analyze one exact historical situation using pickup location, "
                    "hour, day and vehicle type. Returns bookings, completion, "
                    "earnings, distance, cancellations and festival context."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pickup_location": types.Schema(
                            type=types.Type.STRING,
                            description="Pickup location name.",
                        ),
                        "hour": types.Schema(
                            type=types.Type.INTEGER,
                            description="Hour of day from 0 to 23.",
                        ),
                        "day_name": types.Schema(
                            type=types.Type.STRING,
                            description="Day of week.",
                        ),
                        "vehicle_type": types.Schema(
                            type=types.Type.STRING,
                            description="Vehicle type or All Vehicle Types.",
                        ),
                    },
                    required=[
                        "pickup_location",
                        "hour",
                        "day_name",
                        "vehicle_type",
                    ],
                ),
            ),
            types.FunctionDeclaration(
                name="ai_cancellation_patterns",
                description=(
                    "Analyze historical customer and driver cancellation rates by "
                    "pickup location, optionally filtered to one vehicle type or location."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pickup_location": types.Schema(
                            type=types.Type.STRING,
                            description="Optional pickup location. Leave blank for all locations.",
                        ),
                        "vehicle_type": types.Schema(
                            type=types.Type.STRING,
                            description="Vehicle type or All Vehicle Types.",
                        ),
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="ai_earnings_patterns",
                description=(
                    "Analyze historical completed-ride earnings patterns including average "
                    "booking value, distance and value per km."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pickup_location": types.Schema(
                            type=types.Type.STRING,
                            description="Optional pickup location. Leave blank for all locations.",
                        ),
                        "vehicle_type": types.Schema(
                            type=types.Type.STRING,
                            description="Vehicle type or All Vehicle Types.",
                        ),
                        "hour": types.Schema(
                            type=types.Type.INTEGER,
                            description="Optional hour from 0 to 23.",
                        ),
                        "day_name": types.Schema(
                            type=types.Type.STRING,
                            description="Optional day of week.",
                        ),
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="ai_demand_patterns",
                description=(
                    "Analyze historical completed-ride volume patterns by hour and day, "
                    "optionally filtered by location, vehicle, hour or day."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "pickup_location": types.Schema(
                            type=types.Type.STRING,
                            description="Optional pickup location. Leave blank for all locations.",
                        ),
                        "vehicle_type": types.Schema(
                            type=types.Type.STRING,
                            description="Vehicle type or All Vehicle Types.",
                        ),
                        "hour": types.Schema(
                            type=types.Type.INTEGER,
                            description="Optional hour from 0 to 23.",
                        ),
                        "day_name": types.Schema(
                            type=types.Type.STRING,
                            description="Optional day of week.",
                        ),
                    },
                ),
            ),
        ]
    )
]


def run_gemini_agent_loop(
    user_query,
    active_context_result=None,
):

    client = get_gemini_client()

    if not client:
        return (
            "The AI Assistant is currently unavailable. "
            "You can still use the historical analytics pages."
        )

    contents = []

    if active_context_result:
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        "CURRENT HISTORICAL CONTEXT: "
                        + json.dumps(active_context_result, default=str)
                    )
                ],
            )
        )
        contents.append(
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(
                        "Understood. I have loaded the historical context."
                    )
                ],
            )
        )

    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(user_query)
            ],
        )
    )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=gemini_tools,
        temperature=0.2,
    )

    try:
        for _ in range(3):

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
            )

            if not response.function_calls:
                return (
                    response.text
                    if response.text
                    else "Historical analysis completed."
                )

            if not response.candidates:
                break

            contents.append(
                response.candidates[0].content
            )

            tool_parts = []

            for function_call in response.function_calls:

                func_name = function_call.name
                func_args = dict(function_call.args)

                tool = ANALYTICS_TOOLS.get(func_name)

                if not tool:
                    tool_result = {
                        "found": False,
                        "message": "Requested analytics tool was not available.",
                    }
                else:
                    try:
                        tool_result = tool(**func_args)
                    except Exception as exc:
                        tool_result = {
                            "found": False,
                            "message": f"Analytics tool error: {exc}",
                        }

                tool_parts.append(
                    types.Part.from_function_response(
                        name=func_name,
                        response={
                            "result": normalize_analytics_result(tool_result)
                            if isinstance(tool_result, (pd.DataFrame, pd.Series))
                            else tool_result
                        },
                    )
                )

            contents.append(
                types.Content(
                    role="user",
                    parts=tool_parts,
                )
            )

        return "Historical analysis completed, but the assistant could not finish combining the requested analytics."

    except Exception:
        return (
            "The AI Assistant is currently experiencing high demand. "
            "Please use the historical metrics pages directly."
        )


def generate_home_insight(
    context_data
):

    client = get_gemini_client()

    if not client:
        return None

    prompt = f"""
Summarize this historical ride dataset result:

{json.dumps(context_data, default=str)}

Rules:

- Historical facts only.
- No predictions.
- No driving recommendations.
- No phrases such as "go here", "drive here",
  "expected earnings", or "future demand".
- Give 2 or 3 concise bullet points.
"""

    try:

        config = types.GenerateContentConfig(
            system_instruction=(
                "You are a strict historical mobility analyst. "
                "Return concise historical facts only."
            ),
            temperature=0.2,
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config,
        )

        return (
            response.text
            if response.text
            else None
        )

    except Exception:

        return None


# ==============================================================================
# SIDEBAR
# ==============================================================================

st.sidebar.title(
    "🚘 RideIntel"
)

st.sidebar.caption(
    "Historical Mobility Intelligence"
)

st.sidebar.divider()


nav_options = {
    "🏠 Home": "Home",
    "📈 Demand Patterns": "Demand",
    "💰 Historical Earnings": "Earnings",
    "🚫 Cancellations": "Cancellations",
    "🤖 AI Assistant": "AI Assistant",
}


selected_label = st.sidebar.radio(
    "Navigation",
    options=list(nav_options.keys()),
    label_visibility="collapsed",
)

selected_page = nav_options[
    selected_label
]


st.sidebar.divider()

st.sidebar.caption(
    "Region"
)

st.sidebar.write(
    "**Delhi NCR**"
)

st.sidebar.caption(
    "Dataset"
)

st.sidebar.write(
    "**Historical 2024 Records**"
)


# ==============================================================================
# HOME
# ==============================================================================

if selected_page == "Home":

    st.title(
        "Historical Ride Insight"
    )

    st.caption(
        "Examine what the historical data recorded for a "
        "specific location, time, day, and vehicle type."
    )

    if df_main is None:

        display_data_error()
        st.stop()

    locations = sorted(
        df_main[
            "Pickup_Location"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    vehicle_types = (
        ["All Vehicle Types"]
        + [
            value
            for value in sorted(
                df_main[
                    "Vehicle_Type"
                ]
                .dropna()
                .unique()
                .tolist()
            )
            if value != "All Vehicle Types"
        ]
    )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    hours = list(range(24))

    st.header(
        "Check a Historical Situation"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    with col1:

        location_index = (
            locations.index("AIIMS")
            if "AIIMS" in locations
            else 0
        )

        sel_location = st.selectbox(
            "Pickup Location",
            locations,
            index=location_index,
        )

    with col2:

        sel_hour = st.selectbox(
            "Hour of Day",
            hours,
            index=15,
            format_func=lambda hour:
                f"{hour:02d}:00",
        )

    with col3:

        sel_day = st.selectbox(
            "Day of Week",
            days,
            index=0,
        )

    with col4:

        sel_vehicle = st.selectbox(
            "Vehicle Type",
            vehicle_types,
            index=0,
        )

    vehicle_arg = (
        None
        if sel_vehicle == "All Vehicle Types"
        else sel_vehicle
    )

    with st.spinner(
        "Checking historical ride patterns..."
    ):

        result = (
            an.contextual_location_hour_analysis(
                pickup_location=sel_location,
                hour=sel_hour,
                day_name=sel_day,
                vehicle_type=vehicle_arg,
            )
        )

        result = normalize_analytics_result(
            result
        )

    st.session_state[
        "home_last_context"
    ] = {
        "location": sel_location,
        "hour": sel_hour,
        "day": sel_day,
        "vehicle_type": sel_vehicle,
    }

    st.session_state[
        "home_last_result"
    ] = result

    st.divider()

    st.subheader(
        "Historical Recorded Pattern"
    )

    st.write(
        f"**Location:** {sel_location}  |  "
        f"**Time:** {sel_hour:02d}:00  |  "
        f"**Day:** {sel_day}  |  "
        f"**Vehicle:** {sel_vehicle}"
    )

    if result.get("is_fallback"):

        st.warning(
            result.get(
                "warning",
                "The broader historical pattern is being shown "
                "because the exact vehicle-specific sample is small.",
            )
        )

    show_metric_cards(
        [
            {
                "label": "Historical Bookings",
                "value": (
                    f"{result.get('total_bookings', 0):,}"
                ),
                "help": "Recorded booking attempts in this historical context.",
            },
            {
                "label": "Historical Completion",
                "value": (
                    f"{result.get('completion_rate', 0):.1f}%"
                ),
                "help": "Percentage of recorded bookings that were completed.",
            },
            {
                "label": "Average Value / Km",
                "value": (
                    f"₹{result.get('avg_value_per_km', 0):.2f}"
                ),
                "help": "Average booking value divided by ride distance for completed rides.",
            },
            {
                "label": "Average Booking Value",
                "value": (
                    f"₹{result.get('avg_booking_value', 0):.2f}"
                ),
                "help": "Average recorded booking value.",
            },
            {
                "label": "Average Ride Distance",
                "value": (
                    f"{result.get('avg_ride_distance', 0):.2f} km"
                ),
                "help": "Average distance of recorded completed rides.",
            },
        ]
    )

    show_metric_cards(
        [
            {
                "label": "Customer Cancellations",
                "value": (
                    f"{result.get('customer_cancellation_rate', 0):.1f}%"
                ),
                "help": "Historical customer cancellation rate.",
            },
            {
                "label": "Driver Cancellations",
                "value": (
                    f"{result.get('driver_cancellation_rate', 0):.1f}%"
                ),
                "help": "Historical driver cancellation rate.",
            },
            {
                "label": "Combined Cancellation",
                "value": (
                    f"{result.get('combined_cancellation_rate', 0):.1f}%"
                ),
                "help": "Historical combined cancellation rate.",
            },
            {
                "label": "Festival Context",
                "value": str(
                    result.get(
                        "festival_info",
                        "None",
                    )
                ),
                "help": "Historical festival information for this context.",
            },
        ]
    )

    st.caption(
        "Historical averages across recorded rides. These figures do not represent one driver’s actual daily earnings."
    )

    with st.expander("📊 Show full details"):
        st.subheader("Detailed Historical Context")
        st.caption(
            "Underlying analytics result for the selected historical situation."
        )
        st.json(result)

    weather_context = get_historical_weather_context(
        historical_weather, sel_day, sel_hour
    )

    if weather_context:
        st.subheader("Historical Weather Context")
        st.caption(
            "January 2024 weather records matching the selected weekday and hour. "
            "This is historical context, not live weather or a prediction."
        )
        weather_cols = st.columns(4)
        weather_cols[0].metric(
            "Avg Temperature",
            f"{weather_context.get('Temp_C', 0):.1f} °C"
        )
        weather_cols[1].metric(
            "Avg Humidity",
            f"{weather_context.get('Humidity', 0):.0f}%"
        )
        weather_cols[2].metric(
            "Avg Rainfall",
            f"{weather_context.get('Precip_mm', 0):.2f} mm"
        )
        weather_cols[3].metric(
            "Conditions",
            weather_context.get("Conditions", "Not available")
        )

    ai_summary = generate_home_insight(
        result
    )

    if ai_summary:

        st.subheader(
            "Historical Pattern Summary"
        )

        st.info(
            ai_summary
        )


# ==============================================================================
# DEMAND
# ==============================================================================

elif selected_page == "Demand":

    st.title(
        "📈 Demand Patterns"
    )

    st.caption(
        "Analyze historical completed-ride volumes "
        "across locations and hours."
    )

    if df_main is None:

        display_data_error()
        st.stop()

    locations = sorted(
        df_main[
            "Pickup_Location"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    vehicles = sorted(
        df_main[
            "Vehicle_Type"
        ]
        .dropna()
        .unique()
        .tolist()
    )

    col1, col2 = (
        st.columns(2)
    )

    with col1:

        selected_locations = (
            st.multiselect(
                "Filter Locations",
                locations,
                default=locations[:3],
            )
        )

    with col2:

        selected_vehicles = (
            st.multiselect(
                "Filter Vehicle Types",
                vehicles,
                default=vehicles,
            )
        )

    filtered_df = df_main[
        (
            df_main[
                "Booking_Status"
            ]
            == "Completed"
        )
        & df_main[
            "Pickup_Location"
        ].isin(
            selected_locations
        )
        & df_main[
            "Vehicle_Type"
        ].isin(
            selected_vehicles
        )
    ]

    # Demand KPIs
    total_completed = int(len(filtered_df))

    hourly_demand = (
        filtered_df
        .groupby("Hour")
        .size()
        .reset_index(
            name="Booking_Count"
        )
    )

    if not hourly_demand.empty:
        peak_row = hourly_demand.loc[hourly_demand["Booking_Count"].idxmax()]
        peak_hour = int(peak_row["Hour"])
        peak_hour_rides = int(peak_row["Booking_Count"])
        active_hours = int(hourly_demand["Hour"].nunique())
        avg_active_hour = total_completed / active_hours if active_hours else 0
    else:
        peak_hour = None
        peak_hour_rides = 0
        avg_active_hour = 0

    show_metric_cards(
        [
            {
                "label": "Completed Historical Rides",
                "value": f"{total_completed:,}",
                "help": "Completed rides included after applying the selected location and vehicle filters.",
            },
            {
                "label": "Busiest Historical Hour",
                "value": f"{peak_hour:02d}:00" if peak_hour is not None else "—",
                "help": "Hour with the highest recorded completed-ride volume in the selected data.",
            },
            {
                "label": "Peak Hour Completed Rides",
                "value": f"{peak_hour_rides:,}",
                "help": "Recorded completed rides during the busiest historical hour.",
            },
            {
                "label": "Avg Rides / Active Hour",
                "value": f"{avg_active_hour:.1f}",
                "help": "Average completed rides across hours that have at least one recorded completed ride.",
            },
        ]
    )

    st.subheader(
        "Hourly Completed-Ride Distribution"
    )

    chart = (
        alt.Chart(
            hourly_demand
        )
        .mark_bar(
            color="#38bdf8"
        )
        .encode(
            x=alt.X(
                "Hour:O",
                title="Hour of Day",
            ),
            y=alt.Y(
                "Booking_Count:Q",
                title="Completed Historical Rides",
            ),
            tooltip=[
                "Hour",
                "Booking_Count",
            ],
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )


# ==============================================================================
# EARNINGS
# ==============================================================================

elif selected_page == "Earnings":

    st.title("💰 Historical Earnings Analysis")

    st.caption(
        "Compare historical earning patterns across selected locations, "
        "hours, and vehicle types."
    )

    if df_main is None:
        display_data_error()
        st.stop()

    st.caption(
        "Historical averages across recorded rides. These figures do not "
        "represent one driver’s actual daily earnings."
    )

    locations = sorted(
        df_main["Pickup_Location"].dropna().unique().tolist()
    )
    vehicles = sorted(
        df_main["Vehicle_Type"].dropna().unique().tolist()
    )

    col1, col2 = st.columns(2)

    with col1:
        selected_locations = st.multiselect(
            "Locations to Compare",
            locations,
            default=locations[:5],
        )

    with col2:
        selected_vehicles = st.multiselect(
            "Vehicle Types to Compare",
            vehicles,
            default=vehicles,
        )

    if not selected_locations:
        st.warning("Select at least one location to compare.")
        st.stop()

    if not selected_vehicles:
        st.warning("Select at least one vehicle type to compare.")
        st.stop()

    completed_df = df_main[
        (df_main["Booking_Status"] == "Completed")
        & df_main["Pickup_Location"].isin(selected_locations)
        & df_main["Vehicle_Type"].isin(selected_vehicles)
    ].copy()

    st.metric(
        "Completed Historical Rides Included",
        f"{len(completed_df):,}",
    )

    if completed_df.empty:
        st.info("No completed historical rides match the selected filters.")
        st.stop()

    # Comparison table comes first so users can read exact values immediately.
    st.subheader("Historical Earnings Comparison")

    comparison_table = (
        completed_df
        .groupby(["Pickup_Location", "Vehicle_Type"])
        .agg(
            Completed_Rides=("Booking_Status", "size"),
            Average_Booking_Value=("Booking_Value", "mean"),
            Average_Ride_Distance=("Ride_Distance", "mean"),
            Average_Value_Per_Km=("Value_Per_Km", "mean"),
        )
        .reset_index()
        .sort_values(
            ["Average_Value_Per_Km", "Completed_Rides"],
            ascending=[False, False],
        )
    )

    comparison_table = comparison_table.rename(
        columns={
            "Pickup_Location": "Location",
            "Vehicle_Type": "Vehicle",
            "Completed_Rides": "Completed Rides",
            "Average_Booking_Value": "Avg Booking Value (₹)",
            "Average_Ride_Distance": "Avg Ride Distance (km)",
            "Average_Value_Per_Km": "Avg Value / Km (₹)",
        }
    )

    st.dataframe(
        comparison_table,
        hide_index=True,
        width="stretch",
        column_config={
            "Avg Booking Value (₹)": st.column_config.NumberColumn(format="₹%.2f"),
            "Avg Ride Distance (km)": st.column_config.NumberColumn(format="%.2f km"),
            "Avg Value / Km (₹)": st.column_config.NumberColumn(format="₹%.2f"),
            "Completed Rides": st.column_config.NumberColumn(format="%d"),
        },
    )

    st.caption(
        "Exact historical comparison across the selected locations and vehicle types."
    )

    # Chart 1: Average Value / Km by Location
    st.subheader("Average Value / Km by Location")

    location_comparison = (
        completed_df
        .groupby("Pickup_Location")
        .agg(
            Average_Value_Per_Km=("Value_Per_Km", "mean"),
            Completed_Rides=("Booking_Status", "size"),
        )
        .reset_index()
        .sort_values("Average_Value_Per_Km", ascending=False)
    )

    location_chart = (
        alt.Chart(location_comparison)
        .mark_bar(color="#38bdf8")
        .encode(
            x=alt.X(
                "Average_Value_Per_Km:Q",
                title="Average Value / Km (₹)",
                axis=alt.Axis(labelColor="#0f172a", titleColor="#0f172a"),
            ),
            y=alt.Y(
                "Pickup_Location:N",
                sort="-x",
                title="Pickup Location",
                axis=alt.Axis(labelColor="#0f172a", titleColor="#0f172a"),
            ),
            tooltip=[
                "Pickup_Location",
                alt.Tooltip("Average_Value_Per_Km:Q", format=".2f"),
                alt.Tooltip("Completed_Rides:Q", format=",d"),
            ],
        )
        .properties(height=max(300, min(700, len(location_comparison) * 28)))
    )

    st.altair_chart(location_chart, use_container_width=True)

    st.caption(
        "Historical average ₹/km by selected pickup location. "
        "Completed-ride volume is shown in the tooltip for context."
    )

    # Chart 2: Average Value / Km by Hour
    st.subheader("Average Value / Km by Hour")

    hourly_comparison = (
        completed_df
        .groupby("Hour")
        .agg(
            Average_Value_Per_Km=("Value_Per_Km", "mean"),
            Completed_Rides=("Booking_Status", "size"),
        )
        .reset_index()
        .sort_values("Hour")
    )

    hourly_chart = (
        alt.Chart(hourly_comparison)
        .mark_line(point=True, color="#10b981")
        .encode(
            x=alt.X(
                "Hour:O",
                sort=list(range(24)),
                title="Hour of Day",
                axis=alt.Axis(labelColor="#0f172a", titleColor="#0f172a"),
            ),
            y=alt.Y(
                "Average_Value_Per_Km:Q",
                title="Average Value / Km (₹)",
                axis=alt.Axis(labelColor="#0f172a", titleColor="#0f172a"),
            ),
            tooltip=[
                alt.Tooltip("Hour:Q", format="02d"),
                alt.Tooltip("Average_Value_Per_Km:Q", format=".2f"),
                alt.Tooltip("Completed_Rides:Q", format=",d"),
            ],
        )
        .properties(height=350)
    )

    st.altair_chart(hourly_chart, use_container_width=True)

    st.caption(
        "Historical average ₹/km by hour across the selected locations "
        "and vehicle types."
    )

    st.caption(
        "All comparisons describe recorded historical completed rides. "
        "They do not indicate guaranteed future earnings or one driver’s daily income."
    )


# ==============================================================================
# CANCELLATIONS
# ==============================================================================

elif selected_page == "Cancellations":

    st.title(
        "🚫 Cancellation Analysis"
    )

    st.caption(
        "Examine historical customer and driver cancellation patterns "
        "across selected locations and vehicle types."
    )

    if df_main is None:

        display_data_error()
        st.stop()

    locations = sorted(
        df_main["Pickup_Location"].dropna().unique().tolist()
    )
    vehicles = sorted(
        df_main["Vehicle_Type"].dropna().unique().tolist()
    )

    col1, col2 = st.columns(2)

    with col1:
        selected_locations = st.multiselect(
            "Locations to Analyze",
            locations,
            default=locations[:5],
        )

    with col2:
        selected_vehicles = st.multiselect(
            "Vehicle Types to Analyze",
            vehicles,
            default=vehicles,
        )

    if not selected_locations:
        st.warning("Select at least one location to analyze.")
        st.stop()

    if not selected_vehicles:
        st.warning("Select at least one vehicle type to analyze.")
        st.stop()

    filtered = df_main[
        df_main["Pickup_Location"].isin(selected_locations)
        & df_main["Vehicle_Type"].isin(selected_vehicles)
    ].copy()

    total_bookings = len(filtered)
    customer_count = int(
        (filtered["Booking_Status"] == "Cancelled by Customer").sum()
    )
    driver_count = int(
        (filtered["Booking_Status"] == "Cancelled by Driver").sum()
    )

    customer_rate = customer_count / total_bookings * 100 if total_bookings else 0
    driver_rate = driver_count / total_bookings * 100 if total_bookings else 0
    combined_rate = (customer_count + driver_count) / total_bookings * 100 if total_bookings else 0

    show_metric_cards(
        [
            {
                "label": "Historical Bookings",
                "value": f"{total_bookings:,}",
                "help": "Recorded bookings included after applying the selected filters.",
            },
            {
                "label": "Customer Cancellation",
                "value": f"{customer_rate:.1f}%",
                "help": "Historical share of bookings cancelled by customers.",
            },
            {
                "label": "Driver Cancellation",
                "value": f"{driver_rate:.1f}%",
                "help": "Historical share of bookings cancelled by drivers.",
            },
            {
                "label": "Combined Cancellation",
                "value": f"{combined_rate:.1f}%",
                "help": "Historical share of bookings cancelled by either side.",
            },
        ]
    )

    st.subheader(
        "Cancellation Rate by Pickup Location"
    )

    location_total = (
        filtered.groupby("Pickup_Location")
        .size()
        .reset_index(name="Total_Bookings")
    )

    customer = (
        filtered[filtered["Booking_Status"] == "Cancelled by Customer"]
        .groupby("Pickup_Location")
        .size()
        .rename("Customer_Cancellations")
    )

    driver = (
        filtered[filtered["Booking_Status"] == "Cancelled by Driver"]
        .groupby("Pickup_Location")
        .size()
        .rename("Driver_Cancellations")
    )

    cancel_chart_df = location_total.set_index("Pickup_Location")
    cancel_chart_df["Customer_Cancellations"] = customer
    cancel_chart_df["Driver_Cancellations"] = driver
    cancel_chart_df = cancel_chart_df.fillna(0).reset_index()

    cancel_chart_df["Customer Rate"] = (
        cancel_chart_df["Customer_Cancellations"]
        / cancel_chart_df["Total_Bookings"]
        * 100
    )
    cancel_chart_df["Driver Rate"] = (
        cancel_chart_df["Driver_Cancellations"]
        / cancel_chart_df["Total_Bookings"]
        * 100
    )
    cancel_chart_df["Combined Rate"] = (
        cancel_chart_df["Customer_Cancellations"]
        + cancel_chart_df["Driver_Cancellations"]
    ) / cancel_chart_df["Total_Bookings"] * 100

    cancel_chart_df = cancel_chart_df.sort_values(
        ["Combined Rate", "Total_Bookings"],
        ascending=[False, False],
    ).head(15)

    chart_long = cancel_chart_df.melt(
        id_vars=["Pickup_Location", "Total_Bookings"],
        value_vars=["Customer Rate", "Driver Rate"],
        var_name="Cancellation Type",
        value_name="Rate",
    )

    chart = (
        alt.Chart(chart_long)
        .mark_bar()
        .encode(
            x=alt.X(
                "Rate:Q",
                title="Cancellation Rate (%)",
                axis=alt.Axis(labelColor="#0f172a", titleColor="#0f172a"),
            ),
            y=alt.Y(
                "Pickup_Location:N",
                sort=cancel_chart_df["Pickup_Location"].tolist(),
                title="Pickup Location",
                axis=alt.Axis(labelColor="#0f172a", titleColor="#0f172a"),
            ),
            color=alt.Color(
                "Cancellation Type:N",
                title="Cancellation Type",
            ),
            tooltip=[
                "Pickup_Location",
                alt.Tooltip("Cancellation Type:N", title="Type"),
                alt.Tooltip("Rate:Q", format=".1f", title="Rate (%)"),
                alt.Tooltip("Total_Bookings:Q", format=",d", title="Bookings"),
            ],
        )
        .properties(
            height=max(350, min(650, len(cancel_chart_df) * 32)),
        )
    )

    st.altair_chart(
        chart,
        use_container_width=True,
    )

    st.caption(
        "Historical cancellation rates across the selected filters. "
        "Rates describe recorded bookings and do not indicate future cancellation outcomes."
    )


# ==============================================================================
# DEEP ANALYTICS
# ==============================================================================

# ==============================================================================
# AI ASSISTANT
# ==============================================================================

elif selected_page == "AI Assistant":

    st.title(
        "🤖 AI Mobility Assistant"
    )

    st.caption(
        "Explore historical patterns and ask analytical "
        "questions about the ride data."
    )

    active_context = (
        st.session_state.get(
            "home_last_context"
        )
    )

    active_result = (
        st.session_state.get(
            "home_last_result"
        )
    )

    if (
        active_context
        and active_result is not None
    ):

        st.info(
            "Active historical context: "
            f"{active_context.get('location')} | "
            f"{active_context.get('hour'):02d}:00 | "
            f"{active_context.get('day')} | "
            f"{active_context.get('vehicle_type')}"
        )

    if "messages" not in st.session_state:

        st.session_state.messages = []

    for message in (
        st.session_state.messages
    ):

        with st.chat_message(
            message["role"]
        ):

            st.markdown(
                message["content"]
            )

    user_prompt = st.chat_input(
        "Ask about historical completion, cancellations, or earnings..."
    )

    if user_prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_prompt,
            }
        )

        with st.chat_message(
            "user"
        ):

            st.markdown(
                user_prompt
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "Analyzing historical records..."
            ):

                assistant_reply = (
                    run_gemini_agent_loop(
                        user_query=user_prompt,
                        active_context_result=(
                            active_result
                        ),
                    )
                )

            st.markdown(
                assistant_reply
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": assistant_reply,
            }
        )