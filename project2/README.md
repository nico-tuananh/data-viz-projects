# Project 2 — Tariff Tensions, Narrative Divides

An interactive media-intelligence dashboard analysing how Western and Chinese media
constructed asymmetric emotional narratives during the 2025 US–China tariff escalation.

**Research question:** Do media systems merely report tariff escalation, or do they construct
different emotional narratives around the same conflict?

**Data source:** GDELT v2 · **Dataset window:** Feb 1 – Apr 30, 2025 · **Stack:** Python Shiny

---

## Live App

**[https://lnbphuong.shinyapps.io/tariff-tensions/](https://lnbphuong.shinyapps.io/tariff-tensions/)**

---

## Dashboard Features

| Section | Description |
|---|---|
| 01 · Conflict Timeline | Daily event volume by media group; annotated peak spikes |
| 02 · Narrative Spread | Pacific globe + flat world map of GDELT event geography; source-domain table |
| 03 · Emotional Divergence | ToneGap time series; tone violin; tone-vs-coverage bubble chart |
| 04 · Keyword Framing | Contrastive TF-IDF word cloud and ranked diverging bar chart |
| 05 · Narrative Gap Forecasting | ARIMA / Holt-Winters / Prophet / TimesFM evaluated on a 14-day holdout |
| Narrative Assistant | Optional floating AI chatbot powered by DeepSeek (requires API key) |

All charts respond to the sidebar's **date range**, **media group**, and **event direction** filters in real time. (Exception: the ToneGap time series in Section 03 is precomputed from all Western and Chinese events — only the date range filter applies to it.)

---

## About the Data

This dashboard uses **GDELT v2 event data** filtered to US–China tariff-war coverage.

| Field | Meaning |
|---|---|
| One event row | One GDELT event record (a reported action between actors) |
| `SOURCEURL` | One associated source URL stored for that event row |
| `NumArticles` | Total article mentions related to that event (as reported by GDELT) |
| `NumSources` | Number of sources that reported the event (as reported by GDELT) |
| **Events KPI** | Count of event rows in the current filter |
| **Articles KPI** | Sum of `NumArticles` across filtered events |
| **Unique Sources KPI** | Count of distinct source domains extracted from `SOURCEURL` |
| **Western tone KPI** | Mean `AvgTone` across Western-labelled events in the current filter |
| **Chinese tone KPI** | Mean `AvgTone` across Chinese-labelled events in the current filter |
| **ToneGap** | Difference in average tone between Western and Chinese media — used for narrative divergence analysis |

Media group assignment is by outlet domain (Western / Chinese / Global-Other). Tone scores are
machine-coded by GDELT (scale −100 to +100) and are relative, not human-annotated.

---

## Repository Structure

```
project2/
├── shiny_app/              # Dashboard app (Python Shiny)
│   ├── app.py              # Shiny app object — entrypoint for deploy & shiny run
│   ├── components/         # UI components: charts, chatbot widget, layout helpers
│   ├── utils/              # Data loading, transforms, TF-IDF text analysis, DeepSeek client, colour constants
│   └── static/             # CSS, hero image, and VinUni logo
│
├── data/                   # Precomputed datasets (committed — no BigQuery needed to run)
│   ├── gdelt_events_cleaned.parquet
│   ├── daily_aggregates.parquet
│   ├── weekly_aggregates.parquet
│   ├── tone_gap_series.parquet
│   └── url_text_cache.parquet
│
├── forecasting/            # Forecast models and precomputed outputs
│   ├── forecast_models.py
│   ├── output/             # forecast_metrics.csv, forecast_predictions.csv, forecast_summary.txt
│   └── images/             # Model forecast plots (ARIMA, Holt-Winters, Prophet, TimesFM)
│
├── scripts/                # Data collection and preprocessing (not needed to run the dashboard)
│   ├── data_collection.py  # GDELT BigQuery ETL pipeline
│   ├── url_scraper.py      # Article headline scraper
│   └── setup_bigquery.py   # BigQuery credential check
│
├── docs/                   # Reports and setup notes
│   ├── forecast_report.md  # Forecasting methodology & results
│   ├── timesfm_setup.md    # TimesFM environment setup guide
│   └── DATA_PIPELINE.md    # GDELT ETL pipeline walkthrough
│
├── main.py                 # Dashboard launcher (runs shiny_app/app.py via subprocess)
├── requirements.txt        # Full local environment (dashboard + pipeline + models)
├── requirements-deploy.txt # Lightweight dependencies for shinyapps.io deployment
├── requirements-model.txt  # Prophet venv dependencies
└── .env.example            # Environment variable template (safe to commit)
```

---

## Local Setup

```bash
# 1. Navigate to project root
cd project2

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Set up the AI chatbot
cp .env.example .env
# Edit .env and add your DeepSeek key:
#   DEEPSEEK_API_KEY=<your-key-here>
# The dashboard runs fully without this — the chatbot shows a friendly fallback if the key is missing.

# 5. Launch the dashboard  →  http://127.0.0.1:8004


# Custom port or auto-reload
python main.py --port 8005 --reload
```

Alternatively, run directly with Shiny:

```bash
shiny run shiny_app/app.py --port 8004
```

---

## DeepSeek Chatbot (Optional)

The Narrative Assistant chatbot is entirely optional. The dashboard is fully functional without it.

- Copy `.env.example` to `.env` and add your `DEEPSEEK_API_KEY`.
- **Never commit `.env`** — it is listed in `.gitignore`.
- If the key is absent or invalid, the chatbot panel shows a graceful fallback message and all other dashboard features continue to work.
- For deployment, set `DEEPSEEK_API_KEY` as a secure environment variable in the shinyapps.io dashboard (Settings → Environment Variables).

---

## Data Pipeline (optional — not needed to run the dashboard)

Precomputed data in `data/` and `forecasting/output/` are committed to the repo. To regenerate from scratch:

```bash
# Verify BigQuery credentials
python scripts/setup_bigquery.py

# Collect and preprocess GDELT data
python scripts/data_collection.py

# Re-run forecast models
python forecasting/forecast_models.py
# Writes to forecasting/output/ and forecasting/images/
```

---

## Deployment

The app is deployed on [shinyapps.io](https://lnbphuong.shinyapps.io/tariff-tensions/).
`main.py` is the deployment entrypoint. Precomputed data and forecast outputs are bundled with
the deployment; no live data fetching is required at runtime.

To redeploy:

```bash
rsconnect deploy shiny . \
  --name lnbphuong \
  --title "tariff-tensions" \
  --requirements-file requirements-deploy.txt \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".env" \
  --exclude "*.pyc" \
  --exclude "scripts/" \
  --exclude "requirements-model.txt"
```

`.env` is explicitly excluded so no secrets are uploaded. The `DEEPSEEK_API_KEY` is configured
separately as a secure environment variable in the shinyapps.io dashboard.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DEEPSEEK_API_KEY` | Optional | DeepSeek API key for the Narrative Assistant chatbot |

Copy `.env.example` to `.env` locally. **Never commit `.env`.**

---

## Reproducibility

- All data required to run the dashboard is precomputed and committed under `data/`.
- Forecast outputs are precomputed and committed under `forecasting/output/`.
- No BigQuery access or internet connection is needed to run the dashboard locally.
- The data pipeline scripts (`scripts/`) are provided for full reproducibility but are not part of the normal run flow.

For detailed setup notes (Prophet venv, TimesFM, forecasting methodology), see `docs/`. For a full walkthrough of the GDELT ETL pipeline, see [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md).

---

## Team & Task Allocation

This project was a collaborative effort across research design, data engineering, visualisation, and deployment.

| Team Member | Contributions |
|---|---|
| **Le Ngoc Bich Phuong** | Defined the research question and analytical framing; designed the storytelling flow and chart logic. Implemented contrastive TF-IDF keyword framing and the word cloud pipeline. Improved user-facing guidance, interaction notes, and overall dashboard usability. Deployed the final Shiny app and contributed to the report. |
| **Nguyen The An** | Ran forecasting models including ARIMA, Holt-Winters, Prophet, and TimesFM; evaluated results using MAE and RMSE. Built the initial Shiny interface and local execution workflow. Implemented the AI Narrative Assistant chatbot and contributed to the presentation slides and report. |
| **Phan Nguyen Tuan Anh** | Queried, filtered, and cleaned the GDELT data using BigQuery. Generated the event-level, daily, weekly, source, and ToneGap aggregate datasets used across the dashboard. Supported refinement of the word cloud data pipeline and contributed to the report. |
| **Luong Tran Sang** | Built the main dashboard layout and integrated the visual sections into a coherent Shiny app. Implemented and polished the core dashboard graphs, including timeline, map, tone divergence, distribution, and coverage-intensity views. Helped finalize the dashboard concept and contributed to the report. |

All components were iteratively reviewed and integrated as a team, with each member contributing across multiple areas throughout the project.
