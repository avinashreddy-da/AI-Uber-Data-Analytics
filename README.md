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

![Home](screenshots/home.png)

### 🇮🇳 India Explorer
Explore historical mobility information across supported Indian cities.

![India Explorer](screenshots/india-explorer.png)

### 📈 Demand Patterns
Analyze demand by city, hour, ride type and demand level.

![Demand Patterns](screenshots/demand-patterns.png)

### 💰 Historical Earnings
Explore historical fares, ride distance and ride-type patterns.

![Historical Earnings](screenshots/historical-earnings.png)

### ❌ Cancellations
Analyze historical cancellation rates and cancellation patterns.

![Cancellations](screenshots/cancellations.png)

### 🤖 AI Assistant
Ask natural-language questions about the historical mobility data.

![AI Assistant](screenshots/ai-assistant.png)

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
