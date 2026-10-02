# 🚕 MobilityLens — AI-Powered Mobility Analytics

MobilityLens is an interactive **Data Analytics application** built with Python, SQL, Streamlit, APIs, and Generative AI to help users understand historical ride-demand and mobility patterns.

The application analyzes the **FairFare synthetic/generated multi-city dataset** to explore demand, fares, cancellations, ride types, driver availability, and other mobility metrics across major Indian cities.

It also combines historical analytics with **current weather and traffic context** and uses **Google Gemini Generative AI** to explain calculated historical insights in natural language.

> **Important:** FairFare is synthetic/generated data created for analytical demonstration. It is not official Uber, Ola, or real-world operational data. Historical patterns should not be interpreted as guaranteed future outcomes.

---

## 📌 Business Problem

Ride-hailing platforms generate large amounts of data related to demand, fares, cancellations, ride types, driver availability, weather, and other operational factors.

However, raw mobility data can be difficult for users to explore and interpret.

The goal of MobilityLens is to provide an interactive way to:

- Understand historical ride-demand patterns
- Explore fare and ride-distance behavior
- Analyze cancellation patterns
- Compare cities and ride types
- Examine relationships between demand and operational factors
- Add current weather and traffic context
- Ask natural-language questions about the historical data

The application combines traditional Data Analytics with Generative AI to make the analysis easier to explore and understand.

---

## 🎯 Project Objective

The main objective of MobilityLens is to build an interactive mobility analytics application that combines:

- SQL-based historical analysis
- Python and Pandas data processing
- Interactive Streamlit dashboards
- Live API-based contextual information
- Generative AI for natural-language explanations

The project demonstrates how a Data Analyst can combine **data analysis, business understanding, APIs, and Generative AI** into an end-to-end analytics application.

---

## 🔍 What the Application Analyzes

MobilityLens focuses on several important mobility metrics:

- 🚕 Ride demand
- 💰 Final fare
- 📏 Ride distance
- ❌ Cancellation rate
- 🚗 Driver availability
- 📈 Demand score
- 🚘 Ride type
- 🌦️ Weather
- 🚦 Traffic context
- 📍 City and place context
- ⏰ Hourly demand patterns

---

# 📊 Application Pages

## 🏠 1. Home

The Home page provides a consolidated view of the selected mobility context.

It includes:

- Historical KPIs
- Booking and ride metrics
- Demand levels
- Average fare
- Average ride distance
- Cancellation metrics
- Historical weather patterns
- Current weather context
- Historical mobility information

### Screenshot

![MobilityLens Home](screenshots/home.png)

---

## 🇮🇳 2. India Explorer

The India Explorer allows users to explore mobility information across the supported cities.

Currently supported cities:

- Hyderabad
- Delhi
- Mumbai
- Bangalore
- Chennai

### Screenshot

![India Explorer](screenshots/india-explorer.png)

---

## 📈 3. Demand Patterns

This page focuses on historical demand behavior.

Users can explore demand patterns based on:

- City
- Hour
- Ride type
- Demand level

The analysis helps identify how demand varies across different time periods and mobility contexts.

### Screenshot

![Demand Patterns](screenshots/demand-patterns.png)

---

## 💰 4. Historical Earnings

This page analyzes historical fare and earnings-related information.

Users can explore:

- Historical fares
- Ride types
- Ride distance
- City-level differences
- Historical mobility patterns related to earnings

The analysis is based on historical records in the FairFare dataset and does not represent guaranteed future earnings.

### Screenshot

![Historical Earnings](screenshots/historical-earnings.png)

---

## ❌ 5. Cancellations

The Cancellations page analyzes historical cancellation behavior.

It helps explore:

- Cancellation rates
- Cancellation-related patterns
- Ride-type differences
- City-level patterns
- Historical operational context

### Screenshot

![Cancellations](screenshots/cancellations.png)

---

## 🤖 6. AI Assistant

The AI Assistant allows users to ask natural-language questions about the historical mobility data.

For example:

> **"Based on the historical data in this dataset, what factors are associated with higher demand?"**

The application first calculates relevant evidence using its SQL/Python analytics layer and then provides that evidence to Gemini.

Gemini converts the calculated evidence into a natural-language explanation.

### Screenshot

![AI Assistant](screenshots/ai-assistant.png)

---

# 🔄 Project Workflow

The application follows a **data-first analytics workflow**:

```text
FairFare Dataset
       ↓
SQLite Database
       ↓
SQL Historical Analysis
       ↓
Python / Pandas Processing
       ↓
Current API Context
       ↓
Streamlit Application
       ↓
Gemini Generative AI
       ↓
Natural-Language Explanation
