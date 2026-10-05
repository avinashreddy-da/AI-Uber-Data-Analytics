import os
import json
import time

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st

from dotenv import load_dotenv
from google import genai
from google.genai import types

import importlib.util


def _load_local_database_module():
    """Load the project's database.py explicitly, avoiding name collisions with other modules."""
    module_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "database.py",
    )

    if not os.path.exists(module_path):
        return None

    try:
        spec = importlib.util.spec_from_file_location(
            "_mobilitylens_database",
            module_path,
        )

        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    except Exception:
        return None


db = _load_local_database_module()


# ==============================================================================
# CONFIG
# ==============================================================================

load_dotenv()

st.set_page_config(
    page_title="MobilityLens | AI Mobility Analytics",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==============================================================================
# CONSTANTS
# ==============================================================================

FAIRFARE_PATH = os.path.join(
    "data",
    "fairfare_ride_demand_dataset.csv",
)

SUPPORTED_CITY_COORDS = {
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867},
    "Delhi": {"lat": 28.6139, "lon": 77.2090},
    "Chennai": {"lat": 13.0827, "lon": 80.2707},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777},
}

ZONE_PATH = os.path.join(
    "data",
    "mobilitylens_zones.csv",
)

ZONE_MAX_DISTANCE_KM = 6.0

DB_PATH = os.path.join(
    "data",
    "mobilitylens.db",
)


def database_available():
    """Return True only when the local SQLite backend and required entry points are available."""
    if not os.path.exists(DB_PATH) or db is None:
        return False

    required_functions = (
        "get_fairfare_rows",
        "get_zone_context_sql",
        "get_zone_event_signal_sql",
        "get_zone_demand_scores_sql",
        "get_city_summary_sql",
        "get_city_list",
        "get_ride_type_list",
        "get_city_demand_sql",
        "get_hourly_demand_sql",
        "get_city_earnings_sql",
        "get_city_cancellations_sql",
        "get_zone_rows_sql",
        "get_zone_demand_sql",
        "get_zone_earnings_sql",
        "get_zone_cancellations_sql",
    )

    return all(
        hasattr(db, name)
        for name in required_functions
    )


def zoned_database_available():
    """Return True when the SQL backend also contains rides_zoned."""
    if not database_available():
        return False

    if hasattr(db, "table_exists"):
        try:
            return bool(
                db.table_exists("rides_zoned")
            )
        except Exception:
            return False

    try:
        return bool(
            db.get_zone_context_sql
        )
    except Exception:
        return False


CITY_BOUNDS = {
    "Hyderabad": (
        17.20,
        17.60,
        78.20,
        78.65,
    ),
    "Delhi": (
        28.40,
        28.90,
        76.80,
        77.50,
    ),
    "Chennai": (
        12.75,
        13.30,
        80.05,
        80.35,
    ),
    "Bangalore": (
        12.75,
        13.25,
        77.30,
        77.85,
    ),
    "Mumbai": (
        18.75,
        19.35,
        72.70,
        73.15,
    ),
}

CITY_ALIASES = {
    "hyderabad": "Hyderabad",
    "secunderabad": "Hyderabad",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "gurgaon": "Delhi",
    "gurugram": "Delhi",
    "noida": "Delhi",
    "ghaziabad": "Delhi",
    "faridabad": "Delhi",
    "chennai": "Chennai",
    "madras": "Chennai",
    "bangalore": "Bangalore",
    "bengaluru": "Bangalore",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
}

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def csv_day_of_week_code(day_name):
    """Map UI weekday name to FairFare Day_of_Week (Monday=0)."""
    if day_name is None or (
        isinstance(day_name, float)
        and pd.isna(day_name)
    ):
        return None

    if isinstance(day_name, (int, float)):
        value = int(day_name)

        if 0 <= value <= 6:
            return value

        return None

    value = str(day_name).strip()

    if not value:
        return None

    lowered = value.lower()

    for code, name in enumerate(DAYS):
        if name.lower() == lowered:
            return code

    try:
        code = int(float(value))

        if 0 <= code <= 6:
            return code

    except (ValueError, TypeError):
        pass

    return None


RIDE_TYPE_ORDER = [
    "Economy",
    "Premium",
    "Luxury",
]


# ==============================================================================
# GLOBAL CSS
# ==============================================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }

    [data-testid="stHeader"] {
        background-color: #0f172a;
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important;
        border-right: 1px solid #334155;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 4px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        color: #e2e8f0 !important;
        font-size: 0.92rem !important;
        font-weight: 500 !important;
        padding: 9px 12px !important;
        margin: 2px 0 !important;
        border-radius: 8px !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: rgba(56, 189, 248, 0.08) !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background-color: rgba(56, 189, 248, 0.14) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border-left: 3px solid #38bdf8 !important;
        padding-left: 9px !important;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label p {
        color: inherit !important;
        font-weight: inherit !important;
        margin: 0 !important;
    }

    section[data-testid="stSidebar"] input {
        display: none !important;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
    }

    div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] span,
div[data-testid="stMarkdownContainer"] strong,
div[data-testid="stMarkdownContainer"] li,
div[data-testid="stMarkdownContainer"] li *,
div[data-testid="stCaptionContainer"] p,
div[data-testid="stCaptionContainer"] span,
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

    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        border: 1px solid #475569 !important;
        color: #f8fafc !important;
        border-radius: 8px !important;
    }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] span,
    div[data-testid="stSelectbox"] div[data-baseweb="select"] input {
        color: #f8fafc !important;
    }

    div[data-testid="stMultiSelect"] [data-baseweb="tag"],
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] * {
        color: #f8fafc !important;
        background-color: #334155 !important;
    }

    div[data-baseweb="popover"],
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li {
        background-color: #1e293b !important;
        color: #f8fafc !important;
    }

    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background-color: #334155 !important;
        color: #ffffff !important;
    }

    div[data-testid="stMetric"] {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *,
    div[data-testid="stMetricDelta"],
    div[data-testid="stMetricDelta"] * {
        color: #f8fafc !important;
    }

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

    div[data-testid="stChatInput"] {
        background-color: #1e293b !important;
        border: 1px solid #475569 !important;
        border-radius: 10px !important;
        box-shadow: none !important;
    }

    div[data-testid="stChatInput"] > div,
    div[data-testid="stChatInput"] textarea {
        background-color: #1e293b !important;
        border: none !important;
        color: #f8fafc !important;
        caret-color: #f8fafc !important;
    }

    div[data-testid="stChatInput"] textarea::placeholder {
        color: #94a3b8 !important;
        opacity: 1 !important;
    }

    div[data-testid="stChatInput"] svg {
        color: #cbd5e1 !important;
        fill: #cbd5e1 !important;
    }

    details {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 10px !important;
    }

    details summary {
        color: #f8fafc !important;
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stDataFrame"] * {
        color: #f8fafc !important;
    }

    .live-context-label {
        font-size: 0.72rem;
        line-height: 1.1;
        color: #cbd5e1;
        margin-bottom: 4px;
        min-height: 28px;
        display: flex;
        align-items: flex-end;
    }

    .live-context-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 12px;
        min-height: 95px;
    }

    .live-context-value {
        color: #f8fafc;
        font-size: 1.05rem;
        font-weight: 700;
        overflow-wrap: anywhere;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# DATA LOADING
# ==============================================================================

@st.cache_data
def load_fairfare_data(file_path):
    if not os.path.exists(file_path):
        return None

    try:
        data = pd.read_csv(file_path)
    except Exception:
        return None

    required = {
        "City",
        "Date",
        "Day_of_Week",
        "Ride_Distance_KM",
        "Ride_Type",
        "Weather",
        "Event",
        "Available_Drivers",
        "Demand_Level",
        "Surge_Multiplier",
        "Final_Fare",
        "Hour_of_Day",
        "Is_Weekend",
        "Cancellation_Rate",
        "Demand_Score",
        "Driver_Availability",
        "Traffic_Delay",
        "Cancellation_Probability",
    }

    missing = required.difference(data.columns)

    if missing:
        return None

    data["City"] = (
        data["City"]
        .astype(str)
        .str.strip()
    )

    data["Date"] = pd.to_datetime(
        data["Date"],
        errors="coerce",
    )

    data["Day_of_Week"] = (
        data["Day_of_Week"]
        .astype(str)
        .str.strip()
    )

    data["Ride_Type"] = (
        data["Ride_Type"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    data["Weather"] = (
        data["Weather"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    data["Event"] = (
        data["Event"]
        .fillna("No Event Recorded")
        .astype(str)
        .str.strip()
    )

    numeric_columns = [
        "Latitude",
        "Longitude",
        "Ride_Distance_KM",
        "Available_Drivers",
        "Surge_Multiplier",
        "Final_Fare",
        "Hour_of_Day",
        "Is_Weekend",
        "Driver_Performance_Score",
        "Driver_XP",
        "Cancellation_Rate",
        "Demand_Score",
        "Driver_Availability",
        "Traffic_Delay",
        "Cancellation_Probability",
        "Driver_Trust_Score",
        "Rider_Trust_Score",
        "Leaderboard_Rank",
    ]

    for column in numeric_columns:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

    data["Fare_Per_KM"] = np.where(
        data["Ride_Distance_KM"] > 0,
        data["Final_Fare"]
        / data["Ride_Distance_KM"],
        np.nan,
    )

    return data


fairfare_df = load_fairfare_data(
    FAIRFARE_PATH
)


# ==============================================================================
# GENERAL HELPERS
# ==============================================================================

def normalize_city_name(city):
    if city is None:
        return None

    cleaned = str(city).strip()

    if not cleaned:
        return None

    return CITY_ALIASES.get(
        cleaned.lower(),
        cleaned,
    )


def show_metric_cards(metrics):
    """Display KPI cards in rows of four."""
    for start in range(
        0,
        len(metrics),
        4,
    ):
        batch = metrics[start:start + 4]

        columns = st.columns(4)

        for column, metric in zip(
            columns,
            batch,
        ):
            with column:
                st.metric(
                    label=metric["label"],
                    value=metric["value"],
                    help=metric.get("help"),
                )


def format_number(
    value,
    decimals=1,
):
    if value is None or pd.isna(value):
        return "—"

    return f"{float(value):,.{decimals}f}"


def rate_to_percent(series):
    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    if values.dropna().empty:
        return values

    if values.abs().max() <= 1.0:
        return values * 100

    return values


def fairfare_filter(
    city=None,
    cities=None,
    hour=None,
    day_name=None,
    ride_types=None,
    weather=None,
):
    """Historical FairFare row access."""

    if database_available():
        try:
            requested_cities = None

            if cities is not None:
                requested_cities = [
                    normalize_city_name(value)
                    for value in cities
                ]

            return db.get_fairfare_rows(
                city=(
                    normalize_city_name(city)
                    if city
                    else None
                ),
                cities=requested_cities,
                hour=hour,
                day_name=day_name,
                ride_types=ride_types,
                weather=weather,
            )

        except Exception:
            pass

    if fairfare_df is None:
        return pd.DataFrame()

    data = fairfare_df.copy()

    if cities is not None:
        requested_cities = [
            normalize_city_name(value)
            for value in cities
        ]

        if not requested_cities:
            return pd.DataFrame()

        data = data[
            data["City"].isin(
                requested_cities
            )
        ]

    elif city:
        data = data[
            data["City"]
            == normalize_city_name(city)
        ]

    if hour is not None:
        data = data[
            data["Hour_of_Day"]
            == int(hour)
        ]

    if day_name:
        data = data[
            data["Day_of_Week"]
            .astype(str)
            .str.strip()
            .str.lower()
            == str(day_name)
            .strip()
            .lower()
        ]

    if ride_types:
        data = data[
            data["Ride_Type"].isin(
                ride_types
            )
        ]

    if weather:
        data = data[
            data["Weather"]
            .astype(str)
            .str.lower()
            == str(weather).lower()
        ]

    return data


# ==============================================================================
# DEMONSTRATION ZONES / HISTORICAL LOCATION LAYER
# ==============================================================================

@st.cache_data
def load_zone_data(file_path):
    if not os.path.exists(file_path):
        return None

    try:
        zones = pd.read_csv(file_path)
    except Exception:
        return None

    required = {
        "city",
        "zone",
        "lat",
        "lon",
        "zone_type",
    }

    if not required.issubset(
        zones.columns
    ):
        return None

    zones = zones.copy()

    zones["city"] = (
        zones["city"]
        .astype(str)
        .str.strip()
    )

    zones["zone"] = (
        zones["zone"]
        .astype(str)
        .str.strip()
    )

    zones["zone_type"] = (
        zones["zone_type"]
        .astype(str)
        .str.strip()
    )

    zones["lat"] = pd.to_numeric(
        zones["lat"],
        errors="coerce",
    )

    zones["lon"] = pd.to_numeric(
        zones["lon"],
        errors="coerce",
    )

    zones = zones.dropna(
        subset=[
            "lat",
            "lon",
        ]
    ).copy()

    zones = zones[
        zones["city"].isin(
            SUPPORTED_CITY_COORDS
        )
    ].copy()

    return zones


def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2,
):
    lat1 = np.radians(
        np.asarray(
            lat1,
            dtype=float,
        )
    )

    lon1 = np.radians(
        np.asarray(
            lon1,
            dtype=float,
        )
    )

    lat2 = np.radians(
        np.asarray(
            lat2,
            dtype=float,
        )
    )

    lon2 = np.radians(
        np.asarray(
            lon2,
            dtype=float,
        )
    )

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2.0) ** 2
    )

    return (
        6371.0088
        * 2
        * np.arcsin(
            np.sqrt(a)
        )
    )


def assign_fairfare_zones(
    data,
    zones,
):
    """
    Create a zone-assigned view without altering
    the raw FairFare data.
    """

    if (
        data is None
        or data.empty
        or zones is None
        or zones.empty
    ):
        return (
            pd.DataFrame(),
            {
                "input_records": (
                    0
                    if data is None
                    else int(len(data))
                ),
                "coordinate_valid_records": 0,
                "zone_assigned_records": 0,
                "excluded_records": (
                    0
                    if data is None
                    else int(len(data))
                ),
            },
        )

    work = data.copy()

    work["Latitude"] = pd.to_numeric(
        work["Latitude"],
        errors="coerce",
    )

    work["Longitude"] = pd.to_numeric(
        work["Longitude"],
        errors="coerce",
    )

    assigned_parts = []
    valid_total = 0

    for city_value in sorted(
        work["City"]
        .dropna()
        .unique()
        .tolist()
    ):
        city = normalize_city_name(
            city_value
        )

        city_rows = work[
            work["City"]
            == city_value
        ].copy()

        city_zones = zones[
            zones["city"]
            == city
        ].copy()

        if (
            city_rows.empty
            or city_zones.empty
        ):
            continue

        bounds = CITY_BOUNDS.get(
            city
        )

        if bounds:
            (
                min_lat,
                max_lat,
                min_lon,
                max_lon,
            ) = bounds

            valid_mask = (
                city_rows["Latitude"]
                .between(
                    min_lat,
                    max_lat,
                )
                & city_rows["Longitude"]
                .between(
                    min_lon,
                    max_lon,
                )
            )

        else:
            valid_mask = (
                city_rows["Latitude"]
                .notna()
                & city_rows["Longitude"]
                .notna()
            )

        valid_rows = city_rows[
            valid_mask
        ].copy()

        valid_total += int(
            len(valid_rows)
        )

        if valid_rows.empty:
            continue

        zone_lat = (
            city_zones["lat"]
            .to_numpy()
        )

        zone_lon = (
            city_zones["lon"]
            .to_numpy()
        )

        distances = np.column_stack(
            [
                haversine_km(
                    valid_rows[
                        "Latitude"
                    ].to_numpy(),
                    valid_rows[
                        "Longitude"
                    ].to_numpy(),
                    zlat,
                    zlon,
                )
                for zlat, zlon in zip(
                    zone_lat,
                    zone_lon,
                )
            ]
        )

        nearest_idx = (
            distances.argmin(
                axis=1
            )
        )

        nearest_dist = distances[
            np.arange(
                len(valid_rows)
            ),
            nearest_idx,
        ]

        nearest = (
            city_zones
            .iloc[
                nearest_idx
            ]
            .reset_index(
                drop=True
            )
        )

        valid_rows["Zone"] = (
            nearest["zone"]
            .to_numpy()
        )

        valid_rows["Zone_Type"] = (
            nearest["zone_type"]
            .to_numpy()
        )

        valid_rows[
            "Zone_Latitude"
        ] = nearest["lat"].to_numpy()

        valid_rows[
            "Zone_Longitude"
        ] = nearest["lon"].to_numpy()

        valid_rows[
            "Zone_Distance_KM"
        ] = nearest_dist

        valid_rows = valid_rows[
            valid_rows[
                "Zone_Distance_KM"
            ]
            <= ZONE_MAX_DISTANCE_KM
        ].copy()

        if not valid_rows.empty:
            assigned_parts.append(
                valid_rows
            )

    if assigned_parts:
        assigned = pd.concat(
            assigned_parts,
            ignore_index=True,
        )
    else:
        assigned = pd.DataFrame()

    return (
        assigned,
        {
            "input_records": int(
                len(work)
            ),
            "coordinate_valid_records": int(
                valid_total
            ),
            "zone_assigned_records": int(
                len(assigned)
            ),
            "excluded_records": int(
                len(work)
                - len(assigned)
            ),
        },
    )


fairfare_zones = load_zone_data(
    ZONE_PATH
)

fairfare_zoned_df, zone_assignment_stats = (
    assign_fairfare_zones(
        fairfare_df,
        fairfare_zones,
    )
)


# ==============================================================================
# CITY DETECTION
# ==============================================================================

@st.cache_data(ttl=1800)
def geolocate_ip(user_ip):
    if not user_ip:
        return None

    try:
        response = requests.get(
            f"https://ipwho.is/{user_ip}",
            timeout=5,
        )

        response.raise_for_status()

        payload = response.json()

        if not payload.get(
            "success",
            False,
        ):
            return None

        return {
            "city": normalize_city_name(
                payload.get("city")
            ),
            "latitude": payload.get(
                "latitude"
            ),
            "longitude": payload.get(
                "longitude"
            ),
            "source": (
                "Approximate network location"
            ),
        }

    except Exception:
        return None


def detect_current_location():
    forced_city = normalize_city_name(
        os.getenv(
            "RIDEINTEL_CITY",
            "",
        ).strip()
    )

    if forced_city:
        forced_lat = os.getenv(
            "RIDEINTEL_LAT",
            "",
        ).strip()

        forced_lon = os.getenv(
            "RIDEINTEL_LON",
            "",
        ).strip()

        coords = SUPPORTED_CITY_COORDS.get(
            forced_city,
            {},
        )

        try:
            latitude = (
                float(forced_lat)
                if forced_lat
                else coords.get("lat")
            )

            longitude = (
                float(forced_lon)
                if forced_lon
                else coords.get("lon")
            )

        except ValueError:
            latitude = coords.get("lat")
            longitude = coords.get("lon")

        return {
            "city": forced_city,
            "latitude": latitude,
            "longitude": longitude,
            "source": "Local testing override",
        }

    try:
        user_ip = getattr(
            st.context,
            "ip_address",
            None,
        )
    except Exception:
        user_ip = None

    return geolocate_ip(
        user_ip
    )


def detect_current_city():
    location = detect_current_location()

    return (
        location.get("city")
        if location
        else None
    )


# ==============================================================================
# LIVE WEATHER
# ==============================================================================

def weather_code_to_category(
    weather_code
):
    try:
        code = int(
            weather_code
        )
    except (
        TypeError,
        ValueError,
    ):
        return "Unknown"

    if code == 0:
        return "Clear"

    if code in {
        1,
        2,
        3,
        45,
        48,
    }:
        return "Cloudy"

    if code in {
        51,
        53,
        55,
        56,
        57,
        61,
        63,
        65,
        66,
        67,
        80,
        81,
        82,
    }:
        return "Rainy"

    if code in {
        71,
        73,
        75,
        77,
        85,
        86,
        95,
        96,
        99,
    }:
        return "Stormy"

    return "Unknown"


@st.cache_data(ttl=600)
def get_live_weather(city):
    city = normalize_city_name(
        city
    )

    coords = SUPPORTED_CITY_COORDS.get(
        city
    )

    if not coords:
        return {
            "available": False,
            "message": (
                "Live weather is not "
                "available for this city."
            ),
        }

    try:
        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "current": (
                    "temperature_2m,"
                    "relative_humidity_2m,"
                    "apparent_temperature,"
                    "precipitation,"
                    "weather_code,"
                    "wind_speed_10m"
                ),
                "timezone": "auto",
            },
            timeout=8,
        )

        response.raise_for_status()

        current = response.json().get(
            "current",
            {},
        )

        weather_code = current.get(
            "weather_code"
        )

        return {
            "available": True,
            "city": city,
            "temperature_c": current.get(
                "temperature_2m"
            ),
            "feels_like_c": current.get(
                "apparent_temperature"
            ),
            "humidity": current.get(
                "relative_humidity_2m"
            ),
            "precipitation_mm": current.get(
                "precipitation"
            ),
            "wind_speed_kmh": current.get(
                "wind_speed_10m"
            ),
            "weather_code": weather_code,
            "weather_category": (
                weather_code_to_category(
                    weather_code
                )
            ),
            "observed_at": current.get(
                "time"
            ),
        }

    except Exception:
        return {
            "available": False,
            "message": (
                "Live weather request failed."
            ),
        }


# ==============================================================================
# LIVE TRAFFIC
# ==============================================================================

@st.cache_data(ttl=300)
def get_live_traffic(city):
    city = normalize_city_name(
        city
    )

    coords = SUPPORTED_CITY_COORDS.get(
        city
    )

    api_key = os.getenv(
        "TOMTOM_API_KEY",
        "",
    ).strip()

    if not coords:
        return {
            "available": False,
            "message": (
                "Live traffic is not "
                "available for this city."
            ),
        }

    if not api_key:
        return {
            "available": False,
            "message": (
                "Live traffic requires "
                "TOMTOM_API_KEY."
            ),
        }

    try:
        response = requests.get(
            "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json",
            params={
                "point": (
                    f"{coords['lat']},"
                    f"{coords['lon']}"
                ),
                "unit": "KMPH",
                "key": api_key,
            },
            timeout=8,
        )

        response.raise_for_status()

        flow = response.json().get(
            "flowSegmentData",
            {},
        )

        current_speed = flow.get(
            "currentSpeed"
        )

        free_flow_speed = flow.get(
            "freeFlowSpeed"
        )

        current_time = flow.get(
            "currentTravelTime"
        )

        free_flow_time = flow.get(
            "freeFlowTravelTime"
        )

        delay_seconds = None

        if (
            current_time is not None
            and free_flow_time is not None
        ):
            delay_seconds = max(
                0,
                float(current_time)
                - float(free_flow_time),
            )

        return {
            "available": True,
            "city": city,
            "current_speed_kmh": current_speed,
            "free_flow_speed_kmh": free_flow_speed,
            "delay_minutes": (
                delay_seconds / 60
                if delay_seconds is not None
                else None
            ),
            "congestion_ratio": (
                float(current_speed)
                / float(free_flow_speed)
                if current_speed
                and free_flow_speed
                else None
            ),
        }

    except requests.exceptions.HTTPError as e:
        return {
            "available": False,
            "message": f"TomTom API error: {e}",
        }

    except requests.exceptions.RequestException as e:

        return {
            "available": False,
            "message": f"TomTom connection error: {e}",
        }

    except Exception as e:
        return {
            "available": False,
            "message": f"Traffic processing error: {e}",
        }


# ==============================================================================
# HISTORICAL FAIRFARE CONTEXT
# ==============================================================================

def get_fairfare_historical_context(
    city,
    hour,
    day_name,
):
    """
    Match current situation using city + hour + weekday.
    """

    exact = fairfare_filter(
        city=city,
        hour=hour,
        day_name=day_name,
    )

    match_level = (
        "City + hour + weekday"
    )

    data = exact

    if data.empty:
        data = fairfare_filter(
            city=city,
            hour=hour,
        )

        match_level = "City + hour"

    if data.empty:
        data = fairfare_filter(
            city=city,
            day_name=day_name,
        )

        match_level = "City + weekday"

    if data.empty:
        return {
            "found": False,
            "message": (
                f"No FairFare historical "
                f"records are available "
                f"for {city}."
            ),
        }

    cancellation_rate = rate_to_percent(
        data["Cancellation_Rate"]
    )

    cancellation_probability = (
        rate_to_percent(
            data[
                "Cancellation_Probability"
            ]
        )
    )

    return {
        "found": True,
        "source": (
            "FairFare synthetic "
            "multi-city dataset"
        ),
        "city": city,
        "hour": int(hour),
        "day_name": day_name,
        "match_level": match_level,
        "sample_size": int(len(data)),
        "avg_demand_score": float(
            data["Demand_Score"].mean()
        ),
        "avg_available_drivers": float(
            data[
                "Available_Drivers"
            ].mean()
        ),
        "avg_driver_availability": float(
            data[
                "Driver_Availability"
            ].mean()
        ),
        "avg_final_fare": float(
            data["Final_Fare"].mean()
        ),
        "avg_fare_per_km": float(
            data["Fare_Per_KM"].mean()
        ),
        "avg_traffic_delay": float(
            data["Traffic_Delay"].mean()
        ),
        "avg_cancellation_rate": float(
            cancellation_rate.mean()
        ),
        "avg_cancellation_probability": float(
            cancellation_probability.mean()
        ),
        "weather_mix": (
            data["Weather"]
            .value_counts()
            .rename_axis("Weather")
            .reset_index(
                name="Records"
            )
            .to_dict(
                orient="records"
            )
        ),
        "demand_levels": (
            data["Demand_Level"]
            .value_counts()
            .rename_axis(
                "Demand_Level"
            )
            .reset_index(
                name="Records"
            )
            .to_dict(
                orient="records"
            )
        ),
        "ride_type_mix": (
            data["Ride_Type"]
            .value_counts()
            .rename_axis(
                "Ride_Type"
            )
            .reset_index(
                name="Records"
            )
            .to_dict(
                orient="records"
            )
        ),
        "event_mix": (
            data["Event"]
            .value_counts()
            .head(8)
            .rename_axis("Event")
            .reset_index(
                name="Records"
            )
            .to_dict(
                orient="records"
            )
        ),
    }


# ==============================================================================
# ZONE / DEMAND HELPERS
# ==============================================================================

def filter_zoned_data(
    city,
    zone,
    ride_type="All Ride Types",
    hour=None,
    day_name=None,
):
    if (
        fairfare_zoned_df is None
        or fairfare_zoned_df.empty
    ):
        return pd.DataFrame()

    data = fairfare_zoned_df[
        (
            fairfare_zoned_df["City"]
            == city
        )
        & (
            fairfare_zoned_df["Zone"]
            == zone
        )
    ].copy()

    if hour is not None:
        data = data[
            data["Hour_of_Day"]
            == int(hour)
        ]

    day_code = csv_day_of_week_code(day_name)

    if day_code is not None:
        data = data[
            pd.to_numeric(
                data["Day_of_Week"],
                errors="coerce",
            )
            == day_code
        ]

    if (
        ride_type
        and ride_type != "All Ride Types"
    ):
        data = data[
            data["Ride_Type"]
            == ride_type
        ]

    return data


def get_demand_level_breakdown(
    data
):
    """Readable Low/Medium/High table."""

    labels = [
        "Low",
        "Medium",
        "High",
    ]

    if (
        data is None
        or data.empty
    ):
        return pd.DataFrame(
            {
                "Demand Level": labels,
                "Records": [
                    0,
                    0,
                    0,
                ],
                "Share": [
                    0.0,
                    0.0,
                    0.0,
                ],
            }
        )

    raw = (
        data["Demand_Level"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    normalized = pd.Series(
        index=data.index,
        dtype="object",
    )

    normalized[
        raw.str.contains(
            "low",
            na=False,
        )
    ] = "Low"

    normalized[
        raw.str.contains(
            "medium",
            na=False,
        )
    ] = "Medium"

    normalized[
        raw.str.contains(
            "high",
            na=False,
        )
    ] = "High"

    mapped_count = int(
        normalized.notna().sum()
    )

    if mapped_count < max(
        3,
        int(len(data) * 0.5),
    ):
        scores = pd.to_numeric(
            data["Demand_Score"],
            errors="coerce",
        )

        scores = scores.fillna(
            scores.median()
        )

        q1 = scores.quantile(
            1 / 3
        )

        q2 = scores.quantile(
            2 / 3
        )

        normalized = pd.Series(
            np.select(
                [
                    scores <= q1,
                    scores <= q2,
                ],
                [
                    "Low",
                    "Medium",
                ],
                default="High",
            ),
            index=data.index,
        )

    counts = normalized.value_counts()

    result = pd.DataFrame(
        {
            "Demand Level": labels
        }
    )

    result["Records"] = (
        result["Demand Level"]
        .map(counts)
        .fillna(0)
        .astype(int)
    )

    result["Share"] = (
        result["Records"]
        / len(data)
        * 100
    ).round(1)

    return result


# ==============================================================================
# FIXED ZONE CONTEXT
# ==============================================================================

def _build_historical_context_result(
    data,
    city,
    zone,
    hour,
    day_name,
    ride_type,
    basis,
    location_basis,
):
    """
    Build the common historical KPI structure.
    """

    if data is None or data.empty:
        return None

    cancellation = rate_to_percent(
        data["Cancellation_Rate"]
    )

    cancellation_probability = (
        rate_to_percent(
            data[
                "Cancellation_Probability"
            ]
        )
    )

    demand_breakdown = (
        get_demand_level_breakdown(
            data
        ).to_dict(
            orient="records"
        )
    )

    return {
        "found": True,
        "city": city,
        "zone": zone,
        "hour": int(hour),
        "day_name": day_name,
        "ride_type": ride_type,
        "basis": basis,
        "location_basis": location_basis,
        "sample_size": int(
            len(data)
        ),
        "bookings": int(
            len(data)
        ),
        "completed_rides_estimated": max(
            0.0,
            len(data)
            * (
                1.0
                - float(
                    cancellation.mean()
                )
                / 100.0
            ),
        ),
        "avg_demand_score": float(
            data["Demand_Score"].mean()
        ),
        "avg_available_drivers": float(
            data[
                "Available_Drivers"
            ].mean()
        ),
        "avg_driver_availability": float(
            data[
                "Driver_Availability"
            ].mean()
        ),
        "avg_fare": float(
            data["Final_Fare"].mean()
        ),
        "avg_fare_per_km": float(
            data["Fare_Per_KM"].mean()
        ),
        "avg_ride_km": float(
            data[
                "Ride_Distance_KM"
            ].mean()
        ),
        "cancellation_rate": float(
            cancellation.mean()
        ),
        "cancellation_probability": float(
            cancellation_probability.mean()
        ),
        "avg_traffic_delay": float(
            data[
                "Traffic_Delay"
            ].mean()
        ),
        "demand_breakdown": demand_breakdown,
        "weather_mix": (
            data["Weather"]
            .value_counts()
            .rename_axis(
                "Weather"
            )
            .reset_index(
                name="Records"
            )
            .to_dict(
                orient="records"
            )
        ),
        "event_signal_available": False,
    }


def get_zone_context(
    city,
    zone,
    hour,
    day_name,
    ride_type="All Ride Types",
    min_records=30,
):
    """
    Historical context selection.

    Priority:

    1. Exact place + hour + weekday
    2. Place + hour
    3. Place + all times
    4. City + hour + weekday
    5. City + hour
    6. City + all times

    IMPORTANT:
    The exact weekday/hour combination does NOT require
    30 records. Even one matching record is accepted.

    This prevents the old bug where the weekday filter
    was silently dropped because the exact group had
    fewer than min_records.
    """

    # ------------------------------------------------------------------
    # SQL backend
    # ------------------------------------------------------------------

    if zoned_database_available():
        try:
            result = db.get_zone_context_sql(
                city,
                zone,
                hour,
                day_name,
                (
                    None
                    if ride_type
                    == "All Ride Types"
                    else [ride_type]
                ),
                min_records,
            )

            if result.get("found"):
                result[
                    "location_basis"
                ] = (
                    "Zone-level historical records"
                )

                return result

        except Exception:
            pass

        # --------------------------------------------------------------
        # If SQL zone data has no match, use city-level SQL fallback.
        # --------------------------------------------------------------

        try:
            if hasattr(
                db,
                "get_city_context_sql",
            ):
                city_result = (
                    db.get_city_context_sql(
                        city,
                        hour,
                        day_name,
                        ride_type,
                        min_records,
                    )
                )

                if city_result.get(
                    "found"
                ):
                    city_result[
                        "zone"
                    ] = zone

                    city_result[
                        "location_basis"
                    ] = (
                        "City-level historical fallback"
                    )

                    return city_result

        except Exception:
            pass

    # ------------------------------------------------------------------
    # Python / CSV fallback
    # ------------------------------------------------------------------

    if (
        fairfare_df is None
        or fairfare_df.empty
    ):
        return {
            "found": False,
            "message": (
                "Historical FairFare "
                "data is unavailable."
            ),
        }

    # ------------------------------------------------------------------
    # ZONE DATA
    # ------------------------------------------------------------------

    zone_base = pd.DataFrame()

    if (
        fairfare_zoned_df is not None
        and not fairfare_zoned_df.empty
    ):
        zone_base = fairfare_zoned_df[
            (
                fairfare_zoned_df["City"]
                == city
            )
            & (
                fairfare_zoned_df["Zone"]
                == zone
            )
        ].copy()

    if (
        ride_type
        and ride_type
        != "All Ride Types"
    ):
        zone_base = zone_base[
            zone_base["Ride_Type"]
            == ride_type
        ]

    # ------------------------------------------------------------------
    # 1. EXACT PLACE + HOUR + WEEKDAY
    # ------------------------------------------------------------------

    day_code = csv_day_of_week_code(day_name)

    if not zone_base.empty:
        exact_zone = zone_base[
            zone_base["Hour_of_Day"]
            == int(hour)
        ].copy()

        if day_code is not None:
            exact_zone = exact_zone[
                pd.to_numeric(
                    exact_zone[
                        "Day_of_Week"
                    ],
                    errors="coerce",
                )
                == day_code
            ]

            if not exact_zone.empty:
                result = (
                    _build_historical_context_result(
                        exact_zone,
                        city,
                        zone,
                        hour,
                        day_name,
                        ride_type,
                        "Exact: place + hour + day",
                        "Zone-level historical records",
                    )
                )

                if result:
                    return result

        # --------------------------------------------------------------
        # 2. PLACE + HOUR
        # --------------------------------------------------------------

        hour_zone = zone_base[
            zone_base["Hour_of_Day"]
            == int(hour)
        ].copy()

        if not hour_zone.empty:
            result = (
                _build_historical_context_result(
                    hour_zone,
                    city,
                    zone,
                    hour,
                    day_name,
                    ride_type,
                    "Place + hour",
                    "Zone-level historical records",
                )
            )

            if result:
                return result

        # --------------------------------------------------------------
        # 3. PLACE + ALL TIMES
        # --------------------------------------------------------------

        result = (
            _build_historical_context_result(
                zone_base,
                city,
                zone,
                hour,
                day_name,
                ride_type,
                "Place + all times",
                "Zone-level historical records",
            )
        )

        if result:
            return result

    # ------------------------------------------------------------------
    # CITY FALLBACK
    # ------------------------------------------------------------------

    city_data = fairfare_df[
        fairfare_df["City"]
        == city
    ].copy()

    if (
        ride_type
        and ride_type
        != "All Ride Types"
    ):
        city_data = city_data[
            city_data["Ride_Type"]
            == ride_type
        ]

    # ------------------------------------------------------------------
    # 4. CITY + HOUR + WEEKDAY
    # ------------------------------------------------------------------

    exact_city = city_data[
        city_data["Hour_of_Day"]
        == int(hour)
    ].copy()

    if day_code is not None:
        exact_city = exact_city[
            pd.to_numeric(
                exact_city[
                    "Day_of_Week"
                ],
                errors="coerce",
            )
            == day_code
        ]

        if not exact_city.empty:
            result = (
                _build_historical_context_result(
                    exact_city,
                    city,
                    zone,
                    hour,
                    day_name,
                    ride_type,
                    "City + hour + weekday",
                    "City-level historical fallback",
                )
            )

            if result:
                return result

    # ------------------------------------------------------------------
    # 5. CITY + HOUR
    # ------------------------------------------------------------------

    hour_city = city_data[
        city_data["Hour_of_Day"]
        == int(hour)
    ].copy()

    if not hour_city.empty:
        result = (
            _build_historical_context_result(
                hour_city,
                city,
                zone,
                hour,
                day_name,
                ride_type,
                "City + hour",
                "City-level historical fallback",
            )
        )

        if result:
            return result

    # ------------------------------------------------------------------
    # 6. CITY + ALL TIMES
    # ------------------------------------------------------------------

    if not city_data.empty:
        result = (
            _build_historical_context_result(
                city_data,
                city,
                zone,
                hour,
                day_name,
                ride_type,
                "City + all times",
                "City-level historical fallback",
            )
        )

        if result:
            return result

    # ------------------------------------------------------------------
    # NOTHING FOUND
    # ------------------------------------------------------------------

    return {
        "found": False,
        "message": (
            f"No historical records are "
            f"available for {zone}, {city}."
        ),
    }


def get_zone_event_signal(
    city,
    zone,
    ride_type="All Ride Types",
):
    if zoned_database_available():
        try:
            result = (
                db.get_zone_event_signal_sql(
                    city,
                    zone,
                    ride_type,
                )
            )

            if (
                result.get(
                    "event_avg_demand"
                )
                is not None
                or result.get(
                    "normal_avg_demand"
                )
                is not None
            ):
                return result

        except Exception:
            pass

    data = fairfare_filter(
        city=city,
        ride_types=(
            None
            if ride_type
            == "All Ride Types"
            else [ride_type]
        ),
    )

    if data.empty:
        return {
            "event_avg_demand": None,
            "normal_avg_demand": None,
            "demand_delta_pct": None,
        }

    event_mask = (
        data["Event"]
        != "No Event Recorded"
    )

    event_avg = (
        data.loc[
            event_mask,
            "Demand_Score",
        ].mean()
        if event_mask.any()
        else None
    )

    normal_avg = (
        data.loc[
            ~event_mask,
            "Demand_Score",
        ].mean()
        if (~event_mask).any()
        else None
    )

    delta = None

    if (
        pd.notna(event_avg)
        and pd.notna(normal_avg)
        and normal_avg != 0
    ):
        delta = (
            (
                event_avg
                - normal_avg
            )
            / abs(normal_avg)
            * 100.0
        )

    return {
        "event_avg_demand": (
            float(event_avg)
            if pd.notna(event_avg)
            else None
        ),
        "normal_avg_demand": (
            float(normal_avg)
            if pd.notna(normal_avg)
            else None
        ),
        "demand_delta_pct": (
            float(delta)
            if delta is not None
            else None
        ),
    }


# ==============================================================================
# NEARBY ZONES
# ==============================================================================

def get_top_nearby_zones(
    city,
    current_lat,
    current_lon,
    selected_zone,
    selected_demand,
    selected_hour,
    selected_day,
    selected_ride_type,
):
    """
    Compare other demonstration zones in the same city.

    Only zones with actual assigned historical records for
    the selected context are included.
    """

    if (
        fairfare_zoned_df is None
        or fairfare_zoned_df.empty
        or current_lat is None
        or current_lon is None
    ):
        return []

    city_zones = fairfare_zones[
        fairfare_zones["city"]
        == city
    ].copy()

    if city_zones.empty:
        return []

    city_zones["Current_Distance_KM"] = (
        haversine_km(
            current_lat,
            current_lon,
            city_zones["lat"].to_numpy(),
            city_zones["lon"].to_numpy(),
        )
    )

    results = []

    for _, row in city_zones.iterrows():

        zone = row["zone"]

        if zone == selected_zone:
            continue

        data = filter_zoned_data(
            city=city,
            zone=zone,
            ride_type=selected_ride_type,
            hour=selected_hour,
            day_name=selected_day,
        )

        if data.empty:
            continue

        demand = float(
            data["Demand_Score"].mean()
        )

        if demand <= float(
            selected_demand
        ):
            continue

        results.append(
            {
                "Place": zone,
                "Distance from Current Location (km)": round(
                    float(
                        row[
                            "Current_Distance_KM"
                        ]
                    ),
                    2,
                ),
                "Records": int(
                    len(data)
                ),
                "Avg Demand Score": round(
                    demand,
                    2,
                ),
            }
        )

    results.sort(
        key=lambda item: (
            -item[
                "Avg Demand Score"
            ],
            item[
                "Distance from Current Location (km)"
            ],
        )
    )

    return results[:5]


# ==============================================================================
# CITY SUMMARIES / MAP
# ==============================================================================

def get_city_summary(city):
    if database_available():
        try:
            data = (
                db.get_city_summary_sql(
                    city
                )
            )

            if not data.empty:
                row = data.iloc[0]

                cancel = float(
                    row[
                        "Avg_Cancellation_Rate"
                    ]
                )

                if abs(cancel) <= 1:
                    cancel *= 100

                return {
                    "City": city,
                    "Latitude": (
                        SUPPORTED_CITY_COORDS[
                            city
                        ]["lat"]
                    ),
                    "Longitude": (
                        SUPPORTED_CITY_COORDS[
                            city
                        ]["lon"]
                    ),
                    "Records": int(
                        row["Records"]
                    ),
                    "Avg_Demand_Score": float(
                        row[
                            "Avg_Demand_Score"
                        ]
                    ),
                    "Avg_Available_Drivers": float(
                        row[
                            "Avg_Available_Drivers"
                        ]
                    ),
                    "Avg_Fare": float(
                        row["Avg_Fare"]
                    ),
                    "Avg_Cancellation": cancel,
                }

        except Exception:
            pass

    data = fairfare_filter(
        city=city
    )

    if data.empty:
        return None

    cancellation = rate_to_percent(
        data["Cancellation_Rate"]
    )

    return {
        "City": city,
        "Latitude": (
            SUPPORTED_CITY_COORDS[
                city
            ]["lat"]
        ),
        "Longitude": (
            SUPPORTED_CITY_COORDS[
                city
            ]["lon"]
        ),
        "Records": len(data),
        "Avg_Demand_Score": (
            data["Demand_Score"]
            .mean()
        ),
        "Avg_Available_Drivers": (
            data[
                "Available_Drivers"
            ].mean()
        ),
        "Avg_Fare": (
            data["Final_Fare"]
            .mean()
        ),
        "Avg_Cancellation": (
            cancellation.mean()
        ),
    }


def get_city_map_data():
    if (
        fairfare_df is None
        or fairfare_df.empty
    ):
        return pd.DataFrame()

    rows = []

    for city in sorted(
        fairfare_df[
            "City"
        ]
        .dropna()
        .unique()
        .tolist()
    ):
        city = normalize_city_name(
            city
        )

        if city not in SUPPORTED_CITY_COORDS:
            continue

        summary = get_city_summary(
            city
        )

        if summary:
            rows.append(summary)

    return pd.DataFrame(rows)


# ==============================================================================
# AI ASSISTANT
# ==============================================================================

def get_gemini_client():
    api_key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    if not api_key:
        return None

    try:
        return genai.Client(
            api_key=api_key
        )
    except Exception:
        return None


def _is_retryable_gemini_error(
    exc
):
    message = str(exc).upper()

    return any(
        marker in message
        for marker in (
            "503",
            "UNAVAILABLE",
            "500",
            "INTERNAL",
        )
    )


def generate_gemini_content_with_retry(
    client,
    contents,
    config,
    max_attempts=3,
    base_delay=2,
):
    for attempt in range(
        max_attempts
    ):
        try:
            return client.models.generate_content(
                model="gemini-3.8-flash",
                contents=contents,
                config=config,
            )

        except Exception as exc:

            if not _is_retryable_gemini_error(
                exc
            ):
                raise

            if (
                attempt
                == max_attempts - 1
            ):
                raise

            time.sleep(
                base_delay
                * (
                    2 ** attempt
                )
            )

    raise RuntimeError(
        "Gemini request failed after retries."
    )


def ai_fairfare_context(
    city,
    hour=None,
    day_name=None,
    ride_type="All Ride Types",
):
    if fairfare_df is None:
        return {
            "found": False,
            "message": (
                "FairFare dataset "
                "is not available."
            ),
        }

    data = fairfare_filter(
        city=city,
        hour=hour,
        day_name=day_name,
    )

    if (
        ride_type
        and ride_type
        != "All Ride Types"
    ):
        data = data[
            data["Ride_Type"]
            == ride_type
        ]

    if data.empty:
        return {
            "found": False,
            "message": (
                "No FairFare records "
                "match this context."
            ),
        }

    cancellation_rate = rate_to_percent(
        data["Cancellation_Rate"]
    )

    return {
        "found": True,
        "source": (
            "FairFare synthetic "
            "multi-city dataset"
        ),
        "city": city,
        "hour": (
            hour
            if hour is not None
            else "All Hours"
        ),
        "day_name": (
            day_name
            or "All Days"
        ),
        "ride_type": ride_type,
        "sample_size": len(data),
        "avg_demand_score": round(
            float(
                data[
                    "Demand_Score"
                ].mean()
            ),
            2,
        ),
        "avg_fare": round(
            float(
                data[
                    "Final_Fare"
                ].mean()
            ),
            2,
        ),
        "avg_fare_per_km": round(
            float(
                data[
                    "Fare_Per_KM"
                ].mean()
            ),
            2,
        ),
        "avg_available_drivers": round(
            float(
                data[
                    "Available_Drivers"
                ].mean()
            ),
            2,
        ),
        "avg_cancellation_rate": round(
            float(
                cancellation_rate.mean()
            ),
            2,
        ),
        "weather_mix": (
            data["Weather"]
            .value_counts()
            .head(6)
            .to_dict()
        ),
        "demand_levels": (
            data["Demand_Level"]
            .value_counts()
            .head(6)
            .to_dict()
        ),
        "events": (
            data["Event"]
            .value_counts()
            .head(8)
            .to_dict()
        ),
    }


def run_ai_assistant(
    user_query,
    active_context=None,
):
    client = get_gemini_client()

    if not client:
        return (
            "The AI Assistant is currently "
            "unavailable. The historical "
            "FairFare analytics pages are "
            "still available."
        )

    city = (
        active_context.get(
            "city"
        )
        if active_context
        else detect_current_city()
    )

    city = normalize_city_name(
        city
    )

    context_for_ai = {
        "active_context": active_context,
        "current_city": city,
        "available_cities": (
            sorted(
                fairfare_df[
                    "City"
                ]
                .dropna()
                .unique()
                .tolist()
            )
            if fairfare_df is not None
            else []
        ),
    }

    if (
        city in SUPPORTED_CITY_COORDS
        and fairfare_df is not None
    ):
        context_for_ai[
            "city_summary"
        ] = ai_fairfare_context(
            city=city
        )

    prompt = f"""
You are MobilityLens AI, a historical mobility analytics assistant.

The only historical ride source used by this application is the FairFare
synthetic/generated multi-city dataset. It covers Hyderabad, Delhi, Chennai,
Bangalore and Mumbai.

User question:
{user_query}

Available evidence:
{json.dumps(context_for_ai, default=str)}

Rules:
- Use historical recorded evidence only.
- Answer in 3 to 4 bullets, about 80 to 100 words in total, followed by one short line starting with "Overall". Do not list or repeat KPI values one by one.
- Each bullet explains one business insight about the most relevant metrics or patterns in the provided evidence. Use at most two numbers per bullet.
- When a city average is available and useful, compare the place with the city average and give both values, for example "3.25% vs 4.95%".
- Lead with the most important pattern. Skip metrics that show nothing notable.
- Do not describe demand as moderate, strong, or weak unless the evidence supports it. Prefer evidence-based wording such as "slightly below the city average".
- Use cautious wording such as "suggests" or "is lower than". Do not state causes, predictions, recommendations, or driver instructions.
- Do not use the word "trend" for a single historical slice.
- Mention once, briefly, that the data is synthetic, for example "(synthetic data)". Mention the number of records only when it is under 10, and then say the result is indicative.
- Use cancellation rate only when it is provided in the evidence. Never mention, calculate, estimate, or infer cancellation probability.
- Always preserve the exact units provided in the evidence, especially % for cancellation rates. Never remove or change units.
- Live weather or traffic is current context, not historical ride evidence.
- When discussing a Home demonstration zone, describe it as a simulated/demo zone and do not call it official neighbourhood data.
- If asked how this assistant works, say it is a Generative AI assistant that explains metrics calculated by the app, not an autonomous agent.
- If little evidence is available, give fewer bullets. Do not pad or invent anything to fill space.
- Keep the answer concise and practical.
- Write fare values in rupees with the ₹ sign.
"""

    try:
        config = types.GenerateContentConfig(
            system_instruction=(
                "You are a strict historical "
                "mobility analyst. Return concise "
                "evidence-based answers only."
            ),
            temperature=0.2,
        )

        response = (
            generate_gemini_content_with_retry(
                client=client,
                contents=prompt,
                config=config,
            )
        )

        return (
            response.text
            if response.text
            else "Historical analysis completed."
        )

    except Exception as exc:

        error_text = str(
            exc
        ).upper()

        if (
            "429" in error_text
            or "RESOURCE_EXHAUSTED"
            in error_text
            or "QUOTA" in error_text
        ):
            return (
                "The AI Assistant has reached "
                "the current Gemini API quota. "
                "The MobilityLens historical "
                "analytics pages are still "
                "available."
            )

        if (
            "503" in error_text
            or "UNAVAILABLE"
            in error_text
        ):
            return (
                "Gemini is temporarily unavailable "
                "because the service is under high "
                "demand. Please retry the AI Assistant "
                "later."
            )

        return (
            "The AI Assistant could not "
            "complete the request."
        )


# ==============================================================================
# PAGE HELPERS
# ==============================================================================

def render_live_context(city):

    weather = get_live_weather(
        city
    )

    traffic = get_live_traffic(
        city
    )

    st.subheader(
        "Current Live Context"
    )

    cols = st.columns(4)

    values = []

    if weather.get(
        "available"
    ):
        values = [
            (
                "Live Temperature",
                (
                    f"{format_number(
                        weather.get("temperature_c"),
                        1
                    )} °C"
                ),
            ),
            (
                "Live Weather",
                str(
                    weather.get(
                        "weather_category",
                        "Unknown",
                    )
                ),
            ),
        ]

    else:
        values = [
            (
                "Live Temperature",
                "Unavailable",
            ),
            (
                "Live Weather",
                "Unavailable",
            ),
        ]

    if traffic.get(
        "available"
    ):
        delay = traffic.get(
            "delay_minutes"
        )

        speed = traffic.get(
            "current_speed_kmh"
        )

        values.extend(
            [
                (
                    "Traffic Delay",
                    (
                        f"{format_number(delay, 1)} min"
                        if delay is not None
                        else "N/A"
                    ),
                ),
                (
                    "Current Speed",
                    (
                        f"{format_number(speed, 0)} km/h"
                        if speed is not None
                        else "N/A"
                    ),
                ),
            ]
        )

    else:
        traffic_message = traffic.get(
            "message",
            "Live traffic unavailable.",
        )

        values.extend(
            [
                (
                    "Traffic Delay",
                    "Unavailable",
                ),
                (
                    "Current Speed",
                    "Unavailable",
                ),
            ]
        )

    for col, (label, value) in zip(
        cols,
        values,
    ):
        with col:
            card_html = (
                f'<div class="live-context-card">'
                f'<div class="live-context-label">{label}</div>'
                f'<div class="live-context-value">{value}</div>'
                f'</div>'
            )

            st.markdown(
                card_html,
                unsafe_allow_html=True,
            )

    st.caption(
        "Live weather is current context. "
        "Live traffic is optional and requires a "
        "TomTom API key. Historical ride metrics "
        "remain separate from live signals."
    )

    return weather, traffic

# ==============================================================================
# HOME
# ==============================================================================
# ==============================================================================
# SIDEBAR
# ==============================================================================

st.sidebar.title(
    "🚘 MobilityLens"
)

st.sidebar.caption(
    "Historical Mobility Intelligence"
)

st.sidebar.divider()

nav_options = {
    "🏠 Home": "Home",
    "🇮🇳 India Explorer": "India Explorer",
    "📈 Demand Patterns": "Demand",
    "💰 Historical Earnings": "Earnings",
    "🚫 Cancellations": "Cancellations",
    "🤖 AI Assistant": "AI Assistant",
}

selected_label = st.sidebar.radio(
    "Navigation",
    options=list(
        nav_options.keys()
    ),
    label_visibility="collapsed",
)

selected_page = nav_options[
    selected_label
]

if selected_page == "Home":
    

    current_location = (
        detect_current_location()
    )

    st.title(
        "Historical Mobility Context"
    )

    st.caption(
        "Your current approximate location "
        "identifies the city used for historical "
        "context. You can select a place in that "
        "city when you want to test place-level history."
    )

    if fairfare_df is None:
        st.error(
            "FairFare dataset not found. Make sure "
            "`data/fairfare_ride_demand_dataset.csv` exists."
        )

        st.stop()

    detected_city = (
        current_location.get("city")
        if current_location
        else None
    )

    if (
        detected_city
        not in SUPPORTED_CITY_COORDS
    ):
        st.warning(
            f"Current city could not be matched "
            f"to a supported FairFare city "
            f"({detected_city or 'Unavailable'}). "
            "The app will not substitute another city."
        )

        st.caption(
            "For local testing, set "
            "`RIDEINTEL_CITY=Hyderabad` in `.env`."
        )

        st.stop()

    city_zones = fairfare_zones[
        fairfare_zones["city"]
        == detected_city
    ].copy()

    if city_zones.empty:
        st.error(
            "No places are configured "
            "for the detected city."
        )

        st.stop()

    current_lat = (
        current_location.get(
            "latitude"
        )
    )

    current_lon = (
        current_location.get(
            "longitude"
        )
    )

    if (
        current_lat is not None
        and current_lon is not None
    ):
        city_zones[
            "Current_Distance_KM"
        ] = haversine_km(
            current_lat,
            current_lon,
            city_zones[
                "lat"
            ].to_numpy(),
            city_zones[
                "lon"
            ].to_numpy(),
        )

        nearest_zone = (
            city_zones.loc[
                city_zones[
                    "Current_Distance_KM"
                ].idxmin()
            ].to_dict()
        )

    else:
        nearest_zone = (
            city_zones.iloc[
                0
            ].to_dict()
        )

    st.info(
        f"Detected city: **{detected_city}**. "
        "City detection is approximate network location; "
        "the app does not use precise GPS location."
    )

    if (
        current_location.get(
            "source"
        )
        == "Local testing override"
    ):
        st.caption(
            f"Test location context: "
            f"**{nearest_zone['zone']}**"
        )
    else:
        st.caption(
            f"Current location context: "
            f"**{nearest_zone['zone']}**"
        )

    st.subheader(
        "Historical Situation"
    )

    st.caption(
        "The current city is detected automatically. "
        "Choose another place only when you want to "
        "test a different place in that city."
    )

    now = pd.Timestamp.now(
        tz="Asia/Kolkata"
    )

    zones = city_zones[
        "zone"
    ].tolist()

    nearest_name = (
        nearest_zone["zone"]
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        selected_hour = st.selectbox(
            "Hour of Day",
            list(range(24)),
            index=int(now.hour),
            format_func=lambda value: (
                f"{value:02d}:00"
            ),
        )

    with c2:
        selected_day = st.selectbox(
            "Day of Week",
            DAYS,
            index=DAYS.index(
                now.day_name()
            ),
        )

    with c3:
        selected_zone = st.selectbox(
            "Historical Place",
            zones,
            index=zones.index(
                nearest_name
            ),
            help=(
                "Defaults to the nearest place "
                "for the current location. You can "
                "select another place to test it."
            ),
        )

    city_ride_types = [
        "All Ride Types",
        *[
            v
            for v in RIDE_TYPE_ORDER
            if v
            in fairfare_df[
                fairfare_df[
                    "City"
                ]
                == detected_city
            ][
                "Ride_Type"
            ]
            .dropna()
            .unique()
            .tolist()
        ],
    ]

    selected_ride_type = st.selectbox(
        "Ride Type",
        city_ride_types,
    )

    live_weather, live_traffic = (
        render_live_context(
            detected_city
        )
    )

    historical = get_zone_context(
        detected_city,
        selected_zone,
        selected_hour,
        selected_day,
        selected_ride_type,
    )

    st.subheader(
        "Historical Records Matching This Context"
    )

    if not historical.get(
        "found"
    ):
        st.warning(
            historical.get(
                "message",
                "No historical records found "
                "for the selected place.",
            )
        )

        st.info(
            "Try another place, hour, weekday, "
            "or All Ride Types."
        )

        st.stop()

    if (
        historical.get(
            "location_basis"
        )
        == "City-level historical fallback"
    ):
        st.warning(
            f"No assigned historical records "
            f"were available for **{selected_zone}**. "
            f"The KPIs below use **{detected_city} "
            f"city-level historical records** instead."
        )

    show_metric_cards(
        [
            {
                "label": "Bookings",
                "value": (
                    f"{historical['bookings']:,}"
                ),
                "help": (
                    "Historical records in the "
                    "selected place/time context."
                ),
            },
            {
                "label": "Completed Rides (est.)",
                "value": (
                    f"{historical['completed_rides_estimated']:.1f}"
                ),
                "help": (
                    "Estimated from historical bookings "
                    "and cancellation rate because FairFare "
                    "has no ride-status field."
                ),
            },
            {
                "label": "Cancellation Rate",
                "value": (
                    f"{historical['cancellation_rate']:.2f}%"
                ),
                "help": (
                    "Average recorded cancellation rate."
                ),
            },
            {
                "label": "Avg Ride Distance",
                "value": (
                    f"{historical['avg_ride_km']:.2f} km"
                ),
                "help": (
                    "Average recorded ride distance."
                ),
            },
            {
                "label": "Average Fare",
                "value": (
                    f"₹{historical['avg_fare']:.2f}"
                ),
                "help": (
                    "Average recorded fare."
                ),
            },
            {
                "label": "Average Demand Score",
                "value": (
                    f"{historical['avg_demand_score']:.3f}"
                ),
                "help": (
                    "Average recorded demand score."
                ),
            },
            {
                "label": "Historical Event Signal",
                "value": (
                    "Compared"
                    if historical.get(
                        "event_signal_available"
                    )
                    else "Limited"
                ),
                "help": (
                    "Historical association, "
                    "not a causal claim."
                ),
            },
        ]
    )

    st.caption(
        f"Filter level used: "
        f"**{historical['basis']}** | "
        f"Records matched: "
        f"**{historical['sample_size']:,}** | "
        f"Place: **{selected_zone}** | "
        f"Day: **{selected_day}** | "
        f"Hour: **{selected_hour:02d}:00** | "
        f"Ride Type: **{selected_ride_type}**"
    )

    d1, d2 = st.columns(2)

    with d1:
        st.subheader(
            "Historical Demand Levels"
        )

        st.dataframe(
            pd.DataFrame(
                historical[
                    "demand_breakdown"
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    with d2:
        st.subheader(
            "Historical Weather Mix"
        )

        st.dataframe(
            pd.DataFrame(
                historical[
                    "weather_mix"
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

    nearby = []

    if (
        historical.get(
            "location_basis"
        )
        == "Zone-level historical records"
    ):
        nearby = get_top_nearby_zones(
            detected_city,
            current_lat,
            current_lon,
            selected_zone,
            historical[
                "avg_demand_score"
            ],
            selected_hour,
            selected_day,
            selected_ride_type,
        )

    st.subheader(
        "Nearby Historical Places with Higher Recorded Demand"
    )

    if nearby:
        st.dataframe(
            pd.DataFrame(nearby),
            use_container_width=True,
            hide_index=True,
        )

    elif (
        historical.get(
            "location_basis"
        )
        == "City-level historical fallback"
    ):
        st.caption(
            "Nearby-place comparison is unavailable "
            "because the selected place has no assigned "
            "historical records."
        )

    else:
        st.caption(
            "No nearby demonstration place has a higher "
            "recorded demand score for this context."
        )

    context_payload = {
        "app": "MobilityLens",
        "data_label": (
            "Simulated data for demonstration"
        ),
        "city": detected_city,
        "historical_place": selected_zone,
        "hour": selected_hour,
        "day_name": selected_day,
        "ride_type": selected_ride_type,
        "historical": historical,
        "live_weather": live_weather,
        "live_traffic": live_traffic,
        "nearby_higher_demand_places": nearby,
        "interpretation": (
            "Current location identifies the city; "
            "place labels are simulated demonstration "
            "zones. Historical values are recorded examples, "
            "not live ride data or predictions."
        ),
    }

    st.session_state[
        "home_last_context"
    ] = context_payload

    with st.expander(
        "📊 Show current + historical details"
    ):
        st.json(
            context_payload
        )

    if st.button(
        "Generate AI Historical Summary",
        key="home_ai_summary",
    ):
        with st.spinner(
            "Generating historical summary..."
        ):
            summary = run_ai_assistant(
                user_query=(
                    f"Summarize the historical "
                    f"evidence for {detected_city}, "
                    f"place {selected_zone}, "
                    f"{selected_hour:02d}:00, "
                    f"{selected_day}, "
                    f"Ride Type "
                    f"{selected_ride_type}."
                ),
                active_context=context_payload,
            )

        st.subheader(
            "Historical Pattern Summary"
        )

        with st.container(border=True):
            st.markdown(summary)


# ==============================================================================
# INDIA EXPLORER
# ==============================================================================

elif selected_page == "India Explorer":

    st.title(
        "🇮🇳 India Mobility Explorer"
    )

    st.caption(
        "Explore the five FairFare cities and "
        "the demonstration zones used to organize "
        "historical records. Coordinates are approximate "
        "and not a live driver map."
    )

    if (
        fairfare_df is None
        or fairfare_zones is None
    ):
        st.error(
            "FairFare data or demonstration "
            "zones are unavailable."
        )

        st.stop()

    map_data = get_city_map_data()

    if map_data.empty:
        st.warning(
            "No supported FairFare cities "
            "are available."
        )

        st.stop()

    st.subheader(
        "City Coverage"
    )

    st.map(
        map_data,
        latitude="Latitude",
        longitude="Longitude",
        size="Records",
        zoom=4,
        height=430,
    )

    selected_city = st.selectbox(
        "Explore City",
        map_data["City"].tolist(),
    )

    summary = get_city_summary(
        selected_city
    )

    show_metric_cards(
        [
            {
                "label": "Historical Records",
                "value": (
                    f"{int(summary['Records']):,}"
                ),
                "help": (
                    "All FairFare records "
                    "for the selected city."
                ),
            },
            {
                "label": "Average Demand Score",
                "value": (
                    f"{summary['Avg_Demand_Score']:.1f}"
                ),
                "help": (
                    "Average recorded "
                    "Demand_Score."
                ),
            },
            {
                "label": "Average Fare",
                "value": (
                    f"₹{summary['Avg_Fare']:.2f}"
                ),
                "help": (
                    "Average recorded Final_Fare."
                ),
            },
            {
                "label": "Average Cancellation",
                "value": (
                    f"{summary['Avg_Cancellation']:.2f}%"
                ),
                "help": (
                    "Average recorded "
                    "Cancellation_Rate."
                ),
            },
        ]
    )

    selected_zones = fairfare_zones[
        fairfare_zones["city"]
        == selected_city
    ].copy()

    st.subheader(
        f"Demonstration Zones in {selected_city}"
    )

    zone_map = selected_zones.rename(
        columns={
            "lat": "Latitude",
            "lon": "Longitude",
        }
    )[
        [
            "zone",
            "zone_type",
            "Latitude",
            "Longitude",
        ]
    ]

    st.map(
        zone_map,
        latitude="Latitude",
        longitude="Longitude",
        zoom=9,
        height=360,
    )

    st.dataframe(
        selected_zones.rename(
            columns={
                "city": "City",
                "zone": "Zone",
                "zone_type": "Zone Type",
                "lat": "Latitude",
                "lon": "Longitude",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    assigned = fairfare_zoned_df[
        fairfare_zoned_df["City"]
        == selected_city
    ]

    st.caption(
        f"Zone assignment coverage: "
        f"{len(assigned):,} of "
        f"{len(fairfare_filter(city=selected_city)):,} "
        f"city records were assigned within the "
        f"{ZONE_MAX_DISTANCE_KM:.0f} km threshold. "
        "City-level summaries use the complete FairFare city data."
    )

    st.caption(
        "**Simulated data for demonstration.**"
    )


# ==============================================================================
# DEMAND
# ==============================================================================

elif selected_page == "Demand":

    st.title(
        "📈 Demand Patterns"
    )

    st.caption(
        "Analyze historical demand and driver "
        "availability across FairFare cities "
        "or specific places."
    )

    st.caption(
        "Simulated data for demonstration"
    )

    if (
        not database_available()
        and fairfare_df is None
    ):
        st.error(
            "FairFare data is unavailable. "
            "Check the dataset and SQLite database."
        )

        st.stop()

    cities = (
        db.get_city_list()
        if database_available()
        else sorted(
            fairfare_df[
                "City"
            ]
            .dropna()
            .unique()
            .tolist()
        )
    )

    types = (
        db.get_ride_type_list()
        if database_available()
        else sorted(
            fairfare_df[
                "Ride_Type"
            ]
            .dropna()
            .unique()
            .tolist()
        )
    )

    ride_types = [
        "All Ride Types"
    ] + [
        v
        for v in RIDE_TYPE_ORDER
        if v in types
    ]

    level = st.selectbox(
        "Analysis Level",
        [
            "City",
            "Place",
        ],
    )

    ride_type = st.selectbox(
        "Ride Type",
        ride_types,
    )

    ride_types_filter = (
        None
        if ride_type
        == "All Ride Types"
        else [ride_type]
    )

    if level == "City":

        selected_cities = (
            st.multiselect(
                "Cities",
                cities,
                default=cities,
            )
        )

        if not selected_cities:
            st.warning(
                "Select at least one city."
            )

            st.stop()

        data = fairfare_filter(
            cities=selected_cities,
            ride_types=ride_types_filter,
        )

        if database_available():
            comparison = (
                db.get_city_demand_sql(
                    selected_cities,
                    ride_type,
                )
            )
        else:
            comparison = (
                data.groupby("City")
                .agg(
                    Average_Demand_Score=(
                        "Demand_Score",
                        "mean",
                    ),
                    Average_Available_Drivers=(
                        "Available_Drivers",
                        "mean",
                    ),
                    Records=(
                        "City",
                        "size",
                    ),
                )
                .reset_index()
            )

        comparison_name = "City"
        x_key = "City"

    else:

        city = st.selectbox(
            "City",
            cities,
        )

        zones = fairfare_zones[
            fairfare_zones["city"]
            == city
        ]["zone"].tolist()

        selected_zones = (
            st.multiselect(
                "Places",
                zones,
                default=zones,
            )
        )

        if not selected_zones:
            st.warning(
                "Select at least one place."
            )

            st.stop()

        if (
            database_available()
            and zoned_database_available()
        ):
            data = db.get_zone_rows_sql(
                city,
                selected_zones,
                ride_type,
            )

            comparison = (
                db.get_zone_demand_sql(
                    city,
                    selected_zones,
                    ride_type,
                )
            )

        else:
            data = fairfare_zoned_df[
                (
                    fairfare_zoned_df[
                        "City"
                    ]
                    == city
                )
                & (
                    fairfare_zoned_df[
                        "Zone"
                    ].isin(
                        selected_zones
                    )
                )
            ].copy()

            if (
                ride_type
                != "All Ride Types"
            ):
                data = data[
                    data[
                        "Ride_Type"
                    ]
                    == ride_type
                ]

            if not data.empty:
                comparison = (
                    data.groupby(
                        "Zone"
                    )
                    .agg(
                        Average_Demand_Score=(
                            "Demand_Score",
                            "mean",
                        ),
                        Average_Available_Drivers=(
                            "Available_Drivers",
                            "mean",
                        ),
                        Records=(
                            "Zone",
                            "size",
                        ),
                    )
                    .reset_index()
                )
            else:
                comparison = pd.DataFrame()

        comparison_name = "Place"
        x_key = "Zone"

    if data.empty:
        st.warning(
            "No historical records match "
            "the selected filters."
        )

        st.stop()

    show_metric_cards(
        [
            {
                "label": "Historical Records",
                "value": f"{len(data):,}",
                "help": (
                    "FairFare records in the "
                    "selected analysis scope."
                ),
            },
            {
                "label": "Average Demand Score",
                "value": (
                    f"{data['Demand_Score'].mean():.1f}"
                ),
                "help": (
                    "Average recorded demand score."
                ),
            },
            {
                "label": "Average Available Drivers",
                "value": (
                    f"{data['Available_Drivers'].mean():.1f}"
                ),
                "help": (
                    "Average recorded driver "
                    "availability count."
                ),
            },
            {
                "label": "Average Driver Availability",
                "value": (
                    f"{data['Driver_Availability'].mean():.1f}"
                ),
                "help": (
                    "Average recorded "
                    "Driver_Availability."
                ),
            },
        ]
    )

    st.subheader(
        f"Average Historical Demand Score by "
        f"{comparison_name}"
    )

    if not comparison.empty:

        chart = (
            alt.Chart(comparison)
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{x_key}:N",
                    title="City / Place",
                    axis=alt.Axis(
                        labelColor="#0f172a",
                        titleColor="#0f172a",
                    ),
                ),
                y=alt.Y(
                    "Average_Demand_Score:Q",
                    title="Average Demand Score",
                    axis=alt.Axis(
                        labelColor="#0f172a",
                        titleColor="#0f172a",
                    ),
                ),
                tooltip=[
                    x_key,
                    alt.Tooltip(
                        "Average_Demand_Score:Q",
                        format=".1f",
                    ),
                    alt.Tooltip(
                        "Records:Q",
                        format=",d",
                    ),
                ],
            )
            .properties(
                height=380
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )

    st.subheader(
        "Historical Demand Score by Hour"
    )

    hourly = (
        data.groupby(
            "Hour_of_Day"
        )
        .agg(
            Average_Demand_Score=(
                "Demand_Score",
                "mean",
            ),
            Records=(
                "Hour_of_Day",
                "size",
            ),
        )
        .reset_index()
    )

    chart = (
        alt.Chart(hourly)
        .mark_line(
            point=True
        )
        .encode(
            x=alt.X(
                "Hour_of_Day:O",
                title="Hour of Day",
                sort=list(
                    range(24)
                ),
                axis=alt.Axis(
                    labelColor="#0f172a",
                    titleColor="#0f172a",
                ),
            ),
            y=alt.Y(
                "Average_Demand_Score:Q",
                title="Average Demand Score",
                axis=alt.Axis(
                    labelColor="#0f172a",
                    titleColor="#0f172a",
                ),
            ),
            tooltip=[
                alt.Tooltip(
                    "Hour_of_Day:Q",
                    title="Hour",
                ),
                alt.Tooltip(
                    "Average_Demand_Score:Q",
                    format=".1f",
                ),
                alt.Tooltip(
                    "Records:Q",
                    format=",d",
                ),
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

    st.subheader(
        "Historical Demand Levels"
    )

    levels = (
        get_demand_level_breakdown(
            data
        )
    )

    st.dataframe(
        levels,
        use_container_width=True,
        hide_index=True,
    )


# ==============================================================================
# EARNINGS
# ==============================================================================

elif selected_page == "Earnings":

    st.title(
        "💰 Historical Earnings Analysis"
    )

    st.caption(
        "Compare recorded fares and fare-per-kilometre "
        "patterns across FairFare cities or specific places."
    )

    st.caption(
        "Simulated data for demonstration"
    )

    if (
        not database_available()
        and fairfare_df is None
    ):
        st.error(
            "FairFare data is unavailable. "
            "Check the dataset and SQLite database."
        )

        st.stop()

    cities = (
        db.get_city_list()
        if database_available()
        else sorted(
            fairfare_df[
                "City"
            ]
            .dropna()
            .unique()
            .tolist()
        )
    )

    types = (
        db.get_ride_type_list()
        if database_available()
        else sorted(
            fairfare_df[
                "Ride_Type"
            ]
            .dropna()
            .unique()
            .tolist()
        )
    )

    ride_types = [
        "All Ride Types"
    ] + [
        v
        for v in RIDE_TYPE_ORDER
        if v in types
    ]

    level = st.selectbox(
        "Analysis Level",
        [
            "City",
            "Place",
        ],
    )

    ride_type = st.selectbox(
        "Ride Type",
        ride_types,
    )

    if level == "City":

        selected_cities = (
            st.multiselect(
                "Cities",
                cities,
                default=cities,
            )
        )

        if not selected_cities:
            st.warning(
                "Select at least one city."
            )

            st.stop()

        filter_types = (
            None
            if ride_type
            == "All Ride Types"
            else [ride_type]
        )

        data = fairfare_filter(
            cities=selected_cities,
            ride_types=filter_types,
        )

        if database_available():
            comparison = (
                db.get_city_earnings_sql(
                    selected_cities,
                    ride_type,
                )
            )
        else:
            comparison = (
                data.groupby(
                    [
                        "City",
                        "Ride_Type",
                    ]
                )
                .agg(
                    Records=(
                        "City",
                        "size",
                    ),
                    Average_Fare=(
                        "Final_Fare",
                        "mean",
                    ),
                    Average_Fare_Per_KM=(
                        "Fare_Per_KM",
                        "mean",
                    ),
                    Average_Ride_Distance=(
                        "Ride_Distance_KM",
                        "mean",
                    ),
                )
                .reset_index()
            )

    else:

        city = st.selectbox(
            "City",
            cities,
        )

        zones = fairfare_zones[
            fairfare_zones["city"]
            == city
        ]["zone"].tolist()

        selected_zones = (
            st.multiselect(
                "Places",
                zones,
                default=zones,
            )
        )

        if not selected_zones:
            st.warning(
                "Select at least one place."
            )

            st.stop()

        if (
            database_available()
            and zoned_database_available()
        ):
            data = db.get_zone_rows_sql(
                city,
                selected_zones,
                ride_type,
            )

            comparison = (
                db.get_zone_earnings_sql(
                    city,
                    selected_zones,
                    ride_type,
                )
            )

        else:
            data = fairfare_zoned_df[
                (
                    fairfare_zoned_df[
                        "City"
                    ]
                    == city
                )
                & (
                    fairfare_zoned_df[
                        "Zone"
                    ].isin(
                        selected_zones
                    )
                )
            ].copy()

            if (
                ride_type
                != "All Ride Types"
            ):
                data = data[
                    data[
                        "Ride_Type"
                    ]
                    == ride_type
                ]

            if not data.empty:
                comparison = (
                    data.groupby(
                        [
                            "Zone",
                            "Ride_Type",
                        ]
                    )
                    .agg(
                        Records=(
                            "Zone",
                            "size",
                        ),
                        Average_Fare=(
                            "Final_Fare",
                            "mean",
                        ),
                        Average_Fare_Per_KM=(
                            "Fare_Per_KM",
                            "mean",
                        ),
                        Average_Ride_Distance=(
                            "Ride_Distance_KM",
                            "mean",
                        ),
                    )
                    .reset_index()
                )
            else:
                comparison = pd.DataFrame()

    if data.empty:
        st.warning(
            "No historical records match "
            "the selected filters."
        )

        st.stop()

    show_metric_cards(
        [
            {
                "label": "Historical Records",
                "value": f"{len(data):,}",
                "help": (
                    "FairFare records in "
                    "the selected scope."
                ),
            },
            {
                "label": "Average Fare",
                "value": (
                    f"₹{data['Final_Fare'].mean():.2f}"
                ),
                "help": (
                    "Average recorded final fare."
                ),
            },
            {
                "label": "Average Fare / Km",
                "value": (
                    f"₹{data['Fare_Per_KM'].mean():.2f}"
                ),
                "help": (
                    "Average recorded fare "
                    "per kilometre."
                ),
            },
            {
                "label": "Average Ride Distance",
                "value": (
                    f"{data['Ride_Distance_KM'].mean():.2f} km"
                ),
                "help": (
                    "Average recorded ride distance."
                ),
            },
        ]
    )

    st.subheader(
        f"Historical Earnings Comparison by "
        f"{level}"
    )

    if comparison.empty:
        st.info(
            "No place-level records are available "
            "for the selected places."
        )

    else:
        st.dataframe(
            comparison.rename(
                columns={
                    "Zone": "Place",
                    "Ride_Type": "Ride Type",
                    "Average_Fare": "Avg Fare (₹)",
                    "Average_Fare_Per_KM": (
                        "Avg Fare / Km (₹)"
                    ),
                    "Average_Ride_Distance": (
                        "Avg Distance (km)"
                    ),
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# CANCELLATIONS
# ==============================================================================

elif selected_page == "Cancellations":

    st.title(
        "🚫 Cancellation Analysis"
    )

    st.caption(
        "Analyze recorded cancellation rate and "
        "cancellation probability across FairFare "
        "cities or specific places."
    )

    st.caption(
        "Simulated data for demonstration"
    )

    if (
        not database_available()
        and fairfare_df is None
    ):
        st.error(
            "FairFare data is unavailable. "
            "Check the dataset and SQLite database."
        )

        st.stop()

    cities = (
        db.get_city_list()
        if database_available()
        else sorted(
            fairfare_df[
                "City"
            ]
            .dropna()
            .unique()
            .tolist()
        )
    )

    types = (
        db.get_ride_type_list()
        if database_available()
        else sorted(
            fairfare_df[
                "Ride_Type"
            ]
            .dropna()
            .unique()
            .tolist()
        )
    )

    ride_types = [
        "All Ride Types"
    ] + [
        v
        for v in RIDE_TYPE_ORDER
        if v in types
    ]

    level = st.selectbox(
        "Analysis Level",
        [
            "City",
            "Place",
        ],
    )

    ride_type = st.selectbox(
        "Ride Type",
        ride_types,
    )

    if level == "City":

        selected_cities = (
            st.multiselect(
                "Cities",
                cities,
                default=cities,
            )
        )

        if not selected_cities:
            st.warning(
                "Select at least one city."
            )

            st.stop()

        filter_types = (
            None
            if ride_type
            == "All Ride Types"
            else [ride_type]
        )

        data = fairfare_filter(
            cities=selected_cities,
            ride_types=filter_types,
        )

        if database_available():
            comparison = (
                db.get_city_cancellations_sql(
                    selected_cities,
                    ride_type,
                )
            )
        else:
            comparison = pd.DataFrame()

        if comparison.empty:

            xdata = data.copy()

            xdata[
                "Cancellation_Rate_Pct"
            ] = rate_to_percent(
                xdata[
                    "Cancellation_Rate"
                ]
            )

            xdata[
                "Cancellation_Probability_Pct"
            ] = rate_to_percent(
                xdata[
                    "Cancellation_Probability"
                ]
            )

            comparison = (
                xdata.groupby(
                    "City"
                )
                .agg(
                    Average_Cancellation_Rate=(
                        "Cancellation_Rate_Pct",
                        "mean",
                    ),
                    Average_Cancellation_Probability=(
                        "Cancellation_Probability_Pct",
                        "mean",
                    ),
                    Average_Traffic_Delay=(
                        "Traffic_Delay",
                        "mean",
                    ),
                    Records=(
                        "City",
                        "size",
                    ),
                )
                .reset_index()
            )

    else:

        city = st.selectbox(
            "City",
            cities,
        )

        zones = fairfare_zones[
            fairfare_zones["city"]
            == city
        ]["zone"].tolist()

        selected_zones = (
            st.multiselect(
                "Places",
                zones,
                default=zones,
            )
        )

        if not selected_zones:
            st.warning(
                "Select at least one place."
            )

            st.stop()

        if (
            database_available()
            and zoned_database_available()
        ):
            data = db.get_zone_rows_sql(
                city,
                selected_zones,
                ride_type,
            )

            comparison = (
                db.get_zone_cancellations_sql(
                    city,
                    selected_zones,
                    ride_type,
                )
            )

        else:
            data = fairfare_zoned_df[
                (
                    fairfare_zoned_df[
                        "City"
                    ]
                    == city
                )
                & (
                    fairfare_zoned_df[
                        "Zone"
                    ].isin(
                        selected_zones
                    )
                )
            ].copy()

            if (
                ride_type
                != "All Ride Types"
            ):
                data = data[
                    data[
                        "Ride_Type"
                    ]
                    == ride_type
                ]

            if data.empty:
                comparison = (
                    pd.DataFrame()
                )

            else:
                data[
                    "Cancellation_Rate_Pct"
                ] = rate_to_percent(
                    data[
                        "Cancellation_Rate"
                    ]
                )

                data[
                    "Cancellation_Probability_Pct"
                ] = rate_to_percent(
                    data[
                        "Cancellation_Probability"
                    ]
                )

                comparison = (
                    data.groupby(
                        "Zone"
                    )
                    .agg(
                        Average_Cancellation_Rate=(
                            "Cancellation_Rate_Pct",
                            "mean",
                        ),
                        Average_Cancellation_Probability=(
                            "Cancellation_Probability_Pct",
                            "mean",
                        ),
                        Average_Traffic_Delay=(
                            "Traffic_Delay",
                            "mean",
                        ),
                        Records=(
                            "Zone",
                            "size",
                        ),
                    )
                    .reset_index()
                )

    if data.empty:
        st.warning(
            "No historical records match "
            "the selected filters."
        )

        st.stop()

    rate = rate_to_percent(
        data[
            "Cancellation_Rate"
        ]
    )

    prob = rate_to_percent(
        data[
            "Cancellation_Probability"
        ]
    )

    show_metric_cards(
        [
            {
                "label": "Historical Records",
                "value": f"{len(data):,}",
                "help": (
                    "FairFare records in "
                    "the selected scope."
                ),
            },
            {
                "label": "Avg Cancellation Rate",
                "value": (
                    f"{rate.mean():.2f}%"
                ),
                "help": (
                    "Average recorded "
                    "cancellation rate."
                ),
            },
            {
                "label": "Avg Cancellation Probability",
                "value": (
                    f"{prob.mean():.2f}%"
                ),
                "help": (
                    "Average recorded "
                    "cancellation probability."
                ),
            },
            {
                "label": "Avg Traffic Delay",
                "value": (
                    f"{data['Traffic_Delay'].mean():.2f}"
                ),
                "help": (
                    "Average recorded "
                    "Traffic_Delay."
                ),
            },
        ]
    )

    st.subheader(
        f"Historical Cancellation Rate by "
        f"{level}"
    )

    if comparison.empty:
        st.info(
            "No place-level records are available "
            "for the selected places."
        )

    else:
        name = (
            "Zone"
            if "Zone"
            in comparison.columns
            else "City"
        )

        chart = (
            alt.Chart(comparison)
            .mark_bar()
            .encode(
                x=alt.X(
                    f"{name}:N",
                    title="City / Place",
                    axis=alt.Axis(
                        labelColor="#0f172a",
                        titleColor="#0f172a",
                    ),
                ),
                y=alt.Y(
                    "Average_Cancellation_Rate:Q",
                    title=(
                        "Average Cancellation Rate (%)"
                    ),
                    axis=alt.Axis(
                        labelColor="#0f172a",
                        titleColor="#0f172a",
                    ),
                ),
                tooltip=[
                    name,
                    alt.Tooltip(
                        "Average_Cancellation_Rate:Q",
                        format=".2f",
                    ),
                    alt.Tooltip(
                        "Records:Q",
                        format=",d",
                    ),
                ],
            )
            .properties(
                height=380
            )
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )

        st.dataframe(
            comparison.rename(
                columns={
                    "Zone": "Place",
                    "Average_Cancellation_Rate": (
                        "Avg Cancellation Rate (%)"
                    ),
                    "Average_Cancellation_Probability": (
                        "Avg Cancellation Probability (%)"
                    ),
                    "Average_Traffic_Delay": (
                        "Avg Traffic Delay"
                    ),
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# AI ASSISTANT PAGE
# ==============================================================================

elif selected_page == "AI Assistant":

    st.title(
        "🤖 AI Mobility Assistant"
    )

    st.caption(
        "Ask questions about the historical "
        "FairFare multi-city dataset."
    )

    st.caption(
        "Simulated data for demonstration"
    )
    active_context = (
        st.session_state.get(
            "home_last_context"
        )
    )

    if active_context:

        st.info(
            "Active Home context: "
            f"{active_context.get('city')} | "
            f"{int(active_context.get('hour', 0)):02d}:00 | "
            f"{active_context.get('day_name')} | "
            f"{active_context.get('ride_type', 'All Ride Types')} | "
            f"{active_context.get('historical_place', 'City Level')}"
        )

    if (
        "messages"
        not in st.session_state
    ):
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
        "Ask about historical demand, earnings, cancellations, weather context, or cities..."
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
                "Analyzing historical FairFare evidence..."
            ):
                reply = run_ai_assistant(
                    user_query=user_prompt,
                    active_context=active_context,
                )

            st.markdown(
                reply
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )