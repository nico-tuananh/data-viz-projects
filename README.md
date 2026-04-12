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

### Dataset
Palmer Penguins dataset, suitable for exploring classification, relationships, and distributions.

### Technical Requirements

**Data Preparation**
- Implementation of a clear data preprocessing pipeline
- Handling of missing values, filtering, and data aggregation

**Core Visualizations**
- Foundational charts (scatter plots, bar charts, distributions) exploring physical attributes of penguin species across islands

**Text Visualization**
- Advanced annotations, dynamic markdown summaries, or visual guides
- Integration of text elements to support data storytelling

**Interactive & Dynamic Elements**
- Data filtering capabilities (by species, island, or sex)
- Dynamic updates through hover effects, dropdowns, or sliders

**Machine Learning Integration**
- At least one visualization highlighting ML concepts
- Examples: K-Means clustering visualization or PCA plot for dimensionality reduction

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
