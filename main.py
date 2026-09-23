import os
import sqlite3
import json

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
)

# ==========================================
# 1. PAGE CONFIGURATION & PATHS
# ==========================================
st.set_page_config(
    page_title="Ride Decision Support — Delhi NCR",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RAW_PATH = os.path.join(DATA_DIR, "uber_rides_raw.csv")
CLEANED_PATH = os.path.join(DATA_DIR, "uber_rides_cleaned.csv")
DB_PATH = os.path.join(DATA_DIR, "uber_rides.db")

NAV_HOME = "🏠 Home"
NAV_DEMAND = "📍 Demand"
NAV_EARNINGS = "💰 Earnings"
NAV_CANCEL = "❌ Cancellations"
NAV_ANALYTICS = "📊 Analytics"
NAV_AI = "🤖 AI Assistant"
NAV_PAGES = [NAV_HOME, NAV_DEMAND, NAV_EARNINGS, NAV_CANCEL, NAV_ANALYTICS, NAV_AI]

ALL_HOURS = "All hours"
ALL_DAYS = "All days"
ALL_LOCATIONS = "All pickup locations"


# =========================================================
# 2. AUTOMATED DATA CLEANING PIPELINE (UNCHANGED)
# =========================================================
def clean_uber_data(raw_csv_path: str, output_csv_path: str = None) -> pd.DataFrame:
    """
    Automated cleaning pipeline for Uber rides dataset:
    - Leaves raw CSV completely untouched.
    - Strips literal quotes from Booking ID and Customer ID.
    - Combines Date and Time into a unified Pickup_DateTime.
    - Extracts Hour, Day_Name, and Is_Weekend.
    - Calculates Value_Per_Km for Completed rides.
    - Drops redundant indicator columns and raw Date/Time strings.
    - Saves to a separate cleaned CSV.
    """
    df = pd.read_csv(raw_csv_path)
    df["Booking ID"] = df["Booking ID"].astype(str).str.strip("\"'")
    df["Customer ID"] = df["Customer ID"].astype(str).str.strip("\"'")
    df["Pickup_DateTime"] = pd.to_datetime(
        df["Date"] + " " + df["Time"], format="%d-%m-%Y %H:%M:%S"
    )
    df["Hour"] = df["Pickup_DateTime"].dt.hour
    df["Day_Name"] = df["Pickup_DateTime"].dt.day_name()
    df["Is_Weekend"] = df["Pickup_DateTime"].dt.dayofweek.isin([5, 6]).astype(int)
    df["Value_Per_Km"] = (df["Booking Value"] / df["Ride Distance"]).where(
        df["Booking Status"] == "Completed"
    )
    cols_to_drop = [
        "Cancelled Rides by Customer",
        "Cancelled Rides by Driver",
        "Incomplete Rides",
        "Date",
        "Time",
    ]
    df.drop(columns=cols_to_drop, inplace=True)
    if output_csv_path:
        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
        df.to_csv(output_csv_path, index=False)
    return df


def build_sqlite_database(csv_path: str, db_path: str) -> None:
    """Creates an SQLite database from the cleaned Uber rides CSV."""
    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    df.to_sql(name="rides", con=conn, if_exists="replace", index=False)
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_rides_booking_id ON rides("Booking ID");')
    cursor.execute(
        'CREATE INDEX IF NOT EXISTS idx_rides_pickup_location ON rides("Pickup Location");'
    )
    conn.commit()
    conn.close()


def query_sqlite(query: str, params=()) -> pd.DataFrame:
    """Runs a read-only SQL query against uber_rides.db and returns a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    result_df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return result_df


@st.cache_data(show_spinner="Loading cleaned dataset...")
def get_cleaned_data():
    if not os.path.exists(CLEANED_PATH) and os.path.exists(RAW_PATH):
        clean_uber_data(RAW_PATH, CLEANED_PATH)
    if not os.path.exists(DB_PATH) and os.path.exists(CLEANED_PATH):
        build_sqlite_database(CLEANED_PATH, DB_PATH)
    if os.path.exists(CLEANED_PATH):
        return pd.read_csv(CLEANED_PATH)
    if os.path.exists(RAW_PATH):
        return pd.read_csv(RAW_PATH)
    return None


# ==========================================
# 3. CACHED ANALYTICS WRAPPERS (no SQL here)
# ==========================================
@st.cache_data(show_spinner=False)
def load_overall_kpis() -> pd.DataFrame:
    return overall_kpis()


@st.cache_data(show_spinner=False)
def load_demand_by_pickup() -> pd.DataFrame:
    return completed_rides_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_demand_by_hour() -> pd.DataFrame:
    return completed_rides_by_hour()


@st.cache_data(show_spinner=False)
def load_demand_by_day() -> pd.DataFrame:
    return completed_rides_by_day_of_week()


@st.cache_data(show_spinner=False)
def load_demand_pickup_hour() -> pd.DataFrame:
    return completed_rides_by_pickup_and_hour()


@st.cache_data(show_spinner=False)
def load_high_demand(hour, day_name, top_n: int) -> pd.DataFrame:
    return high_demand_pickup_locations(hour=hour, day_name=day_name, top_n=top_n)


@st.cache_data(show_spinner=False)
def load_avg_fare_by_pickup() -> pd.DataFrame:
    return avg_booking_value_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_avg_vpk_by_pickup() -> pd.DataFrame:
    return avg_value_per_km_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_avg_vpk_by_hour() -> pd.DataFrame:
    return avg_value_per_km_by_hour()


@st.cache_data(show_spinner=False)
def load_opportunity(min_rides: int, top_n: int, hour, day_name) -> pd.DataFrame:
    return strong_earning_opportunity_locations(
        min_completed_rides=min_rides,
        top_n=top_n,
        hour=hour,
        day_name=day_name,
    )


@st.cache_data(show_spinner=False)
def load_status_distribution() -> pd.DataFrame:
    return booking_status_distribution()


@st.cache_data(show_spinner=False)
def load_cancel_by_pickup() -> pd.DataFrame:
    return cancellation_rate_by_pickup_location()


@st.cache_data(show_spinner=False)
def load_cancel_by_hour() -> pd.DataFrame:
    return cancellation_rate_by_hour()


@st.cache_data(show_spinner=False)
def load_customer_cancel() -> pd.DataFrame:
    return customer_cancellation_counts_and_rates()


@st.cache_data(show_spinner=False)
def load_driver_cancel() -> pd.DataFrame:
    return driver_cancellation_counts_and_rates()


@st.cache_data(show_spinner=False)
def load_customer_reasons() -> pd.DataFrame:
    return customer_cancellation_reasons()


@st.cache_data(show_spinner=False)
def load_driver_reasons() -> pd.DataFrame:
    return driver_cancellation_reasons()


@st.cache_data(show_spinner=False)
def load_incomplete_reasons() -> pd.DataFrame:
    return incomplete_ride_counts_and_reasons()


def go_to(page: str) -> None:
    st.session_state.nav = page
    st.rerun()


def parse_hour(selection: str):
    return None if selection == ALL_HOURS else int(selection.split(":")[0])


def parse_day(selection: str):
    return None if selection == ALL_DAYS else selection


def parse_location(selection: str):
    return None if selection == ALL_LOCATIONS else selection


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, sort: str | None = "-y") -> None:
    if df.empty:
        st.info("No rows to chart for the current filters.")
        return
    x_enc = alt.X(x, title=x.split(":")[0].replace("_", " ").title())
    if sort is not None:
        x_enc = alt.X(x, sort=sort, title=x.split(":")[0].replace("_", " ").title())
    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=x_enc,
            y=alt.Y(y, title=y.replace("_", " ").title()),
            tooltip=list(df.columns),
        )
        .properties(title=title, height=280)
    )
    st.altair_chart(chart, width="stretch")


def ranked_table(df: pd.DataFrame, value_col: str = "completed_rides") -> pd.DataFrame:
    out = df.copy().reset_index(drop=True)
    out.insert(0, "rank", range(1, len(out) + 1))
    return out


# ==========================================
# 4. PAGE RENDERERS
# ==========================================
def render_home() -> None:
    st.title("Ride Decision Support")
    st.caption("Delhi NCR operational dataset · built for ride-hailing workers")
    st.markdown(
        """
        This application helps workers inspect **where demand concentrates**,
        **where completed rides show stronger fare intensity**, and
        **where cancellations appear more often in this dataset**.

        Geography is Delhi NCR. The same layout can later use a comparable
        Hyderabad extract without renaming the current data.
        """
    )

    kpis = load_overall_kpis().iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total bookings", f"{int(kpis['total_bookings']):,}")
    c2.metric("Completed rides", f"{int(kpis['completed_rides']):,}")
    c3.metric("Completion rate", f"{kpis['completion_rate'] * 100:.1f}%")
    c4.metric("Avg. value / km", f"₹{kpis['avg_value_per_km']:.2f}")
    st.caption("Value per km uses completed rides only; missing values are not imputed.")

    st.subheader("Choose a decision area")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("**📍 Demand Intelligence**")
        st.write("Which pickup areas and hours show the most completed rides?")
        if st.button("Open Demand", width="stretch"):
            go_to(NAV_DEMAND)
    with col_b:
        st.markdown("**💰 Earnings Opportunity**")
        st.write("Where do completed rides combine volume with higher ₹/km?")
        if st.button("Open Earnings", width="stretch"):
            go_to(NAV_EARNINGS)
    with col_c:
        st.markdown("**❌ Cancellation Patterns**")
        st.write("Where are higher cancellation rates observed in this dataset?")
        if st.button("Open Cancellations", width="stretch"):
            go_to(NAV_CANCEL)


def render_demand() -> None:
    st.title("📍 Demand Intelligence")
    st.caption("Completed rides only · Delhi NCR")
    st.markdown(
        "Select an hour, day, or pickup area to rank **high-demand pickup locations** "
        "by completed-ride volume in this dataset."
    )

    locations = ["All pickup locations"] + load_demand_by_pickup()["pickup_location"].tolist()
    hour_options = [ALL_HOURS] + [f"{h:02d}:00" for h in range(24)]
    day_options = [ALL_DAYS] + list(VALID_DAYS)

    f1, f2, f3, f4 = st.columns([1, 1, 1.4, 0.8])
    with f1:
        hour_sel = st.selectbox("Hour", hour_options)
    with f2:
        day_sel = st.selectbox("Day of week", day_options)
    with f3:
        loc_sel = st.selectbox("Pickup location", locations)
    with f4:
        top_n = st.number_input("Show top", min_value=5, max_value=30, value=10, step=1)

    hour = parse_hour(hour_sel)
    day_name = parse_day(day_sel)
    location = parse_location(loc_sel)

    ranked = load_high_demand(hour, day_name, int(top_n))
    if location:
        ranked = ranked[ranked["pickup_location"] == location]
        if ranked.empty:
            fallback = load_high_demand(hour, day_name, 176)
            ranked = fallback[fallback["pickup_location"] == location]

    ranked = ranked_table(ranked)

    st.subheader("High-demand pickup locations")
    if ranked.empty:
        st.info("No completed rides match the current filters.")
    else:
        lead = ranked.iloc[0]
        filter_bits = []
        if hour is not None:
            filter_bits.append(f"hour {hour:02d}:00")
        if day_name:
            filter_bits.append(day_name)
        if location:
            filter_bits.append(location)
        context = " for " + ", ".join(filter_bits) if filter_bits else " across all hours and days"
        st.success(
            f"In this dataset{context}, **{lead['pickup_location']}** ranks #{int(lead['rank'])} "
            f"with **{int(lead['completed_rides']):,}** completed rides."
        )
        st.dataframe(
            ranked[["rank", "pickup_location", "completed_rides"]],
            hide_index=True,
            width="stretch",
        )

    st.markdown("---")
    st.subheader("Supporting analytics")
    tab1, tab2, tab3, tab4 = st.tabs(
        ["By pickup location", "By hour", "By day", "Pickup × hour"]
    )
    with tab1:
        by_loc = load_demand_by_pickup().head(20)
        bar_chart(by_loc, "pickup_location", "completed_rides", "Top 20 pickup locations")
    with tab2:
        by_hour = load_demand_by_hour()
        bar_chart(by_hour, "hour:O", "completed_rides", "Completed rides by hour", sort=None)
        peak = by_hour.loc[by_hour["completed_rides"].idxmax()]
        st.caption(
            f"Peak completed-ride hour in this dataset: {int(peak['hour']):02d}:00 "
            f"({int(peak['completed_rides']):,} rides)."
        )
    with tab3:
        by_day = load_demand_by_day()
        bar_chart(by_day, "day_name", "completed_rides", "Completed rides by day", sort=None)
    with tab4:
        grid = load_demand_pickup_hour()
        if location:
            loc_grid = grid[grid["pickup_location"] == location]
            bar_chart(
                loc_grid,
                "hour:O",
                "completed_rides",
                f"Hourly completed rides — {location}",
                sort=None,
            )
        else:
            top_locs = load_demand_by_pickup().head(12)["pickup_location"].tolist()
            heat = grid[grid["pickup_location"].isin(top_locs)]
            chart = (
                alt.Chart(heat)
                .mark_rect()
                .encode(
                    x=alt.X("hour:O", title="Hour"),
                    y=alt.Y("pickup_location:N", sort=top_locs, title="Pickup location"),
                    color=alt.Color("completed_rides:Q", title="Completed rides"),
                    tooltip=["pickup_location", "hour", "completed_rides"],
                )
                .properties(title="Top 12 locations × hour", height=360)
            )
            st.altair_chart(chart, width="stretch")
            st.caption("Heatmap limited to the 12 highest-volume pickup locations for readability.")


def render_earnings() -> None:
    st.title("💰 Earnings Opportunity")
    st.caption("Completed rides only · Delhi NCR")
    st.markdown(
        """
        Compare fare level, distance, and **₹/km** across pickup areas and hours.
        **Opportunity Score = Average Value_Per_Km × Completed Ride Volume**.
        This is a descriptive ranking in this dataset, not a forecast of future earnings.
        """
    )

    kpis = load_overall_kpis().iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Avg. booking value", f"₹{kpis['avg_booking_value']:.0f}")
    m2.metric("Avg. ride distance", f"{kpis['avg_ride_distance']:.1f} km")
    m3.metric("Avg. value / km", f"₹{kpis['avg_value_per_km']:.2f}")
    m4.metric("Completed volume", f"{int(kpis['completed_rides']):,}")

    locations = [ALL_LOCATIONS] + load_avg_vpk_by_pickup()["pickup_location"].tolist()
    hour_options = [ALL_HOURS] + [f"{h:02d}:00" for h in range(24)]
    day_options = [ALL_DAYS] + list(VALID_DAYS)

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        hour_sel = st.selectbox("Hour", hour_options, key="earn_hour")
    with f2:
        day_sel = st.selectbox("Day of week", day_options, key="earn_day")
    with f3:
        loc_sel = st.selectbox("Pickup location", locations, key="earn_loc")
    with f4:
        min_rides = st.number_input("Min. completed rides", min_value=20, max_value=500, value=100, step=10)

    hour = parse_hour(hour_sel)
    day_name = parse_day(day_sel)
    location = parse_location(loc_sel)
    min_for_query = 20 if (hour is not None or day_name) else int(min_rides)

    opp = load_opportunity(min_for_query, 20, hour, day_name)
    if location:
        scoped = load_opportunity(1, 500, hour, day_name)
        opp = scoped[scoped["pickup_location"] == location]

    st.subheader("Locations with stronger earning opportunity")
    if opp.empty:
        st.info("No completed-ride earnings rows match the current filters.")
    else:
        lead = opp.iloc[0]
        st.success(
            f"In this dataset, **{lead['pickup_location']}** has the highest Opportunity Score "
            f"among the current filters ({lead['opportunity_score']:,.0f}). "
            "That combines observed ₹/km with completed-ride volume — it is not a prediction."
        )
        show_cols = [
            "pickup_location",
            "completed_rides",
            "avg_booking_value",
            "avg_ride_distance",
            "avg_value_per_km",
            "opportunity_score",
        ]
        display = opp[show_cols].copy()
        display.insert(0, "rank", range(1, len(display) + 1))
        st.dataframe(display, hide_index=True, width="stretch")

    st.markdown("---")
    st.subheader("Supporting analytics")
    t1, t2, t3, t4 = st.tabs(
        ["₹/km by location", "Booking value by location", "₹/km by hour", "Volume vs opportunity"]
    )
    with t1:
        vpk = load_avg_vpk_by_pickup().head(20)
        bar_chart(vpk, "pickup_location", "avg_value_per_km", "Highest average ₹/km (top 20)")
    with t2:
        fare = load_avg_fare_by_pickup().head(20)
        bar_chart(fare, "pickup_location", "avg_booking_value", "Highest average booking value (top 20)")
    with t3:
        vpk_h = load_avg_vpk_by_hour()
        bar_chart(vpk_h, "hour:O", "avg_value_per_km", "Average ₹/km by hour", sort=None)
        best = vpk_h.loc[vpk_h["avg_value_per_km"].idxmax()]
        st.caption(
            f"Highest average ₹/km in this dataset: {int(best['hour']):02d}:00 "
            f"(₹{best['avg_value_per_km']:.2f}/km)."
        )
    with t4:
        scatter_src = load_opportunity(1, 176, hour, day_name)
        if scatter_src.empty:
            st.info("Not enough completed rides to plot.")
        else:
            chart = (
                alt.Chart(scatter_src)
                .mark_circle(size=70)
                .encode(
                    x=alt.X("completed_rides:Q", title="Completed ride volume"),
                    y=alt.Y("avg_value_per_km:Q", title="Average ₹/km"),
                    color=alt.Color("opportunity_score:Q", title="Opportunity Score"),
                    tooltip=[
                        "pickup_location",
                        "completed_rides",
                        "avg_value_per_km",
                        "avg_booking_value",
                        "opportunity_score",
                    ],
                )
                .properties(title="Ride volume vs ₹/km (descriptive)", height=320)
            )
            st.altair_chart(chart, width="stretch")


def render_cancellations() -> None:
    st.title("❌ Cancellation Patterns")
    st.caption("Descriptive patterns in this Delhi NCR dataset — not causal claims")
    st.markdown(
        "Rates use **all bookings** in each group as the denominator. "
        "A higher rate means an associated cancellation pattern, not that a place or hour causes cancellations."
    )

    status = load_status_distribution()
    customer = load_customer_cancel().iloc[0]
    driver = load_driver_cancel().iloc[0]
    combined_rate = (
        customer["customer_cancellations"] + driver["driver_cancellations"]
    ) / customer["total_bookings"]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Customer cancel rate", f"{customer['customer_cancellation_rate'] * 100:.1f}%")
    k2.metric("Driver cancel rate", f"{driver['driver_cancellation_rate'] * 100:.1f}%")
    k3.metric("Combined cancel rate", f"{combined_rate * 100:.1f}%")
    k4.metric("Total bookings", f"{int(customer['total_bookings']):,}")

    locations = [ALL_LOCATIONS] + load_cancel_by_pickup()["pickup_location"].tolist()
    hour_options = [ALL_HOURS] + [f"{h:02d}:00" for h in range(24)]
    f1, f2 = st.columns(2)
    with f1:
        loc_sel = st.selectbox("Pickup location", locations, key="cxl_loc")
    with f2:
        hour_sel = st.selectbox("Hour", hour_options, key="cxl_hour")
    location = parse_location(loc_sel)
    hour = parse_hour(hour_sel)

    by_loc = load_cancel_by_pickup()
    by_hour = load_cancel_by_hour()
    if location:
        loc_row = by_loc[by_loc["pickup_location"] == location]
        if not loc_row.empty:
            rate = loc_row.iloc[0]["combined_cancellation_rate"]
            st.info(
                f"In this dataset, **{location}** has a combined cancellation rate of "
                f"**{rate * 100:.1f}%** of bookings at that pickup area."
            )
    if hour is not None:
        hour_row = by_hour[by_hour["hour"] == hour]
        if not hour_row.empty:
            rate = hour_row.iloc[0]["combined_cancellation_rate"]
            st.info(
                f"At **{hour:02d}:00**, this dataset shows a combined cancellation rate of "
                f"**{rate * 100:.1f}%** of that hour's bookings."
            )

    st.subheader("Booking-status distribution")
    bar_chart(status, "booking_status", "booking_count", "Bookings by status")
    st.dataframe(status, hide_index=True, width="stretch")

    st.markdown("---")
    st.subheader("Supporting analysis")
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
        loc_view = by_loc if not location else by_loc[by_loc["pickup_location"] == location]
        st.dataframe(
            loc_view.head(25) if location is None else loc_view,
            hide_index=True,
            width="stretch",
        )
        chart_df = by_loc.head(15)
        bar_chart(
            chart_df,
            "pickup_location",
            "combined_cancellation_rate",
            "Higher combined cancellation rates observed (top 15)",
        )
    with t2:
        hour_view = by_hour if hour is None else by_hour[by_hour["hour"] == hour]
        st.dataframe(hour_view, hide_index=True, width="stretch")
        bar_chart(
            by_hour,
            "hour:O",
            "combined_cancellation_rate",
            "Combined cancellation rate by hour",
            sort=None,
        )
    with t3:
        reasons = load_customer_reasons()
        bar_chart(reasons, "cancellation_reason", "reason_count", "Customer cancellation reasons")
        st.dataframe(reasons, hide_index=True, width="stretch")
    with t4:
        reasons = load_driver_reasons()
        bar_chart(reasons, "cancellation_reason", "reason_count", "Driver cancellation reasons")
        st.dataframe(reasons, hide_index=True, width="stretch")
    with t5:
        reasons = load_incomplete_reasons()
        bar_chart(reasons, "incomplete_reason", "incomplete_count", "Incomplete ride reasons")
        st.dataframe(reasons, hide_index=True, width="stretch")


def render_analytics() -> None:
    st.title("📊 Analytics / Explore Data")
    st.caption("Detailed tables for the underlying Delhi NCR extract and cleaning pipeline")

    if os.path.exists(RAW_PATH):
        if st.sidebar.button("⚡ Re-run Cleaning Pipeline"):
            with st.spinner("Executing cleaning pipeline..."):
                clean_uber_data(RAW_PATH, CLEANED_PATH)
                st.cache_data.clear()
                st.sidebar.success("CSV pipeline executed successfully!")

    if os.path.exists(CLEANED_PATH):
        if st.sidebar.button("🗄️ Rebuild SQLite Database"):
            with st.spinner("Rebuilding SQLite database & indexes..."):
                build_sqlite_database(CLEANED_PATH, DB_PATH)
                st.cache_data.clear()
                st.sidebar.success("Database rebuilt successfully!")

    st.sidebar.markdown("---")
    dataset_choice = st.sidebar.radio(
        "Active Data Engine:",
        options=["Cleaned Dataset (Active)", "Raw Dataset (Reference)"],
        index=0,
    )

    if dataset_choice == "Cleaned Dataset (Active)":
        df = get_cleaned_data()
        active_title = "Cleaned Operational Dataset (`uber_rides_cleaned.csv` & `uber_rides.db`)"
    else:
        df = pd.read_csv(RAW_PATH) if os.path.exists(RAW_PATH) else None
        active_title = "Raw Untouched Dataset (`uber_rides_raw.csv`)"

    if df is None:
        st.error("Dataset not found in `data/` directory.")
        return

    st.subheader(active_title)
    if os.path.exists(DB_PATH):
        st.success(
            "SQLite database active: `uber_rides.db` (table `rides`, "
            "indexes on Booking ID and Pickup Location)."
        )

    num_rows, num_cols = df.shape
    completed_count = (
        int((df["Booking Status"] == "Completed").sum()) if "Booking Status" in df.columns else 0
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total rows", f"{num_rows:,}")
    col2.metric("Total columns", f"{num_cols:,}")
    col3.metric("Completed rides", f"{completed_count:,}")
    if "Value_Per_Km" in df.columns and completed_count > 0:
        col4.metric("Median ₹/km", f"₹{df['Value_Per_Km'].median():.2f}")
    else:
        mem_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
        col4.metric("Memory footprint", f"{mem_mb:.1f} MB")

    st.subheader("Dataset preview: first 20 rows")
    st.caption(f"Showing first 20 records of {num_rows:,} total rows")
    st.dataframe(df.head(20), width="stretch")

    st.subheader(f"Columns & schema ({num_cols} columns)")
    null_counts = df.isnull().sum()
    col_info = pd.DataFrame(
        {
            "#": range(1, len(df.columns) + 1),
            "Column Name": df.columns,
            "Data Type": [str(dtype) for dtype in df.dtypes],
            "Non-Null Count": (num_rows - null_counts).values,
            "Null Count": null_counts.values,
            "Null Percentage": [(count / num_rows) * 100 for count in null_counts.values],
        }
    )
    col_info["Null Percentage"] = col_info["Null Percentage"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(col_info, hide_index=True, width="stretch")

    with st.expander("Descriptive statistics"):
        tab1, tab2 = st.tabs(["Numerical metrics", "Categorical metrics"])
        with tab1:
            num_df = df.select_dtypes(include=["number"])
            if not num_df.empty:
                st.dataframe(num_df.describe().T, width="stretch")
        with tab2:
            cat_df = df.select_dtypes(exclude=["number"])
            if not cat_df.empty:
                st.dataframe(cat_df.astype(str).describe().T, width="stretch")



def render_ai_assistant() -> None:

    st.title("🤖 AI Assistant")

    st.caption("Ask questions about your ride data.")

    load_dotenv()

    client = genai.Client()

    get_demand = {
        "type": "function",
        "name": "completed_rides_by_pickup_location",
        "description": (
            "Returns the number of completed rides for each "
            "pickup location."
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
            "Returns pickup locations with strong earning opportunities "
            "based on average booking value and value per kilometer."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }

    question = st.chat_input(
        "Ask about ride demand or earnings..."
    )

    if question:

        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant"):

            with st.spinner("Analyzing your data..."):

                interaction = client.interactions.create(
                    model="gemini-3.6-flash",
                    input=question,
                    tools=[get_demand, get_earnings],
                )

                for step in interaction.steps:

                    if step.type == "function_call":

                        if step.name == "completed_rides_by_pickup_location":
                            result = completed_rides_by_pickup_location()

                        elif step.name == "strong_earning_opportunity_locations":
                            result = strong_earning_opportunity_locations()

                        follow_up = client.interactions.create(
                            model="gemini-3.6-flash",
                            previous_interaction_id=interaction.id,
                            input=[
                                {
                                    "type": "function_result",
                                    "name": step.name,
                                    "call_id": step.id,
                                    "result": [
                                        {
                                            "type": "text",
                                            "text": json.dumps(
                                                result.to_dict(
                                                    orient="records"
                                                )
                                            ),
                                        }
                                    ],
                                }
                            ],
                        )

                        st.write(
                            follow_up.output_text
                        )



# ==========================================
# 5. NAVIGATION
# ==========================================
if "nav" not in st.session_state:
    st.session_state.nav = NAV_HOME

st.sidebar.title("Ride Decision Support")
st.sidebar.caption("Delhi NCR")
st.sidebar.radio("Navigate", NAV_PAGES, key="nav")
st.sidebar.markdown("---")

page = st.session_state.nav
try:
    if not os.path.exists(DB_PATH) and page != NAV_ANALYTICS:
        st.error("SQLite database not found. Open Analytics to rebuild it from the cleaned CSV.")
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
    st.error(str(exc))
