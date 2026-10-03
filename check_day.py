import database

result = database.read_sql("""
    SELECT
        Day_of_Week,
        strftime('%w', Date) AS Actual_Day,
        COUNT(*) AS Records
    FROM rides
    WHERE City = ?
    GROUP BY Day_of_Week, Actual_Day
    ORDER BY Day_of_Week, Actual_Day
""", ("Hyderabad",))

print(result)