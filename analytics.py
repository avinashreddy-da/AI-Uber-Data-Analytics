"""
SQL-driven analytics layer for the existing Uber rides SQLite database.

Source of truth: data/uber_rides.db, table `rides`.

Demand and earnings metrics use Booking Status = 'Completed' only.

Cancellation/reason NULLs are treated as structurally expected, not as
data-quality errors.

Results are descriptive/associational — they do not imply causation.

Vehicle-type filtering is optional. When vehicle_type is not provided,
analytics use all vehicle types.

Contextual vehicle-type analysis uses a minimum historical sample size.
If the vehicle-specific sample is too small, the contextual analysis falls
back to the broader all-vehicle pattern and clearly labels that fallback.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Optional, Union

import pandas as pd


TABLE_NAME = "rides"

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "data",
    "uber_rides.db",
)

REQUIRED_COLUMNS = [
    "Booking Status",
    "Pickup Location",
    "Vehicle Type",
    "Hour",
    "Day_Name",
    "Is_Weekend",
    "Booking Value",
    "Ride Distance",
    "Value_Per_Km",
    "Reason for cancelling by Customer",
    "Driver Cancellation Reason",
    "Incomplete Rides Reason",
    "Date",
    "Festival_Name",
    "Is_Festival",
]

COMPLETED_STATUS = "Completed"
CUSTOMER_CANCEL_STATUS = "Cancelled by Customer"
DRIVER_CANCEL_STATUS = "Cancelled by Driver"
INCOMPLETE_STATUS = "Incomplete"

# Contextual analysis below this sample size is considered too sparse
# for vehicle-specific interpretation.
MIN_CONTEXT_SAMPLE_SIZE = 5

VALID_DAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

DAY_ORDER_SQL = """
CASE "Day_Name"
    WHEN 'Monday' THEN 1
    WHEN 'Tuesday' THEN 2
    WHEN 'Wednesday' THEN 3
    WHEN 'Thursday' THEN 4
    WHEN 'Friday' THEN 5
    WHEN 'Saturday' THEN 6
    WHEN 'Sunday' THEN 7
    ELSE 8
END
"""


class AnalyticsError(Exception):
    """Raised when the analytics database, table, or required columns are missing."""


class SQLiteQueryHelper:
    """Reusable read-only SQLite helper that keeps one connection open."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._validated = False

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            if not os.path.exists(self.db_path):
                raise AnalyticsError(
                    f"SQLite database not found at: {self.db_path}"
                )

            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row

        if not self._validated:
            self.validate_schema()

        return self._conn

    def validate_schema(self) -> None:
        conn = self._conn

        if conn is None:
            raise AnalyticsError("Cannot validate schema before connecting.")

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

        if TABLE_NAME not in tables:
            raise AnalyticsError(
                f"Required table '{TABLE_NAME}' is missing from {self.db_path}. "
                f"Found tables: {sorted(tables) or 'none'}"
            )

        existing_columns = {
            row[1]
            for row in conn.execute(
                f'PRAGMA table_info("{TABLE_NAME}")'
            ).fetchall()
        }

        missing = [
            col
            for col in REQUIRED_COLUMNS
            if col not in existing_columns
        ]

        if missing:
            raise AnalyticsError(
                f"Table '{TABLE_NAME}' is missing required columns: {missing}"
            )

        self._validated = True

    def query(
        self,
        sql: str,
        params: Union[tuple, dict, list, None] = None,
    ) -> pd.DataFrame:
        conn = self.connect()
        return pd.read_sql_query(sql, conn, params=params or ())

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            self._validated = False

    def __enter__(self) -> "SQLiteQueryHelper":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


DbSource = Union[str, SQLiteQueryHelper, None]


def _get_helper(db: DbSource) -> tuple[SQLiteQueryHelper, bool]:
    """Return (helper, owns_helper). Caller must close if owns_helper is True."""

    if isinstance(db, SQLiteQueryHelper):
        return db, False

    path = db if isinstance(db, str) else DEFAULT_DB_PATH
    return SQLiteQueryHelper(path), True


def _run_query(
    sql: str,
    db: DbSource = None,
    params: Union[tuple, dict, list, None] = None,
) -> pd.DataFrame:
    helper, owns = _get_helper(db)

    try:
        return helper.query(sql, params)
    finally:
        if owns:
            helper.close()


def _validate_optional_hour(hour: Optional[int]) -> None:
    if hour is not None and (
        not isinstance(hour, int)
        or hour < 0
        or hour > 23
    ):
        raise AnalyticsError(
            "hour must be an integer between 0 and 23, or None."
        )


def _validate_optional_day(day_name: Optional[str]) -> None:
    if day_name is not None and day_name not in VALID_DAYS:
        raise AnalyticsError(
            f"day_name must be one of {list(VALID_DAYS)}, or None."
        )


def _validate_optional_vehicle_type(
    vehicle_type: Optional[str],
) -> None:
    if vehicle_type is not None:
        if not isinstance(vehicle_type, str) or not vehicle_type.strip():
            raise AnalyticsError(
                "vehicle_type must be a non-empty string, or None."
            )


def _vehicle_filter(
    vehicle_type: Optional[str],
) -> tuple[str, tuple]:
    """
    SQL fragment plus parameters for optional Vehicle Type filtering.

    When vehicle_type is None, no vehicle filter is applied.
    """

    _validate_optional_vehicle_type(vehicle_type)

    if vehicle_type is None:
        return "", ()

    return (
        'AND "Vehicle Type" = ?',
        (vehicle_type.strip(),),
    )


def _completed_time_filters(
    hour: Optional[int],
    day_name: Optional[str],
) -> tuple[str, tuple]:
    """SQL fragment plus params for optional Hour / Day_Name filters."""

    _validate_optional_hour(hour)
    _validate_optional_day(day_name)

    hour_filter = -1 if hour is None else hour
    day_filter = "" if day_name is None else day_name

    clause = """
        AND (? = -1 OR Hour = ?)
        AND (? = '' OR "Day_Name" = ?)
    """

    return clause, (
        hour_filter,
        hour_filter,
        day_filter,
        day_filter,
    )


def overall_kpis(db: DbSource = None) -> pd.DataFrame:
    """High-level dataset KPIs. AVG(Value_Per_Km) ignores NULLs."""

    sql = """
        SELECT
            COUNT(*) AS total_bookings,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS completed_rides,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS completion_rate,

            AVG(
                CASE
                    WHEN "Booking Status" = ?
                    THEN "Booking Value"
                END
            ) AS avg_booking_value,

            AVG(
                CASE
                    WHEN "Booking Status" = ?
                    THEN "Ride Distance"
                END
            ) AS avg_ride_distance,

            AVG("Value_Per_Km") AS avg_value_per_km

        FROM rides
    """

    params = (
        COMPLETED_STATUS,
        COMPLETED_STATUS,
        COMPLETED_STATUS,
        COMPLETED_STATUS,
    )

    return _run_query(sql, db, params)


# ---------------------------------------------------------------------------
# 1. Demand Intelligence
# ---------------------------------------------------------------------------

def completed_rides_by_pickup_location(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Completed ride counts by pickup location, optionally by vehicle type."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,
            COUNT(*) AS completed_rides
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY "Pickup Location"
        ORDER BY completed_rides DESC, pickup_location ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def completed_rides_by_hour(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Completed ride counts by hour, optionally by vehicle type."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            Hour AS hour,
            COUNT(*) AS completed_rides
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY Hour
        ORDER BY Hour ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def completed_rides_by_day_of_week(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Completed ride counts by weekday, optionally by vehicle type."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Day_Name" AS day_name,
            COUNT(*) AS completed_rides
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY "Day_Name"
        ORDER BY {DAY_ORDER_SQL}
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def completed_rides_by_pickup_and_hour(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Completed ride counts by pickup location and hour."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,
            Hour AS hour,
            COUNT(*) AS completed_rides
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY "Pickup Location", Hour
        ORDER BY pickup_location ASC, hour ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def high_demand_pickup_locations(
    hour: Optional[int] = None,
    day_name: Optional[str] = None,
    top_n: int = 15,
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Top pickup locations by completed rides, with optional filters."""

    if not isinstance(top_n, int) or top_n < 1:
        raise AnalyticsError("top_n must be a positive integer.")

    time_sql, time_params = _completed_time_filters(
        hour,
        day_name,
    )

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,
            COUNT(*) AS completed_rides
        FROM rides
        WHERE "Booking Status" = ?
        {time_sql}
        {vehicle_sql}
        GROUP BY "Pickup Location"
        ORDER BY completed_rides DESC, pickup_location ASC
        LIMIT ?
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *time_params,
            *vehicle_params,
            top_n,
        ),
    )


def high_demand_pickup_locations_for_hour(
    hour: int,
    top_n: int = 10,
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Top pickup locations by completed rides for a selected hour."""

    df = high_demand_pickup_locations(
        hour=hour,
        day_name=None,
        top_n=top_n,
        db=db,
        vehicle_type=vehicle_type,
    )

    df.insert(1, "hour", hour)
    return df


# ---------------------------------------------------------------------------
# 2. Earnings Opportunity
# ---------------------------------------------------------------------------

def avg_booking_value_by_pickup_location(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Average booking value by pickup location."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,
            COUNT(*) AS completed_rides,
            AVG("Booking Value") AS avg_booking_value
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY "Pickup Location"
        ORDER BY avg_booking_value DESC, pickup_location ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def avg_ride_distance_by_pickup_location(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Average ride distance by pickup location."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,
            COUNT(*) AS completed_rides,
            AVG("Ride Distance") AS avg_ride_distance
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY "Pickup Location"
        ORDER BY avg_ride_distance DESC, pickup_location ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def avg_value_per_km_by_pickup_location(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Average Value_Per_Km by pickup location."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,
            COUNT(*) AS completed_rides,
            COUNT("Value_Per_Km") AS rides_with_value_per_km,
            AVG("Value_Per_Km") AS avg_value_per_km
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY "Pickup Location"
        ORDER BY avg_value_per_km DESC, pickup_location ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def avg_booking_value_by_hour(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Average booking value by hour."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            Hour AS hour,
            COUNT(*) AS completed_rides,
            AVG("Booking Value") AS avg_booking_value
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY Hour
        ORDER BY Hour ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def avg_value_per_km_by_hour(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Average Value_Per_Km by hour."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            Hour AS hour,
            COUNT(*) AS completed_rides,
            COUNT("Value_Per_Km") AS rides_with_value_per_km,
            AVG("Value_Per_Km") AS avg_value_per_km
        FROM rides
        WHERE "Booking Status" = ?
        {vehicle_sql}
        GROUP BY Hour
        ORDER BY Hour ASC
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *vehicle_params,
        ),
    )


def strong_earning_opportunity_locations(
    min_completed_rides: int = 100,
    top_n: int = 15,
    db: DbSource = None,
    *,
    hour: Optional[int] = None,
    day_name: Optional[str] = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    Pickup locations with both ride volume and fare intensity.

    opportunity_score = avg_value_per_km * completed_rides

    This is a descriptive ranking, not a causal claim.
    """

    if (
        not isinstance(min_completed_rides, int)
        or min_completed_rides < 1
    ):
        raise AnalyticsError(
            "min_completed_rides must be a positive integer."
        )

    if not isinstance(top_n, int) or top_n < 1:
        raise AnalyticsError(
            "top_n must be a positive integer."
        )

    time_sql, time_params = _completed_time_filters(
        hour,
        day_name,
    )

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,
            COUNT(*) AS completed_rides,
            AVG("Booking Value") AS avg_booking_value,
            AVG("Ride Distance") AS avg_ride_distance,
            AVG("Value_Per_Km") AS avg_value_per_km,
            AVG("Value_Per_Km") * COUNT(*) AS opportunity_score
        FROM rides
        WHERE "Booking Status" = ?
        {time_sql}
        {vehicle_sql}
        GROUP BY "Pickup Location"
        HAVING COUNT(*) >= ?
           AND AVG("Value_Per_Km") IS NOT NULL
        ORDER BY
            opportunity_score DESC,
            avg_value_per_km DESC,
            pickup_location ASC
        LIMIT ?
    """

    return _run_query(
        sql,
        db,
        (
            COMPLETED_STATUS,
            *time_params,
            *vehicle_params,
            min_completed_rides,
            top_n,
        ),
    )


# ---------------------------------------------------------------------------
# 3. Cancellation Patterns
# ---------------------------------------------------------------------------

def booking_status_distribution(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Count and share of all bookings by Booking Status."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    denominator_sql = f"""
        SELECT COUNT(*)
        FROM rides
        WHERE 1 = 1
        {vehicle_sql}
    """

    sql = f"""
        SELECT
            "Booking Status" AS booking_status,
            COUNT(*) AS booking_count,
            ROUND(
                100.0 * COUNT(*) /
                ({denominator_sql}),
                2
            ) AS pct_of_bookings
        FROM rides
        WHERE 1 = 1
        {vehicle_sql}
        GROUP BY "Booking Status"
        ORDER BY booking_count DESC
    """

    params = (
        *vehicle_params,
        *vehicle_params,
    )

    return _run_query(sql, db, params)


def cancellation_rate_by_pickup_location(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """
    Customer, driver, and combined cancellation rates by pickup location.
    """

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            "Pickup Location" AS pickup_location,

            COUNT(*) AS total_bookings,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS customer_cancellations,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS driver_cancellations,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS customer_cancellation_rate,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS driver_cancellation_rate,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" IN (?, ?)
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS combined_cancellation_rate

        FROM rides
        WHERE 1 = 1
        {vehicle_sql}

        GROUP BY "Pickup Location"

        ORDER BY
            combined_cancellation_rate DESC,
            total_bookings DESC,
            pickup_location ASC
    """

    params = (
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        *vehicle_params,
    )

    return _run_query(sql, db, params)


def cancellation_rate_by_hour(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Customer, driver, and combined cancellation rates by hour."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            Hour AS hour,

            COUNT(*) AS total_bookings,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS customer_cancellations,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS driver_cancellations,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS customer_cancellation_rate,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS driver_cancellation_rate,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" IN (?, ?)
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS combined_cancellation_rate

        FROM rides
        WHERE 1 = 1
        {vehicle_sql}

        GROUP BY Hour
        ORDER BY Hour ASC
    """

    params = (
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        *vehicle_params,
    )

    return _run_query(sql, db, params)


def customer_cancellation_counts_and_rates(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Overall customer cancellation count and rate."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            COUNT(*) AS total_bookings,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS customer_cancellations,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS customer_cancellation_rate

        FROM rides
        WHERE 1 = 1
        {vehicle_sql}
    """

    return _run_query(
        sql,
        db,
        (
            CUSTOMER_CANCEL_STATUS,
            CUSTOMER_CANCEL_STATUS,
            *vehicle_params,
        ),
    )


def driver_cancellation_counts_and_rates(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Overall driver cancellation count and rate."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            COUNT(*) AS total_bookings,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS driver_cancellations,

            ROUND(
                1.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                4
            ) AS driver_cancellation_rate

        FROM rides
        WHERE 1 = 1
        {vehicle_sql}
    """

    return _run_query(
        sql,
        db,
        (
            DRIVER_CANCEL_STATUS,
            DRIVER_CANCEL_STATUS,
            *vehicle_params,
        ),
    )


def customer_cancellation_reasons(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Reason counts among customer-cancelled bookings."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            COALESCE(
                "Reason for cancelling by Customer",
                'Not recorded'
            ) AS cancellation_reason,

            COUNT(*) AS reason_count,

            ROUND(
                100.0 * COUNT(*) / (
                    SELECT COUNT(*)
                    FROM rides
                    WHERE "Booking Status" = ?
                    {vehicle_sql}
                ),
                2
            ) AS pct_of_customer_cancellations

        FROM rides

        WHERE "Booking Status" = ?
        {vehicle_sql}

        GROUP BY
            COALESCE(
                "Reason for cancelling by Customer",
                'Not recorded'
            )

        ORDER BY
            reason_count DESC,
            cancellation_reason ASC
    """

    params = (
        CUSTOMER_CANCEL_STATUS,
        *vehicle_params,
        CUSTOMER_CANCEL_STATUS,
        *vehicle_params,
    )

    return _run_query(sql, db, params)


def driver_cancellation_reasons(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Reason counts among driver-cancelled bookings."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            COALESCE(
                "Driver Cancellation Reason",
                'Not recorded'
            ) AS cancellation_reason,

            COUNT(*) AS reason_count,

            ROUND(
                100.0 * COUNT(*) / (
                    SELECT COUNT(*)
                    FROM rides
                    WHERE "Booking Status" = ?
                    {vehicle_sql}
                ),
                2
            ) AS pct_of_driver_cancellations

        FROM rides

        WHERE "Booking Status" = ?
        {vehicle_sql}

        GROUP BY
            COALESCE(
                "Driver Cancellation Reason",
                'Not recorded'
            )

        ORDER BY
            reason_count DESC,
            cancellation_reason ASC
    """

    params = (
        DRIVER_CANCEL_STATUS,
        *vehicle_params,
        DRIVER_CANCEL_STATUS,
        *vehicle_params,
    )

    return _run_query(sql, db, params)


def incomplete_ride_counts_and_reasons(
    db: DbSource = None,
    vehicle_type: Optional[str] = None,
) -> pd.DataFrame:
    """Incomplete booking count plus reason breakdown."""

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            COALESCE(
                "Incomplete Rides Reason",
                'Not recorded'
            ) AS incomplete_reason,

            COUNT(*) AS incomplete_count,

            ROUND(
                100.0 * COUNT(*) / (
                    SELECT COUNT(*)
                    FROM rides
                    WHERE "Booking Status" = ?
                    {vehicle_sql}
                ),
                2
            ) AS pct_of_incomplete_rides

        FROM rides

        WHERE "Booking Status" = ?
        {vehicle_sql}

        GROUP BY
            COALESCE(
                "Incomplete Rides Reason",
                'Not recorded'
            )

        ORDER BY
            incomplete_count DESC,
            incomplete_reason ASC
    """

    params = (
        INCOMPLETE_STATUS,
        *vehicle_params,
        INCOMPLETE_STATUS,
        *vehicle_params,
    )

    return _run_query(sql, db, params)


# ---------------------------------------------------------------------------
# 4. Contextual Driver Intelligence
# ---------------------------------------------------------------------------

def _contextual_query(
    pickup_location: str,
    hour: int,
    day_name: str,
    vehicle_type: Optional[str],
    db: DbSource,
) -> pd.DataFrame:
    """
    Internal contextual query.

    If vehicle_type is provided, the query is filtered to that vehicle.
    """

    vehicle_sql, vehicle_params = _vehicle_filter(vehicle_type)

    sql = f"""
        SELECT
            ? AS pickup_location,
            ? AS hour,
            ? AS day_name,

            CASE
                WHEN ? IN ('Saturday', 'Sunday')
                THEN 1
                ELSE 0
            END AS is_weekend,

            COUNT(*) AS total_bookings,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS completed_rides,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                2
            ) AS completion_rate,

            ROUND(
                AVG(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN "Booking Value"
                    END
                ),
                2
            ) AS avg_booking_value,

            ROUND(
                AVG(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN "Ride Distance"
                    END
                ),
                2
            ) AS avg_ride_distance,

            ROUND(
                AVG(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN "Value_Per_Km"
                    END
                ),
                2
            ) AS avg_value_per_km,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS customer_cancellations,

            SUM(
                CASE
                    WHEN "Booking Status" = ?
                    THEN 1 ELSE 0
                END
            ) AS driver_cancellations,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                2
            ) AS customer_cancellation_rate,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN "Booking Status" = ?
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                2
            ) AS driver_cancellation_rate,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN "Booking Status" IN (?, ?)
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                2
            ) AS combined_cancellation_rate,

            SUM(
                CASE
                    WHEN "Is_Festival" = 1
                    THEN 1 ELSE 0
                END
            ) AS festival_bookings,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN "Is_Festival" = 1
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                2
            ) AS festival_booking_share,

            GROUP_CONCAT(
                DISTINCT
                CASE
                    WHEN "Festival_Name" IS NOT NULL
                    THEN "Festival_Name"
                END
            ) AS observed_festivals

        FROM rides

        WHERE "Pickup Location" = ?
          AND Hour = ?
          AND "Day_Name" = ?
          {vehicle_sql}
    """

    params = (
        pickup_location.strip(),
        hour,
        day_name,
        day_name,
        COMPLETED_STATUS,
        COMPLETED_STATUS,
        COMPLETED_STATUS,
        COMPLETED_STATUS,
        COMPLETED_STATUS,
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        CUSTOMER_CANCEL_STATUS,
        DRIVER_CANCEL_STATUS,
        pickup_location.strip(),
        hour,
        day_name,
        *vehicle_params,
    )

    return _run_query(sql, db, params)


def _empty_contextual_result(
    pickup_location: str,
    hour: int,
    day_name: str,
    vehicle_type: Optional[str],
    warning: str,
) -> pd.DataFrame:
    """Create a consistent zero-result contextual response."""

    return pd.DataFrame(
        [
            {
                "pickup_location": pickup_location.strip(),
                "hour": hour,
                "day_name": day_name,
                "is_weekend": int(
                    day_name in ("Saturday", "Sunday")
                ),
                "vehicle_type_requested": vehicle_type,
                "vehicle_type_used": vehicle_type,
                "vehicle_type_fallback": False,
                "sample_size_warning": warning,
                "total_bookings": 0,
                "completed_rides": 0,
                "completion_rate": None,
                "avg_booking_value": None,
                "avg_ride_distance": None,
                "avg_value_per_km": None,
                "customer_cancellations": 0,
                "driver_cancellations": 0,
                "customer_cancellation_rate": None,
                "driver_cancellation_rate": None,
                "combined_cancellation_rate": None,
                "festival_bookings": 0,
                "festival_booking_share": 0.0,
                "observed_festivals": None,
            }
        ]
    )


def contextual_location_hour_analysis(
    pickup_location: str,
    hour: int,
    day_name: str,
    vehicle_type: Optional[str] = None,
    db: DbSource = None,
) -> pd.DataFrame:
    """
    Combined historical context for one pickup location, hour, day,
    and optionally vehicle type.

    Vehicle-specific analysis is used only when enough historical records
    exist. If the vehicle-specific sample is below
    MIN_CONTEXT_SAMPLE_SIZE, the function falls back to the broader
    all-vehicle pattern and clearly labels the fallback.

    Results describe historical patterns in the dataset.
    They do not predict future outcomes or imply causation.
    """

    if not isinstance(pickup_location, str) or not pickup_location.strip():
        raise AnalyticsError(
            "pickup_location must be a non-empty string."
        )

    _validate_optional_hour(hour)
    _validate_optional_day(day_name)
    _validate_optional_vehicle_type(vehicle_type)

    requested_vehicle = (
        vehicle_type.strip()
        if vehicle_type is not None
        else None
    )

    # ---------------------------------------------------------------
    # First: try vehicle-specific context if requested.
    # ---------------------------------------------------------------

    result = _contextual_query(
        pickup_location=pickup_location,
        hour=hour,
        day_name=day_name,
        vehicle_type=requested_vehicle,
        db=db,
    )

    if result.empty:
        result = _empty_contextual_result(
            pickup_location,
            hour,
            day_name,
            requested_vehicle,
            "No historical records were found for this selection.",
        )
        return result

    vehicle_sample_size = int(
        result.iloc[0]["total_bookings"] or 0
    )

    # ---------------------------------------------------------------
    # No vehicle filter: return normal all-vehicle context.
    # ---------------------------------------------------------------

    if requested_vehicle is None:
        result.insert(
            4,
            "vehicle_type_requested",
            "All Vehicle Types",
        )
        result.insert(
            5,
            "vehicle_type_used",
            "All Vehicle Types",
        )
        result.insert(
            6,
            "vehicle_type_fallback",
            False,
        )
        result.insert(
            7,
            "sample_size_warning",
            result["total_bookings"].apply(
                lambda x: (
                    "Very small historical sample; "
                    "interpret with caution."
                    if int(x or 0) < MIN_CONTEXT_SAMPLE_SIZE
                    else None
                )
            ),
        )

        return result

    # ---------------------------------------------------------------
    # Vehicle-specific sample is large enough.
    # ---------------------------------------------------------------

    if vehicle_sample_size >= MIN_CONTEXT_SAMPLE_SIZE:
        result.insert(
            4,
            "vehicle_type_requested",
            requested_vehicle,
        )
        result.insert(
            5,
            "vehicle_type_used",
            requested_vehicle,
        )
        result.insert(
            6,
            "vehicle_type_fallback",
            False,
        )
        result.insert(
            7,
            "sample_size_warning",
            None,
        )

        return result

    # ---------------------------------------------------------------
    # Vehicle-specific sample is too small.
    # Fall back to all vehicle types.
    # ---------------------------------------------------------------

    broader_result = _contextual_query(
        pickup_location=pickup_location,
        hour=hour,
        day_name=day_name,
        vehicle_type=None,
        db=db,
    )

    if broader_result.empty:
        return _empty_contextual_result(
            pickup_location,
            hour,
            day_name,
            requested_vehicle,
            (
                f"Only {vehicle_sample_size} historical bookings were "
                f"found for {requested_vehicle}. The broader all-vehicle "
                "pattern was also unavailable."
            ),
        )

    broader_sample_size = int(
        broader_result.iloc[0]["total_bookings"] or 0
    )

    broader_result.insert(
        4,
        "vehicle_type_requested",
        requested_vehicle,
    )

    broader_result.insert(
        5,
        "vehicle_type_used",
        "All Vehicle Types",
    )

    broader_result.insert(
        6,
        "vehicle_type_fallback",
        True,
    )

    broader_result.insert(
        7,
        "vehicle_specific_sample_size",
        vehicle_sample_size,
    )

    broader_result.insert(
        8,
        "sample_size_warning",
        (
            f"Vehicle-specific data for {requested_vehicle} had only "
            f"{vehicle_sample_size} historical booking(s), which is "
            f"below the minimum sample size of "
            f"{MIN_CONTEXT_SAMPLE_SIZE}. "
            f"The broader all-vehicle pattern is shown instead "
            f"({broader_sample_size} historical booking(s))."
        ),
    )

    return broader_result


# ---------------------------------------------------------------------------
# 5. Festival Intelligence
# ---------------------------------------------------------------------------

def get_festival_summary(
    helper: SQLiteQueryHelper,
) -> pd.DataFrame:
    """Compare ride outcomes on selected festival vs non-festival dates."""

    query = """
        SELECT
            "Is_Festival",

            COUNT(*) AS total_rides,

            SUM(
                CASE
                    WHEN "Booking Status" = 'Completed'
                    THEN 1 ELSE 0
                END
            ) AS completed_rides,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN "Booking Status" = 'Completed'
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                2
            ) AS completion_rate,

            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN "Booking Status" IN (
                            'Cancelled by Customer',
                            'Cancelled by Driver'
                        )
                        THEN 1 ELSE 0
                    END
                ) / COUNT(*),
                2
            ) AS cancellation_rate

        FROM rides
        GROUP BY "Is_Festival"
        ORDER BY "Is_Festival";
    """

    return helper.query(query)


def get_festival_earnings(
    helper: SQLiteQueryHelper,
) -> pd.DataFrame:
    """Compare completed-ride earnings on festival vs non-festival days."""

    query = """
        SELECT
            "Is_Festival",

            COUNT(*) AS completed_rides,

            ROUND(
                AVG("Booking Value"),
                2
            ) AS avg_booking_value,

            ROUND(
                AVG("Ride Distance"),
                2
            ) AS avg_ride_distance,

            ROUND(
                AVG("Value_Per_Km"),
                2
            ) AS avg_value_per_km

        FROM rides

        WHERE "Booking Status" = 'Completed'

        GROUP BY "Is_Festival"
        ORDER BY "Is_Festival";
    """

    return helper.query(query)


# ---------------------------------------------------------------------------
# All analytics functions
# ---------------------------------------------------------------------------

ALL_ANALYTICS_FUNCTIONS = (
    overall_kpis,
    completed_rides_by_pickup_location,
    completed_rides_by_hour,
    completed_rides_by_day_of_week,
    completed_rides_by_pickup_and_hour,
    high_demand_pickup_locations,
    high_demand_pickup_locations_for_hour,
    avg_booking_value_by_pickup_location,
    avg_ride_distance_by_pickup_location,
    avg_value_per_km_by_pickup_location,
    avg_booking_value_by_hour,
    avg_value_per_km_by_hour,
    strong_earning_opportunity_locations,
    booking_status_distribution,
    cancellation_rate_by_pickup_location,
    cancellation_rate_by_hour,
    customer_cancellation_counts_and_rates,
    driver_cancellation_counts_and_rates,
    customer_cancellation_reasons,
    driver_cancellation_reasons,
    incomplete_ride_counts_and_reasons,
    contextual_location_hour_analysis,
    get_festival_summary,
    get_festival_earnings,
)


if __name__ == "__main__":
    with SQLiteQueryHelper() as helper:
        print("\nFestival earnings:\n")
        result = get_festival_earnings(helper)
        print(result.to_string(index=False))

        print("\nAll-vehicle contextual analysis:\n")
        result = contextual_location_hour_analysis(
            pickup_location="Barakhamba Road",
            hour=14,
            day_name="Saturday",
            db=helper,
        )
        print(result.to_string(index=False))

        print("\nBike contextual analysis:\n")
        result = contextual_location_hour_analysis(
            pickup_location="Barakhamba Road",
            hour=14,
            day_name="Saturday",
            vehicle_type="Bike",
            db=helper,
        )
        print(result.to_string(index=False))