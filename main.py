import os
import sqlite3
import json
import re

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai

from analytics import (
    AnalyticsError,
    VALID_DAYS,
    avg_booking_value_by_pickup_location,
    avg_value_per_km_by_hour,
    avg_value_per_km_by_pickup_location,
    booking_status_distribution,
    cancellation_rate_by_hour,
    cancellation_rate_by_pickup_location,
    completed_rides_by_day_of_week,
    completed_rides_by_hour,
    completed_rides_by_pickup_and_hour,
    completed_rides_by_pickup_location,
    customer_cancellation_counts_and_rates,
    customer_cancellation_reasons,
    driver_cancellation_counts_and_rates,
    driver_cancellation_reasons,
    high_demand_pickup_locations,
    incomplete_ride_counts_and_reasons,
    overall_kpis,
    strong_earning_opportunity_locations,
    contextual_location_hour_analysis,
)


# =========================================================
# 1. APPLICATION CONFIGURATION
# =========================================================

load_dotenv()

st.set_page_config(
    page_title="Ride Decision Support — Delhi NCR",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)


APP_TITLE = "Ride Decision Support"
DATASET_REGION = "Delhi NCR"

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data",
)

RAW_PATH = os.path.join(
    DATA_DIR,
    "uber_rides_raw.csv",
)

CLEANED_PATH = os.path.join(
    DATA_DIR,
    "uber_rides_cleaned.csv",
)

DB_PATH = os.path.join(
    DATA_DIR,
    "uber_rides.db",
)


# =========================================================
# 2. NAVIGATION
# =========================================================

NAV_HOME = "🏠 Home"
NAV_DEMAND = "📍 Demand"
NAV_EARNINGS = "💰 Earnings"
NAV_CANCEL = "❌ Cancellations"
NAV_ANALYTICS = "📊 Analytics"
NAV_AI = "🤖 AI Assistant"

NAV_PAGES = [
    NAV_HOME,
    NAV_DEMAND,
    NAV_EARNINGS,
    NAV_CANCEL,
    NAV_ANALYTICS,
    NAV_AI,
]


# =========================================================
# 3. COMMON CONSTANTS
# =========================================================

ALL_HOURS = "All hours"
ALL_DAYS = "All days"
ALL_LOCATIONS = "All pickup locations"

VEHICLE_TYPES = [
    "All Vehicle Types",
    "Bike",
    "Auto",
    "Go Mini",
    "Go Sedan",
    "Premier Sedan",
    "eBike",
    "Uber XL",
]


# =========================================================
# 4. AUTOMATED DATA CLEANING PIPELINE
# =========================================================

def clean_uber_data(
    raw_csv_path: str,
    output_csv_path: str = None,
) -> pd.DataFrame:
    """
    Automated cleaning pipeline for the Uber rides dataset.

    Raw CSV is never modified.

    Creates:
        - cleaned Booking ID
        - cleaned Customer ID
        - Pickup_DateTime
        - Hour
        - Day_Name
        - Is_Weekend
        - Value_Per_Km

    Removes redundant/raw columns.
    """

    if not os.path.exists(raw_csv_path):
        raise FileNotFoundError(
            f"Raw dataset not found: {raw_csv_path}"
        )

    df = pd.read_csv(
        raw_csv_path
    )

    required_columns = [
        "Booking ID",
        "Customer ID",
        "Date",
        "Time",
        "Booking Value",
        "Ride Distance",
        "Booking Status",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "The raw dataset is missing required columns: "
            + ", ".join(missing_columns)
        )

    # -----------------------------------------------------
    # Clean identifiers
    # -----------------------------------------------------

    df["Booking ID"] = (
        df["Booking ID"]
        .astype(str)
        .str.strip("\"'")
    )

    df["Customer ID"] = (
        df["Customer ID"]
        .astype(str)
        .str.strip("\"'")
    )

    # -----------------------------------------------------
    # Date/time
    # -----------------------------------------------------

    df["Pickup_DateTime"] = pd.to_datetime(
        df["Date"].astype(str)
        + " "
        + df["Time"].astype(str),
        format="%d-%m-%Y %H:%M:%S",
        errors="coerce",
    )

    df["Hour"] = (
        df["Pickup_DateTime"]
        .dt.hour
    )

    df["Day_Name"] = (
        df["Pickup_DateTime"]
        .dt.day_name()
    )

    df["Is_Weekend"] = (
        df["Pickup_DateTime"]
        .dt.dayofweek
        .isin([5, 6])
        .astype(int)
    )

    # -----------------------------------------------------
    # Value per kilometer
    # -----------------------------------------------------

    completed_mask = (
        df["Booking Status"]
        == "Completed"
    )

    valid_distance = (
        df["Ride Distance"].notna()
        & (df["Ride Distance"] > 0)
    )

    df["Value_Per_Km"] = (
        df["Booking Value"]
        / df["Ride Distance"]
    ).where(
        completed_mask
        & valid_distance
    )

    # -----------------------------------------------------
    # Remove redundant/raw columns
    # -----------------------------------------------------

    cols_to_drop = [
        "Cancelled Rides by Customer",
        "Cancelled Rides by Driver",
        "Incomplete Rides",
        "Date",
        "Time",
    ]

    existing_drop_columns = [
        column
        for column in cols_to_drop
        if column in df.columns
    ]

    if existing_drop_columns:
        df.drop(
            columns=existing_drop_columns,
            inplace=True,
        )

    # -----------------------------------------------------
    # Save cleaned data
    # -----------------------------------------------------

    if output_csv_path:

        output_dir = os.path.dirname(
            output_csv_path
        )

        if output_dir:
            os.makedirs(
                output_dir,
                exist_ok=True,
            )

        df.to_csv(
            output_csv_path,
            index=False,
        )

    return df


# =========================================================
# 5. SQLITE DATABASE
# =========================================================

def build_sqlite_database(
    csv_path: str,
    db_path: str,
) -> None:
    """
    Builds the SQLite database from the cleaned CSV.
    """

    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"Cleaned dataset not found: {csv_path}"
        )

    df = pd.read_csv(
        csv_path
    )

    os.makedirs(
        os.path.dirname(db_path),
        exist_ok=True,
    )

    conn = sqlite3.connect(
        db_path
    )

    try:

        df.to_sql(
            name="rides",
            con=conn,
            if_exists="replace",
            index=False,
        )

        cursor = conn.cursor()

        cursor.execute(
            'CREATE INDEX IF NOT EXISTS '
            'idx_rides_booking_id '
            'ON rides("Booking ID");'
        )

        cursor.execute(
            'CREATE INDEX IF NOT EXISTS '
            'idx_rides_pickup_location '
            'ON rides("Pickup Location");'
        )

        cursor.execute(
            'CREATE INDEX IF NOT EXISTS '
            'idx_rides_booking_status '
            'ON rides("Booking Status");'
        )

        cursor.execute(
            'CREATE INDEX IF NOT EXISTS '
            'idx_rides_hour '
            'ON rides("Hour");'
        )

        conn.commit()

    finally:

        conn.close()


def query_sqlite(
    query: str,
    params=(),
) -> pd.DataFrame:
    """
    Executes a read-only SQL query against the SQLite database.
    """

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            "SQLite database does not exist."
        )

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        return pd.read_sql_query(
            query,
            conn,
            params=params,
        )

    finally:

        conn.close()


# =========================================================
# 6. DATA LOADER
# =========================================================

@st.cache_data(
    show_spinner="Loading cleaned dataset..."
)
def get_cleaned_data():

    if (
        not os.path.exists(CLEANED_PATH)
        and os.path.exists(RAW_PATH)
    ):

        clean_uber_data(
            RAW_PATH,
            CLEANED_PATH,
        )

    if (
        not os.path.exists(DB_PATH)
        and os.path.exists(CLEANED_PATH)
    ):

        build_sqlite_database(
            CLEANED_PATH,
            DB_PATH,
        )

    if os.path.exists(CLEANED_PATH):

        return pd.read_csv(
            CLEANED_PATH
        )

    if os.path.exists(RAW_PATH):

        return pd.read_csv(
            RAW_PATH
        )

    return None


# =========================================================
# 7. CACHED ANALYTICS WRAPPERS
# =========================================================

@st.cache_data(show_spinner=False)
def load_overall_kpis():
    return overall_kpis()


@st.cache_data(show_spinner=False)
def load_demand_by_pickup():
    return completed_rides_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_demand_by_hour():
    return completed_rides_by_hour()


@st.cache_data(show_spinner=False)
def load_demand_by_day():
    return completed_rides_by_day_of_week()


@st.cache_data(show_spinner=False)
def load_demand_pickup_hour():
    return completed_rides_by_pickup_and_hour()


@st.cache_data(show_spinner=False)
def load_high_demand(
    hour,
    day_name,
    top_n: int,
):
    return high_demand_pickup_locations(
        hour=hour,
        day_name=day_name,
        top_n=top_n,
    )


@st.cache_data(show_spinner=False)
def load_avg_fare_by_pickup():
    return avg_booking_value_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_avg_vpk_by_pickup():
    return avg_value_per_km_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_avg_vpk_by_hour():
    return avg_value_per_km_by_hour()


@st.cache_data(show_spinner=False)
def load_opportunity(
    min_rides: int,
    top_n: int,
    hour,
    day_name,
):
    return strong_earning_opportunity_locations(
        min_completed_rides=min_rides,
        top_n=top_n,
        hour=hour,
        day_name=day_name,
    )


@st.cache_data(show_spinner=False)
def load_status_distribution():
    return booking_status_distribution()


@st.cache_data(show_spinner=False)
def load_cancel_by_pickup():
    return cancellation_rate_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_cancel_by_hour():
    return cancellation_rate_by_hour()


@st.cache_data(show_spinner=False)
def load_customer_cancel():
    return customer_cancellation_counts_and_rates()


@st.cache_data(show_spinner=False)
def load_driver_cancel():
    return driver_cancellation_counts_and_rates()


@st.cache_data(show_spinner=False)
def load_customer_reasons():
    return customer_cancellation_reasons()


@st.cache_data(show_spinner=False)
def load_driver_reasons():
    return driver_cancellation_reasons()


@st.cache_data(show_spinner=False)
def load_incomplete_reasons():
    return incomplete_ride_counts_and_reasons()


# =========================================================
# 8. PICKUP LOCATIONS
# =========================================================

@st.cache_data(show_spinner=False)
def load_pickup_locations() -> list[str]:
    """
    Loads actual pickup locations from SQLite.
    """

    result = query_sqlite(
        """
        SELECT DISTINCT "Pickup Location"
        FROM rides
        WHERE "Pickup Location" IS NOT NULL
          AND TRIM("Pickup Location") <> ''
        ORDER BY "Pickup Location";
        """
    )

    if result.empty:
        return []

    return (
        result["Pickup Location"]
        .astype(str)
        .tolist()
    )


# =========================================================
# 9. GENERAL HELPERS
# =========================================================

def go_to(page: str) -> None:

    st.session_state.nav = page

    st.rerun()


def parse_hour(selection: str):

    return (
        None
        if selection == ALL_HOURS
        else int(
            selection.split(":")[0]
        )
    )


def parse_day(selection: str):

    return (
        None
        if selection == ALL_DAYS
        else selection
    )


def parse_location(selection: str):

    return (
        None
        if selection == ALL_LOCATIONS
        else selection
    )


def format_percentage(value, decimals: int = 2) -> str:
    """
    Safely formats percentage values.

    Some analytics functions return rates as decimals
    such as 0.8333, while contextual results may already
    contain percentage-point values such as 83.33.

    This helper prevents:
        83.33 -> 8333.00%

    and correctly displays:
        0.8333 -> 83.33%
        83.33 -> 83.33%
    """

    try:

        numeric_value = float(value)

        if pd.isna(numeric_value):
            return "—"

        if abs(numeric_value) <= 1:
            numeric_value *= 100

        return f"{numeric_value:.{decimals}f}%"

    except (
        TypeError,
        ValueError,
    ):

        return "—"


def safe_float(value):
    """
    Safely converts a value to float.
    """

    try:

        numeric_value = float(value)

        if pd.isna(numeric_value):
            return None

        return numeric_value

    except (
        TypeError,
        ValueError,
    ):

        return None


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    sort: str | None = "-y",
) -> None:

    if df.empty:

        st.info(
            "No rows to chart for the current filters."
        )

        return

    x_title = (
        x.split(":")[0]
        .replace("_", " ")
        .title()
    )

    y_title = (
        y.replace("_", " ")
        .title()
    )

    x_enc = alt.X(
        x,
        title=x_title,
    )

    if sort is not None:

        x_enc = alt.X(
            x,
            sort=sort,
            title=x_title,
        )

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=x_enc,
            y=alt.Y(
                y,
                title=y_title,
            ),
            tooltip=list(
                df.columns
            ),
        )
        .properties(
            title=title,
            height=280,
        )
    )

    st.altair_chart(
        chart,
        width="stretch",
    )


def ranked_table(
    df: pd.DataFrame,
    value_col: str = "completed_rides",
) -> pd.DataFrame:

    out = (
        df.copy()
        .reset_index(drop=True)
    )

    out.insert(
        0,
        "rank",
        range(
            1,
            len(out) + 1,
        ),
    )

    return out


# =========================================================
# 10. HOME PAGE — CONTEXTUAL ANALYSIS
# =========================================================

def get_home_context_result(
    pickup_location: str,
    hour: int,
    day_name: str,
    vehicle_type: str,
) -> pd.DataFrame:

    selected_vehicle_type = (
        None
        if vehicle_type
        == "All Vehicle Types"
        else vehicle_type
    )

    return contextual_location_hour_analysis(
        pickup_location=pickup_location,
        hour=hour,
        day_name=day_name,
        vehicle_type=selected_vehicle_type,
    )


def prepare_home_result_for_ai(
    result: pd.DataFrame,
) -> str:

    if result.empty:

        return (
            "No matching historical records were found."
        )

    safe_result = result.copy()

    safe_result = safe_result.where(
        pd.notnull(safe_result),
        None,
    )

    return json.dumps(
        safe_result.to_dict(
            orient="records"
        ),
        ensure_ascii=False,
        default=str,
    )


def generate_home_insight(
    pickup_location: str,
    hour: int,
    day_name: str,
    vehicle_type: str,
    result: pd.DataFrame,
) -> str:
    """
    Gemini is used ONLY as the explanation layer.

    Historical analytics are calculated by the application first.
    Gemini does not calculate the analytics and does not make
    predictions.
    """

    client = genai.Client()

    result_text = prepare_home_result_for_ai(
        result
    )

    prompt = f"""
You are the business-analysis explanation layer for a
ride-hailing worker decision-support application.

The application uses historical {DATASET_REGION} ride data.

The worker selected:

Pickup location: {pickup_location}
Hour: {hour:02d}:00
Day: {day_name}
Vehicle type: {vehicle_type}

The analytics layer has already calculated the historical
context for this exact selection.

ANALYTICS RESULT:
{result_text}

Your task is ONLY to explain the historical result.

RULES:

1. Lead with the most useful historical finding.

2. Keep the answer concise:
   normally 3 to 5 sentences.

3. Use ONLY numbers contained in the analytics result.

4. Never invent or calculate unsupported numbers.

5. Do not make predictions.

6. Do not say:
   "you will get more rides"
   "you will earn more"
   "go here"
   "demand will increase"
   or similar predictive/recommendation language.

7. Use responsible wording such as:
   "Historically, this location showed..."
   "The historical records show..."
   "Among the recorded bookings..."

8. Consider multiple signals when available:
   - booking volume
   - completed rides
   - completion rate
   - average booking value
   - average ride distance
   - average value per kilometer
   - customer cancellation rate
   - driver cancellation rate
   - combined cancellation rate
   - festival activity

9. Explain trade-offs when useful.

10. Do not make causal claims.

11. Cancellation rates are descriptive historical patterns.

12. If a cancellation reason is present, describe it only
    as a recorded/reported reason.

13. If a small-sample warning is present, mention it.

14. If the vehicle-specific sample is too small and the analytics
    layer falls back to all vehicles, explicitly mention that.

15. The dataset is {DATASET_REGION}.
    Never call it Hyderabad data.

16. Do not use headings such as "Key Takeaways".

17. Do not use a Markdown table.

18. Do not mention AI, Gemini, Python, SQL, tools, or implementation.

Return only the final business explanation.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    return clean_ai_response(
        response.text
        if response.text
        else ""
    )


# =========================================================
# 11. HOME PAGE
# =========================================================

def render_home() -> None:

    st.title(
        APP_TITLE
    )

    st.caption(
        f"Historical ride intelligence for ride-hailing workers · "
        f"{DATASET_REGION}"
    )

    st.markdown(
        """
        Use a **location, time, day, and vehicle type** to inspect
        what the historical records show for that context.

        The Home page is designed for a **quick decision view**:
        select the context, get the historical pattern, and move on.

        The application does not predict future rides or future earnings.
        """
    )

    # -----------------------------------------------------
    # Overall KPIs
    # -----------------------------------------------------

    kpis = (
        load_overall_kpis()
        .iloc[0]
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total bookings",
        f"{int(kpis['total_bookings']):,}",
    )

    c2.metric(
        "Completed rides",
        f"{int(kpis['completed_rides']):,}",
    )

    c3.metric(
        "Completion rate",
        format_percentage(
            kpis["completion_rate"],
            decimals=1,
        ),
    )

    c4.metric(
        "Avg. value / km",
        f"₹{kpis['avg_value_per_km']:.2f}",
    )

    st.caption(
        "Value per km uses completed rides only; "
        "missing values are not imputed."
    )

    st.markdown("---")

    # -----------------------------------------------------
    # Main quick-decision experience
    # -----------------------------------------------------

    st.subheader(
        "Quick historical insight"
    )

    st.write(
        "Choose the current ride context. "
        "The application will analyze the matching historical "
        "records and show the main pattern."
    )

    try:

        locations = load_pickup_locations()

    except Exception as exc:

        st.error(
            f"Could not load pickup locations from SQLite: {exc}"
        )

        locations = []

    if not locations:

        st.warning(
            "No pickup locations were found in the SQLite database."
        )

        return

    f1, f2, f3, f4 = st.columns(
        [2.4, 1, 1.3, 1.5]
    )

    with f1:

        pickup_location = st.selectbox(
            "Pickup Location",
            locations,
            key="home_pickup_location",
        )

    with f2:

        hour = st.selectbox(
            "Hour",
            list(range(24)),
            format_func=lambda x: f"{x:02d}:00",
            key="home_hour",
        )

    with f3:

        day_name = st.selectbox(
            "Day",
            list(VALID_DAYS),
            key="home_day",
        )

    with f4:

        vehicle_type = st.selectbox(
            "Vehicle Type",
            VEHICLE_TYPES,
            key="home_vehicle_type",
        )

    get_insight = st.button(
        "🔎 Get Insight",
        type="primary",
        width="stretch",
    )

    if not get_insight:
        return

    # -----------------------------------------------------
    # Historical analysis
    # -----------------------------------------------------

    with st.spinner(
        "Analyzing historical ride patterns..."
    ):

        try:

            result = get_home_context_result(
                pickup_location=pickup_location,
                hour=int(hour),
                day_name=day_name,
                vehicle_type=vehicle_type,
            )

        except AnalyticsError as exc:

            st.error(
                str(exc)
            )

            return

        except Exception as exc:

            st.error(
                f"Could not complete the historical analysis: {exc}"
            )

            return

    if result.empty:

        st.info(
            "The dataset does not contain enough matching "
            "historical records for this location, hour, and day."
        )

        return

    # Save context for AI Assistant.
    st.session_state.home_last_result = (
        result.copy()
    )

    st.session_state.home_last_context = {
        "pickup_location": pickup_location,
        "hour": int(hour),
        "day_name": day_name,
        "vehicle_type": vehicle_type,
    }

    # -----------------------------------------------------
    # Historical warning
    # -----------------------------------------------------

    sample_warning = None

    if "sample_size_warning" in result.columns:

        warnings = (
            result[
                "sample_size_warning"
            ]
            .dropna()
            .astype(str)
        )

        if not warnings.empty:

            sample_warning = (
                warnings.iloc[0]
            )

    if sample_warning:

        st.warning(
            f"Historical sample note: {sample_warning}"
        )

    # -----------------------------------------------------
    # Vehicle fallback warning
    # -----------------------------------------------------

    vehicle_fallback = False

    if "vehicle_type_fallback" in result.columns:

        fallback_values = (
            result[
                "vehicle_type_fallback"
            ]
            .dropna()
            .tolist()
        )

        if fallback_values:

            vehicle_fallback = bool(
                fallback_values[0]
            )

    if vehicle_fallback:

        used_vehicle = (
            result[
                "vehicle_type_used"
            ].iloc[0]
            if "vehicle_type_used"
            in result.columns
            else "All Vehicle Types"
        )

        specific_sample = (
            result[
                "vehicle_specific_sample_size"
            ].iloc[0]
            if "vehicle_specific_sample_size"
            in result.columns
            else None
        )

        if specific_sample is not None:

            st.info(
                f"The selected vehicle type had only "
                f"{int(specific_sample)} historical booking(s), "
                f"below the minimum sample threshold. "
                f"The broader {used_vehicle} historical pattern "
                f"is shown instead."
            )

    # -----------------------------------------------------
    # Gemini explanation
    #
    # IMPORTANT:
    # Gemini is optional for the Home page.
    # The historical Demand / Earnings / Cancellation
    # sections below work independently of Gemini.
    # -----------------------------------------------------

    insight = ""

    with st.spinner(
        "Generating the business explanation..."
    ):

        try:

            insight = generate_home_insight(
                pickup_location=pickup_location,
                hour=int(hour),
                day_name=day_name,
                vehicle_type=vehicle_type,
                result=result,
            )

        except Exception:

            insight = ""

    # -----------------------------------------------------
    # Main insight
    # -----------------------------------------------------

    st.markdown(
        "### Historical insight"
    )

    if insight:

        st.success(
            insight
        )

    else:

        st.info(
            "The historical analysis is available below. "
            "The AI explanation is temporarily unavailable, "
            "but the historical Demand, Earnings, and "
            "Cancellation evidence is still available."
        )

    # -----------------------------------------------------
    # Extract main historical values
    # -----------------------------------------------------

    row = result.iloc[0]

    total_bookings = safe_float(
        row.get("total_bookings")
    )

    completed_rides = safe_float(
        row.get("completed_rides")
    )

    completion_rate = safe_float(
        row.get("completion_rate")
    )

    avg_booking_value = safe_float(
        row.get("avg_booking_value")
    )

    avg_ride_distance = safe_float(
        row.get("avg_ride_distance")
    )

    avg_value_per_km = safe_float(
        row.get("avg_value_per_km")
    )

    customer_cancellations = safe_float(
        row.get("customer_cancellations")
    )

    customer_cancellation_rate = safe_float(
        row.get("customer_cancellation_rate")
    )

    driver_cancellations = safe_float(
        row.get("driver_cancellations")
    )

    driver_cancellation_rate = safe_float(
        row.get("driver_cancellation_rate")
    )

    combined_cancellations = safe_float(
        row.get("combined_cancellations")
    )

    combined_cancellation_rate = safe_float(
        row.get("combined_cancellation_rate")
    )

    festival_bookings = safe_float(
        row.get("festival_bookings")
    )

    festival_booking_share = safe_float(
        row.get("festival_booking_share")
    )

    # -----------------------------------------------------
    # Historical evidence
    #
    # This is now deliberately divided into:
    # Demand / Earnings / Cancellation.
    # -----------------------------------------------------

    st.markdown(
        "### Historical evidence"
    )

    st.caption(
        "These three sections are calculated directly from "
        "the matching historical records."
    )

    demand_col, earnings_col, cancel_col = st.columns(3)

    # =====================================================
    # DEMAND
    # =====================================================

    with demand_col:

        st.markdown(
            "#### 📍 Demand"
        )

        st.metric(
            "Historical bookings",
            (
                f"{int(total_bookings):,}"
                if total_bookings is not None
                else "—"
            ),
        )

        st.metric(
            "Completed rides",
            (
                f"{int(completed_rides):,}"
                if completed_rides is not None
                else "—"
            ),
        )

        st.metric(
            "Completion rate",
            (
                format_percentage(
                    completion_rate,
                    decimals=2,
                )
                if completion_rate is not None
                else "—"
            ),
        )

        st.caption(
            "Demand here is represented by the historical "
            "booking and completed-ride activity in this exact context."
        )

    # =====================================================
    # EARNINGS
    # =====================================================

    with earnings_col:

        st.markdown(
            "#### 💰 Earnings"
        )

        st.metric(
            "Avg. booking value",
            (
                f"₹{avg_booking_value:,.2f}"
                if avg_booking_value is not None
                else "—"
            ),
        )

        st.metric(
            "Avg. ride distance",
            (
                f"{avg_ride_distance:,.2f} km"
                if avg_ride_distance is not None
                else "—"
            ),
        )

        st.metric(
            "Avg. value / km",
            (
                f"₹{avg_value_per_km:,.2f}"
                if avg_value_per_km is not None
                else "—"
            ),
        )

        st.caption(
            "₹/km uses completed rides and helps compare "
            "booking value relative to ride distance."
        )

    # =====================================================
    # CANCELLATION
    # =====================================================

    with cancel_col:

        st.markdown(
            "#### ❌ Cancellation"
        )

        st.metric(
            "Customer cancellation",
            (
                format_percentage(
                    customer_cancellation_rate,
                    decimals=2,
                )
                if customer_cancellation_rate is not None
                else "—"
            ),
        )

        st.metric(
            "Driver cancellation",
            (
                format_percentage(
                    driver_cancellation_rate,
                    decimals=2,
                )
                if driver_cancellation_rate is not None
                else "—"
            ),
        )

        st.metric(
            "Combined cancellation",
            (
                format_percentage(
                    combined_cancellation_rate,
                    decimals=2,
                )
                if combined_cancellation_rate is not None
                else "—"
            ),
        )

        st.caption(
            "Cancellation rates are descriptive historical "
            "patterns and do not establish causation."
        )

    # -----------------------------------------------------
    # Additional historical context
    # -----------------------------------------------------

    festival_available = (
        festival_bookings is not None
        or festival_booking_share is not None
    )

    if festival_available:

        st.markdown("#### 🎉 Festival context")

        festival_col1, festival_col2 = st.columns(2)

        with festival_col1:

            st.metric(
                "Festival bookings",
                (
                    f"{int(festival_bookings):,}"
                    if festival_bookings is not None
                    else "—"
                ),
            )

        with festival_col2:

            st.metric(
                "Festival booking share",
                (
                    format_percentage(
                        festival_booking_share,
                        decimals=2,
                    )
                    if festival_booking_share is not None
                    else "—"
                ),
            )

        if (
            "observed_festivals" in result.columns
            and pd.notna(row.get("observed_festivals"))
        ):

            observed_festivals = str(
                row["observed_festivals"]
            )

            if observed_festivals.strip():

                st.caption(
                    f"Observed festival activity in this context: "
                    f"{observed_festivals}"
                )

    # -----------------------------------------------------
    # Detailed context
    # -----------------------------------------------------

    with st.expander(
        "View detailed historical context"
    ):

        display_columns = [
            "total_bookings",
            "completed_rides",
            "completion_rate",
            "avg_booking_value",
            "avg_ride_distance",
            "avg_value_per_km",
            "customer_cancellations",
            "customer_cancellation_rate",
            "driver_cancellations",
            "driver_cancellation_rate",
            "combined_cancellations",
            "combined_cancellation_rate",
            "festival_bookings",
            "festival_booking_share",
            "observed_festivals",
            "vehicle_type_requested",
            "vehicle_type_used",
            "vehicle_type_fallback",
            "vehicle_specific_sample_size",
            "sample_size_warning",
        ]

        available_columns = [
            column
            for column in display_columns
            if column in result.columns
        ]

        if available_columns:

            detail_df = result[
                available_columns
            ].copy()

            # Convert rate columns to readable percentages
            # without changing the underlying analytics result.
            percentage_columns = [
                "completion_rate",
                "customer_cancellation_rate",
                "driver_cancellation_rate",
                "combined_cancellation_rate",
                "festival_booking_share",
            ]

            for column in percentage_columns:

                if column in detail_df.columns:

                    detail_df[column] = (
                        detail_df[column]
                        .apply(
                            lambda value:
                            format_percentage(
                                value,
                                decimals=2,
                            )
                            if pd.notna(value)
                            else "—"
                        )
                    )

            st.dataframe(
                detail_df,
                hide_index=True,
                width="stretch",
            )

        else:

            st.dataframe(
                result,
                hide_index=True,
                width="stretch",
            )

    # -----------------------------------------------------
    # Deeper analytics
    # -----------------------------------------------------

    st.markdown("---")

    st.subheader(
        "Explore further"
    )

    st.write(
        "Use the detailed analytics pages when you want "
        "to inspect broader historical patterns beyond "
        "this exact context."
    )

    col_a, col_b, col_c = st.columns(3)

    with col_a:

        st.markdown(
            "**📍 Demand Intelligence**"
        )

        st.write(
            "Explore which pickup areas and hours "
            "show more completed rides."
        )

        if st.button(
            "Open Demand",
            width="stretch",
        ):

            go_to(
                NAV_DEMAND
            )

    with col_b:

        st.markdown(
            "**💰 Earnings Opportunity**"
        )

        st.write(
            "Compare completed-ride volume, booking "
            "value, distance, and ₹/km."
        )

        if st.button(
            "Open Earnings",
            width="stretch",
        ):

            go_to(
                NAV_EARNINGS
            )

    with col_c:

        st.markdown(
            "**❌ Cancellation Patterns**"
        )

        st.write(
            "Explore historical cancellation patterns "
            "across locations and hours."
        )

        if st.button(
            "Open Cancellations",
            width="stretch",
        ):

            go_to(
                NAV_CANCEL
            )


# =========================================================
# 12. DEMAND PAGE
# =========================================================

def render_demand() -> None:

    st.title(
        "📍 Demand Intelligence"
    )

    st.caption(
        f"Completed rides only · {DATASET_REGION}"
    )

    st.markdown(
        "Select an hour, day, or pickup area to rank "
        "**high-demand pickup locations** "
        "by completed-ride volume in this dataset."
    )

    locations = (
        [ALL_LOCATIONS]
        + load_demand_by_pickup()[
            "pickup_location"
        ].tolist()
    )

    hour_options = (
        [ALL_HOURS]
        + [
            f"{h:02d}:00"
            for h in range(24)
        ]
    )

    day_options = (
        [ALL_DAYS]
        + list(VALID_DAYS)
    )

    f1, f2, f3, f4 = st.columns(
        [1, 1, 1.4, 0.8]
    )

    with f1:

        hour_sel = st.selectbox(
            "Hour",
            hour_options,
        )

    with f2:

        day_sel = st.selectbox(
            "Day of week",
            day_options,
        )

    with f3:

        loc_sel = st.selectbox(
            "Pickup location",
            locations,
        )

    with f4:

        top_n = st.number_input(
            "Show top",
            min_value=5,
            max_value=30,
            value=10,
            step=1,
        )

    hour = parse_hour(
        hour_sel
    )

    day_name = parse_day(
        day_sel
    )

    location = parse_location(
        loc_sel
    )

    ranked = load_high_demand(
        hour,
        day_name,
        int(top_n),
    )

    if location:

        ranked = ranked[
            ranked[
                "pickup_location"
            ]
            == location
        ]

        if ranked.empty:

            fallback = load_high_demand(
                hour,
                day_name,
                176,
            )

            ranked = fallback[
                fallback[
                    "pickup_location"
                ]
                == location
            ]

    ranked = ranked_table(
        ranked
    )

    st.subheader(
        "High-demand pickup locations"
    )

    if ranked.empty:

        st.info(
            "No completed rides match the current filters."
        )

    else:

        lead = ranked.iloc[0]

        filter_bits = []

        if hour is not None:

            filter_bits.append(
                f"hour {hour:02d}:00"
            )

        if day_name:

            filter_bits.append(
                day_name
            )

        if location:

            filter_bits.append(
                location
            )

        context = (
            " for "
            + ", ".join(filter_bits)
            if filter_bits
            else " across all hours and days"
        )

        st.success(
            f"In this dataset{context}, "
            f"**{lead['pickup_location']}** "
            f"ranks #{int(lead['rank'])} with "
            f"**{int(lead['completed_rides']):,}** "
            f"completed rides."
        )

        st.dataframe(
            ranked[
                [
                    "rank",
                    "pickup_location",
                    "completed_rides",
                ]
            ],
            hide_index=True,
            width="stretch",
        )

    st.markdown("---")

    st.subheader(
        "Supporting analytics"
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "By pickup location",
            "By hour",
            "By day",
            "Pickup × hour",
        ]
    )

    with tab1:

        by_loc = (
            load_demand_by_pickup()
            .head(20)
        )

        bar_chart(
            by_loc,
            "pickup_location",
            "completed_rides",
            "Top 20 pickup locations",
        )

    with tab2:

        by_hour = (
            load_demand_by_hour()
        )

        bar_chart(
            by_hour,
            "hour:O",
            "completed_rides",
            "Completed rides by hour",
            sort=None,
        )

        peak = by_hour.loc[
            by_hour[
                "completed_rides"
            ].idxmax()
        ]

        st.caption(
            f"Peak completed-ride hour in this dataset: "
            f"{int(peak['hour']):02d}:00 "
            f"({int(peak['completed_rides']):,} rides)."
        )

    with tab3:

        by_day = (
            load_demand_by_day()
        )

        bar_chart(
            by_day,
            "day_name",
            "completed_rides",
            "Completed rides by day",
            sort=None,
        )

    with tab4:

        grid = (
            load_demand_pickup_hour()
        )

        if location:

            loc_grid = grid[
                grid[
                    "pickup_location"
                ]
                == location
            ]

            bar_chart(
                loc_grid,
                "hour:O",
                "completed_rides",
                f"Hourly completed rides — {location}",
                sort=None,
            )

        else:

            top_locs = (
                load_demand_by_pickup()
                .head(12)[
                    "pickup_location"
                ]
                .tolist()
            )

            heat = grid[
                grid[
                    "pickup_location"
                ].isin(top_locs)
            ]

            chart = (
                alt.Chart(heat)
                .mark_rect()
                .encode(
                    x=alt.X(
                        "hour:O",
                        title="Hour",
                    ),
                    y=alt.Y(
                        "pickup_location:N",
                        sort=top_locs,
                        title="Pickup location",
                    ),
                    color=alt.Color(
                        "completed_rides:Q",
                        title="Completed rides",
                    ),
                    tooltip=[
                        "pickup_location",
                        "hour",
                        "completed_rides",
                    ],
                )
                .properties(
                    title="Top 12 locations × hour",
                    height=360,
                )
            )

            st.altair_chart(
                chart,
                width="stretch",
            )

            st.caption(
                "Heatmap limited to the 12 highest-volume "
                "pickup locations for readability."
            )


# =========================================================
# 13. EARNINGS PAGE
# =========================================================

def render_earnings() -> None:

    st.title(
        "💰 Earnings Opportunity"
    )

    st.caption(
        f"Completed rides only · {DATASET_REGION}"
    )

    st.markdown(
        """
        Compare fare level, distance, and **₹/km**
        across pickup areas and hours.

        **Opportunity Score = Average Value_Per_Km × Completed Ride Volume.**

        This is a descriptive ranking in this dataset,
        not a forecast of future earnings.
        """
    )

    kpis = (
        load_overall_kpis()
        .iloc[0]
    )

    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Avg. booking value",
        f"₹{kpis['avg_booking_value']:.0f}",
    )

    m2.metric(
        "Avg. ride distance",
        f"{kpis['avg_ride_distance']:.1f} km",
    )

    m3.metric(
        "Avg. value / km",
        f"₹{kpis['avg_value_per_km']:.2f}",
    )

    m4.metric(
        "Completed volume",
        f"{int(kpis['completed_rides']):,}",
    )

    locations = (
        [ALL_LOCATIONS]
        + load_avg_vpk_by_pickup()[
            "pickup_location"
        ].tolist()
    )

    hour_options = (
        [ALL_HOURS]
        + [
            f"{h:02d}:00"
            for h in range(24)
        ]
    )

    day_options = (
        [ALL_DAYS]
        + list(VALID_DAYS)
    )

    f1, f2, f3, f4 = st.columns(4)

    with f1:

        hour_sel = st.selectbox(
            "Hour",
            hour_options,
            key="earn_hour",
        )

    with f2:

        day_sel = st.selectbox(
            "Day of week",
            day_options,
            key="earn_day",
        )

    with f3:

        loc_sel = st.selectbox(
            "Pickup location",
            locations,
            key="earn_loc",
        )

    with f4:

        min_rides = st.number_input(
            "Min. completed rides",
            min_value=20,
            max_value=500,
            value=100,
            step=10,
        )

    hour = parse_hour(
        hour_sel
    )

    day_name = parse_day(
        day_sel
    )

    location = parse_location(
        loc_sel
    )

    min_for_query = (
        20
        if (
            hour is not None
            or day_name
        )
        else int(min_rides)
    )

    opp = load_opportunity(
        min_for_query,
        20,
        hour,
        day_name,
    )

    if location:

        scoped = load_opportunity(
            1,
            500,
            hour,
            day_name,
        )

        opp = scoped[
            scoped[
                "pickup_location"
            ]
            == location
        ]

    st.subheader(
        "Locations with stronger earning opportunity"
    )

    if opp.empty:

        st.info(
            "No completed-ride earnings rows "
            "match the current filters."
        )

    else:

        lead = opp.iloc[0]

        st.success(
            f"In this dataset, "
            f"**{lead['pickup_location']}** "
            f"has the highest Opportunity Score "
            f"among the current filters "
            f"({lead['opportunity_score']:,.0f}). "
            "That combines observed ₹/km with "
            "completed-ride volume — it is not a prediction."
        )

        show_cols = [
            "pickup_location",
            "completed_rides",
            "avg_booking_value",
            "avg_ride_distance",
            "avg_value_per_km",
            "opportunity_score",
        ]

        display = opp[
            show_cols
        ].copy()

        display.insert(
            0,
            "rank",
            range(
                1,
                len(display) + 1,
            ),
        )

        st.dataframe(
            display,
            hide_index=True,
            width="stretch",
        )

    st.markdown("---")

    st.subheader(
        "Supporting analytics"
    )

    t1, t2, t3, t4 = st.tabs(
        [
            "₹/km by location",
            "Booking value by location",
            "₹/km by hour",
            "Volume vs opportunity",
        ]
    )

    with t1:

        vpk = (
            load_avg_vpk_by_pickup()
            .head(20)
        )

        bar_chart(
            vpk,
            "pickup_location",
            "avg_value_per_km",
            "Highest average ₹/km (top 20)",
        )

    with t2:

        fare = (
            load_avg_fare_by_pickup()
            .head(20)
        )

        bar_chart(
            fare,
            "pickup_location",
            "avg_booking_value",
            "Highest average booking value (top 20)",
        )

    with t3:

        vpk_h = (
            load_avg_vpk_by_hour()
        )

        bar_chart(
            vpk_h,
            "hour:O",
            "avg_value_per_km",
            "Average ₹/km by hour",
            sort=None,
        )

        best = vpk_h.loc[
            vpk_h[
                "avg_value_per_km"
            ].idxmax()
        ]

        st.caption(
            f"Highest average ₹/km in this dataset: "
            f"{int(best['hour']):02d}:00 "
            f"(₹{best['avg_value_per_km']:.2f}/km)."
        )

    with t4:

        scatter_src = load_opportunity(
            1,
            176,
            hour,
            day_name,
        )

        if scatter_src.empty:

            st.info(
                "Not enough completed rides to plot."
            )

        else:

            chart = (
                alt.Chart(
                    scatter_src
                )
                .mark_circle(
                    size=70
                )
                .encode(
                    x=alt.X(
                        "completed_rides:Q",
                        title="Completed ride volume",
                    ),
                    y=alt.Y(
                        "avg_value_per_km:Q",
                        title="Average ₹/km",
                    ),
                    color=alt.Color(
                        "opportunity_score:Q",
                        title="Opportunity Score",
                    ),
                    tooltip=[
                        "pickup_location",
                        "completed_rides",
                        "avg_value_per_km",
                        "avg_booking_value",
                        "opportunity_score",
                    ],
                )
                .properties(
                    title="Ride volume vs ₹/km (descriptive)",
                    height=320,
                )
            )

            st.altair_chart(
                chart,
                width="stretch",
            )


# =========================================================
# 14. CANCELLATION PAGE
# =========================================================

def render_cancellations() -> None:

    st.title(
        "❌ Cancellation Patterns"
    )

    st.caption(
        f"Descriptive patterns in this {DATASET_REGION} dataset — "
        "not causal claims"
    )

    st.markdown(
        "Rates use **all bookings** in each group as the denominator. "
        "A higher rate means an associated cancellation pattern, "
        "not that a place or hour causes cancellations."
    )

    status = (
        load_status_distribution()
    )

    customer = (
        load_customer_cancel()
        .iloc[0]
    )

    driver = (
        load_driver_cancel()
        .iloc[0]
    )

    combined_rate = (
        customer[
            "customer_cancellations"
        ]
        + driver[
            "driver_cancellations"
        ]
    ) / customer[
        "total_bookings"
    ]

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Customer cancel rate",
        f"{customer['customer_cancellation_rate'] * 100:.1f}%",
    )

    k2.metric(
        "Driver cancel rate",
        f"{driver['driver_cancellation_rate'] * 100:.1f}%",
    )

    k3.metric(
        "Combined cancel rate",
        f"{combined_rate * 100:.1f}%",
    )

    k4.metric(
        "Total bookings",
        f"{int(customer['total_bookings']):,}",
    )

    locations = (
        [ALL_LOCATIONS]
        + load_cancel_by_pickup()[
            "pickup_location"
        ].tolist()
    )

    hour_options = (
        [ALL_HOURS]
        + [
            f"{h:02d}:00"
            for h in range(24)
        ]
    )

    f1, f2 = st.columns(2)

    with f1:

        loc_sel = st.selectbox(
            "Pickup location",
            locations,
            key="cxl_loc",
        )

    with f2:

        hour_sel = st.selectbox(
            "Hour",
            hour_options,
            key="cxl_hour",
        )

    location = parse_location(
        loc_sel
    )

    hour = parse_hour(
        hour_sel
    )

    by_loc = (
        load_cancel_by_pickup()
    )

    by_hour = (
        load_cancel_by_hour()
    )

    if location:

        loc_row = by_loc[
            by_loc[
                "pickup_location"
            ]
            == location
        ]

        if not loc_row.empty:

            rate = loc_row.iloc[0][
                "combined_cancellation_rate"
            ]

            st.info(
                f"In this dataset, **{location}** "
                f"has a combined cancellation rate of "
                f"**{rate * 100:.1f}%** of bookings "
                f"at that pickup area."
            )

    if hour is not None:

        hour_row = by_hour[
            by_hour[
                "hour"
            ]
            == hour
        ]

        if not hour_row.empty:

            rate = hour_row.iloc[0][
                "combined_cancellation_rate"
            ]

            st.info(
                f"At **{hour:02d}:00**, this dataset "
                f"shows a combined cancellation rate of "
                f"**{rate * 100:.1f}%** of that hour's bookings."
            )

    st.subheader(
        "Booking-status distribution"
    )

    bar_chart(
        status,
        "booking_status",
        "booking_count",
        "Bookings by status",
    )

    st.dataframe(
        status,
        hide_index=True,
        width="stretch",
    )

    st.markdown("---")

    st.subheader(
        "Supporting analysis"
    )

    t1, t2, t3, t4, t5 = st.tabs(
        [
            "Rate by location",
            "Rate by hour",
            "Customer reasons",
            "Driver reasons",
            "Incomplete rides",
        ]
    )

    with t1:

        loc_view = (
            by_loc
            if not location
            else by_loc[
                by_loc[
                    "pickup_location"
                ]
                == location
            ]
        )

        st.dataframe(
            (
                loc_view.head(25)
                if location is None
                else loc_view
            ),
            hide_index=True,
            width="stretch",
        )

        chart_df = (
            by_loc.head(15)
        )

        bar_chart(
            chart_df,
            "pickup_location",
            "combined_cancellation_rate",
            "Higher combined cancellation rates observed (top 15)",
        )

    with t2:

        hour_view = (
            by_hour
            if hour is None
            else by_hour[
                by_hour[
                    "hour"
                ]
                == hour
            ]
        )

        st.dataframe(
            hour_view,
            hide_index=True,
            width="stretch",
        )

        bar_chart(
            by_hour,
            "hour:O",
            "combined_cancellation_rate",
            "Combined cancellation rate by hour",
            sort=None,
        )

    with t3:

        reasons = (
            load_customer_reasons()
        )

        bar_chart(
            reasons,
            "cancellation_reason",
            "reason_count",
            "Customer cancellation reasons",
        )

        st.dataframe(
            reasons,
            hide_index=True,
            width="stretch",
        )

    with t4:

        reasons = (
            load_driver_reasons()
        )

        bar_chart(
            reasons,
            "cancellation_reason",
            "reason_count",
            "Driver cancellation reasons",
        )

        st.dataframe(
            reasons,
            hide_index=True,
            width="stretch",
        )

    with t5:

        reasons = (
            load_incomplete_reasons()
        )

        bar_chart(
            reasons,
            "incomplete_reason",
            "incomplete_count",
            "Incomplete ride reasons",
        )

        st.dataframe(
            reasons,
            hide_index=True,
            width="stretch",
        )


# =========================================================
# 15. ANALYTICS / DATA PAGE
# =========================================================

def render_analytics() -> None:

    st.title(
        "📊 Analytics / Explore Data"
    )

    st.caption(
        f"Detailed tables for the underlying {DATASET_REGION} "
        "extract and cleaning pipeline"
    )

    # -----------------------------------------------------
    # Re-run cleaning
    # -----------------------------------------------------

    if os.path.exists(RAW_PATH):

        if st.sidebar.button(
            "⚡ Re-run Cleaning Pipeline"
        ):

            with st.spinner(
                "Executing cleaning pipeline..."
            ):

                clean_uber_data(
                    RAW_PATH,
                    CLEANED_PATH,
                )

                if os.path.exists(
                    DB_PATH
                ):

                    os.remove(
                        DB_PATH
                    )

                build_sqlite_database(
                    CLEANED_PATH,
                    DB_PATH,
                )

                st.cache_data.clear()

                st.sidebar.success(
                    "CSV cleaning and SQLite rebuild completed!"
                )

                st.rerun()

    # -----------------------------------------------------
    # Rebuild SQLite
    # -----------------------------------------------------

    if os.path.exists(CLEANED_PATH):

        if st.sidebar.button(
            "🗄️ Rebuild SQLite Database"
        ):

            with st.spinner(
                "Rebuilding SQLite database & indexes..."
            ):

                build_sqlite_database(
                    CLEANED_PATH,
                    DB_PATH,
                )

                st.cache_data.clear()

                st.sidebar.success(
                    "Database rebuilt successfully!"
                )

                st.rerun()

    st.sidebar.markdown(
        "---"
    )

    dataset_choice = st.sidebar.radio(
        "Active Data Engine:",
        options=[
            "Cleaned Dataset (Active)",
            "Raw Dataset (Reference)",
        ],
        index=0,
    )

    if (
        dataset_choice
        == "Cleaned Dataset (Active)"
    ):

        df = get_cleaned_data()

        active_title = (
            "Cleaned Operational Dataset "
            "(`uber_rides_cleaned.csv` & `uber_rides.db`)"
        )

    else:

        df = (
            pd.read_csv(
                RAW_PATH
            )
            if os.path.exists(
                RAW_PATH
            )
            else None
        )

        active_title = (
            "Raw Untouched Dataset "
            "(`uber_rides_raw.csv`)"
        )

    if df is None:

        st.error(
            "Dataset not found in `data/` directory."
        )

        return

    st.subheader(
        active_title
    )

    if os.path.exists(
        DB_PATH
    ):

        st.success(
            "SQLite database active: "
            "`uber_rides.db` "
            "(table `rides`, indexes on Booking ID, "
            "Pickup Location, Booking Status, and Hour)."
        )

    num_rows, num_cols = (
        df.shape
    )

    completed_count = (
        int(
            (
                df[
                    "Booking Status"
                ]
                == "Completed"
            ).sum()
        )
        if "Booking Status"
        in df.columns
        else 0
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    col1.metric(
        "Total rows",
        f"{num_rows:,}",
    )

    col2.metric(
        "Total columns",
        f"{num_cols:,}",
    )

    col3.metric(
        "Completed rides",
        f"{completed_count:,}",
    )

    if (
        "Value_Per_Km" in df.columns
        and completed_count > 0
    ):

        col4.metric(
            "Median ₹/km",
            f"₹{df['Value_Per_Km'].median():.2f}",
        )

    else:

        mem_mb = (
            df.memory_usage(
                deep=True
            ).sum()
            / (1024 * 1024)
        )

        col4.metric(
            "Memory footprint",
            f"{mem_mb:.1f} MB",
        )

    # -----------------------------------------------------
    # Preview
    # -----------------------------------------------------

    st.subheader(
        "Dataset preview: first 20 rows"
    )

    st.caption(
        f"Showing first 20 records of "
        f"{num_rows:,} total rows"
    )

    st.dataframe(
        df.head(20),
        width="stretch",
    )

    # -----------------------------------------------------
    # Schema
    # -----------------------------------------------------

    st.subheader(
        f"Columns & schema ({num_cols} columns)"
    )

    null_counts = (
        df.isnull().sum()
    )

    col_info = pd.DataFrame(
        {
            "#": range(
                1,
                len(df.columns) + 1,
            ),
            "Column Name": df.columns,
            "Data Type": [
                str(dtype)
                for dtype in df.dtypes
            ],
            "Non-Null Count": (
                num_rows
                - null_counts
            ).values,
            "Null Count": (
                null_counts
            ).values,
            "Null Percentage": [
                (
                    count
                    / num_rows
                ) * 100
                for count
                in null_counts.values
            ],
        }
    )

    col_info[
        "Null Percentage"
    ] = (
        col_info[
            "Null Percentage"
        ]
        .apply(
            lambda x: f"{x:.1f}%"
        )
    )

    st.dataframe(
        col_info,
        hide_index=True,
        width="stretch",
    )

    # -----------------------------------------------------
    # Descriptive statistics
    # -----------------------------------------------------

    with st.expander(
        "Descriptive statistics"
    ):

        tab1, tab2 = st.tabs(
            [
                "Numerical metrics",
                "Categorical metrics",
            ]
        )

        with tab1:

            num_df = (
                df.select_dtypes(
                    include=["number"]
                )
            )

            if not num_df.empty:

                st.dataframe(
                    num_df.describe().T,
                    width="stretch",
                )

        with tab2:

            cat_df = (
                df.select_dtypes(
                    exclude=["number"]
                )
            )

            if not cat_df.empty:

                st.dataframe(
                    cat_df.astype(str)
                    .describe()
                    .T,
                    width="stretch",
                )


# =========================================================
# 16. AI ASSISTANT
# =========================================================

def clean_ai_response(
    text: str,
) -> str:
    """
    Removes formatting artifacts from AI-generated output.
    """

    if not text:
        return ""

    text = re.sub(
        r"\[svg\]\(http\://localhost:[^)]+\)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"!\[[^\]]*\]\(http\://localhost:[^)]+\)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def render_ai_assistant() -> None:

    st.title("🤖 AI Assistant")

    st.caption(
        "Ask questions about historical demand, earnings, "
        "cancellations, or get deeper reasoning about your "
        "latest Home-page insight."
    )

    load_dotenv()

    client = genai.Client()

    # =========================================================
    # HOME PAGE CONTEXT
    # =========================================================

    home_context = st.session_state.get(
        "home_last_context",
        None,
    )

    home_result = st.session_state.get(
        "home_last_result",
        None,
    )

    if (
        home_context is not None
        and home_result is not None
        and not home_result.empty
    ):

        st.info(
            "💡 The AI Assistant can use your latest Home-page "
            "context for deeper questions."
        )

        hc1, hc2, hc3, hc4 = st.columns(4)

        hc1.metric(
            "Location",
            home_context["pickup_location"],
        )

        hc2.metric(
            "Hour",
            f"{int(home_context['hour']):02d}:00",
        )

        hc3.metric(
            "Day",
            home_context["day_name"],
        )

        hc4.metric(
            "Vehicle",
            home_context["vehicle_type"],
        )

        st.caption(
            "Example: after checking Home, you can ask "
            "\"Why are cancellations high here?\" or "
            "\"What should I understand from these numbers?\""
        )

    # =========================================================
    # AI RESPONSE RULES
    # =========================================================

    AI_INSTRUCTIONS = """

You are the business-analysis assistant for a ride-hailing
decision-support application used by drivers.

Your job is to help the worker understand the historical
Delhi NCR ride dataset.

PRODUCT STRUCTURE:

The application has two related experiences:

1. HOME PAGE
   The Home page gives the worker a quick historical snapshot
   for a selected:
   - pickup location
   - hour
   - day
   - vehicle type

2. AI ASSISTANT
   The AI Assistant provides deeper reasoning and explanations.

The AI Assistant can work in TWO ways:

A. HOME-CONTEXT MODE
   If the worker has already used the Home page, use the
   Home-page context and historical result when the question
   relates to that context.

B. INDEPENDENT MODE
   If there is no Home-page context, or if the worker asks a
   general question, use the available analytics tools normally.

IMPORTANT:

The Home page and AI Assistant are NOT duplicate features.

Home gives the worker a quick answer.

AI Assistant helps the worker understand WHY the historical
numbers look the way they do and lets the worker ask deeper
follow-up questions.

The AI Assistant is NOT a prediction engine.

The application is NOT a live ride-hailing platform.

It does NOT predict individual future earnings or future ride
availability.

=========================================================
GENERAL RESPONSE RULES
=========================================================

1. Give concise, business-friendly answers.

2. Normally answer in about 3–5 sentences.

3. Lead with the main finding.

4. Use only numbers returned by the analytics tools or provided
   in the Home-page historical context.

5. Never invent numbers, locations, dates, festivals, or patterns.

6. Do not create a large Markdown table unless the user explicitly
   asks for one.

7. Do not repeat the same number unnecessarily.

8. Use bullets only when they improve readability.

9. Do not produce unnecessary headings for short answers.

10. Never include HTML, SVG, localhost links, or UI/debug artifacts.

11. Do not infer causes from descriptive data.

12. Do not assign blame to drivers, customers, locations, or hours.

13. When cancellation reasons are available, describe them as
    reported or recorded reasons.

14. A recorded cancellation reason does not prove the underlying cause.

15. Clearly distinguish:

    - completed rides
    - customer cancellations
    - driver cancellations
    - no-driver-found bookings
    - incomplete rides

16. When comparing driver and customer cancellations, describe
    the observed percentages without assuming why they differ.

17. Always describe findings as historical patterns or associations
    observed in this dataset.

18. Do not make predictions such as:

    "You will get more rides."

    "You will definitely earn more."

    "Demand will increase."

    "Go here because you will get a ride."

19. Use responsible wording such as:

    "Historically, this location showed..."

    "In the historical records..."

    "The dataset shows..."

    "Among the recorded rides..."

20. The dataset represents Delhi NCR.

21. NEVER call the current dataset Hyderabad data.

22. If the user asks a simple question, answer simply.

23. Do not force the user to understand technical analytics terminology.

24. If a user asks something like:

    "what does this mean?"

    explain the result in simple driver-friendly language.

25. If a user asks:

    "why?"

    explain the historical signals available in the data,
    but do not claim that the data proves causation.

26. If a user asks:

    "what should I understand?"

    explain the trade-offs and meaning of the historical
    numbers without making a guaranteed recommendation.

=========================================================
HOME-CONTEXT RULES
=========================================================

If Home-page context is provided:

- Treat it as the driver's current investigation context.

- Use the exact:
  location
  hour
  day
  vehicle type

- Use the historical result associated with that context.

- If the question clearly refers to:
  "here"
  "this location"
  "this hour"
  "these numbers"
  "this result"
  "why is cancellation high?"
  "why is value per km low?"
  "what does this mean?"
  "explain this"

  then use the Home context.

- Do not ask the driver to repeat the location, hour, day,
  or vehicle type when they are already available from Home.

- If the user asks a completely unrelated general question,
  use the appropriate analytics tool instead.

- If the Home result contains a small-sample warning, mention it
  when relevant.

- If the Home result contains vehicle fallback information,
  explain that the selected vehicle had insufficient historical
  records and the broader pattern was used.

=========================================================
CONTEXTUAL ANALYSIS
=========================================================

For a specific location + hour + day question, use:

contextual_location_hour_analysis

Consider these signals together:

- booking volume
- completed rides
- completion rate
- average booking value
- average ride distance
- average value per kilometer
- customer cancellation rate
- driver cancellation rate
- combined cancellation rate
- festival activity
- observed festivals

Do not focus on only one metric when contextual analysis is available.

Explain trade-offs when useful.

For example:

A higher average booking value does not automatically mean a
stronger earning opportunity because ride distance and ₹/km
also matter.

A higher historical cancellation rate is an observed pattern.
It does not prove that the location or hour causes cancellations.

=========================================================
SIMPLE QUESTIONS
=========================================================

The worker may ask normal/simple questions.

Examples:

"what is cancellation rate?"

"what does ₹/km mean?"

"why should I look at completed rides?"

"what does this result mean?"

"why is high booking value not enough?"

Answer these in simple language.

Do not force a tool call when a simple explanation can be given
without data.

=========================================================
DATA RULES
=========================================================

If the question requires actual dataset numbers:

- Use the relevant analytics tool.
- Never invent values.

If a specific location, hour and day are given:

- Use contextual_location_hour_analysis.

If broad demand is requested:

- Use completed_rides_by_pickup_location.

If broad earning opportunity is requested:

- Use strong_earning_opportunity_locations.

If cancellation status is requested:

- Use booking_status_distribution.

If cancellation by location is requested:

- Use cancellation_rate_by_pickup_location.

If cancellation by hour is requested:

- Use cancellation_rate_by_hour.

If customer cancellation reasons are requested:

- Use customer_cancellation_reasons.

If driver cancellation reasons are requested:

- Use driver_cancellation_reasons.

If incomplete ride reasons are requested:

- Use incomplete_ride_counts_and_reasons.

=========================================================
"""

    # =========================================================
    # ANALYTICS TOOLS
    # =========================================================

    get_demand = {
        "type": "function",
        "name": "completed_rides_by_pickup_location",
        "description": (
            "Returns the number of completed rides for each "
            "pickup location. Use for broad historical demand "
            "questions."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    get_earnings = {
        "type": "function",
        "name": "strong_earning_opportunity_locations",
        "description": (
            "Returns pickup locations with stronger historical "
            "earning opportunity based on average booking value, "
            "average value per kilometer, and completed ride volume."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    get_contextual_analysis = {
        "type": "function",
        "name": "contextual_location_hour_analysis",
        "description": (
            "Returns a combined historical analysis for one specific "
            "pickup location, hour of day, and day of week, optionally "
            "filtered by vehicle type. Use for specific location and "
            "time questions. The result includes booking volume, "
            "completed rides, completion rate, average booking value, "
            "ride distance, value per kilometer, cancellation rates, "
            "and festival activity."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pickup_location": {
                    "type": "string",
                    "description": (
                        "Exact pickup location from the Delhi NCR dataset."
                    ),
                },
                "hour": {
                    "type": "integer",
                    "description": (
                        "Hour of day using 24-hour format."
                    ),
                },
                "day_name": {
                    "type": "string",
                    "enum": [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ],
                },
                "vehicle_type": {
                    "type": "string",
                    "enum": [
                        "All Vehicle Types",
                        "Bike",
                        "Auto",
                        "Go Mini",
                        "Go Sedan",
                        "Premier Sedan",
                        "eBike",
                        "Uber XL",
                    ],
                },
            },
            "required": [
                "pickup_location",
                "hour",
                "day_name",
                "vehicle_type",
            ],
        },
    }

    get_cancellations = {
        "type": "function",
        "name": "booking_status_distribution",
        "description": (
            "Returns the overall distribution of booking statuses."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    get_cancellation_by_location = {
        "type": "function",
        "name": "cancellation_rate_by_pickup_location",
        "description": (
            "Returns cancellation rates by pickup location."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    get_cancellation_by_hour = {
        "type": "function",
        "name": "cancellation_rate_by_hour",
        "description": (
            "Returns cancellation rates by hour."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    get_customer_cancellation_reasons = {
        "type": "function",
        "name": "customer_cancellation_reasons",
        "description": (
            "Returns reported customer cancellation reasons."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    get_driver_cancellation_reasons = {
        "type": "function",
        "name": "driver_cancellation_reasons",
        "description": (
            "Returns reported driver cancellation reasons."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    get_incomplete_reasons = {
        "type": "function",
        "name": "incomplete_ride_counts_and_reasons",
        "description": (
            "Returns incomplete ride counts and reported reasons."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    tools = [
        get_contextual_analysis,
        get_demand,
        get_earnings,
        get_cancellations,
        get_cancellation_by_location,
        get_cancellation_by_hour,
        get_customer_cancellation_reasons,
        get_driver_cancellation_reasons,
        get_incomplete_reasons,
    ]

    # =========================================================
    # HOME CONTEXT → GEMINI
    # =========================================================

    home_context_text = ""

    if (
        home_context is not None
        and home_result is not None
        and not home_result.empty
    ):

        safe_home_result = home_result.copy()

        safe_home_result = safe_home_result.where(
            pd.notnull(safe_home_result),
            None,
        )

        home_result_json = json.dumps(
            safe_home_result.to_dict(
                orient="records"
            ),
            ensure_ascii=False,
            default=str,
        )

        home_context_text = f"""

=========================================================
LATEST HOME-PAGE CONTEXT
=========================================================

The driver most recently checked this context on the Home page:

Pickup location: {home_context["pickup_location"]}
Hour: {int(home_context["hour"]):02d}:00
Day: {home_context["day_name"]}
Vehicle type: {home_context["vehicle_type"]}

The Home page's historical analysis result is:

{home_result_json}

IMPORTANT:

If the driver's next question refers to "here", "this",
"this location", "this hour", "these numbers", "this result",
or asks for a deeper explanation of the Home result, use this
context.

Do not ask the driver to repeat the Home-page selection.

The Home result is historical data, not a prediction.
"""

    # =========================================================
    # USER QUESTION
    # =========================================================

    question = st.chat_input(
        "Ask a simple question or ask deeper about your Home insight..."
    )

    if not question:
        return

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):

        with st.spinner("Analyzing your data..."):

            try:

                interaction = client.interactions.create(
                    model=GEMINI_MODEL,
                    input=(
                        AI_INSTRUCTIONS
                        + home_context_text
                        + "\n\nUSER QUESTION:\n"
                        + question
                    ),
                    tools=tools,
                )

            except Exception as exc:

                st.error(
                    f"Could not connect to Gemini: {exc}"
                )

                return

            function_call_found = False

            for step in interaction.steps:

                if step.type != "function_call":
                    continue

                function_call_found = True

                # =================================================
                # CONTEXTUAL ANALYSIS
                # =================================================

                if (
                    step.name
                    == "contextual_location_hour_analysis"
                ):

                    args = step.arguments

                    if isinstance(
                        args,
                        str,
                    ):
                        args = json.loads(args)

                    pickup_location = args.get(
                        "pickup_location"
                    )

                    hour = args.get(
                        "hour"
                    )

                    day_name = args.get(
                        "day_name"
                    )

                    vehicle_type = args.get(
                        "vehicle_type",
                        "All Vehicle Types",
                    )

                    if (
                        not pickup_location
                        or hour is None
                        or not day_name
                        or not vehicle_type
                    ):

                        st.error(
                            "Please provide a complete location, "
                            "hour, day, and vehicle type."
                        )

                        return

                    try:

                        hour = int(hour)

                    except (
                        TypeError,
                        ValueError,
                    ):

                        st.error(
                            "The requested hour could not be interpreted."
                        )

                        return

                    selected_vehicle_type = (
                        None
                        if vehicle_type
                        == "All Vehicle Types"
                        else vehicle_type
                    )

                    result = (
                        contextual_location_hour_analysis(
                            pickup_location=pickup_location,
                            hour=hour,
                            day_name=day_name,
                            vehicle_type=selected_vehicle_type,
                        )
                    )

                # =================================================
                # GENERAL DEMAND
                # =================================================

                elif (
                    step.name
                    == "completed_rides_by_pickup_location"
                ):

                    result = (
                        completed_rides_by_pickup_location()
                    )

                # =================================================
                # GENERAL EARNINGS
                # =================================================

                elif (
                    step.name
                    == "strong_earning_opportunity_locations"
                ):

                    result = (
                        strong_earning_opportunity_locations()
                    )

                # =================================================
                # BOOKING STATUS
                # =================================================

                elif (
                    step.name
                    == "booking_status_distribution"
                ):

                    result = (
                        booking_status_distribution()
                    )

                # =================================================
                # CANCELLATION BY LOCATION
                # =================================================

                elif (
                    step.name
                    == "cancellation_rate_by_pickup_location"
                ):

                    result = (
                        cancellation_rate_by_pickup_location()
                    )

                # =================================================
                # CANCELLATION BY HOUR
                # =================================================

                elif (
                    step.name
                    == "cancellation_rate_by_hour"
                ):

                    result = (
                        cancellation_rate_by_hour()
                    )

                # =================================================
                # CUSTOMER REASONS
                # =================================================

                elif (
                    step.name
                    == "customer_cancellation_reasons"
                ):

                    result = (
                        customer_cancellation_reasons()
                    )

                # =================================================
                # DRIVER REASONS
                # =================================================

                elif (
                    step.name
                    == "driver_cancellation_reasons"
                ):

                    result = (
                        driver_cancellation_reasons()
                    )

                # =================================================
                # INCOMPLETE RIDES
                # =================================================

                elif (
                    step.name
                    == "incomplete_ride_counts_and_reasons"
                ):

                    result = (
                        incomplete_ride_counts_and_reasons()
                    )

                else:

                    continue

                # =================================================
                # RESULT → GEMINI
                # =================================================

                result_text = json.dumps(
                    result.to_dict(
                        orient="records"
                    ),
                    ensure_ascii=False,
                    default=str,
                )

                try:

                    follow_up = client.interactions.create(
                        model=GEMINI_MODEL,
                        previous_interaction_id=interaction.id,
                        input=[
                            {
                                "type": "function_result",
                                "name": step.name,
                                "call_id": step.id,
                                "result": [
                                    {
                                        "type": "text",
                                        "text": result_text,
                                    }
                                ],
                            }
                        ],
                    )

                    answer = clean_ai_response(
                        follow_up.output_text
                    )

                except Exception as exc:

                    st.error(
                        f"Could not generate the final AI explanation: "
                        f"{exc}"
                    )

                    return

                if answer:

                    st.write(answer)

                else:

                    st.info(
                        "The historical analysis completed, "
                        "but no explanation was returned."
                    )

                break

            # =====================================================
            # NO TOOL CALL
            # =====================================================

            if not function_call_found:

                answer = clean_ai_response(
                    interaction.output_text
                )

                if answer:

                    st.write(answer)

                else:

                    st.info(
                        "I could not identify the relevant analytics "
                        "for that question. Try asking about a location, "
                        "time, demand, earnings, or cancellations."
                    )


# =========================================================
# 17. SIDEBAR NAVIGATION
# =========================================================

if "nav" not in st.session_state:

    st.session_state.nav = (
        NAV_HOME
    )


st.sidebar.title(
    APP_TITLE
)

st.sidebar.caption(
    DATASET_REGION
)

st.sidebar.radio(
    "Navigate",
    NAV_PAGES,
    key="nav",
)

st.sidebar.markdown(
    "---"
)


# =========================================================
# 18. PAGE ROUTING
# =========================================================

page = st.session_state.nav


try:

    # -----------------------------------------------------
    # All pages except Analytics require SQLite.
    # Analytics can rebuild it.
    # -----------------------------------------------------

    if (
        not os.path.exists(DB_PATH)
        and page != NAV_ANALYTICS
    ):

        st.error(
            "SQLite database not found. "
            "Open Analytics to rebuild it from "
            "the cleaned CSV."
        )

        st.info(
            "If this is the first run, open "
            "📊 Analytics and rebuild the database."
        )

    elif page == NAV_HOME:

        render_home()

    elif page == NAV_DEMAND:

        render_demand()

    elif page == NAV_EARNINGS:

        render_earnings()

    elif page == NAV_CANCEL:

        render_cancellations()

    elif page == NAV_ANALYTICS:

        render_analytics()

    elif page == NAV_AI:

        render_ai_assistant()


except AnalyticsError as exc:

    st.error(
        str(exc)
    )

except FileNotFoundError as exc:

    st.error(
        str(exc)
    )

except Exception as exc:

    st.error(
        "The application encountered an unexpected error."
    )

    st.caption(
        f"Technical detail: {exc}"
    )