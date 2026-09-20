# Kaggle Dataset Explorer (Streamlit App)

A lightweight, interactive Streamlit application to explore datasets (e.g., from Kaggle).

## Features
- **Auto-detection**: Automatically finds any `.csv` files stored in `data/`.
- **Drag & Drop**: Direct CSV file uploader in the sidebar.
- **Dataset Metrics**: Instant summary of total rows, columns, missing values, and memory footprint.
- **Data Preview**: Interactive preview of the first 20 rows.
- **Schema Inspector**: Complete breakdown of column names, data types, and null value percentages.
- **Statistical Summary**: Comprehensive `df.describe()` summary for numerical and categorical features.

## Setup Instructions

### 1. Create and Activate a Virtual Environment
```bash
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Add Your Kaggle Dataset
Paste your downloaded Kaggle CSV file into the `data/` directory:
```
data/
  your_dataset.csv
```

### 4. Run the Streamlit Application
```bash
streamlit run main.py
```
