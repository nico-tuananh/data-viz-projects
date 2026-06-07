"""Small data transforms used by the Shiny server and chart builders."""

from __future__ import annotations

import pandas as pd


def event_daily(events: pd.DataFrame) -> pd.DataFrame:
    """Build daily aggregates from filtered event rows so all filters apply."""
    if events.empty or "Date" not in events or "MediaGroup" not in events:
        return pd.DataFrame()
    return (
        events.groupby(["Date", "MediaGroup"], as_index=False)
        .agg(
            TotalEvents=("GLOBALEVENTID", "count"),
            TotalArticles=("NumArticles", "sum"),
            AvgTone=("AvgTone", "mean"),
            WeightedTone=("AvgTone", "mean"),
        )
        .sort_values("Date")
    )


def geo_points(events: pd.DataFrame) -> pd.DataFrame:
    """Aggregate event rows into map markers to keep first paint fast."""
    required = {"ActionGeo_Lat", "ActionGeo_Long", "MediaGroup", "ActionCountry", "NumArticles", "AvgTone"}
    if events.empty or not required.issubset(events.columns):
        return pd.DataFrame()
    geo = events.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"]).copy()
    if geo.empty:
        return pd.DataFrame()
    if "ActionGeo_FullName" not in geo:
        geo["ActionGeo_FullName"] = geo["ActionCountry"]
    if "SourceDomain" not in geo:
        geo["SourceDomain"] = "Unknown"
    if "EventDirection" not in geo:
        geo["EventDirection"] = "Unknown"
    grouped = (
        geo.groupby(
            [
                "ActionGeo_FullName",
                "ActionCountry",
                "ActionGeo_Lat",
                "ActionGeo_Long",
                "MediaGroup",
            ],
            dropna=False,
            as_index=False,
        )
        .agg(
            Events=("GLOBALEVENTID", "count"),
            NumArticles=("NumArticles", "sum"),
            AvgTone=("AvgTone", "mean"),
            TopSource=("SourceDomain", lambda values: values.value_counts().index[0] if len(values) else "Unknown"),
            Directions=("EventDirection", lambda values: ", ".join(sorted(set(map(str, values.dropna())))[:3])),
        )
    )
    return grouped.sort_values("NumArticles", ascending=False).head(1200)



def gap_extremes(tone_gap: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    if tone_gap.empty or "ToneGap" not in tone_gap:
        return None, None
    gap = tone_gap.dropna(subset=["ToneGap"])
    if gap.empty:
        return None, None
    return gap.loc[gap["ToneGap"].idxmax()], gap.loc[gap["ToneGap"].idxmin()]


def forecast_metric_cards(metrics: pd.DataFrame) -> list[dict]:
    if metrics.empty or not {"model", "mae", "rmse"}.issubset(metrics.columns):
        return []
    best_mae = metrics["mae"].min()
    rows = []
    for _, row in metrics.sort_values("mae").iterrows():
        rows.append({
            "model": row["model"],
            "mae": float(row["mae"]),
            "rmse": float(row["rmse"]),
            "best": bool(row["mae"] == best_mae),
        })
    return rows


