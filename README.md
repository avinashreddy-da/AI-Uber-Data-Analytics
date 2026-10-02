# MobilityLens — AI-Powered Mobility Analytics

MobilityLens is an interactive Streamlit application that combines **Data Analytics, SQL, Python, APIs, and Generative AI** to explore historical ride-demand and mobility patterns.

The application uses the **FairFare synthetic/generated multi-city dataset** to analyze demand, fares, cancellations, ride types, and other mobility metrics across major Indian cities. It also uses current weather and traffic context and Gemini Generative AI to provide natural-language explanations of historical data.

> **Important:** FairFare is synthetic/generated data for analytical demonstration. It is not official Uber, Ola, or real-world operational data. Historical patterns shown by the application should not be interpreted as guaranteed future outcomes.

---

## Features

### 📊 Historical Mobility Analytics

- Historical booking and ride metrics
- Demand-level analysis
- Average fare analysis
- Ride-distance analysis
- Cancellation analysis
- Ride-type comparisons
- City-level comparisons
- Historical weather patterns
- Historical demand patterns by hour and ride type

### 🌦️ Live Context

- Current approximate user location
- Current city detection
- Live weather information
- Optional traffic context
- Historical data combined with current contextual information

### 🤖 Generative AI Assistant

The application integrates **Google Gemini Generative AI** to explain historical mobility patterns in natural language.

The AI Assistant:

- Uses calculated historical evidence from the application
- Explains demand, fare, cancellation, and mobility patterns
- Provides business-oriented interpretations
- Identifies important factors in the historical data
- Clearly treats FairFare as synthetic/generated data
- Does not guarantee or predict future ride outcomes

### 🗄️ SQL-Based Analytics

Historical FairFare data is stored in SQLite and queried using SQL for:

- Filtering
- Aggregations
- Grouping
- City comparisons
- Hourly analysis
- Ride-type analysis
- Historical KPI calculations

### 📍 City and Place Exploration

The application supports historical exploration across:

- Hyderabad
- Delhi
- Mumbai
- Bangalore
- Chennai

The application also provides selected place/zone contexts for organizing available historical records.

---

## Application Pages

### Home

Provides a consolidated view of the selected city/place, including:

- Historical KPIs
- Demand levels
- Average fare
- Ride distance
- Cancellation metrics
- Historical weather mix
- Current weather context
- Historical mobility context

### India Explorer

Explore supported Indian cities and available mobility/zone information.

### Demand Patterns

Analyze historical demand patterns by:

- City
- Hour
- Ride type
- Demand level

### Historical Earnings

Explore historical fare and earnings-related metrics across different cities and ride types.

### Cancellations

Analyze historical cancellation patterns and cancellation-related metrics.

### AI Assistant

Ask natural-language questions about the historical mobility data and receive Gemini-generated explanations based on the application's calculated evidence.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Application logic and data processing |
| Pandas | Data manipulation and analysis |
| NumPy | Numerical operations |
| SQL / SQLite | Historical data storage and querying |
| Streamlit | Interactive web application |
| Altair | Data visualization |
| Requests | API requests |
| Open-Meteo | Live weather context |
| TomTom | Traffic context |
| Google Gemini | Generative AI explanations |
| python-dotenv | Environment variable management |

---

## Architecture

```text
FairFare Dataset
       │
       ▼
   SQLite Database
       │
       ▼
   SQL Queries
       │
       ▼
Python / Pandas Processing
       │
       ├──────────────► Live Weather API
       │
       ├──────────────► Traffic API
       │
       ▼
   Streamlit UI
       │
       ▼
 Gemini Generative AI
       │
       ▼
Natural-Language Insights