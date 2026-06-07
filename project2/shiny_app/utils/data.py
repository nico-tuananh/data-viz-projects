"""Data loading and filtering helpers for the Shiny dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MODEL_OUTPUT_DIR = PROJECT_ROOT / "forecasting" / "output"


@dataclass(frozen=True)
class DashboardData:
    events: pd.DataFrame
    tone_gap: pd.DataFrame
    forecast_metrics: pd.DataFrame
    forecast_predictions: pd.DataFrame
    data_dir: Path
    model_dir: Path
    warnings: tuple[str, ...]


def _read_table(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    for col in parse_dates or []:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_dashboard_data() -> DashboardData:
    """Load all precomputed artifacts once at app startup."""
    if not (DATA_DIR / "gdelt_events_cleaned.parquet").exists():
        raise FileNotFoundError(
            f"gdelt_events_cleaned.parquet not found in {DATA_DIR}. "
            "Run scripts/data_collection.py or pull the latest git changes."
        )
    data_dir = DATA_DIR
    warnings: list[str] = []

    events = _read_table(data_dir / "gdelt_events_cleaned.parquet", ["Date", "WeekStart", "DateAdded"])
    if events.empty:
        events = _read_table(data_dir / "gdelt_events_cleaned.csv", ["Date", "WeekStart", "DateAdded"])
    if events.empty:
        warnings.append("Missing gdelt_events_cleaned data.")

    tone_gap = _read_table(data_dir / "tone_gap_series.parquet", ["Date"])
    if tone_gap.empty:
        tone_gap = _read_table(data_dir / "tone_gap_series.csv", ["Date"])
    if tone_gap.empty:
        warnings.append("Missing tone_gap_series data.")

    metrics = _read_table(MODEL_OUTPUT_DIR / "forecast_metrics.csv")
    predictions = _read_table(MODEL_OUTPUT_DIR / "forecast_predictions.csv", ["Date"])
    if metrics.empty or predictions.empty:
        warnings.append("Missing forecast output files; forecasting charts will show a message.")

    for df in (events, tone_gap):
        if "MediaGroup" in df.columns:
            df["MediaGroup"] = df["MediaGroup"].fillna("Unknown")

    return DashboardData(
        events=events,
        tone_gap=tone_gap,
        forecast_metrics=metrics,
        forecast_predictions=predictions,
        data_dir=data_dir,
        model_dir=MODEL_OUTPUT_DIR,
        warnings=tuple(warnings),
    )


def available_media(events: pd.DataFrame) -> list[str]:
    preferred = ["Western", "Chinese", "Global/Other"]
    if events.empty or "MediaGroup" not in events:
        return preferred
    present = [m for m in preferred if m in set(events["MediaGroup"].dropna())]
    extras = sorted(set(events["MediaGroup"].dropna()) - set(present))
    return present + extras


def available_directions(events: pd.DataFrame) -> list[str]:
    preferred = ["USA→CHN", "CHN→USA"]
    if events.empty or "EventDirection" not in events:
        return preferred
    present = [d for d in preferred if d in set(events["EventDirection"].dropna())]
    extras = sorted(set(events["EventDirection"].dropna()) - set(preferred))
    return present + extras


def date_bounds(events: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    if events.empty or "Date" not in events:
        fallback_start = pd.Timestamp("2025-02-01")
        return fallback_start, pd.Timestamp("2025-04-30")
    return events["Date"].min(), events["Date"].max()


def filter_by_controls(
    df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
    media_groups: list[str],
    event_directions: list[str] | None = None,
    date_col: str = "Date",
) -> pd.DataFrame:
    if df.empty or date_col not in df:
        return df.copy()
    filtered = df[
        (df[date_col] >= start)
        & (df[date_col] <= end)
    ].copy()
    if media_groups and "MediaGroup" in filtered:
        filtered = filtered[filtered["MediaGroup"].isin(media_groups)]
    if event_directions and "EventDirection" in filtered:
        filtered = filtered[filtered["EventDirection"].isin(event_directions)]
    return filtered


def top_sources(events: pd.DataFrame, limit: int = 12) -> pd.DataFrame:
    if events.empty or "SourceDomain" not in events:
        return pd.DataFrame(columns=["SourceDomain", "Events", "Articles", "AvgTone"])
    grouped = (
        events.groupby("SourceDomain", dropna=False)
        .agg(
            Events=("GLOBALEVENTID", "count"),
            Articles=("NumArticles", "sum"),
            AvgTone=("AvgTone", "mean"),
        )
        .reset_index()
        .sort_values("Events", ascending=False)
        .head(limit)
    )
    grouped["AvgTone"] = grouped["AvgTone"].round(2)
    return grouped
