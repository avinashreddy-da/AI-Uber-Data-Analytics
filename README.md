# 🚕 MobilityLens — AI-Powered Mobility Data Analytics

## 📌 Overview

**MobilityLens** is an AI-powered Data Analytics web application built using **Python, SQL, Streamlit, APIs, and Generative AI**.

The application analyzes historical ride-demand data to explore:

- Ride demand
- Fares
- Ride distance
- Driver availability
- Cancellations
- Demand scores
- Weather and event patterns
- City and location-level mobility patterns

It also combines historical analysis with **current weather and optional traffic context** and uses **Google Gemini Generative AI** to explain calculated analytical results in natural language.

MobilityLens is designed as an **end-to-end Data Analyst portfolio project**, demonstrating how data analysis, SQL, Python, APIs, visualization, application development, and Generative AI can work together in a single application.

> **Important:** The FairFare dataset used by this project is synthetic/generated data. It does not represent official Uber, Ola, or other ride-hailing operational statistics.

---

# 🎯 Objective

The main objective of MobilityLens is to turn mobility data into understandable business insights.

The application helps answer questions such as:

- When is historical ride demand higher or lower?
- How does demand vary by city and hour?
- How does driver availability relate to demand?
- How do ride distance and ride type relate to fares?
- When are cancellations more common?
- How are weather and event categories associated with demand?
- What historical mobility patterns exist for a selected location?
- What is the current weather and traffic context for a selected location?
- Can analytical results be explained through natural language?

---

# 💼 Business Problem

Ride-hailing businesses need to understand how **demand, pricing, driver availability, cancellations, weather, traffic, and events** vary across different mobility situations.

MobilityLens brings these factors together in one interactive application so users can explore historical mobility patterns and understand the factors associated with them.

The application focuses on **historical evidence and analysis**, rather than making guaranteed future predictions.

---

# 🏗️ Application Architecture

MobilityLens follows an end-to-end analytics architecture:

```text
                         USER
                           │
                           ▼
                  ┌─────────────────┐
                  │    Streamlit    │
                  │    Frontend     │
                  └────────┬────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ Python Application  │
                │ Logic + Pandas      │
                └───────┬───────┬─────┘
                        │       │
             ┌──────────▼───┐   └───────────────┐
             │ SQLite / SQL │                   │
             │ Historical   │                   │
             │ Data Layer   │                   │
             └──────────────┘                   │
                                               │
                                  ┌────────────▼────────────┐
                                  │ External APIs           │
                                  │ Weather / Traffic       │
                                  └─────────────────────────┘
                        │
                        ▼
                ┌─────────────────────┐
                │ Analytical Evidence │
                │ KPIs / Aggregations │
                │ Historical Patterns │
                └──────────┬──────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Gemini LLM     │
                  │ Generative AI  │
                  └───────┬────────┘
                          │
                          ▼
                  Natural-Language
                     Business
                      Insight

```

---

# 🖥️ Frontend

### Streamlit

Streamlit is used to build the interactive web application.

The frontend provides:

- City and location selection
- Day and hour filters
- Ride-type filters
- KPI cards
- Historical demand tables
- Charts and visualizations
- Weather information
- Traffic context
- India Explorer
- AI Assistant
- Historical context and fallback information

The application allows users to interact with the analysis without directly writing SQL or Python queries.

---

# ⚙️ Backend / Application Logic

### Python

Python acts as the main application and analytical layer.

It handles:

- Data loading
- Data processing
- Historical filtering
- KPI calculations
- Demand-level classification
- Cancellation calculations
- Fare analysis
- Ride-distance analysis
- Driver availability analysis
- Location processing
- Haversine distance calculations
- Zone assignment
- API integration
- Preparing analytical evidence for Gemini
- Streamlit application orchestration

### Pandas

Pandas is used for data manipulation and analytical processing, including:

- Filtering records
- Grouping and aggregation
- Calculating averages and rates
- Processing historical records
- Handling numeric fields
- Preparing data for charts and tables
- Supporting fallback analysis when location-specific historical records are sparse

### NumPy

NumPy is used for numerical operations, including calculations involved in location and distance processing.

---

# 🗄️ Database & SQL Layer

### SQLite

SQLite provides the local analytical database layer for the FairFare mobility data.

The project creates a local SQLite database from the source dataset.

### SQL

SQL is used for analytical operations such as:

- Filtering
- `COUNT`
- `SUM`
- `AVG`
- `GROUP BY`
- City-level analysis
- Hourly analysis
- Ride-type analysis
- Demand analysis
- Fare analysis
- Cancellation analysis
- Driver availability analysis

The application also contains **Python/Pandas processing and fallback logic** for cases where the required historical records or database-level context are not available.

This allows the application to continue providing useful historical context instead of failing when a selected location has sparse data.

---

# 📍 Location & Historical Context

MobilityLens uses demonstration zones to organize historical mobility records into location-level context.

The location workflow is:

```text
Selected Location
       ↓
Latitude / Longitude
       ↓
Haversine Distance Calculation
       ↓
Nearest Demonstration Zone
       ↓
Historical Zone Records
       ↓
Selected Day + Hour + Ride Type
       ↓
Historical KPIs

```

The application uses demonstration zone coordinates rather than claiming that the dataset contains official neighborhood-level ride statistics.

For locations where sufficient place-specific historical records are not available, the application can fall back to broader historical context.

The fallback sequence is:

```text
Place + Hour + Day
        ↓
Place + Hour
        ↓
Place + All Times
        ↓
City + Hour + Day
        ↓
City + Hour
        ↓
City + All Times

```

The Home page displays the **historical filter level and number of records used**, so users can understand the basis of the displayed KPIs.

---

# 📊 Analytics Performed

MobilityLens performs business-oriented analysis across several dimensions.

### Demand Analysis

The application analyzes:

- Demand by city
- Demand by hour
- Demand by ride type
- Demand scores
- Demand levels
- Driver availability alongside demand

### Fare Analysis

The application analyzes:

- Average fare
- Ride distance
- Fare by ride type
- Fare-per-distance patterns
- Historical fare differences across mobility contexts

### Cancellation Analysis

The application analyzes:

- Historical cancellation rate
- Cancellation probability
- Cancellation patterns across different mobility contexts

### Driver Analysis

The application examines:

- Available drivers
- Driver availability
- Relationship between driver availability and demand
- Driver-related historical metrics available in the dataset

### Weather & Event Analysis

The application can compare historical demand metrics across:

- Weather categories
- Event vs non-event records

These are treated as **historical associations**, not proof of causation.

---

# 📏 Metric Definitions

### Bookings

Number of historical ride records matching the selected context.

### Completed Rides

An estimated value calculated from bookings and the historical cancellation rate:

```text
Estimated Completed Rides
=
Bookings × (1 − Cancellation Rate)

```

### Cancellation Rate

Historical cancellation rate associated with the selected records.

### Cancellation Probability

A separate historical dataset field representing cancellation probability.

These two metrics are not treated as the same measure.

### Average Fare

Average `Final_Fare` across the selected historical records.

### Fare per KM

Fare relative to ride distance.

### Demand Score

A historical demand-related score already present in the dataset.

The original generation formula for the individual `Demand_Score` field is not documented in the current project code, so the application does not claim a specific mathematical generation formula.

### Demand Levels

The application derives **Low, Medium, and High** demand categories from the available demand-score distribution when usable categorical demand labels are not available.

### Available Drivers vs Driver Availability

These are treated as separate dataset fields and are not assumed to represent the same metric.

---

# 📂 Dataset

The application uses the **FairFare Ride Demand Dataset**, containing synthetic/generated mobility records across multiple Indian cities.

### Supported Cities

- Hyderabad
- Delhi
- Mumbai
- Bangalore
- Chennai

### Important Fields


| Column                | Description                  |
| --------------------- | ---------------------------- |
| `City`                | City of the ride             |
| `Date`                | Ride date                    |
| `Day_of_Week`         | Day of the week              |
| `Ride_Distance_KM`    | Ride distance                |
| `Ride_Type`           | Economy, Premium, or Luxury  |
| `Weather`             | Historical weather category  |
| `Event`               | Historical event category    |
| `Available_Drivers`   | Available driver count       |
| `Demand_Level`        | Dataset demand field         |
| `Surge_Multiplier`    | Historical surge multiplier  |
| `Final_Fare`          | Final ride fare              |
| `Hour_of_Day`         | Hour of the ride             |
| `Cancellation_Rate`   | Historical cancellation rate |
| `Demand_Score`        | Historical demand score      |
| `Driver_Availability` | Driver availability measure  |
| `Traffic_Delay`       | Historical traffic delay     |


> The dataset is synthetic/generated and should not be interpreted as official operational data from Uber, Ola, or another ride-hailing company.

---

# 🌐 API Integration

## Weather API

**Open-Meteo** is used to retrieve current weather information.

The weather information provides current context for the selected location and is separate from the historical FairFare observations.

## Traffic API

**TomTom Traffic API** can provide current traffic context where available.

Traffic information is treated as additional live context rather than historical FairFare data.

---

# 🤖 Generative AI

MobilityLens integrates **Google Gemini** as a Generative AI layer.

The AI Assistant does not independently calculate the underlying business metrics.

Instead, the application first performs the analysis using Python/SQL and prepares relevant evidence.

The workflow is:

```text
User Question
      ↓
MobilityLens receives the question
      ↓
Python / SQL analyze historical data
      ↓
Relevant metrics and evidence are calculated
      ↓
Evidence is provided to Gemini
      ↓
Gemini interprets the analytical evidence
      ↓
Natural-Language Business Insight

```

For example, a user can ask:

> What factors are associated with higher demand?

The application calculates the relevant historical evidence first, then Gemini explains those results in natural language.

### Important

MobilityLens uses **Generative AI**, not an autonomous Agentic AI architecture.

Gemini is used primarily for **natural-language interpretation and explanation of analytical results**.

---

# 📱 Application Pages

## 🏠 Home

Provides the main historical mobility context.

Includes:

- Current approximate city context
- Selected location
- Historical records
- KPI metrics
- Demand levels
- Weather mix
- Zone comparison
- Ride-type analysis
- Current weather
- Optional traffic context
- Historical filter level and record count

---

## 🇮🇳 India Explorer

Allows users to explore supported Indian cities and demonstration zones.

Users can examine historical mobility information across different locations.

---

## 📈 Demand Patterns

Analyzes historical demand by:

- City
- Hour
- Ride type
- Demand level
- Driver availability

---

## 💰 Historical Earnings

Explores historical fare and earnings-related patterns using:

- Ride distance
- Ride type
- Fare
- Historical mobility records

---

## ❌ Cancellations

Analyzes historical cancellation behavior and related mobility factors.

---

## 🤖 AI Assistant

Allows users to ask natural-language questions about the historical mobility dataset.

The assistant uses calculated analytical evidence to generate business-oriented explanations.

---

# 🔄 End-to-End Data Flow

```text
FairFare CSV
     ↓
Data Loading
     ↓
Python / Pandas Processing
     ↓
SQLite Database
     ↓
SQL + Python Historical Analysis
     ↓
KPIs / Aggregations / Business Evidence
     ↓
Streamlit Visualization
     ↓
Current Weather / Traffic APIs
     ↓
Gemini Generative AI
     ↓
Natural-Language Business Insights

```

---

# 💼 Business Impact

MobilityLens helps mobility stakeholders explore historical patterns related to:

- **Demand:** Understand when and where historical ride demand has been higher or lower.
- **Driver Availability:** Examine driver availability alongside historical demand.
- **Pricing:** Compare fares across ride types and distances.
- **Cancellations:** Identify historical cancellation patterns.
- **Weather & Events:** Analyze external conditions alongside mobility demand.
- **Locations:** Compare mobility patterns across cities and selected demonstration zones.
- **Decision Support:** Bring multiple mobility metrics together in one interactive application.
- **AI-Assisted Analysis:** Convert calculated analytical results into easy-to-understand natural-language explanations.

Overall, MobilityLens demonstrates how historical mobility data can be transformed into **business insights about demand, pricing, driver availability, and cancellations**.

---

# 🛠️ Technology Stack


| Layer               | Technology         | Purpose                                  |
| ------------------- | ------------------ | ---------------------------------------- |
| Frontend            | Streamlit          | Interactive web application              |
| Programming         | Python             | Application and analytics logic          |
| Data Analysis       | Pandas             | Data processing and analysis             |
| Numerical Computing | NumPy              | Numerical calculations                   |
| Database            | SQLite             | Local analytical database                |
| Query Language      | SQL                | Filtering and aggregation                |
| Visualization       | Altair / Streamlit | Charts and visual analysis               |
| Weather API         | Open-Meteo         | Current weather context                  |
| Traffic API         | TomTom             | Current traffic context                  |
| Generative AI       | Google Gemini      | Natural-language analytical explanations |
| Version Control     | Git                | Source-code version control              |
| Repository          | GitHub             | Project hosting                          |
| Development         | Cursor             | AI-assisted development                  |


---

# 📸 Application Screenshots

## Home

![MobilityLens Home](https://chatgpt.com/c/Screenshots/home.png)

## India Explorer

![India Explorer](https://chatgpt.com/c/Screenshots/india-explorer.png)

## Demand Patterns

![Demand Patterns](https://chatgpt.com/c/Screenshots/demand-patterns.png)

## Historical Earnings

![Historical Earnings](https://chatgpt.com/c/Screenshots/historical-earnings.png)

## Cancellations

![Cancellations](https://chatgpt.com/c/Screenshots/cancellations.png)

## AI Assistant

![AI Assistant](https://chatgpt.com/c/Screenshots/ai-assistant.png)

---

# 📂 Project Structure

```text
AI-Uber-Data-Analytics/
│
├── data/
│   ├── fairfare_ride_demand_dataset.csv
│   ├── mobilitylens_zones.csv
│   └── README.md
│
├── Screenshots/
│   ├── ai-assistant.png
│   ├── cancellations.png
│   ├── demand-patterns.png
│   ├── historical-earnings.png
│   ├── home.png
│   └── india-explorer.png
│
├── main.py
├── database.py
├── create_database.py
├── requirements.txt
├── README.md
└── .gitignore

```

---

# ⚙️ Setup

## 1. Clone the Repository

```bash
git clone https://github.com/avinashreddy-da/AI-Uber-Data-Analytics.git
cd AI-Uber-Data-Analytics

```

## 2. Install Dependencies

```bash
pip install -r requirements.txt

```

## 3. Configure API Keys

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
TOMTOM_API_KEY=your_tomtom_api_key

```

API keys should never be committed to GitHub.

## 4. Create the Database

```bash
python create_database.py

```

## 5. Run the Application

```bash
streamlit run main.py

```

---

# ⚠️ Limitations

- The FairFare dataset is synthetic/generated data.
- Historical results do not represent official Uber/Ola operational statistics.
- The application does not guarantee future demand, fares, earnings, or cancellation outcomes.
- Demonstration zones are used to organize historical records.
- Some selected locations may not have sufficient place-specific historical records.
- When place-specific records are sparse, the application can use broader city-level historical context.
- Current weather and traffic are live contextual information and are not historical FairFare observations.
- Event analysis represents historical association and should not be interpreted as causation.
- API availability and quotas can affect live weather, traffic, or AI functionality.
- Gemini explanations depend on the analytical evidence provided by the application.

---

# 🧠 Skills Demonstrated

### Data Analytics

- Data Cleaning
- Exploratory Data Analysis
- Business Analysis
- KPI Development
- Historical Pattern Analysis
- Statistical Interpretation

### Technical

- Python
- Pandas
- NumPy
- SQL
- SQLite
- Streamlit
- Altair
- API Integration
- Generative AI

### Business

- Demand Analysis
- Pricing Analysis
- Cancellation Analysis
- Driver Availability Analysis
- Location Analysis
- Business Insight Generation

### Development

- Git
- GitHub
- Cursor
- Application Development
- End-to-End Analytics Workflow

---

# 📌 Key Takeaway

MobilityLens demonstrates an end-to-end Data Analytics workflow:

```text
Raw Mobility Data
       ↓
Data Processing
       ↓
SQL + Python Analysis
       ↓
Business Evidence
       ↓
Interactive Streamlit Application
       ↓
Live API Context
       ↓
Generative AI Explanation

```

The project demonstrates how a Data Analyst can combine **business analysis, SQL, Python, visualization, APIs, application development, and Generative AI** to build an interactive analytics solution.

---

# 👨‍💻 Author

**Avinash Reddy**

MSc Statistics — Pondicherry University

**Aspiring Data Analyst**

**Skills:** SQL | Python | Pandas | Excel | Power BI | Statistics | Business Analysis | Generative AI

