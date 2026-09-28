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
       GLOBAL APP
       ============================================================ */

    .stApp {
        background-color: #0f172a !important;
        color: #f8fafc !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #0f172a !important;
    }

    [data-testid="stHeader"] {
        background-color: #0f172a !important;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }


    /* ============================================================
       GLOBAL TEXT — WHITE
       ============================================================ */

    .stApp h1,
    .stApp h2,
    .stApp h3,
    .stApp h4,
    .stApp h5,
    .stApp h6 {
        color: #f8fafc !important;
    }

    .stApp p,
    .stApp label,
    .stApp span,
    .stApp li,
    .stApp td,
    .stApp th {
        color: #f8fafc !important;
    }

    .stMarkdown,
    .stMarkdown p,
    .stMarkdown span,
    .stMarkdown strong,
    .stMarkdown em {
        color: #f8fafc !important;
    }

    .stCaption,
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {
        color: #f8fafc !important;
    }


    /* ============================================================
       SIDEBAR
       ============================================================ */

    section[data-testid="stSidebar"] {
        background-color: #0b1120 !important;
        border-right: 1px solid #334155 !important;
    }

    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #f8fafc !important;
    }


    /* ============================================================
       SIDEBAR NAVIGATION
       ============================================================ */

    section[data-testid="stSidebar"]
    div[role="radiogroup"] {
        gap: 4px;
    }

    section[data-testid="stSidebar"]
    div[role="radiogroup"]
    label {
        color: #f8fafc !important;
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

    div[data-testid="stSelectbox"] label,
    div[data-testid="stSelectbox"] label p {
        color: #f8fafc !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }

    div[data-testid="stSelectbox"]
    div[data-baseweb="select"] {
        background-color: #1e293b !important;
        border-radius: 8px !important;
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
        fill: #f8fafc !important;
    }


    /* ============================================================
       SELECTBOX POPUP
       ============================================================ */

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

    div[data-baseweb="popover"] li * {
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

    div[data-testid="stMultiSelect"] label,
    div[data-testid="stMultiSelect"] label p {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMultiSelect"]
    div[data-baseweb="select"] {
        background-color: #1e293b !important;
        border-radius: 8px !important;
    }

    div[data-testid="stMultiSelect"]
    div[data-baseweb="select"] span {
        color: #f8fafc !important;
    }

    div[data-testid="stMultiSelect"]
    div[data-baseweb="select"] input {
        color: #f8fafc !important;
    }


    /* ============================================================
       SLIDER
       ============================================================ */

    div[data-testid="stSlider"] label,
    div[data-testid="stSlider"] label p {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stSlider"] div {
        color: #f8fafc !important;
    }


    /* ============================================================
       METRIC CARDS
       ============================================================ */

    div[data-testid="stMetric"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        border-radius: 12px !important;
        padding: 18px !important;
    }

    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] p,
    div[data-testid="stMetricLabel"] span {
        color: #f8fafc !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] div,
    div[data-testid="stMetricValue"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    div[data-testid="stMetricDelta"],
    div[data-testid="stMetricDelta"] div,
    div[data-testid="stMetricDelta"] span {
        color: #f8fafc !important;
    }


    /* ============================================================
       BUTTONS
       ============================================================ */

    .stButton > button {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    .stButton > button * {
        color: #f8fafc !important;
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

    div[data-testid="stChatInput"] textarea {
        background-color: #1e293b !important;
        color: #f8fafc !important;
    }

    div[data-testid="stChatInput"] textarea::placeholder {
        color: #cbd5e1 !important;
    }


    /* ============================================================
       CHAT MESSAGES
       ============================================================ */

    div[data-testid="stChatMessage"] {
        color: #f8fafc !important;
    }

    div[data-testid="stChatMessage"] p,
    div[data-testid="stChatMessage"] span,
    div[data-testid="stChatMessage"] li {
        color: #f8fafc !important;
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

    details summary span {
        color: #f8fafc !important;
    }


    /* ============================================================
       INFO / WARNING / ERROR / SUCCESS BOXES
       ============================================================ */

    div[data-testid="stAlert"] {
        color: #f8fafc !important;
    }

    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span {
        color: #f8fafc !important;
    }


    /* ============================================================
       DATAFRAME
       ============================================================ */

    div[data-testid="stDataFrame"] {
        color: #f8fafc !important;
    }


    /* ============================================================
       JSON
       ============================================================ */

    div[data-testid="stJson"] {
        color: #f8fafc !important;
    }


    /* ============================================================
       DIVIDERS
       ============================================================ */

    hr {
        border-color: #334155 !important;
    }


    /* ============================================================
       LINKS
       ============================================================ */

    .stApp a {
        color: #38bdf8 !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
# ALTair CHART STYLE
# ==============================================================================

def style_chart(chart):

    return (
        chart
        .configure(
            background="#0f172a"
        )
        .configure_view(
            strokeWidth=0
        )
        .configure_axis(
            labelColor="#f8fafc",
            titleColor="#f8fafc",
            domainColor="#475569",
            tickColor="#475569",
            gridColor="#334155",
        )
        .configure_legend(
            labelColor="#f8fafc",
            titleColor="#f8fafc",
        )
        .configure_title(
            color="#f8fafc"
        )
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


df_main = load_and_clean_data(DATA_PATH)


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


def show_metric_cards(metrics):

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


ANALYTICS_TOOLS = {
    "contextual_location_hour_analysis":
        an.contextual_location_hour_analysis
}


SYSTEM_INSTRUCTION = """
You are RideIntel AI, an analytical assistant for ride-hailing/gig workers
operating in Delhi NCR.

Your job is to explain historical ride data.

Rules:

1. Ground statements in historical data returned by analytics tools.

2. Never make predictions.

3. Never tell drivers where to go or what they should do.

4. Never say expected demand, predicted earnings, or guaranteed outcomes.

5. Use phrases such as historical pattern, recorded activity,
   historical completion rate, and observed in the dataset.

6. For a specific location, hour, day, or vehicle type, use the
   historical analytics tool before answering.

7. Keep answers concise and driver-focused.
"""


gemini_tools = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="contextual_location_hour_analysis",
                description=(
                    "Fetch detailed historical ride metrics for one "
                    "pickup location, hour, day and vehicle type."
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
                            description=(
                                "Vehicle type. Use an actual vehicle "
                                "type or All Vehicle Types."
                            ),
                        ),
                    },
                    required=[
                        "pickup_location",
                        "hour",
                        "day_name",
                        "vehicle_type",
                    ],
                ),
            )
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
                        + json.dumps(
                            active_context_result,
                            default=str,
                        )
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
                types.Part.from_text(
                    user_query
                )
            ],
        )
    )

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=gemini_tools,
        temperature=0.2,
    )

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=config,
        )

        if response.function_calls:

            function_call = response.function_calls[0]

            func_name = function_call.name

            func_args = dict(
                function_call.args
            )

            if func_name in ANALYTICS_TOOLS:

                vehicle = func_args.get(
                    "vehicle_type"
                )

                if vehicle == "All Vehicle Types":
                    vehicle = None

                tool_result = (
                    an.contextual_location_hour_analysis(
                        pickup_location=(
                            func_args.get(
                                "pickup_location"
                            )
                        ),
                        hour=int(
                            func_args.get(
                                "hour"
                            )
                        ),
                        day_name=(
                            func_args.get(
                                "day_name"
                            )
                        ),
                        vehicle_type=vehicle,
                    )
                )

                tool_result = normalize_analytics_result(
                    tool_result
                )

                contents.append(
                    response.candidates[
                        0
                    ].content
                )

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=func_name,
                                response={
                                    "result": tool_result
                                },
                            )
                        ],
                    )
                )

                final_response = (
                    client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=config,
                    )
                )

                return (
                    final_response.text
                    if final_response.text
                    else "Historical analysis completed."
                )

        return (
            response.text
            if response.text
            else "Historical analysis completed."
        )

    except Exception:

        return (
            "The AI Assistant is currently experiencing high demand. "
            "Please use the historical metrics pages directly."
        )


def generate_home_insight(context_data):

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
    "📊 Deep Analytics": "Analytics",
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
                "help": (
                    "Number of booking records observed "
                    "in this historical context."
                ),
            },
            {
                "label": "Historical Completion",
                "value": (
                    f"{result.get('completion_rate', 0):.1f}%"
                ),
                "help": (
                    "Percentage of recorded bookings "
                    "that were completed."
                ),
            },
            {
                "label": "Average Value / Km",
                "value": (
                    f"₹{result.get('avg_value_per_km', 0):.2f}"
                ),
                "help": (
                    "Average recorded booking value divided "
                    "by ride distance for completed rides."
                ),
            },
            {
                "label": "Average Booking Value",
                "value": (
                    f"₹{result.get('avg_booking_value', 0):.2f}"
                ),
                "help": (
                    "Average recorded booking value "
                    "in this historical context."
                ),
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
                "help": (
                    "Percentage of recorded bookings "
                    "cancelled by customers."
                ),
            },
            {
                "label": "Driver Cancellations",
                "value": (
                    f"{result.get('driver_cancellation_rate', 0):.1f}%"
                ),
                "help": (
                    "Percentage of recorded bookings "
                    "cancelled by drivers."
                ),
            },
            {
                "label": "Combined Cancellation",
                "value": (
                    f"{result.get('combined_cancellation_rate', 0):.1f}%"
                ),
                "help": (
                    "Customer and driver cancellations "
                    "combined as a percentage of bookings."
                ),
            },
            {
                "label": "Festival Context",
                "value": str(
                    result.get(
                        "festival_info",
                        "None",
                    )
                ),
                "help": (
                    "Festival information recorded "
                    "for this historical context."
                ),
            },
        ]
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

    st.subheader(
        "Hourly Completed-Ride Distribution"
    )

    hourly_demand = (
        filtered_df
        .groupby("Hour")
        .size()
        .reset_index(
            name="Booking_Count"
        )
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
        style_chart(chart),
        use_container_width=True,
    )


# ==============================================================================
# EARNINGS
# ==============================================================================

elif selected_page == "Earnings":

    st.title(
        "💰 Historical Earnings Analysis"
    )

    st.caption(
        "Review historical booking values and "
        "value-per-kilometer metrics."
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

        sel_loc = st.selectbox(
            "Select Location",
            locations,
        )

    with col2:

        sel_veh = st.selectbox(
            "Select Vehicle Type",
            vehicles,
        )

    filtered_df = df_main[
        (
            df_main[
                "Booking_Status"
            ]
            == "Completed"
        )
        & (
            df_main[
                "Pickup_Location"
            ]
            == sel_loc
        )
        & (
            df_main[
                "Vehicle_Type"
            ]
            == sel_veh
        )
    ]

    show_metric_cards(
        [
            {
                "label": "Average Booking Value",
                "value": (
                    f"₹{filtered_df['Booking_Value'].mean():.2f}"
                    if not filtered_df.empty
                    else "₹0.00"
                ),
                "help": (
                    "Average recorded booking value "
                    "for completed rides."
                ),
            },
            {
                "label": "Average Ride Distance",
                "value": (
                    f"{filtered_df['Ride_Distance'].mean():.1f} km"
                    if not filtered_df.empty
                    else "0.0 km"
                ),
                "help": (
                    "Average recorded ride distance "
                    "for completed rides."
                ),
            },
            {
                "label": "Average Value / Km",
                "value": (
                    f"₹{filtered_df['Value_Per_Km'].mean():.2f}"
                    if not filtered_df.empty
                    else "₹0.00"
                ),
                "help": (
                    "Average recorded booking value "
                    "per kilometer."
                ),
            },
            {
                "label": "Completed Rides",
                "value": (
                    f"{len(filtered_df):,}"
                ),
                "help": (
                    "Number of completed historical "
                    "ride records in the selected context."
                ),
            },
        ]
    )

    st.subheader(
        "Value Per Km by Hour"
    )

    earnings_hourly = (
        filtered_df
        .groupby("Hour")[
            "Value_Per_Km"
        ]
        .mean()
        .reset_index()
    )

    chart = (
        alt.Chart(
            earnings_hourly
        )
        .mark_line(
            point=True,
            color="#10b981",
        )
        .encode(
            x=alt.X(
                "Hour:O",
                title="Hour of Day",
            ),
            y=alt.Y(
                "Value_Per_Km:Q",
                title="Average Value per Km (₹)",
            ),
            tooltip=[
                "Hour",
                alt.Tooltip(
                    "Value_Per_Km:Q",
                    format=".2f",
                ),
            ],
        )
        .properties(
            height=350
        )
    )

    st.altair_chart(
        style_chart(chart),
        use_container_width=True,
    )


# ==============================================================================
# CANCELLATIONS
# ==============================================================================

elif selected_page == "Cancellations":

    st.title(
        "🚫 Cancellation Analysis"
    )

    st.caption(
        "Examine historical customer and driver "
        "cancellation patterns."
    )

    if df_main is None:

        display_data_error()
        st.stop()

    total = (
        df_main
        .groupby(
            "Pickup_Location"
        )
        .size()
        .reset_index(
            name="total"
        )
    )

    customer_cancel = (
        df_main[
            df_main[
                "Booking_Status"
            ]
            == "Cancelled by Customer"
        ]
        .groupby(
            "Pickup_Location"
        )
        .size()
        .reset_index(
            name="customer_cancel"
        )
    )

    loc_canc = total.merge(
        customer_cancel,
        on="Pickup_Location",
        how="left",
    )

    loc_canc[
        "customer_cancel"
    ] = (
        loc_canc[
            "customer_cancel"
        ]
        .fillna(0)
    )

    loc_canc[
        "Customer_Cancellation_%"
    ] = (
        loc_canc[
            "customer_cancel"
        ]
        / loc_canc[
            "total"
        ]
        * 100
    )

    loc_canc = (
        loc_canc
        .sort_values(
            "Customer_Cancellation_%",
            ascending=False,
        )
    )

    st.subheader(
        "Locations by Customer Cancellation Rate"
    )

    chart = (
        alt.Chart(
            loc_canc.head(20)
        )
        .mark_bar(
            color="#ef4444"
        )
        .encode(
            x=alt.X(
                "Customer_Cancellation_%:Q",
                title="Customer Cancellation Rate (%)",
            ),
            y=alt.Y(
                "Pickup_Location:N",
                sort="-x",
                title="Pickup Location",
            ),
            tooltip=[
                "Pickup_Location",
                alt.Tooltip(
                    "Customer_Cancellation_%:Q",
                    format=".1f",
                ),
            ],
        )
        .properties(
            height=400
        )
    )

    st.altair_chart(
        style_chart(chart),
        use_container_width=True,
    )


# ==============================================================================
# DEEP ANALYTICS
# ==============================================================================

elif selected_page == "Analytics":

    st.title(
        "📊 Deep Analytics"
    )

    st.caption(
        "Explore historical ride patterns "
        "for a specific context."
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

    st.subheader(
        "Historical Context Query Tool"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    with col1:

        q_loc = st.selectbox(
            "Location",
            locations,
        )

    with col2:

        q_hr = st.slider(
            "Hour",
            min_value=0,
            max_value=23,
            value=12,
        )

    with col3:

        q_day = st.selectbox(
            "Day",
            days,
        )

    with col4:

        q_veh = st.selectbox(
            "Vehicle",
            vehicle_types,
        )

    q_vehicle = (
        None
        if q_veh == "All Vehicle Types"
        else q_veh
    )

    result = (
        an.contextual_location_hour_analysis(
            pickup_location=q_loc,
            hour=q_hr,
            day_name=q_day,
            vehicle_type=q_vehicle,
        )
    )

    result = normalize_analytics_result(
        result
    )

    if result.get("is_fallback"):

        st.warning(
            result.get(
                "warning",
                "Broader historical context shown.",
            )
        )

    show_metric_cards(
        [
            {
                "label": "Historical Bookings",
                "value": (
                    f"{result.get('total_bookings', 0):,}"
                ),
                "help": (
                    "Number of booking records "
                    "observed in this context."
                ),
            },
            {
                "label": "Completion Rate",
                "value": (
                    f"{result.get('completion_rate', 0):.1f}%"
                ),
                "help": (
                    "Percentage of historical bookings "
                    "that were completed."
                ),
            },
            {
                "label": "Average Value / Km",
                "value": (
                    f"₹{result.get('avg_value_per_km', 0):.2f}"
                ),
                "help": (
                    "Average recorded booking value "
                    "per kilometer."
                ),
            },
            {
                "label": "Combined Cancellation",
                "value": (
                    f"{result.get('combined_cancellation_rate', 0):.1f}%"
                ),
                "help": (
                    "Historical customer and driver "
                    "cancellations combined."
                ),
            },
        ]
    )

    with st.expander(
        "View detailed historical result"
    ):

        st.json(result)


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