# Project 2 — Tariff Tensions, Narrative Divides

An interactive media-intelligence dashboard analysing how Western and Chinese media
constructed asymmetric narratives during the 2025 US–China tariff escalation.

**Data source:** GDELT v2 · **Window:** Feb 1 – Apr 30, 2025 · **Dashboard:** Python Shiny

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API key (optional — only needed for the AI chatbot)
cp .env.example .env
# Edit .env and paste your DeepSeek key:
# DEEPSEEK_API_KEY=sk-...

# 3. Launch the dashboard  → Opens at http://127.0.0.1:8004
python main.py

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
├── requirements.txt        # Full dependencies (dashboard + data pipeline)
├── requirements-deploy.txt # Dashboard-only deps for shinyapps.io deployment
├── requirements-model.txt  # Prophet venv dependencies
└── .env.example            # Environment variable template (safe to commit)
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

Copy `.env.example` to `.env` and fill in your key. **Never commit `.env`** — it is listed in `.gitignore`.

```bash
cp .env.example .env
# then edit .env:
DEEPSEEK_API_KEY=sk-your-actual-key-here
```

The app runs fully without this key — the chatbot will display a friendly fallback message if it is missing.

---

## Deployment to shinyapps.io

> **⚠️ Never commit `.env` or paste your API key into any file that gets committed to git.**
> The `.env` file is listed in `.gitignore` and is intentionally excluded from version control.

### 1. Install rsconnect-python

```bash
pip install rsconnect-python
```

### 2. Authenticate with shinyapps.io

Log in at [shinyapps.io](https://www.shinyapps.io) → Account → Tokens → Show → Copy the token command.
It looks like:

```bash
rsconnect add \
  --account <your-account-name> \
  --name    <your-account-name> \
  --token   <TOKEN> \
  --secret  <SECRET>
```

Run that command once. Your credentials are stored locally in `~/.rsconnect-python/` (never in the repo).

### 3. Deploy the app

Run this from the **project2/** root directory:

```bash
rsconnect deploy shiny \
  --name    <your-shinyapps-account-name> \
  --title   "tariff-tensions" \
  --app-dir . \
  --requirements requirements-deploy.txt \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".env" \
  --exclude "*.pyc" \
  --exclude "scripts/" \
  --exclude "requirements-model.txt" \
  shiny_app/app.py
```

**Why `--app-dir .` (project root)?**
The dashboard's data loaders resolve paths relative to the project root
(`data/`, `forecasting/output/`). Deploying from the root ensures those
relative paths work identically in production and locally.

**Why `requirements-deploy.txt`?**
`requirements.txt` includes BigQuery and data-pipeline packages that are only
needed for data regeneration — not for running the dashboard. Using
`requirements-deploy.txt` keeps the shinyapps.io install fast and avoids
potential build errors from heavy dependencies (Prophet, TimesFM, google-cloud).

### 4. Set the DeepSeek API key securely on shinyapps.io

After deploying, set the API key through the shinyapps.io web dashboard:

1. Go to [shinyapps.io](https://www.shinyapps.io) → **Applications** → click your app
2. Click **Settings** → **Environment Variables** (or **Vars**)
3. Add a new variable:
   - **Name:** `DEEPSEEK_API_KEY`
   - **Value:** `sk-...` (your actual key)
4. Click **Save** and then **Restart** the application

> **✅ Verify:** shinyapps.io environment variables are stored securely on their
> platform — they are NOT part of your deployed bundle and are NOT visible in
> the source files. This is the correct and safe method.
>
> **⚠️ To verify this is available:** log in to shinyapps.io → your app →
> Settings tab and confirm you see an "Environment Variables" or "Vars" section.
> If you do not see it, your plan tier may not support it — check
> [shinyapps.io pricing](https://www.shinyapps.io/#pricing).

### 5. Fallback behaviour (no API key)

If `DEEPSEEK_API_KEY` is not set, the rest of the dashboard works normally.
The chatbot panel will show:

> ⚙️ **AI assistant is unavailable** — `DEEPSEEK_API_KEY` is not configured.

No crash. No stack trace exposed to users.

### 6. Re-deploying after changes

```bash
rsconnect deploy shiny \
  --name    <your-shinyapps-account-name> \
  --title   "tariff-tensions" \
  --app-dir . \
  --requirements requirements-deploy.txt \
  --exclude ".venv" \
  --exclude "__pycache__" \
  --exclude ".env" \
  --exclude "*.pyc" \
  --exclude "scripts/" \
  --exclude "requirements-model.txt" \
  shiny_app/app.py
```

rsconnect will update the existing application in-place.

---

For detailed setup (Prophet venv, TimesFM, chatbot config), see `shiny_app/README.md`.
