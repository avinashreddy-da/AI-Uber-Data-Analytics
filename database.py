import os
import sqlite3
import pandas as pd


# ============================================================
# DATABASE PATH
# ============================================================

DB_PATH = os.path.join(
    "data",
    "mobilitylens.db",
)


# ============================================================
# DATABASE CHECKS
# ============================================================

def database_exists():
    return os.path.exists(DB_PATH)


def table_exists(table_name):
    if not database_exists():
        return False

    connection = sqlite3.connect(DB_PATH)

    try:
        row = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()

        return row is not None

    finally:
        connection.close()


# ============================================================
# CONNECTION
# ============================================================

def get_connection():
    if not database_exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    return sqlite3.connect(DB_PATH)


# ============================================================
# SQL READER
# ============================================================

def read_sql(query, params=()):
    connection = get_connection()

    try:
        return pd.read_sql_query(
            query,
            connection,
            params=params,
        )

    finally:
        connection.close()


# ============================================================
# COMMON SQL HELPERS
# ============================================================

def _city_clause(cities):
    cities = [
        str(city)
        for city in cities
        if city
    ]

    if not cities:
        return "", []

    placeholders = ",".join(
        "?"
        for _ in cities
    )

    return (
        f" AND City IN ({placeholders})",
        cities,
    )


def _ride_type_clause(ride_type):
    if (
        ride_type
        and ride_type != "All Ride Types"
    ):
        return (
            " AND Ride_Type = ?",
            [ride_type],
        )

    return "", []


def _normalized_rate_sql(column):
    return (
        f"AVG("
        f"CASE "
        f"WHEN ABS({column}) <= 1 "
        f"THEN {column} * 100 "
        f"ELSE {column} "
        f"END"
        f")"
    )


# ============================================================
# CITY LIST
# ============================================================

def get_city_list():

    if not database_exists():
        return []

    data = read_sql(
        """
        SELECT DISTINCT City
        FROM rides
        ORDER BY City
        """
    )

    return (
        data["City"]
        .dropna()
        .tolist()
    )


# ============================================================
# RIDE TYPE LIST
# ============================================================

def get_ride_type_list(city=None):

    query = """
        SELECT DISTINCT Ride_Type
        FROM rides
    """

    params = []

    if city:
        query += """
            WHERE City = ?
        """

        params.append(city)

    query += """
        ORDER BY Ride_Type
    """

    data = read_sql(
        query,
        tuple(params),
    )

    return (
        data["Ride_Type"]
        .dropna()
        .tolist()
    )


# ============================================================
# FAIRFARE ROWS
# ============================================================

def get_fairfare_rows(
    city=None,
    cities=None,
    hour=None,
    day_name=None,
    ride_types=None,
    weather=None,
):

    query = """
        SELECT *
        FROM rides
        WHERE 1 = 1
    """

    params = []

    if cities is not None:

        cities = list(cities)

        if not cities:
            return pd.DataFrame()

        clause, values = _city_clause(
            cities
        )

        query += clause
        params.extend(values)

    elif city:

        query += """
            AND City = ?
        """

        params.append(city)

    if hour is not None:

        query += """
            AND Hour_of_Day = ?
        """

        params.append(
            int(hour)
        )

    if day_name:

        query += """
            AND Day_of_Week = ?
        """

        params.append(day_name)

    if ride_types:

        ride_types = list(
            ride_types
        )

        if not ride_types:
            return pd.DataFrame()

        placeholders = ",".join(
            "?"
            for _ in ride_types
        )

        query += (
            f" AND Ride_Type "
            f"IN ({placeholders})"
        )

        params.extend(
            ride_types
        )

    if weather:

        query += """
            AND Weather = ?
        """

        params.append(weather)

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# CITY SUMMARY
# ============================================================

def get_city_summary_sql(city):

    query = f"""
        SELECT
            City,
            COUNT(*) AS Records,
            AVG(Demand_Score)
                AS Avg_Demand_Score,
            AVG(Available_Drivers)
                AS Avg_Available_Drivers,
            AVG(Driver_Availability)
                AS Avg_Driver_Availability,
            AVG(Final_Fare)
                AS Avg_Fare,
            AVG(Fare_Per_KM)
                AS Avg_Fare_Per_KM,

            {_normalized_rate_sql(
                "Cancellation_Rate"
            )}
                AS Avg_Cancellation_Rate,

            {_normalized_rate_sql(
                "Cancellation_Probability"
            )}
                AS Avg_Cancellation_Probability,

            AVG(Traffic_Delay)
                AS Avg_Traffic_Delay

        FROM rides

        WHERE City = ?

        GROUP BY City
    """

    return read_sql(
        query,
        (city,),
    )


# ============================================================
# CITY DEMAND
# ============================================================

def get_city_demand_sql(
    cities=None,
    ride_type=None,
):

    query = """
        SELECT
            City,
            COUNT(*) AS Records,
            AVG(Demand_Score)
                AS Average_Demand_Score,
            AVG(Available_Drivers)
                AS Average_Available_Drivers,
            AVG(Driver_Availability)
                AS Average_Driver_Availability
        FROM rides
        WHERE 1 = 1
    """

    params = []

    if cities:

        clause, values = _city_clause(
            cities
        )

        query += clause
        params.extend(values)

    clause, values = _ride_type_clause(
        ride_type
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY City
        ORDER BY Average_Demand_Score DESC
    """

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# HOURLY DEMAND
# ============================================================

def get_hourly_demand_sql(
    city=None,
    cities=None,
    ride_type=None,
):

    query = """
        SELECT
            Hour_of_Day,
            COUNT(*) AS Records,
            AVG(Demand_Score)
                AS Average_Demand_Score
        FROM rides
        WHERE 1 = 1
    """

    params = []

    if cities is not None:

        if not cities:
            return pd.DataFrame()

        clause, values = _city_clause(
            cities
        )

        query += clause
        params.extend(values)

    elif city:

        query += """
            AND City = ?
        """

        params.append(city)

    clause, values = _ride_type_clause(
        ride_type
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY Hour_of_Day
        ORDER BY Hour_of_Day
    """

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# CITY EARNINGS
# ============================================================

def get_city_earnings_sql(
    cities=None,
    ride_type=None,
):

    query = """
        SELECT
            City,
            Ride_Type,
            COUNT(*) AS Records,
            AVG(Final_Fare)
                AS Average_Fare,
            AVG(Fare_Per_KM)
                AS Average_Fare_Per_KM,
            AVG(Ride_Distance_KM)
                AS Average_Ride_Distance
        FROM rides
        WHERE 1 = 1
    """

    params = []

    if cities:

        clause, values = _city_clause(
            cities
        )

        query += clause
        params.extend(values)

    clause, values = _ride_type_clause(
        ride_type
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY
            City,
            Ride_Type
        ORDER BY
            City,
            Ride_Type
    """

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# CITY CANCELLATIONS
# ============================================================

def get_city_cancellations_sql(
    cities=None,
    ride_type=None,
):

    query = f"""
        SELECT
            City,
            COUNT(*) AS Records,

            {_normalized_rate_sql(
                "Cancellation_Rate"
            )}
                AS Average_Cancellation_Rate,

            {_normalized_rate_sql(
                "Cancellation_Probability"
            )}
                AS Average_Cancellation_Probability,

            AVG(Traffic_Delay)
                AS Average_Traffic_Delay

        FROM rides

        WHERE 1 = 1
    """

    params = []

    if cities:

        clause, values = _city_clause(
            cities
        )

        query += clause
        params.extend(values)

    clause, values = _ride_type_clause(
        ride_type
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY City
        ORDER BY Average_Cancellation_Rate DESC
    """

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# CITY HISTORICAL CONTEXT
# ============================================================

def get_city_context_sql(
    city,
    hour,
    day_name,
    ride_type="All Ride Types",
    min_records=30,
):

    ride_clause, ride_params = (
        _ride_type_clause(
            ride_type
        )
    )

    candidates = [

        (
            "City + hour + weekday",
            """
            AND Hour_of_Day = ?
            AND Day_of_Week = ?
            """,
            [hour, day_name],
        ),

        (
            "City + hour",
            """
            AND Hour_of_Day = ?
            """,
            [hour],
        ),

        (
            "City + all times",
            "",
            [],
        ),
    ]

    for (
        basis,
        extra_clause,
        extra_params,
    ) in candidates:

        count_query = f"""
            SELECT COUNT(*) AS n
            FROM rides
            WHERE City = ?
            {ride_clause}
            {extra_clause}
        """

        params = [
            city,
            *ride_params,
            *extra_params,
        ]

        count_df = read_sql(
            count_query,
            tuple(params),
        )

        count = (
            int(
                count_df.loc[
                    0,
                    "n",
                ]
            )
            if not count_df.empty
            else 0
        )

        if (
            count >= min_records
            or basis == "City + all times"
        ):

            query = f"""
                SELECT
                    COUNT(*) AS bookings,

                    AVG(Demand_Score)
                        AS avg_demand_score,

                    AVG(Available_Drivers)
                        AS avg_available_drivers,

                    AVG(Driver_Availability)
                        AS avg_driver_availability,

                    AVG(Final_Fare)
                        AS avg_fare,

                    AVG(Fare_Per_KM)
                        AS avg_fare_per_km,

                    AVG(Ride_Distance_KM)
                        AS avg_ride_km,

                    {_normalized_rate_sql(
                        "Cancellation_Rate"
                    )}
                        AS cancellation_rate,

                    {_normalized_rate_sql(
                        "Cancellation_Probability"
                    )}
                        AS cancellation_probability,

                    AVG(Traffic_Delay)
                        AS avg_traffic_delay

                FROM rides

                WHERE City = ?
                {ride_clause}
                {extra_clause}
            """

            result = read_sql(
                query,
                tuple(params),
            )

            if (
                result.empty
                or pd.isna(
                    result.loc[
                        0,
                        "bookings",
                    ]
                )
            ):
                continue

            row = (
                result
                .iloc[0]
                .to_dict()
            )

            row.update(
                {
                    "found": count > 0,
                    "city": city,
                    "hour": int(hour),
                    "day_name": day_name,
                    "ride_type": ride_type,
                    "basis": basis,
                    "sample_size": count,
                    "completed_rides_estimated": max(
                        0.0,
                        float(
                            row["bookings"]
                        )
                        * (
                            1.0
                            - float(
                                row[
                                    "cancellation_rate"
                                ]
                            )
                            / 100.0
                        ),
                    ),
                }
            )

            demand_query = f"""
                SELECT
                    Demand_Level,
                    COUNT(*) AS Records
                FROM rides
                WHERE City = ?
                {ride_clause}
                {extra_clause}
                GROUP BY Demand_Level
            """

            demand = read_sql(
                demand_query,
                tuple(params),
            )

            demand_map = {
                "Low": 0,
                "Medium": 0,
                "High": 0,
            }

            for (
                _,
                demand_row,
            ) in demand.iterrows():

                label = str(
                    demand_row[
                        "Demand_Level"
                    ]
                )

                if label in demand_map:
                    demand_map[
                        label
                    ] = int(
                        demand_row[
                            "Records"
                        ]
                    )

            total = max(
                1,
                count,
            )

            row[
                "demand_breakdown"
            ] = [

                {
                    "Demand Level": label,
                    "Records": demand_map[
                        label
                    ],
                    "Share": (
                        demand_map[
                            label
                        ]
                        / total
                        * 100.0
                    ),
                }

                for label in (
                    "Low",
                    "Medium",
                    "High",
                )
            ]

            weather_query = f"""
                SELECT
                    Weather,
                    COUNT(*) AS Records
                FROM rides
                WHERE City = ?
                {ride_clause}
                {extra_clause}
                GROUP BY Weather
                ORDER BY Records DESC
            """

            row[
                "weather_mix"
            ] = (
                read_sql(
                    weather_query,
                    tuple(params),
                )
                .to_dict(
                    orient="records"
                )
            )

            return row

    return {
        "found": False,
        "message": (
            f"No historical records "
            f"are available for {city}."
        ),
    }


# ============================================================
# ZONE HISTORICAL CONTEXT
# ============================================================

def get_zone_context_sql(
    city,
    zone,
    hour,
    day_name,
    ride_type="All Ride Types",
    min_records=30,
):

    ride_clause, ride_params = (
        _ride_type_clause(
            ride_type
        )
    )

    candidates = [

        (
            "Zone + hour + weekday",
            """
            AND Hour_of_Day = ?
            AND Day_of_Week = ?
            """,
            [hour, day_name],
        ),

        (
            "Zone + hour",
            """
            AND Hour_of_Day = ?
            """,
            [hour],
        ),

        (
            "Zone + all times",
            "",
            [],
        ),
    ]

    for (
        basis,
        extra_clause,
        extra_params,
    ) in candidates:

        count_query = f"""
            SELECT COUNT(*) AS n
            FROM rides_zoned
            WHERE City = ?
              AND Zone = ?
            {ride_clause}
            {extra_clause}
        """

        params = [
            city,
            zone,
            *ride_params,
            *extra_params,
        ]

        count_df = read_sql(
            count_query,
            tuple(params),
        )

        count = (
            int(
                count_df.loc[
                    0,
                    "n",
                ]
            )
            if not count_df.empty
            else 0
        )

        if (
            count >= min_records
            or basis == "Zone + all times"
        ):

            if count == 0:
                break

            query = f"""
                SELECT
                    COUNT(*) AS bookings,

                    AVG(Demand_Score)
                        AS avg_demand_score,

                    AVG(Available_Drivers)
                        AS avg_available_drivers,

                    AVG(Driver_Availability)
                        AS avg_driver_availability,

                    AVG(Final_Fare)
                        AS avg_fare,

                    AVG(Fare_Per_KM)
                        AS avg_fare_per_km,

                    AVG(Ride_Distance_KM)
                        AS avg_ride_km,

                    {_normalized_rate_sql(
                        "Cancellation_Rate"
                    )}
                        AS cancellation_rate,

                    {_normalized_rate_sql(
                        "Cancellation_Probability"
                    )}
                        AS cancellation_probability,

                    AVG(Traffic_Delay)
                        AS avg_traffic_delay

                FROM rides_zoned

                WHERE City = ?
                  AND Zone = ?
                {ride_clause}
                {extra_clause}
            """

            result = read_sql(
                query,
                tuple(params),
            )

            if result.empty:
                continue

            row = (
                result
                .iloc[0]
                .to_dict()
            )

            row.update(
                {
                    "found": True,
                    "city": city,
                    "zone": zone,
                    "hour": int(hour),
                    "day_name": day_name,
                    "ride_type": ride_type,
                    "basis": basis,
                    "sample_size": count,
                    "completed_rides_estimated": max(
                        0.0,
                        float(
                            row["bookings"]
                        )
                        * (
                            1.0
                            - float(
                                row[
                                    "cancellation_rate"
                                ]
                            )
                            / 100.0
                        ),
                    ),
                }
            )

            demand_query = f"""
                SELECT
                    Demand_Level,
                    COUNT(*) AS Records
                FROM rides_zoned
                WHERE City = ?
                  AND Zone = ?
                {ride_clause}
                {extra_clause}
                GROUP BY Demand_Level
            """

            demand = read_sql(
                demand_query,
                tuple(params),
            )

            demand_map = {
                "Low": 0,
                "Medium": 0,
                "High": 0,
            }

            for (
                _,
                demand_row,
            ) in demand.iterrows():

                label = str(
                    demand_row[
                        "Demand_Level"
                    ]
                )

                if label in demand_map:
                    demand_map[
                        label
                    ] = int(
                        demand_row[
                            "Records"
                        ]
                    )

            total = max(
                1,
                count,
            )

            row[
                "demand_breakdown"
            ] = [

                {
                    "Demand Level": label,
                    "Records": demand_map[
                        label
                    ],
                    "Share": (
                        demand_map[
                            label
                        ]
                        / total
                        * 100.0
                    ),
                }

                for label in (
                    "Low",
                    "Medium",
                    "High",
                )
            ]

            weather_query = f"""
                SELECT
                    Weather,
                    COUNT(*) AS Records
                FROM rides_zoned
                WHERE City = ?
                  AND Zone = ?
                {ride_clause}
                {extra_clause}
                GROUP BY Weather
                ORDER BY Records DESC
            """

            row[
                "weather_mix"
            ] = (
                read_sql(
                    weather_query,
                    tuple(params),
                )
                .to_dict(
                    orient="records"
                )
            )

            return row

    return {
        "found": False,
        "message": (
            f"No zone-level records "
            f"are available for "
            f"{zone}, {city}."
        ),
    }


# ============================================================
# ZONE EVENT SIGNAL
# ============================================================

def get_zone_event_signal_sql(
    city,
    zone,
    ride_type="All Ride Types",
):

    query = """
        SELECT
            CASE
                WHEN Event = 'No Event Recorded'
                THEN 0
                ELSE 1
            END AS Is_Event,

            AVG(Demand_Score)
                AS Avg_Demand_Score

        FROM rides_zoned

        WHERE City = ?
          AND Zone = ?
    """

    params = [
        city,
        zone,
    ]

    clause, values = (
        _ride_type_clause(
            ride_type
        )
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY Is_Event
    """

    data = read_sql(
        query,
        tuple(params),
    )

    if data.empty:
        return {
            "event_avg_demand": None,
            "normal_avg_demand": None,
            "demand_delta_pct": None,
        }

    event_avg = None
    normal_avg = None

    for _, row in data.iterrows():

        if int(
            row["Is_Event"]
        ) == 1:

            event_avg = float(
                row[
                    "Avg_Demand_Score"
                ]
            )

        else:

            normal_avg = float(
                row[
                    "Avg_Demand_Score"
                ]
            )

    delta = None

    if (
        event_avg is not None
        and normal_avg not in (
            None,
            0,
        )
    ):

        delta = (
            event_avg
            - normal_avg
        ) / abs(
            normal_avg
        ) * 100.0

    return {
        "event_avg_demand": event_avg,
        "normal_avg_demand": normal_avg,
        "demand_delta_pct": delta,
    }


# ============================================================
# ZONE DEMAND SCORES
# ============================================================

def get_zone_demand_scores_sql(
    city,
    hour,
    day_name,
    ride_type="All Ride Types",
):

    clause, values = (
        _ride_type_clause(
            ride_type
        )
    )

    candidates = [

        (
            "Zone + hour + weekday",
            """
            AND Hour_of_Day = ?
            AND Day_of_Week = ?
            """,
            [hour, day_name],
        ),

        (
            "Zone + hour",
            """
            AND Hour_of_Day = ?
            """,
            [hour],
        ),

        (
            "Zone + all times",
            "",
            [],
        ),
    ]

    for (
        basis,
        extra_clause,
        extra_params,
    ) in candidates:

        query = f"""
            SELECT
                Zone,

                AVG(Demand_Score)
                    AS Average_Demand_Score,

                COUNT(*) AS Records

            FROM rides_zoned

            WHERE City = ?
            {clause}
            {extra_clause}

            GROUP BY Zone
        """

        params = [
            city,
            *values,
            *extra_params,
        ]

        result = read_sql(
            query,
            tuple(params),
        )

        if not result.empty:

            result["basis"] = basis

            return result

    return pd.DataFrame()


# ============================================================
# ZONE FILTER
# ============================================================

def _zone_clause(zones):

    if zones is None:
        return "", []

    zones = [
        str(zone)
        for zone in zones
        if zone
    ]

    if not zones:
        return (
            " AND 1 = 0",
            [],
        )

    placeholders = ",".join(
        "?"
        for _ in zones
    )

    return (
        f" AND Zone IN ({placeholders})",
        zones,
    )


# ============================================================
# ZONE ROWS
# ============================================================

def get_zone_rows_sql(
    city,
    zones=None,
    ride_type="All Ride Types",
):

    query = """
        SELECT *
        FROM rides_zoned
        WHERE City = ?
    """

    params = [
        city
    ]

    clause, values = (
        _zone_clause(
            zones
        )
    )

    query += clause
    params.extend(values)

    clause, values = (
        _ride_type_clause(
            ride_type
        )
    )

    query += clause
    params.extend(values)

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# ZONE DEMAND
# ============================================================

def get_zone_demand_sql(
    city,
    zones=None,
    ride_type="All Ride Types",
):

    query = """
        SELECT
            Zone,
            COUNT(*) AS Records,

            AVG(Demand_Score)
                AS Average_Demand_Score,

            AVG(Available_Drivers)
                AS Average_Available_Drivers,

            AVG(Driver_Availability)
                AS Average_Driver_Availability

        FROM rides_zoned

        WHERE City = ?
    """

    params = [
        city
    ]

    clause, values = (
        _zone_clause(
            zones
        )
    )

    query += clause
    params.extend(values)

    clause, values = (
        _ride_type_clause(
            ride_type
        )
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY Zone
        ORDER BY Average_Demand_Score DESC
    """

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# ZONE EARNINGS
# ============================================================

def get_zone_earnings_sql(
    city,
    zones=None,
    ride_type="All Ride Types",
):

    query = """
        SELECT
            Zone,
            Ride_Type,
            COUNT(*) AS Records,

            AVG(Final_Fare)
                AS Average_Fare,

            AVG(Fare_Per_KM)
                AS Average_Fare_Per_KM,

            AVG(Ride_Distance_KM)
                AS Average_Ride_Distance

        FROM rides_zoned

        WHERE City = ?
    """

    params = [
        city
    ]

    clause, values = (
        _zone_clause(
            zones
        )
    )

    query += clause
    params.extend(values)

    clause, values = (
        _ride_type_clause(
            ride_type
        )
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY
            Zone,
            Ride_Type

        ORDER BY
            Zone,
            Ride_Type
    """

    return read_sql(
        query,
        tuple(params),
    )


# ============================================================
# ZONE CANCELLATIONS
# ============================================================

def get_zone_cancellations_sql(
    city,
    zones=None,
    ride_type="All Ride Types",
):

    query = f"""
        SELECT
            Zone,
            COUNT(*) AS Records,

            {_normalized_rate_sql(
                "Cancellation_Rate"
            )}
                AS Average_Cancellation_Rate,

            {_normalized_rate_sql(
                "Cancellation_Probability"
            )}
                AS Average_Cancellation_Probability,

            AVG(Traffic_Delay)
                AS Average_Traffic_Delay

        FROM rides_zoned

        WHERE City = ?
    """

    params = [
        city
    ]

    clause, values = (
        _zone_clause(
            zones
        )
    )

    query += clause
    params.extend(values)

    clause, values = (
        _ride_type_clause(
            ride_type
        )
    )

    query += clause
    params.extend(values)

    query += """
        GROUP BY Zone
        ORDER BY Average_Cancellation_Rate DESC
    """

    return read_sql(
        query,
        tuple(params),
    )