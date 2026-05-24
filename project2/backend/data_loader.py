"""Load and cache parquet datasets for the dashboard backend."""
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

# Cached DataFrames loaded once at import time
EVENTS = pd.read_parquet(DATA_DIR / "gdelt_events_cleaned.parquet")
DAILY = pd.read_parquet(DATA_DIR / "daily_aggregates.parquet")
WEEKLY = pd.read_parquet(DATA_DIR / "weekly_aggregates.parquet")
TONE_GAP = pd.read_parquet(DATA_DIR / "tone_gap_series.parquet")

# Ensure Date columns are Timestamp
EVENTS["Date"] = pd.to_datetime(EVENTS["Date"])
DAILY["Date"] = pd.to_datetime(DAILY["Date"])
WEEKLY["WeekStart"] = pd.to_datetime(WEEKLY["WeekStart"])
TONE_GAP["Date"] = pd.to_datetime(TONE_GAP["Date"])

MEDIA_GROUPS = EVENTS["MediaGroup"].unique().tolist()
EVENT_DIRECTIONS = EVENTS["EventDirection"].unique().tolist()
DATE_MIN = EVENTS["Date"].min().date().isoformat()
DATE_MAX = EVENTS["Date"].max().date().isoformat()


def filter_events(start: str, end: str, media_groups: list[str], event_direction: str):
    df = EVENTS.copy()
    mask = (
        (df["Date"] >= pd.Timestamp(start))
        & (df["Date"] <= pd.Timestamp(end))
        & (df["MediaGroup"].isin(media_groups))
    )
    if event_direction != "All":
        mask &= df["EventDirection"] == event_direction
    return df[mask]


def filter_daily(start: str, end: str, media_groups: list[str], _event_direction: str):
    df = DAILY.copy()
    mask = (
        (df["Date"] >= pd.Timestamp(start))
        & (df["Date"] <= pd.Timestamp(end))
        & (df["MediaGroup"].isin(media_groups))
    )
    # Daily aggregates do not have EventDirection; skip filtering by direction
    return df[mask]


def filter_weekly_geo(start: str, end: str, media_groups: list[str], _event_direction: str):
    df = WEEKLY.copy()
    mask = (
        (df["WeekStart"] >= pd.Timestamp(start))
        & (df["WeekStart"] <= pd.Timestamp(end))
        & (df["MediaGroup"].isin(media_groups))
    )
    # Weekly aggregates do not have EventDirection; skip filtering by direction
    return df[mask]


def filter_tone_gap(start: str, end: str):
    df = TONE_GAP.copy()
    mask = (df["Date"] >= pd.Timestamp(start)) & (df["Date"] <= pd.Timestamp(end))
    return df[mask]
