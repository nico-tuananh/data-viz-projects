<h1 align="center">Project Work for COMP4010 Data Visualization</h1>

<p align="center">
    This repository contains project work for COMP4010 (Data Visualization) course, Spring 2026 semester. It includes two major projects exploring different aspects of data visualization techniques, including data analysis, interactive visualizations, and visual storytelling.
</p>

---

### Team Members
- Group 15: Le Ngoc Bich Phuong, Nguyen The An
- Group 22: Phan Nguyen Tuan Anh, Luong Tran Sang

---

# Project 1: Interactive Dashboard

## Specifications

### Project Overview

This project is an interactive data visualization dashboard built with the Palmer Penguins dataset. It explores penguin species through habitat distribution, physical measurement comparisons, and machine learning-based pattern discovery.

### What the Dashboard Shows

- Species distribution across islands
- Physical differences in bill size, flipper length, and body mass
- Interactive filtering by species, island, and sex
- Text-based narrative guidance for clearer storytelling
- PCA and K-Means clustering to compare unsupervised patterns with actual species groups

### Dataset

The dashboard uses the Palmer Penguins dataset, which contains penguin species, island, sex, and body measurement features.

### Project Goal

The goal of the project is to combine visual analysis, interactivity, and storytelling into a dashboard that helps users understand both the biological differences and the hidden structure within the penguin data.

## Running Instructions

### Requirements
- Python 3.10+ recommended

### 1) Install dependencies
Create and activate a virtual environment, then install packages:

```bash
python -m venv .venv
# Windows PowerShell
.\\.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt
```

### 2) Run the dashboard

```bash
python dashboard.py
```

Then open `http://127.0.0.1:8050/` in your browser.

### (Optional) Regenerate the processed dataset
If you want to export the cleaned dataset with derived features:

```bash
python preprocess.py
```

---

# Project 2: Data Stories: Building Interactive Dashboards with Python Shiny

## Data Collection and Preprocessing

### Step 1: GCP Setup

1. Create GCP project at https://console.cloud.google.com/projectcreate
   - Note your project ID (shown below project name, e.g., `comp4010-project-2`)
   - Or find existing project ID: click project dropdown → copy ID column

2. Enable BigQuery API at https://console.cloud.google.com/apis/library/bigquery.googleapis.com

3. Create service account at https://console.cloud.google.com/iam-admin/serviceaccounts
   - Name: `gdelt-reader`
   - Roles: `BigQuery Job User`, `BigQuery Data Viewer`
   - Create JSON key, download and store it to `project2/secrets/`

4. Create a `.env` file from the template:
```bash
cd project2
cp .env.example .env
```
   Then edit `.env` to match your JSON file name and actual GCP project ID.

### Step 2: Run Pipeline

Run the series of commands below:
```bash
cd project2
pip install -r requirements.txt
python setup_bigquery.py    # Verify GCP setup
python data_collection.py   # BigQuery + scrape headlines + save outputs
```

To scrape headlines onto existing data without re-querying BigQuery (~8–15 min):

```bash
python data_collection.py --scrape-only
```

### Step 3: Output Files

The pipeline produces four dashboard-ready datasets in `project2/data/`:

| File | Description |
|------|-------------|
| `gdelt_events_cleaned.parquet/csv` | Full cleaned event data with media group labels, event direction, tone categories |
| `daily_aggregates.parquet/csv` | Daily metrics by media group (event counts, article totals, weighted tone) |
| `weekly_aggregates.parquet/csv` | Weekly geo-aggregates by country for map visualizations |
| `tone_gap_series.parquet/csv` | Daily ToneGap (Western − Chinese) for forecasting models |

Key fields in the cleaned dataset:
- `Date`, `DateStr`, `WeekStr` — Standardized date fields
- `MediaGroup` — Western, Chinese, or Global/Other
- `EventDirection` — USA→CHN or CHN→USA
- `AvgTone`, `GoldsteinScale` — Sentiment metrics
- `NumArticles`, `NumMentions` — Coverage intensity
- `SourceDomain` — Extracted source domain for analysis
- `ArticleTitle`, `ArticleSnippet` — Scraped from `SOURCEURL` (for word clouds)


### Step 4: Run the Application (FastAPI & React)

After completing the data collection pipeline, start the backend and frontend servers:

#### 1) Run the Backend (FastAPI)
Navigate to the `project2` directory, activate the virtual environment, and launch the Uvicorn server:
```bash
cd project2
source .venv/bin/activate
PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8002 --reload
```
The backend API will start on port `8002`. You can check the server health status at `http://localhost:8002/api/health`.

#### 2) Run the Frontend (React + Vite)
Open a new terminal window, navigate to the frontend directory, install dependencies, and start the dev server:
```bash
cd project2/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```
The frontend dev server will launch on port `5173`. Open `http://localhost:5173/` in your browser to view the dashboard.
