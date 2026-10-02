
# 🚕 MobilityLens — AI-Powered Mobility Data Analytics

## Introduction

MobilityLens is an AI + Data Analytics web application built using **Python, SQL, Streamlit, APIs, and Generative AI**.

The application analyzes historical ride-demand data and combines it with current contextual information such as weather and traffic to help users explore mobility patterns, fares, demand, cancellations, and driver availability.

The project is designed as a **Data Analyst portfolio project** demonstrating how SQL, Python, business analysis, APIs, visualization, and Generative AI can be combined into one end-to-end analytics application.

---

## 🎯 Objective

- Analyze historical mobility and ride-demand patterns.
- Explore demand across cities, hours, and ride types.
- Analyze fares, cancellations, and driver availability.
- Provide current weather and traffic context.
- Allow users to interactively explore mobility data.
- Use Generative AI to explain calculated analytical results in natural language.

---

## 💼 Business Problem

Ride-hailing and mobility platforms generate large amounts of operational data.

A Data Analyst can use this data to answer questions such as:

- When is demand higher?
- How does demand vary across cities and hours?
- How do fares vary by ride type and distance?
- What patterns are associated with cancellations?
- How does driver availability relate to demand?
- How can current weather and traffic provide additional context?

MobilityLens brings these analytical questions together in an interactive application.

---

## 📊 Dataset Description

The project uses the **FairFare Ride Demand Dataset**, containing synthetic/generated mobility records across multiple Indian cities.

### Supported Cities

- Hyderabad
- Delhi
- Mumbai
- Bangalore
- Chennai

### Key Columns

| Column | Description |
|---|---|
| City | City of the ride |
| Date | Ride date |
| Day_of_Week | Day of the week |
| Ride_Distance_KM | Ride distance |
| Ride_Type | Economy, Premium, or Luxury |
| Weather | Historical weather category |
| Event | Historical event category |
| Available_Drivers | Number of available drivers |
| Demand_Level | Low, Medium, or High |
| Surge_Multiplier | Historical surge multiplier |
| Final_Fare | Final ride fare |
| Hour_of_Day | Hour of the ride |
| Cancellation_Rate | Historical cancellation rate |
| Demand_Score | Historical demand score |
| Driver_Availability | Driver availability measure |
| Traffic_Delay | Historical traffic delay |

> The FairFare dataset is synthetic/generated data and does not represent official Uber, Ola, or other ride-hailing operational statistics.

---

## 🛠️ Tools and Libraries

### Programming & Analytics

- Python
- Pandas
- NumPy
- SQL
- SQLite

### Visualization & Application

- Streamlit
- Altair

### APIs

- Open-Meteo
- TomTom Traffic API

### Generative AI

- Google Gemini API

### Development

- Git
- GitHub
- Cursor

---

## 🔄 Project Workflow

    FairFare Dataset
           ↓
    Data Processing
           ↓
    SQLite Database
           ↓
    SQL Analysis
           ↓
    Python Processing
           ↓
    Streamlit Application
           ↓
    APIs + Current Context
           ↓
    Gemini Generative AI
           ↓
    Business Insights

---

## 📱 Application Pages

### 🏠 Home

Provides an overview of the selected mobility context.

Includes:

- Current approximate city context
- Historical mobility records
- KPI metrics
- Demand levels
- Weather mix
- Zone comparison
- Ride-type analysis
- Current weather
- Optional traffic context

### 🇮🇳 India Explorer

Allows users to explore supported Indian cities and demonstration zones.

Users can examine historical mobility information for different locations.

### 📈 Demand Patterns

Analyzes historical demand by:

- City
- Hour
- Ride type
- Demand level
- Driver availability

### 💰 Historical Earnings

Explores historical fare and earnings-related patterns using:

- Ride distance
- Ride type
- Fare
- Historical mobility records

### ❌ Cancellations

Analyzes historical cancellation behavior and related mobility factors.

### 🤖 AI Assistant

The AI Assistant allows users to ask natural-language questions about the historical dataset.

Example:

> What factors are associated with higher demand?

The application first calculates the relevant evidence using SQL and Python and then sends the calculated context to Gemini for explanation.

### AI Workflow

    User Question
          ↓
    SQL / Python Analysis
          ↓
    Calculated Evidence
          ↓
        Gemini
          ↓
    Natural-Language Explanation

The AI Assistant does not independently calculate the underlying metrics. SQL and Python calculate the evidence first, and Gemini explains the results.

The application is a **Generative AI application**, not an autonomous agentic AI system.

---

## 🔍 Key Insights

- Historical demand varies across cities and hours.
- Driver availability can be analyzed alongside demand.
- Fare behavior can be compared with ride distance and ride type.
- Cancellation patterns vary across historical mobility contexts.
- Weather and event categories can be analyzed alongside demand.
- Demand scores provide an additional measure of historical demand.
- Different ride types show different fare and distance patterns.
- Some selected places may use broader city-level historical context when place-specific records are limited.
- Current weather and traffic provide additional context but are not historical FairFare observations.
- Results represent patterns in synthetic/generated data and are not official operational statistics.

---

## 🌦️ API Integration

### Weather API

**Open-Meteo** is used to retrieve current weather information.

### Traffic API

**TomTom** is used to provide current traffic context where available.

### Location

Approximate current location can be used to determine the current city and provide relevant context.

---

## 🗄️ Database & SQL

SQLite is used as the local analytical database.

SQL is used for:

- Filtering
- Aggregation
- City analysis
- Hourly analysis
- Ride-type analysis
- Demand analysis
- Fare calculations
- Cancellation analysis
- Driver availability
- KPI calculations

---

## 💼 Business Impact

MobilityLens demonstrates how a Data Analyst can combine:

- SQL
- Python
- Pandas
- Data Visualization
- APIs
- Business Analysis
- Generative AI

to build an end-to-end analytics application.

The project moves from:

    Raw Mobility Data
           ↓
    Data Processing
           ↓
    Historical Analysis
           ↓
    Business Evidence
           ↓
    Interactive Exploration
           ↓
    Natural-Language Explanation

---

## 📸 Application Screenshots

### Home

![Home](Screenshots/home.png)

### India Explorer

![India Explorer](Screenshots/india-explorer.png)

### Demand Patterns

![Demand Patterns](Screenshots/demand-patterns.png)

### Historical Earnings

![Historical Earnings](Screenshots/historical-earnings.png)

### Cancellations

![Cancellations](Screenshots/cancellations.png)

### AI Assistant

![AI Assistant](Screenshots/ai-assistant.png)

---

## 📂 Project Structure

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

---

## ⚙️ Setup

### 1. Clone the Repository

    git clone https://github.com/avinashreddy-da/AI-Uber-Data-Analytics.git
    cd AI-Uber-Data-Analytics

### 2. Install Dependencies

    pip install -r requirements.txt

### 3. Configure API Keys

Create a `.env` file and add the required API keys:

    GEMINI_API_KEY=your_gemini_api_key
    TOMTOM_API_KEY=your_tomtom_api_key

### 4. Create the Database

    python create_database.py

### 5. Run the Application

    streamlit run main.py

---

## ⚠️ Limitations

- The FairFare dataset is synthetic/generated data.
- Historical results should not be interpreted as official Uber/Ola statistics.
- The application does not predict guaranteed future demand, fares, earnings, or cancellations.
- Demonstration zones are used to organize historical records and may not have place-specific data.
- Some locations may fall back to broader city-level historical context.
- Current weather and traffic are live contextual information and are not historical FairFare observations.
- API availability and quotas may affect live features and AI responses.

---

## 🧠 Skills Demonstrated

- Data Cleaning
- Exploratory Data Analysis
- SQL
- SQLite
- Python
- Pandas
- NumPy
- Data Visualization
- Streamlit
- API Integration
- Business Analysis
- Generative AI
- Git & GitHub
- Dashboard Development
- Natural-Language Analytics

---

## 📌 Key Takeaways

MobilityLens demonstrates an end-to-end Data Analytics workflow where historical mobility data is transformed into interactive business insights.

The project combines **SQL and Python for analytical evidence**, **APIs for current context**, and **Gemini Generative AI for natural-language explanations**.

---

## 👨‍💻 Author

**Avinash Reddy**

MSc Statistics — Pondicherry University

Aspiring Data Analyst

Skills: SQL | Python | Pandas | Excel | Power BI | Statistics | Business Analysis | Generative AI
