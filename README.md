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
