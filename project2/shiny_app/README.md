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
11. [React/FastAPI reference dashboard (optional)](#11-reactfastapi-reference-dashboard-optional)
12. [Known limitations](#12-known-limitations)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Project structure

```
project2/
├── shiny_app/               ← Python Shiny dashboard (primary target)
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
│       └── phrase_word_cloud.png         ← keyword framing image
│
├── backend/                 ← FastAPI backend (React reference app)
│   ├── data/                ← precomputed parquet/CSV files (primary data dir)
│   └── main.py
│
├── data/                    ← fallback data dir (used if backend/data/ missing)
├── model/
│   ├── forecast_models.py   ← ARIMA, Holt-Winters, Prophet, TimesFM
│   ├── output/
│   │   ├── forecast_metrics.csv
│   │   └── forecast_predictions.csv
│   └── timesfm_setup.md
│
├── data_collection.py       ← BigQuery ETL pipeline
├── requirements.txt
├── .env.example             ← template for secrets
└── .env                     ← your actual secrets (NOT committed)
```

The Shiny app reads data from `backend/data/` first, falling back to `data/`.
Both directories already contain precomputed files so the dashboard works
**without running any ETL or model scripts**.

---

## 2. Prerequisites

| Tool | Minimum version | Notes |
|---|---|---|
| Python | 3.11+ | 3.12 recommended |
| pip | any recent | comes with Python |
| uv | any | only needed for TimesFM venv |
| Git | any | to clone TimesFM repo |
| Google Cloud SDK | any | only if re-running ETL |
| Node.js / npm | 18+ | only if running the React app |

---

## 3. Environment setup

### 3a. Create and activate a virtual environment

```bash
cd project2
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3b. Install all Python dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `shiny`, `shinywidgets`, `plotly`, `pandas`, `pyarrow` — dashboard
- `fastapi`, `uvicorn` — reference React backend (optional)
- `statsmodels`, `scikit-learn`, `matplotlib` — ARIMA & Holt-Winters forecasting
- `google-cloud-bigquery`, `db-dtypes` — ETL pipeline (optional)
- `requests`, `beautifulsoup4` — URL scraper (optional)
- `python-dotenv` — `.env` loading

> **Note:** Prophet and TimesFM each require a separate environment.
> See sections 6.2 and 6.3.

---

## 4. Data — precomputed files (quick start)

All precomputed data files are already committed to the repository.
**Skip sections 5 and 6 if you just want to run the dashboard.**

Expected files (already present):

```
backend/data/
├── gdelt_events_cleaned.parquet
├── daily_aggregates.parquet
├── weekly_aggregates.parquet
├── tone_gap_series.parquet
└── url_text_cache.parquet        ← scraped headline text

model/output/
├── forecast_metrics.csv
└── forecast_predictions.csv
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
python setup_bigquery.py
```

### 5c. Run the ETL pipeline

```bash
python data_collection.py
```

This queries GDELT v2 from BigQuery, filters US–China tariff events (Feb–Apr 2025),
enriches with scraped article text, labels media groups, computes aggregates,
and writes all output files to `data/` and `backend/data/`.

Restart the Shiny app after regenerating data (it loads files at startup).

---

## 6. Regenerate forecast outputs

The forecasting script runs four models and writes results to `model/output/`.
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

pip install prophet==1.3.0

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

# Install uv if you don't have it
pip install uv

# Create the TimesFM venv and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[torch]"
deactivate
```

#### Download the model weights

The weights are fetched automatically from Hugging Face on the first run.
They are stored in your local Hugging Face cache (`~/.cache/huggingface/`).
Checkpoint used: `google/timesfm-2.5-200m-pytorch`

If you want to pre-download them:

```bash
source ../timesfm/.venv/bin/activate
python -c "
from huggingface_hub import snapshot_download
snapshot_download('google/timesfm-2.5-200m-pytorch')
print('Download complete.')
"
deactivate
```

The first download is ~800 MB. Subsequent runs use the local cache.

### 6.4 Run the full forecasting script

With both `.venv-prophet` and `../timesfm/.venv` set up, run from `project2/`:

```bash
source .venv/bin/activate
python model/forecast_models.py
```

The script:
- Loads `tone_gap_series` data
- Fits ARIMA (AIC-selected order) and Holt-Winters in-process
- Spawns a subprocess using `.venv-prophet/bin/python` for Prophet
- Spawns a subprocess using `../timesfm/.venv/bin/python` for TimesFM
- Evaluates all four models on a 14-day holdout (Apr 17–30, 2025)
- Writes `model/output/forecast_metrics.csv` and `model/output/forecast_predictions.csv`
- Saves forecast plots to `model/images/`

To run only specific models, edit the `MODELS` list at the top of `forecast_models.py`.

---

## 7. Configure the Narrative Assistant chatbot

The built-in chatbot answers questions about the dashboard using DeepSeek.

### 7a. Get a DeepSeek API key

Sign up at [https://platform.deepseek.com](https://platform.deepseek.com) and
create an API key.

### 7b. Add the key to `.env`

```bash
# In project2/.env
DEEPSEEK_API_KEY=sk-your_actual_key_here
```

> **Security:** `.env` is in `.gitignore` and must never be committed.
> The key is loaded server-side only — it is never sent to the browser.

### 7c. What the chatbot can answer

**Without API key** (instant, local answers):
- Explain ToneGap
- What does the map show?
- Explain keyword framing
- Which forecast model performs best?
- What are the limitations?
- What is GDELT?
- Explain MAE / RMSE
- Describe Western / Chinese media groups

**With API key** (uses DeepSeek with current dashboard context):
- Summarize current filtered view
- Compare Western vs Chinese tone in the active date range
- Any open-ended analytical question about the data

If `DEEPSEEK_API_KEY` is missing, the chatbot shows a friendly message instead
of crashing.

---

## 8. Run the Shiny dashboard

From `project2/`:

```bash
source .venv/bin/activate
shiny run shiny_app/app.py --host 127.0.0.1 --port 8004
```

Then open **[http://127.0.0.1:8004](http://127.0.0.1:8004)** in your browser.

### Port already in use?

```bash
# Kill whatever is using port 8004
lsof -ti :8004 | xargs kill -9

# Or use a different port
shiny run shiny_app/app.py --host 127.0.0.1 --port 8005
```

### Reload after data changes

The Shiny app loads data **once at startup**. After regenerating ETL or forecast
outputs, stop and restart the app for changes to take effect.

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
| Theme | Dark (default) or Light |
| Event direction | Filter by event actor direction |
| Action countries | Drilldown to specific countries |
| Map view | US–China Focus (globe) or Global Spread (flat map) |
| Keyword top-k | Number of TF-IDF terms shown in the framing bar chart |
| Forecast models | Toggle individual forecast model lines |
| Source top-N / search / sort | Filter the source-domain drilldown table |

---

## 11. React/FastAPI reference dashboard (optional)

A React + FastAPI version of the dashboard exists alongside the Shiny app.
It is a visual reference only and is **not required** for the Shiny demo.

### Run the FastAPI backend

```bash
cd project2/backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Run the React frontend

```bash
cd project2/frontend
npm install
npm run dev
```

Opens at **[http://localhost:5173](http://localhost:5173)**.

### Build for production

```bash
cd project2/frontend
npm run build
# Static files written to frontend/dist/
# The FastAPI backend serves them at http://localhost:8000
```

---

## 12. Known limitations

- **GDELT tone is machine-coded.** Values are noisy and should be treated as
  media-pattern signals, not ground-truth political sentiment.
- **Media group labels are domain-level.** Every article from a domain gets the
  same group label; mixed-ownership or multi-language outlets may be
  mis-assigned.
- **Article-text scraping is optional.** TF-IDF keyword framing depends on
  scraped `ArticleTitle` and `ArticleSnippet` fields. When scraping is sparse,
  framing terms are less stable.
- **Event geocoding can be imprecise.** GDELT geolocates events to the first
  geographic match in the article, which may not reflect the true location.
- **Forecast models use a fixed 14-day holdout.** Results are specific to
  Apr 17–30, 2025; different splits may rank models differently.
- **Daily aggregates do not carry event-direction data.** The direction filter
  applies to event-level charts only, not the daily timeline chart.
- **The map is Plotly `scattergeo`.** It is interactive and rotatable but is
  not a full 3-D WebGL globe; very dense clusters may overlap at low zoom.

---

## 13. Troubleshooting

### `ModuleNotFoundError: No module named 'shinywidgets'`
```bash
pip install shinywidgets
```

### `Address already in use` on port 8004
```bash
lsof -ti :8004 | xargs kill -9
```

### Shiny app shows "Missing gdelt_events_cleaned data"
The parquet files are missing. Either:
- Pull the latest git changes (files are committed), or
- Run `python data_collection.py` (requires BigQuery credentials).

### Forecast chart is empty
`model/output/forecast_predictions.csv` is missing. Run:
```bash
python model/forecast_models.py
```

### TimesFM subprocess fails silently
- Confirm `../timesfm/.venv/bin/python` exists.
- Confirm the Hugging Face cache has the weights:
  `~/.cache/huggingface/hub/models--google--timesfm-2.5-200m-pytorch/`
- Run the TimesFM subprocess manually to see the full error:
  ```bash
  ../timesfm/.venv/bin/python model/forecast_models.py --model timesfm
  ```

### Prophet subprocess fails
- Confirm `.venv-prophet/bin/python` exists.
- Check Prophet is installed: `.venv-prophet/bin/pip show prophet`

### DeepSeek chatbot shows "API key not configured"
Add `DEEPSEEK_API_KEY=sk-...` to `project2/.env` and restart the Shiny app.

### Hero image not showing in the dashboard
Confirm `shiny_app/static/US-China-trade-war-web2.jpg` exists.
If missing, copy it from the project root:
```bash
cp US-China-trade-war-web2.jpg shiny_app/static/
```
