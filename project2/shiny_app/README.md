# Python Shiny Dashboard

This directory adds a Python Shiny version of the Project 2 dashboard while preserving the existing React/FastAPI app.

## What It Uses

- Precomputed ETL outputs from `project2/backend/data/` first, with `project2/data/` as a fallback.
- Forecast outputs from `project2/model/output/forecast_metrics.csv` and `project2/model/output/forecast_predictions.csv`.
- No live GDELT queries are run during the Shiny demo.
- The Shiny UI includes both light and dark presentation modes, a rotatable globe-first spread view, and synchronized filters across all sections.

Expected data files:

- `gdelt_events_cleaned.parquet`
- `daily_aggregates.parquet`
- `weekly_aggregates.parquet`
- `tone_gap_series.parquet`
- `model/output/forecast_metrics.csv`
- `model/output/forecast_predictions.csv`

CSV fallbacks are supported for the four ETL datasets.

## Install Dependencies

From `project2/`:

```bash
python -m pip install -r requirements.txt
```

The Shiny dashboard needs:

- `shiny`
- `shinywidgets`
- `plotly`
- `pandas`
- `pyarrow`
- `scikit-learn`

## Run

From `project2/`:

```bash
python -m shiny run shiny_app/app.py --host 127.0.0.1 --port 8004
```

Then open:

```text
http://127.0.0.1:8004
```

## Regenerate ETL Data

From `project2/`:

```bash
python data_collection.py
```

This refreshes the GDELT-derived datasets. The Shiny app loads files at startup, so restart Shiny after regenerating data.

## Regenerate Forecast Outputs

From `project2/`:

```bash
python model/forecast_models.py
```

Forecasting uses a 14-day holdout evaluation and writes metrics and predictions to `project2/model/output/`.

## Dashboard Sections

1. Conflict Timeline: editorial multi-line timeline with annotated spikes and hover details.
2. Narrative Spread: rotatable globe default, global map toggle, and searchable source-domain table.
3. Emotional Divergence: ToneGap, tone distribution, and tone-versus-volume views with chart-level interpretation.
4. Keyword Framing: compact diverging contrastive TF-IDF chart plus ranked framing term cards.
5. Narrative Gap Forecasting: holdout metrics and actual versus predicted ToneGap with best-model highlighting.

## Controls

- Date range
- Media group checkboxes
- Light / Dark mode toggle
- Event direction
- Action-country drilldown
- Map view toggle: `US-China Focus` or `Global Spread`
- Keyword depth selector
- Forecast model selector
- Source-domain top-N, search, and sort controls

## Known Limitations

- Daily aggregates do not carry event direction, so the direction filter applies to event-level charts but not the daily aggregate charts.
- Keyword framing depends on scraped `ArticleTitle` and `ArticleSnippet` fields. When scraping is sparse, terms are less stable.
- Forecast charts use precomputed outputs only; the app intentionally does not trigger slow model regeneration during a live demo.
- The globe view is built with Plotly `scattergeo`, so it is interactive and rotatable but not a full 3D WebGL earth.
