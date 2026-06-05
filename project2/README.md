# Project 2 — Tariff Tensions, Narrative Divides

An interactive media-intelligence dashboard analysing how Western and Chinese media
constructed asymmetric narratives during the 2025 US–China tariff escalation.

**Data source:** GDELT v2 · **Window:** Feb 1 – Apr 30, 2025 · **Dashboard:** Python Shiny

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the dashboard
python main.py
# → Opens at http://127.0.0.1:8004

# Custom port
python main.py --port 8005 --reload
```

---

## Repository Structure

```
project2/
├── shiny_app/              # Main dashboard (Python Shiny)
│   ├── app.py              # Entry point
│   ├── components/         # UI components (charts, chatbot, layout)
│   ├── utils/              # Data loading, transforms, text analysis
│   └── static/             # CSS, images, word cloud PNG
│
├── data/                   # Precomputed data (ready to use)
│   ├── gdelt_events_cleaned.parquet
│   ├── daily_aggregates.parquet
│   ├── weekly_aggregates.parquet
│   ├── tone_gap_series.parquet
│   └── url_text_cache.parquet
│
├── forecasting/            # Forecast models and outputs
│   ├── forecast_models.py  # ARIMA, Holt-Winters, Prophet, TimesFM
│   ├── output/             # forecast_metrics.csv, forecast_predictions.csv
│   └── images/             # Forecast plot PNGs
│
├── scripts/                # Data pipeline scripts
│   ├── data_collection.py  # GDELT BigQuery ETL
│   ├── url_scraper.py      # Article headline scraper
│   └── setup_bigquery.py   # BigQuery credential check
│
├── docs/                   # Documentation
│   ├── forecast_report.md  # Forecasting methodology & results
│   └── timesfm_setup.md    # TimesFM environment setup guide
│
├── main.py                 # Dashboard launcher
├── requirements.txt        # Dashboard + pipeline dependencies (sectioned)
├── requirements-model.txt  # Prophet venv dependencies
└── .env.example            # Environment variable template
```

---

## Data

Precomputed data is stored in `data/` and committed to the repo — no BigQuery access needed for running the dashboard.

To regenerate data from BigQuery:
```bash
python scripts/setup_bigquery.py     # verify credentials
python scripts/data_collection.py    # run ETL pipeline
```

To regenerate forecast outputs:
```bash
python forecasting/forecast_models.py
# Writes to forecasting/output/ and forecasting/images/
```

---

## Dashboard Sections

| Section | Description |
|---------|-------------|
| 01 Conflict Timeline | Daily event volume by media group; annotated peak spikes |
| 02 Narrative Spread | Globe and flat world map of event geography; source-domain table |
| 03 Emotional Divergence | ToneGap time series; tone violin; tone-vs-coverage bubble chart |
| 04 Keyword Framing | Contrastive TF-IDF word cloud and diverging bar chart |
| 05 Narrative Gap Forecasting | ARIMA / Holt-Winters / Prophet / TimesFM on 14-day holdout |
| Narrative Assistant | Floating AI chatbot for data-driven narrative queries |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
DEEPSEEK_API_KEY=your-key          # optional, for chatbot
```

---

For detailed setup (Prophet venv, TimesFM, chatbot config), see `shiny_app/README.md`.
