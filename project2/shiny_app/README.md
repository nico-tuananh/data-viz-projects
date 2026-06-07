# Project 2 — Python Shiny Dashboard

**Tariff Tensions, Narrative Divides**  
An interactive media-intelligence dashboard analysing how Western and Chinese media
constructed asymmetric narratives during the 2025 US–China tariff escalation.

Data source: GDELT v2 · Window: Feb 1 – Apr 30, 2025

---

## Table of Contents

1. [Project structure](#1-project-structure)
2. [Prerequisites](#2-prerequisites)
3. [Environment setup](#3-environment-setup)
4. [Data — precomputed files (quick start)](#4-data--precomputed-files-quick-start)
5. [Regenerate ETL data from BigQuery](#5-regenerate-etl-data-from-bigquery)
6. [Regenerate forecast outputs](#6-regenerate-forecast-outputs)
   - [ARIMA & Holt-Winters](#61-arima--holt-winters)
   - [Prophet (separate venv)](#62-prophet-separate-venv)
   - [TimesFM (separate repo + venv)](#63-timesfm-separate-repo--venv)
   - [Run the full forecasting script](#64-run-the-full-forecasting-script)
7. [Configure the Narrative Assistant chatbot](#7-configure-the-narrative-assistant-chatbot)
8. [Run the Shiny dashboard](#8-run-the-shiny-dashboard)
9. [Dashboard sections](#9-dashboard-sections)
10. [Sidebar controls](#10-sidebar-controls)
11. [Known limitations](#11-known-limitations)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. Project structure

```
project2/
├── shiny_app/               ← Python Shiny dashboard (primary)
│   ├── app.py               ← main Shiny app (UI + server)
│   ├── components/
│   │   ├── charts.py        ← all Plotly chart builders
│   │   ├── chatbot.py       ← Narrative Assistant UI
│   │   └── layout.py        ← reusable UI fragments
│   ├── utils/
│   │   ├── constants.py     ← colour palette, theme styles
│   │   ├── dashboard_context.py ← context builder for the chatbot
│   │   ├── data.py          ← data loading & filtering
│   │   ├── deepseek_client.py   ← DeepSeek API client
│   │   ├── text.py          ← TF-IDF / word cloud helpers
│   │   └── transforms.py    ← aggregation helpers
│   └── static/
│       ├── styles.css
│       ├── US-China-trade-war-web2.jpg   ← hero image
│       └── VinUni_logo.png               ← sidebar footer logo
│
├── data/                    ← precomputed parquet/CSV files
│   ├── gdelt_events_cleaned.parquet
│   ├── daily_aggregates.parquet
│   ├── weekly_aggregates.parquet
│   ├── tone_gap_series.parquet
│   └── url_text_cache.parquet
│
├── forecasting/             ← forecast models and outputs
│   ├── forecast_models.py   ← ARIMA, Holt-Winters, Prophet, TimesFM
│   ├── output/
│   │   ├── forecast_metrics.csv
│   │   ├── forecast_predictions.csv
│   │   └── forecast_summary.txt
│   └── images/              ← forecast plot PNGs
│
├── scripts/                 ← data pipeline scripts
│   ├── data_collection.py   ← GDELT BigQuery ETL
│   ├── url_scraper.py       ← article headline scraper
│   └── setup_bigquery.py    ← BigQuery credential check
│
├── docs/                    ← documentation
│   ├── forecast_report.md   ← forecasting methodology & results
│   ├── timesfm_setup.md     ← TimesFM environment setup guide
│   └── DATA_PIPELINE.md     ← GDELT ETL pipeline walkthrough
│
├── main.py                  ← dashboard launcher
├── requirements.txt         ← dependencies (dashboard + pipeline)
├── requirements-deploy.txt  ← lightweight dependencies for shinyapps.io deployment
├── requirements-model.txt   ← Prophet venv dependencies
└── .env.example             ← environment variable template
```

---

## 2. Prerequisites

| Tool | Minimum version | Notes |
|---|---|---|
| Python | 3.11+ | 3.12 recommended |
| pip | any recent | comes with Python |
| uv | any | only needed for TimesFM venv |
| Git | any | to clone TimesFM repo |
| Google Cloud SDK | any | only if re-running ETL |

---

## 3. Environment setup

### 3a. Create and activate a virtual environment

```bash
cd project2
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3b. Install dashboard dependencies

```bash
pip install -r requirements.txt
```

This installs everything needed to run the dashboard:
`shiny`, `shinywidgets`, `plotly`, `pandas`, `pyarrow`, `matplotlib`, `wordcloud`,
`statsmodels`, `scikit-learn` (for ARIMA/Holt-Winters regeneration),
and optional pipeline deps (`google-cloud-bigquery`, `beautifulsoup4`).

> **Note:** Prophet and TimesFM each require a separate environment.
> See sections 6.2 and 6.3. You do **not** need them to run the dashboard —
> precomputed forecast outputs are already committed to the repo.

---

## 4. Data — precomputed files (quick start)

All precomputed data files are already committed to the repository under `data/`
and `forecasting/output/`. **Skip sections 5 and 6 if you just want to run the dashboard.**

```
data/
├── gdelt_events_cleaned.parquet    ← 23,654 GDELT events (Feb–Apr 2025)
├── daily_aggregates.parquet        ← daily event counts by media group
├── weekly_aggregates.parquet       ← weekly aggregates by country
├── tone_gap_series.parquet         ← daily ToneGap time series (89 days)
└── url_text_cache.parquet          ← scraped article titles & snippets

forecasting/output/
├── forecast_metrics.csv            ← MAE/RMSE for ARIMA, Holt-Winters, Prophet, TimesFM
└── forecast_predictions.csv        ← 14-day holdout predictions per model
```

CSV fallbacks exist alongside the parquet files for compatibility.

---

## 5. Regenerate ETL data from BigQuery

> Only needed if you want fresh GDELT data.
> Requires a Google Cloud project with BigQuery access and a service account key.

### 5a. Create a `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```dotenv
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
DEEPSEEK_API_KEY=sk-your_deepseek_key     # for the chatbot
```

### 5b. Verify BigQuery setup

```bash
python scripts/setup_bigquery.py
```

### 5c. Run the ETL pipeline

```bash
python scripts/data_collection.py
```

This queries GDELT v2 from BigQuery, filters US–China tariff events (Feb–Apr 2025),
enriches with scraped article text, labels media groups, computes aggregates,
and writes all output files to `data/`.

Restart the Shiny app after regenerating data (it loads files at startup).

---

## 6. Regenerate forecast outputs

The forecasting script runs four models and writes results to `forecasting/output/`.
ARIMA and Holt-Winters run in the main `.venv`.
Prophet and TimesFM each need a dedicated environment.

### 6.1 ARIMA & Holt-Winters

No extra setup — these use `statsmodels` already installed in `.venv`.

### 6.2 Prophet (separate venv)

Prophet conflicts with some packages, so it lives in its own environment.

```bash
cd project2
python3 -m venv .venv-prophet
source .venv-prophet/bin/activate
pip install -r requirements-model.txt
deactivate
```

The forecasting script auto-detects `.venv-prophet/bin/python` and delegates
the Prophet run to it via subprocess.

### 6.3 TimesFM (separate repo + venv)

TimesFM requires its own repository cloned as a sibling of `project2/`:

```
data-viz-projects/
├── project2/          ← this repo
└── timesfm/           ← clone here
```

#### Clone and set up TimesFM

```bash
cd ..                  # move up to data-viz-projects/
git clone https://github.com/google-research/timesfm.git
cd timesfm

pip install uv
uv venv
source .venv/bin/activate
uv pip install -e ".[torch]"
deactivate
```

#### Download the model weights

The weights are fetched automatically from Hugging Face on the first run.
Checkpoint used: `google/timesfm-2.5-200m-pytorch` (~800 MB, cached in `~/.cache/huggingface/`).

### 6.4 Run the full forecasting script

With both `.venv-prophet` and `../timesfm/.venv` set up, run from `project2/`:

```bash
source .venv/bin/activate
python forecasting/forecast_models.py
```

The script:
- Fits ARIMA (AIC-selected order) and Holt-Winters in-process
- Spawns a subprocess using `.venv-prophet/bin/python` for Prophet
- Spawns a subprocess using `../timesfm/.venv/bin/python` for TimesFM
- Evaluates all four models on a 14-day holdout (Apr 17–30, 2025)
- Writes `forecasting/output/forecast_metrics.csv` and `forecasting/output/forecast_predictions.csv`
- Saves forecast plots to `forecasting/images/`

---

## 7. Configure the Narrative Assistant chatbot

The built-in chatbot answers questions about the dashboard using DeepSeek.

### 7a. Get a DeepSeek API key

Sign up at [https://platform.deepseek.com](https://platform.deepseek.com) and create an API key.

### 7b. Add the key to `.env`

```bash
# In project2/.env
DEEPSEEK_API_KEY=sk-your_actual_key_here
```

> **Security:** `.env` is in `.gitignore` and must never be committed.

### 7c. What the chatbot can answer

**Without API key** (instant, local answers):
- Explain ToneGap, map, keyword framing, forecast models
- Dataset limitations and GDELT methodology
- MAE / RMSE definitions
- Western vs Chinese media group definitions

**With API key** (uses DeepSeek with current dashboard context):
- Summarize current filtered view
- Compare Western vs Chinese tone in the active date range
- Any open-ended analytical question about the data

If `DEEPSEEK_API_KEY` is missing, the chatbot shows a friendly message instead of crashing.

---

## 8. Run the Shiny dashboard

From `project2/`:

```bash
source .venv/bin/activate
python main.py
# → opens at http://127.0.0.1:8004
```

Or with a custom port:

```bash
python main.py --port 8005 --reload
```

Alternatively, run Shiny directly:

```bash
shiny run shiny_app/app.py --host 127.0.0.1 --port 8004
```

---

## 9. Dashboard sections

| # | Section | What it shows |
|---|---|---|
| 1 | **Conflict Timeline** | Daily event volume by media group; annotated peak spikes; hover for date-level detail |
| 2 | **Narrative Spread** | Globe (US–China Pacific focus) and flat world map; marker = event location, colour = media group, size = article volume; searchable source-domain table |
| 3 | **Emotional Divergence** | ToneGap time series; tone distribution violin/box; tone-vs-coverage bubble chart |
| 4 | **Keyword Framing** | Contrastive TF-IDF word cloud; diverging bar chart; ranked framing term cards |
| 5 | **Narrative Gap Forecasting** | ARIMA, Holt-Winters, Prophet, TimesFM evaluated on 14-day holdout; metric cards; actual-vs-predicted chart |

**ToneGap** = Western weighted tone − Chinese weighted tone.  
Positive → Western coverage is more positive than Chinese; negative → opposite.

---

## 10. Sidebar controls

| Control | Effect |
|---|---|
| Date range | Filters all event-level charts and the source table |
| Media groups | Show / hide Western, Chinese, Global/Other traces |
| Event direction | Filter events by direction: USA→CHN or CHN→USA |
| Theme | Dark (default) or Light |
| Map style | Globe or Flat World Map toggle (in-section, Section 2) |
| Keyword top-k | Number of TF-IDF terms shown in the framing bar chart (in-section, Section 4) |
| Forecast models | Toggle individual forecast model lines (in-section, Section 5) |
| Source top-N / search / sort | Filter the source-domain drilldown table (in-section, Section 2) |

> **Note:** The ToneGap chart (Section 3) is precomputed from all Western and Chinese
> events. The media-group and event-direction filters do not affect ToneGap — only the date range filter applies.

---

## 11. Known limitations

- **GDELT tone is machine-coded.** Values are noisy and should be treated as
  media-pattern signals, not ground-truth political sentiment.
- **Media group labels are domain-level.** Every article from a domain gets the
  same group label; mixed-ownership or multi-language outlets may be mis-assigned.
- **Article-text scraping is optional.** TF-IDF keyword framing depends on
  scraped `ArticleTitle` and `ArticleSnippet` fields. When scraping is sparse,
  framing terms are less stable.
- **Event geocoding can be imprecise.** GDELT geolocates events to the first
  geographic match in the article, which may not reflect the true location.
- **Forecast models use a fixed 14-day holdout.** Results are specific to
  Apr 17–30, 2025; different splits may rank models differently.
- **ToneGap is not media-group-filterable.** It is precomputed from all Western
  and Chinese events; the media-group sidebar filter applies to other charts only.
- **The map is Plotly `scattergeo`.** Interactive and rotatable but dense clusters
  may overlap at low zoom.

---

## 12. Troubleshooting

### `ModuleNotFoundError: No module named 'shinywidgets'`
```bash
pip install -r requirements.txt
```

### `Address already in use` on port 8004
```bash
lsof -ti :8004 | xargs kill -9
```

### Shiny app shows "Missing gdelt_events_cleaned data"
The parquet files are missing. Either pull the latest git changes (files are committed),
or run `python scripts/data_collection.py` (requires BigQuery credentials).

### Forecast chart is empty
`forecasting/output/forecast_predictions.csv` is missing. Run:
```bash
python forecasting/forecast_models.py
```

### TimesFM subprocess fails silently
- Confirm `../timesfm/.venv/bin/python` exists.
- Confirm Hugging Face cache: `~/.cache/huggingface/hub/models--google--timesfm-2.5-200m-pytorch/`

### Prophet subprocess fails
- Confirm `.venv-prophet/bin/python` exists.
- Check: `.venv-prophet/bin/pip show prophet`

### DeepSeek chatbot shows "API key not configured"
Add `DEEPSEEK_API_KEY=sk-...` to `project2/.env` and restart the app.

### Hero image not showing
Confirm `shiny_app/static/US-China-trade-war-web2.jpg` exists.
