# 🚕 MobilityLens — AI-Powered Mobility Analytics

## 📌 Introduction

MobilityLens is an interactive **Data Analytics application** built using SQL, Python, Pandas, Streamlit, APIs and Generative AI to analyze historical ride-demand and mobility patterns.

The project focuses on:

### • 🚕 Ride Demand
### • 💰 Fare & Ride Distance
### • ❌ Cancellation Patterns
### • 🚗 Driver Availability
### • 🚘 Ride Types
### • 🌦️ Weather
### • 🚦 Traffic Context
### • ⏰ Hourly Demand

The application includes:

### • 🏠 Home
### • 🇮🇳 India Explorer
### • 📈 Demand Patterns
### • 💰 Historical Earnings
### • ❌ Cancellations
### • 🤖 AI Assistant

The project combines traditional Data Analytics with Generative AI to help users explore historical mobility data and understand analytical results through natural-language explanations.

> **Important:** FairFare is synthetic/generated data created for analytical demonstration. It is not official Uber, Ola or real-world operational data.

---

## 🎯 Project Objective

The main objective is to analyze historical mobility patterns and build an interactive analytics application that combines SQL, Python, APIs and Generative AI.

This project aims to:

- 📊 Analyze historical demand patterns
- 💰 Analyze fare and distance behavior
- ❌ Analyze cancellation patterns
- 🚗 Examine driver availability
- 🚘 Compare ride types
- 🌦️ Add current weather context
- 🚦 Add traffic context
- 🤖 Answer natural-language questions about historical data
- 📈 Present insights through an interactive Streamlit application

---

## 🏦 Business Problem

Ride-hailing platforms generate large amounts of data related to demand, fares, cancellations, driver availability, weather and traffic.

The challenge is converting this raw mobility data into understandable business insights.

MobilityLens provides an interactive way to explore:

- Demand by city and hour
- Fare and distance patterns
- Cancellation behavior
- Driver availability
- Ride-type differences
- Weather and event associations
- Historical mobility patterns

---

## 📂 Dataset Description

The project uses the **FairFare synthetic/generated multi-city ride-demand dataset**.

### 📌 Key Columns

| Column | Description |
|---|---|
| `City` | City |
| `Date` | Date |
| `Ride_Distance_KM` | Ride distance |
| `Ride_Type` | Ride type |
| `Weather` | Weather condition |
| `Event` | Event category |
| `Available_Drivers` | Available drivers |
| `Demand_Level` | Demand category |
| `Surge_Multiplier` | Surge multiplier |
| `Final_Fare` | Final fare |
| `Hour_of_Day` | Hour |
| `Cancellation_Rate` | Cancellation rate |
| `Demand_Score` | Demand score |
| `Driver_Availability` | Driver availability |
| `Traffic_Delay` | Traffic delay |

### 📍 Supported Cities

- Hyderabad
- Delhi
- Mumbai
- Bangalore
- Chennai

---

## 🛠 Tools and Technologies Used

### 💻 Programming & Query Languages

- Python
- SQL

### 📊 Data Analysis

- Pandas
- NumPy
- SQLite

### 📈 Application & Visualization

- Streamlit
- Altair

### 🌐 APIs

- Open-Meteo Weather API
- TomTom Traffic API
- Requests

### 🤖 Generative AI

- Google Gemini
- Google GenAI SDK

---

## 🔄 Project Workflow

### 1. Data Loading

- Loaded FairFare dataset
- Explored historical mobility data

### 2. Database Creation

- Stored data in SQLite
- Created database using Python and Pandas

### 3. SQL Analysis

- Historical KPIs
- City analysis
- Hourly demand
- Ride-type analysis
- Fare analysis
- Cancellation analysis
- Driver availability

### 4. Python / Pandas

- Data processing
- Transformations
- Location processing
- API integration
- Application logic

### 5. Streamlit Application

- Built interactive mobility analytics pages
- Added historical KPIs and visualizations
- Added live weather and traffic context

### 6. Generative AI

- User asks a natural-language question
- SQL/Python calculates relevant historical evidence
- Evidence is provided to Gemini
- Gemini generates a natural-language explanation

---

## 📊 Application Pages

### 🏠 Home

Historical KPIs, demand, fare, distance, cancellation, weather and current mobility context.

![Home](Screenshots/home.png)

### 🇮🇳 India Explorer

Explore historical mobility information across supported Indian cities.

![India Explorer](Screenshots/india-explorer.png)

### 📈 Demand Patterns

Analyze demand by city, hour, ride type and demand level.

![Demand Patterns](Screenshots/demand-patterns.png)

### 💰 Historical Earnings

Explore historical fares, ride distance and ride-type patterns.

![Historical Earnings](Screenshots/historical-earnings.png)

### ❌ Cancellations

Analyze historical cancellation rates and cancellation patterns.

![Cancellations](Screenshots/cancellations.png)

### 🤖 AI Assistant

Ask natural-language questions about the historical mobility data.

![AI Assistant](Screenshots/ai-assistant.png)

---

## 🤖 AI Assistant

The AI Assistant uses **Google Gemini Generative AI** as an explanation layer.

Example:

> "Based on the historical data in this dataset, what factors are associated with higher demand?"

The workflow is:

```text
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

Open-Meteo is used to retrieve current weather information.

### Traffic API

TomTom is used to provide current traffic context where available.

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

```text
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
```

---

## 📂 Project Structure

```text
MobilityLens/
│
├── main.py
├── database.py
├── create_database.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── screenshots/
│   ├── home.png
│   ├── india-explorer.png
│   ├── demand-patterns.png
│   ├── historical-earnings.png
│   ├── cancellations.png
│   └── ai-assistant.png
│
└── data/
    └── README.md
```

### Main Files

**`main.py`** — Streamlit application, analytics workflow, APIs, location processing and Gemini integration.

**`database.py`** — SQLite database and SQL analytical queries.

**`create_database.py`** — Creates the SQLite database from the FairFare dataset.

**`requirements.txt`** — Python dependencies.

---

## ⚙️ Setup

### 1. Clone Repository

```bash
git clone https://github.com/avinashreddy-da/AI-Uber-Data-Analytics.git
cd AI-Uber-Data-Analytics
```

### 2. Create Virtual Environment

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Keys

Create `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key
TOMTOM_API_KEY=your_tomtom_api_key
```

Do not commit API keys to GitHub.

### 5. Add Dataset

Place the required files inside the `data/` folder:

```text
data/fairfare_ride_demand_dataset.csv
data/mobilitylens_zones.csv
```

### 6. Create Database

```bash
python create_database.py
```

### 7. Run Application

```bash
streamlit run main.py
```

---

## ⚠️ Limitations

- FairFare is synthetic/generated data.
- It is not official Uber or Ola operational data.
- Historical results depend on available records.
- The dataset covers selected Indian cities.
- Some places may use broader city-level historical context.
- Weather and traffic APIs provide current context, not historical observations.
- Historical patterns do not guarantee future demand, fares, earnings or cancellations.
- Gemini provides analytical explanations and should not be treated as an authoritative prediction.
- MobilityLens is a portfolio/demo analytics application, not a production ride-hailing platform.

---

## 🎓 Skills Demonstrated

- SQL
- Python
- Pandas
- NumPy
- SQLite
- Data Analysis
- Business Analysis
- Data Visualization
- Streamlit
- API Integration
- Generative AI
- Google Gemini
- Natural-Language Analytics
- End-to-End Analytics Application Development

---

## 📌 Key Takeaways

- MobilityLens combines Data Analytics with Generative AI.
- SQL and Python calculate the underlying historical evidence.
- Streamlit provides the interactive analytics interface.
- APIs provide current weather and traffic context.
- Gemini converts calculated evidence into natural-language explanations.
- The project demonstrates practical integration of SQL, Python, APIs and Generative AI in a Data Analyst portfolio project.
- The FairFare dataset is synthetic/generated and intended for analytical demonstration.

---

## 👤 Author

**Avinash Reddy**

MSc Statistics — Pondicherry University

**Data Analyst | SQL | Python | Power BI | Excel | Statistics**

This project is part of my Data Analyst portfolio, demonstrating how SQL, Python, APIs, Streamlit and Generative AI can be combined to build an interactive, business-focused mobility analytics application.
Gemini
      ↓
Natural-Language Explanation
