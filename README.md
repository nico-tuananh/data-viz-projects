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

## Project Overview

An interactive data visualization dashboard built with the Palmer Penguins dataset. It explores penguin species through habitat distribution, physical measurement comparisons, and machine learning-based pattern discovery.

### What the Dashboard Shows

- Species distribution across islands
- Physical differences in bill size, flipper length, and body mass
- Interactive filtering by species, island, and sex
- Text-based narrative guidance for clearer storytelling
- PCA and K-Means clustering to compare unsupervised patterns with actual species groups

### Dataset

The dashboard uses the Palmer Penguins dataset, which contains penguin species, island, sex, and body measurement features.

## Running Instructions

**Requirements:** Python 3.10+

```bash
# Install dependencies
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r project1/requirements.txt

# Run the dashboard  →  http://127.0.0.1:8050/
python project1/dashboard.py
```

---

# Project 2: Tariff Tensions, Narrative Divides

An interactive media-intelligence dashboard analysing how Western and Chinese media constructed asymmetric emotional narratives during the 2025 US–China tariff escalation.

**Research question:** Do media systems merely report tariff escalation, or do they construct different emotional narratives around the same conflict?

**Stack:** Python Shiny · **Data:** GDELT v2 · **Window:** Feb 1 – Apr 30, 2025

## Live App

**[https://lnbphuong.shinyapps.io/tariff-tensions/](https://lnbphuong.shinyapps.io/tariff-tensions/)**

## Repository Structure

```
project2/
├── shiny_app/              # Dashboard app (Python Shiny)
│   ├── app.py              # Shiny app object — entrypoint for deploy & shiny run
│   ├── components/         # Charts, chatbot widget, layout helpers
│   ├── utils/              # Data loading, TF-IDF analysis, DeepSeek client
│   └── static/             # CSS, hero image, and VinUni logo
├── data/                   # Precomputed datasets (no BigQuery needed to run)
├── forecasting/            # Forecast models + precomputed outputs
├── scripts/                # GDELT data collection pipeline (optional)
├── docs/                   # Forecasting methodology, setup notes, and data pipeline docs
├── main.py                 # Dashboard launcher
├── requirements.txt        # Full local dependencies
├── requirements-deploy.txt # Deployment-only dependencies
└── requirements-model.txt  # Prophet venv dependencies
```

## Running Locally

```bash
cd project2
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Enable the AI chatbot
cp .env.example .env
# Edit .env and add: DEEPSEEK_API_KEY=<your-key-here>
# The dashboard runs fully without it — chatbot shows a fallback if the key is missing.

# Launch  →  http://127.0.0.1:8004
python main.py
```

See `project2/README.md` for full setup details, deployment instructions, and team task allocation. Data pipeline notes: [`project2/docs/DATA_PIPELINE.md`](project2/docs/DATA_PIPELINE.md).
