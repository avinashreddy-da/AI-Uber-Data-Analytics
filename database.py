import os
import sqlite3
import pandas as pd


# ============================================================
# Paths
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "data",
    "mobilitylens.db",
)


# ============================================================
# Database connection
# ============================================================

def get_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


def read_sql(query, params=None):
    conn = get_connection()

    try:
        return pd.read_sql_query(
            query,
            conn,
            params=params or [],
        )
    finally:
        conn.close()


# ============================================================
# Table helpers
# ============================================================

def get_tables():
    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """

    result = read_sql(query)

    if result.empty:
        return []

    return result["name"].tolist()


def table_exists(table_name):
    return table_name in get_tables()


def get_table_columns(table_name):
    query = f'PRAGMA table_info("{table_name}")'

    result = read_sql(query)

    if result.empty:
        return []

    return result["name"].tolist()


def get_fairfare_table():
    tables = get_tables()

    preferred_tables = [
        "rides",
        "fairfare",
        "fairfare_rides",
        "ride_data",
    ]

    for table in preferred_tables:
        if table in tables:
            return table

    # Fallback: identify a table containing the FairFare columns
    for table in tables:
        try:
            columns = get_table_columns(table)

            if "City" in columns and "Final_Fare" in columns:
                return table

        except Exception:
            continue

    return None


# ============================================================
# Database availability
# ============================================================

def database_available():
    try:
        table = get_fairfare_table()

        if table is None:
            return False

        columns = get_table_columns(table)

        required_columns = [
            "City",
            "Date",
            "Hour_of_Day",
            "Ride_Type",
            "Demand_Level",
            "Demand_Score",
            "Ride_Distance_KM",
            "Final_Fare",
            "Cancellation_Rate",
        ]

        return all(
            column in columns
            for column in required_columns
        )

    except Exception:
        return False


def zoned_database_available():
    try:
        table = get_fairfare_table()

        if table is None:
            return False

        columns = get_table_columns(table)

        return "Zone" in columns

    except Exception:
        return False


# ============================================================
# Weekday helpers
# ============================================================

DAY_NAME_TO_SQLITE_CODE = {
    "sunday": 0,
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
}


def normalize_day_value(day_name):
    """
    Convert the UI weekday name into SQLite's weekday code.

    IMPORTANT:
    We do NOT use the dataset's Day_of_Week column.

    Instead, the SQL query calculates the weekday directly
    from the Date column using SQLite strftime('%w').

    SQLite:
        Sunday    = 0
        Monday    = 1
        Tuesday   = 2
        Wednesday = 3
        Thursday  = 4
        Friday    = 5
        Saturday  = 6
    """

    if day_name is None:
        return None

    if isinstance(day_name, (int, float)):
        value = int(day_name)

        if 0 <= value <= 6:
            return value

        return None

    value = str(day_name).strip().lower()

    if value in DAY_NAME_TO_SQLITE_CODE:
        return DAY_NAME_TO_SQLITE_CODE[value]

    # Support numeric strings if ever passed by the UI
    try:
        value = int(float(value))

        if 0 <= value <= 6:
            return value

    except (ValueError, TypeError):
        pass

    return None


# ============================================================
# SQL weekday condition
# ============================================================

def add_weekday_filter(
    conditions,
    params,
    day_name,
):
    """
    Add a weekday filter based on the actual Date column.

    We intentionally avoid:
        Day_of_Week = ?

    because the FairFare Day_of_Week column was found to be
    inconsistent with Date.
    """

    day_code = normalize_day_value(day_name)

    if day_code is not None:
        conditions.append(
            "CAST(strftime('%w', Date) AS INTEGER) = ?"
        )
        params.append(day_code)

    return conditions, params


# ============================================================
# Ride type helper
# ============================================================

def clean_ride_types(ride_types):
    if not ride_types:
        return []

    if isinstance(ride_types, str):
        ride_types = [ride_types]

    result = []

    for ride_type in ride_types:
        value = str(ride_type).strip()

        if not value:
            continue

        if value.lower() == "all ride types":
            continue

        result.append(value)

    return result


# ============================================================
# Base filters
# ============================================================

def build_base_filters(
    city=None,
    hour=None,
    day_name=None,
    ride_types=None,
    zone=None,
):
    """
    Build common SQL filters.

    Weekday is calculated from Date, NOT from Day_of_Week.
    """

    conditions = []
    params = []

    # --------------------------------------------------------
    # City
    # --------------------------------------------------------

    if city:
        conditions.append("City = ?")
        params.append(city)

    # --------------------------------------------------------
    # Hour
    # --------------------------------------------------------

    if hour is not None:
        conditions.append("Hour_of_Day = ?")
        params.append(int(hour))

    # --------------------------------------------------------
    # Actual weekday from Date
    # --------------------------------------------------------

    conditions, params = add_weekday_filter(
        conditions,
        params,
        day_name,
    )

    # --------------------------------------------------------
    # Ride type
    # --------------------------------------------------------

    ride_types = clean_ride_types(ride_types)

    if ride_types:
        placeholders = ",".join(
            ["?"] * len(ride_types)
        )

        conditions.append(
            f"Ride_Type IN ({placeholders})"
        )

        params.extend(ride_types)

    # --------------------------------------------------------
    # Zone
    # --------------------------------------------------------

    if zone:
        conditions.append("Zone = ?")
        params.append(zone)

    if conditions:
        where_clause = (
            " WHERE "
            + " AND ".join(conditions)
        )
    else:
        where_clause = ""

    return where_clause, params


# ============================================================
# Demand breakdown
# ============================================================

def build_demand_breakdown(
    table,
    where_clause,
    params,
    total_count,
):
    """
    Build Low / Medium / High demand breakdown.

    First attempts to use Demand_Level.

    If the labels cannot be mapped reliably, Demand_Score
    tertiles are used as a fallback.
    """

    labels = [
        "Low",
        "Medium",
        "High",
    ]

    demand_map = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
    }

    # --------------------------------------------------------
    # Stored demand labels
    # --------------------------------------------------------

    query = f"""
        SELECT
            Demand_Level,
            COUNT(*) AS Records
        FROM "{table}"
        {where_clause}
        GROUP BY Demand_Level
    """

    try:
        demand = read_sql(
            query,
            params,
        )
    except Exception:
        demand = pd.DataFrame()

    mapped_records = 0

    if not demand.empty:

        for _, row in demand.iterrows():

            label = str(
                row["Demand_Level"]
            ).strip().lower()

            records = int(
                row["Records"]
            )

            if "low" in label:
                normalized = "Low"

            elif "medium" in label:
                normalized = "Medium"

            elif "high" in label:
                normalized = "High"

            else:
                normalized = None

            if normalized:

                demand_map[normalized] += records

                mapped_records += records

    # --------------------------------------------------------
    # Demand score fallback
    # --------------------------------------------------------

    if mapped_records < max(
        3,
        int(total_count * 0.5),
    ):

        score_query = f"""
            SELECT
                Demand_Score
            FROM "{table}"
            {where_clause}
        """

        try:
            score_rows = read_sql(
                score_query,
                params,
            )
        except Exception:
            score_rows = pd.DataFrame()

        if (
            not score_rows.empty
            and "Demand_Score" in score_rows.columns
        ):

            scores = pd.to_numeric(
                score_rows["Demand_Score"],
                errors="coerce",
            )

            scores = scores.dropna()

            if not scores.empty:

                q1 = scores.quantile(
                    1 / 3
                )

                q2 = scores.quantile(
                    2 / 3
                )

                low = int(
                    (scores <= q1).sum()
                )

                medium = int(
                    (
                        (scores > q1)
                        & (scores <= q2)
                    ).sum()
                )

                high = int(
                    (scores > q2).sum()
                )

                demand_map = {
                    "Low": low,
                    "Medium": medium,
                    "High": high,
                }

    # --------------------------------------------------------
    # Final table
    # --------------------------------------------------------

    result = []

    for label in labels:

        records = int(
            demand_map.get(
                label,
                0,
            )
        )

        share = (
            records / total_count * 100
            if total_count
            else 0
        )

        result.append(
            {
                "Demand Level": label,
                "Records": records,
                "Share": round(
                    share,
                    1,
                ),
            }
        )

    return result


# ============================================================
# Historical context engine
# ============================================================

def _context_query(
    table,
    city,
    hour,
    day_name,
    ride_types=None,
    zone=None,
):
    """
    Historical context engine.

    Priority:

    1. Zone + hour + actual weekday
    2. Zone + hour
    3. Zone + all times
    4. City + hour + actual weekday
    5. City + hour
    6. City + all times

    The exact weekday/hour combination is accepted even if
    it contains only a small number of records.
    """

    if not table:
        return {
            "found": False,
            "basis": "No match",
            "sample_size": 0,
        }

    columns = get_table_columns(table)

    clean_types = clean_ride_types(
        ride_types
    )

    day_code = normalize_day_value(
        day_name
    )

    # ========================================================
    # Common city / ride-type filters
    # ========================================================

    base_conditions = []
    base_params = []

    if city:
        base_conditions.append(
            "City = ?"
        )
        base_params.append(city)

    if clean_types:

        placeholders = ",".join(
            ["?"] * len(clean_types)
        )

        base_conditions.append(
            f"Ride_Type IN ({placeholders})"
        )

        base_params.extend(
            clean_types
        )

    if base_conditions:
        base_where = (
            " WHERE "
            + " AND ".join(base_conditions)
        )
    else:
        base_where = ""

    # ========================================================
    # Candidate filters
    # ========================================================

    candidates = []

    # --------------------------------------------------------
    # Zone-level candidates
    # --------------------------------------------------------

    if (
        zone
        and "Zone" in columns
    ):

        # Zone + hour + actual weekday
        if day_code is not None:

            candidates.append(
                (
                    "Zone + hour + weekday",

                    base_where
                    + " AND Zone = ?"
                    + " AND Hour_of_Day = ?"
                    + " AND CAST(strftime('%w', Date) AS INTEGER) = ?",

                    base_params
                    + [
                        zone,
                        int(hour),
                        day_code,
                    ],
                )
            )

        # Zone + hour
        candidates.append(
            (
                "Zone + hour",

                base_where
                + " AND Zone = ?"
                + " AND Hour_of_Day = ?",

                base_params
                + [
                    zone,
                    int(hour),
                ],
            )
        )

        # Zone + all times
        candidates.append(
            (
                "Zone + all times",

                base_where
                + " AND Zone = ?",

                base_params
                + [zone],
            )
        )

    # ========================================================
    # City-level candidates
    # ========================================================

    # --------------------------------------------------------
    # City + hour + actual weekday
    # --------------------------------------------------------

    if day_code is not None:

        candidates.append(
            (
                "City + hour + weekday",

                base_where
                + " AND Hour_of_Day = ?"
                + " AND CAST(strftime('%w', Date) AS INTEGER) = ?",

                base_params
                + [
                    int(hour),
                    day_code,
                ],
            )
        )

    # --------------------------------------------------------
    # City + hour
    # --------------------------------------------------------

    candidates.append(
        (
            "City + hour",

            base_where
            + " AND Hour_of_Day = ?",

            base_params
            + [int(hour)],
        )
    )

    # --------------------------------------------------------
    # City + all times
    # --------------------------------------------------------

    candidates.append(
        (
            "City + all times",

            base_where,

            base_params,
        )
    )

    # ========================================================
    # Execute candidates
    # ========================================================

    for basis, where_clause, params in candidates:

        count_query = f"""
            SELECT
                COUNT(*) AS n
            FROM "{table}"
            {where_clause}
        """

        try:
            count_result = read_sql(
                count_query,
                params,
            )

            count = int(
                count_result.iloc[0]["n"]
            )

        except Exception:
            continue

        # IMPORTANT:
        # Any non-zero exact match is valid.
        if count <= 0:
            continue

        # ====================================================
        # Main KPIs
        # ====================================================

        metrics_query = f"""
            SELECT

                COUNT(*) AS Bookings,

                AVG(
                    Cancellation_Rate
                ) AS Cancellation_Rate,

                AVG(
                    Ride_Distance_KM
                ) AS Avg_Ride_Distance,

                AVG(
                    Final_Fare
                ) AS Average_Fare,

                AVG(
                    Demand_Score
                ) AS Average_Demand_Score,

                AVG(
                    Available_Drivers
                ) AS Average_Available_Drivers

            FROM "{table}"
            {where_clause}
        """

        try:
            metrics = read_sql(
                metrics_query,
                params,
            ).iloc[0]

        except Exception:
            metrics = pd.Series()

        # ====================================================
        # Event signal
        # ====================================================

        event_query = f"""
            SELECT
                Event,
                COUNT(*) AS Records
            FROM "{table}"
            {where_clause}
            GROUP BY Event
            ORDER BY Records DESC
        """

        try:
            events = read_sql(
                event_query,
                params,
            )
        except Exception:
            events = pd.DataFrame()

        if events.empty:

            event_signal = "Limited"

        else:

            event_values = (
                events["Event"]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            non_event_values = {
                "",
                "none",
                "no event",
                "normal",
                "nan",
            }

            event_records = int(
                events.loc[
                    ~event_values.isin(
                        non_event_values
                    ),
                    "Records",
                ].sum()
            )

            if event_records > 0:
                event_signal = "Present"
            else:
                event_signal = "Limited"

        # ====================================================
        # Demand breakdown
        # ====================================================

        demand_breakdown = (
            build_demand_breakdown(
                table,
                where_clause,
                params,
                count,
            )
        )

        # ====================================================
        # Return result
        # ====================================================

        return {
            "found": True,

            "basis": basis,

            "sample_size": count,

            "bookings": int(
                metrics.get(
                    "Bookings",
                    count,
                )
                if pd.notna(
                    metrics.get(
                        "Bookings",
                        count,
                    )
                )
                else count
            ),

            "cancellation_rate": float(
                metrics.get(
                    "Cancellation_Rate",
                    0,
                )
                if pd.notna(
                    metrics.get(
                        "Cancellation_Rate",
                        0,
                    )
                )
                else 0
            ),

            "avg_ride_distance": float(
                metrics.get(
                    "Avg_Ride_Distance",
                    0,
                )
                if pd.notna(
                    metrics.get(
                        "Avg_Ride_Distance",
                        0,
                    )
                )
                else 0
            ),

            "average_fare": float(
                metrics.get(
                    "Average_Fare",
                    0,
                )
                if pd.notna(
                    metrics.get(
                        "Average_Fare",
                        0,
                    )
                )
                else 0
            ),

            "average_demand_score": float(
                metrics.get(
                    "Average_Demand_Score",
                    0,
                )
                if pd.notna(
                    metrics.get(
                        "Average_Demand_Score",
                        0,
                    )
                )
                else 0
            ),

            "average_available_drivers": float(
                metrics.get(
                    "Average_Available_Drivers",
                    0,
                )
                if pd.notna(
                    metrics.get(
                        "Average_Available_Drivers",
                        0,
                    )
                )
                else 0
            ),

            "event_signal": event_signal,

            "demand_breakdown": demand_breakdown,

            "day_code_used": day_code,
        }

    # ========================================================
    # Nothing found
    # ========================================================

    return {
        "found": False,
        "basis": "No match",
        "sample_size": 0,
    }


# ============================================================
# City context
# ============================================================

def get_city_context_sql(
    city,
    hour,
    day_name,
    ride_type="All Ride Types",
    min_records=1,
):
    """
    City-level historical context.

    min_records is retained for compatibility with app.py,
    but is NOT used as a minimum threshold.
    """

    table = get_fairfare_table()

    if table is None:
        return {
            "found": False,
            "basis": "No match",
            "sample_size": 0,
        }

    return _context_query(
        table=table,
        city=city,
        hour=hour,
        day_name=day_name,
        ride_types=ride_type,
        zone=None,
    )


# ============================================================
# Zone context
# ============================================================

def get_zone_context_sql(
    city,
    zone,
    hour,
    day_name,
    ride_type="All Ride Types",
    min_records=1,
):
    """
    Zone-level historical context.

    If the zone has no assigned records, app.py can fall
    back to city-level context.
    """

    table = get_fairfare_table()

    if table is None:
        return {
            "found": False,
            "basis": "No match",
            "sample_size": 0,
        }

    columns = get_table_columns(table)

    if "Zone" not in columns:
        return {
            "found": False,
            "basis": "Zone unavailable",
            "sample_size": 0,
        }

    return _context_query(
        table=table,
        city=city,
        hour=hour,
        day_name=day_name,
        ride_types=ride_type,
        zone=zone,
    )


# ============================================================
# FairFare rows
# ============================================================

def get_fairfare_rows(
    city=None,
    hour=None,
    day_name=None,
    ride_type="All Ride Types",
    zone=None,
    limit=5000,
):
    """
    Return historical rows using the same filters as the
    main historical context.
    """

    table = get_fairfare_table()

    if table is None:
        return pd.DataFrame()

    where_clause, params = build_base_filters(
        city=city,
        hour=hour,
        day_name=day_name,
        ride_types=ride_type,
        zone=zone,
    )

    query = f"""
        SELECT *
        FROM "{table}"
        {where_clause}
        LIMIT ?
    """

    params = params + [
        int(limit)
    ]

    return read_sql(
        query,
        params,
    )


# ============================================================
# Hourly demand
# ============================================================

def get_hourly_demand_sql(
    city=None,
    ride_type="All Ride Types",
):
    """
    Historical demand by hour.
    """

    table = get_fairfare_table()

    if table is None:
        return pd.DataFrame()

    conditions = []
    params = []

    if city:
        conditions.append(
            "City = ?"
        )
        params.append(city)

    ride_types = clean_ride_types(
        ride_type
    )

    if ride_types:

        placeholders = ",".join(
            ["?"] * len(ride_types)
        )

        conditions.append(
            f"Ride_Type IN ({placeholders})"
        )

        params.extend(
            ride_types
        )

    where_clause = ""

    if conditions:
        where_clause = (
            " WHERE "
            + " AND ".join(conditions)
        )

    query = f"""
        SELECT

            Hour_of_Day,

            COUNT(*) AS Records,

            AVG(
                Demand_Score
            ) AS Average_Demand_Score

        FROM "{table}"

        {where_clause}

        GROUP BY Hour_of_Day

        ORDER BY Hour_of_Day
    """

    return read_sql(
        query,
        params,
    )


# ============================================================
# City demand comparison
# ============================================================

def get_city_demand_sql(
    ride_type="All Ride Types",
):
    """
    Historical demand comparison across cities.
    """

    table = get_fairfare_table()

    if table is None:
        return pd.DataFrame()

    ride_types = clean_ride_types(
        ride_type
    )

    conditions = []
    params = []

    if ride_types:

        placeholders = ",".join(
            ["?"] * len(ride_types)
        )

        conditions.append(
            f"Ride_Type IN ({placeholders})"
        )

        params.extend(
            ride_types
        )

    where_clause = ""

    if conditions:
        where_clause = (
            " WHERE "
            + " AND ".join(conditions)
        )

    query = f"""
        SELECT

            City,

            COUNT(*) AS Records,

            AVG(
                Demand_Score
            ) AS Average_Demand_Score

        FROM "{table}"

        {where_clause}

        GROUP BY City

        ORDER BY Average_Demand_Score DESC
    """

    return read_sql(
        query,
        params,
    )


# ============================================================
# Cancellation analysis
# ============================================================

def get_city_cancellations_sql(
    city=None,
    ride_type="All Ride Types",
):
    """
    Historical cancellation analysis.
    """

    table = get_fairfare_table()

    if table is None:
        return pd.DataFrame()

    conditions = []
    params = []

    if city:
        conditions.append(
            "City = ?"
        )
        params.append(city)

    ride_types = clean_ride_types(
        ride_type
    )

    if ride_types:

        placeholders = ",".join(
            ["?"] * len(ride_types)
        )

        conditions.append(
            f"Ride_Type IN ({placeholders})"
        )

        params.extend(
            ride_types
        )

    where_clause = ""

    if conditions:
        where_clause = (
            " WHERE "
            + " AND ".join(conditions)
        )

    query = f"""
        SELECT

            City,

            COUNT(*) AS Records,

            AVG(
                Cancellation_Rate
            ) AS Average_Cancellation_Rate,

            AVG(
                Cancellation_Probability
            ) AS Average_Cancellation_Probability

        FROM "{table}"

        {where_clause}

        GROUP BY City

        ORDER BY Average_Cancellation_Rate DESC
    """

    return read_sql(
        query,
        params,
    )


# ============================================================
# Nearby / zone demand
# ============================================================

def get_zone_nearby_demand_sql(
    city,
    zone,
    hour,
    day_name,
    ride_type="All Ride Types",
):
    """
    Historical demand for a selected zone, hour and actual
    weekday from Date.
    """

    table = get_fairfare_table()

    if table is None:
        return pd.DataFrame()

    columns = get_table_columns(table)

    if "Zone" not in columns:
        return pd.DataFrame()

    conditions = [
        "City = ?",
        "Zone = ?",
        "Hour_of_Day = ?",
    ]

    params = [
        city,
        zone,
        int(hour),
    ]

    # --------------------------------------------------------
    # Actual weekday from Date
    # --------------------------------------------------------

    conditions, params = add_weekday_filter(
        conditions,
        params,
        day_name,
    )

    # --------------------------------------------------------
    # Ride type
    # --------------------------------------------------------

    ride_types = clean_ride_types(
        ride_type
    )

    if ride_types:

        placeholders = ",".join(
            ["?"] * len(ride_types)
        )

        conditions.append(
            f"Ride_Type IN ({placeholders})"
        )

        params.extend(
            ride_types
        )

    where_clause = (
        " WHERE "
        + " AND ".join(conditions)
    )

    query = f"""
        SELECT

            Demand_Level,

            COUNT(*) AS Records,

            AVG(
                Demand_Score
            ) AS Average_Demand_Score

        FROM "{table}"

        {where_clause}

        GROUP BY Demand_Level

        ORDER BY Records DESC
    """

    try:
        return read_sql(
            query,
            params,
        )
    except Exception:
        return pd.DataFrame()