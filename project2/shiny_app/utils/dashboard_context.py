"""Build a compact text context summary from the current filtered dashboard state.

The context is sent to DeepSeek so it can answer data-grounded questions.
Only aggregates are sent — full DataFrames are never transmitted.
"""
from __future__ import annotations

import pandas as pd


def build_context(
    events: pd.DataFrame,
    tone_gap: pd.DataFrame,
    date_start: pd.Timestamp,
    date_end: pd.Timestamp,
    media_groups: list[str],
    direction: str,
    countries: list[str],
    forecast_metrics: pd.DataFrame,
) -> str:
    lines: list[str] = [
        "=== ACTIVE FILTERS ===",
        f"Date range       : {date_start.date()} → {date_end.date()}",
        f"Media groups     : {', '.join(media_groups) if media_groups else 'none selected'}",
        f"Event direction  : {direction}",
        f"Country filter   : {', '.join(countries) if countries else 'none (all countries)'}",
        "",
        "=== EVENT DATA SUMMARY ===",
    ]

    if events.empty:
        lines.append("No events match the current filter.")
    else:
        lines.append(f"Total events     : {len(events):,}")
        if "NumArticles" in events:
            lines.append(f"Total articles   : {int(events['NumArticles'].sum()):,}")
        if "SourceDomain" in events:
            lines.append(f"Unique sources   : {events['SourceDomain'].nunique():,}")
        if "MediaGroup" in events and "AvgTone" in events:
            for grp in ["Western", "Chinese", "Global/Other"]:
                sub = events[events["MediaGroup"] == grp]
                if not sub.empty:
                    lines.append(f"Avg {grp:14s} tone : {sub['AvgTone'].mean():.2f}")
        if "SourceDomain" in events:
            top5 = events.groupby("SourceDomain").size().nlargest(5).index.tolist()
            lines.append(f"Top 5 domains    : {', '.join(top5)}")

    lines += [
        "",
        "=== TONE GAP ===",
        "Definition: ToneGap = Western weighted tone − Chinese weighted tone.",
        "Positive → Western more positive than Chinese. Negative → opposite.",
    ]
    if not tone_gap.empty and "ToneGap" in tone_gap:
        gap = tone_gap["ToneGap"]
        latest = tone_gap.sort_values("Date").iloc[-1]["ToneGap"]
        lines += [
            f"Period average   : {gap.mean():.2f}",
            f"Period min       : {gap.min():.2f}",
            f"Period max       : {gap.max():.2f}",
            f"Most recent      : {latest:.2f}",
        ]
    else:
        lines.append("ToneGap not available for this filter.")

    lines += [
        "",
        "=== FORECAST MODELS ===",
        "Models: ARIMA, Holt-Winters, Prophet, TimesFM evaluated on a 14-day holdout.",
    ]
    cols = {"model", "mae", "rmse"}
    if not forecast_metrics.empty and cols.issubset(forecast_metrics.columns):
        best = forecast_metrics.sort_values("mae").iloc[0]
        lines.append(
            f"Best model (MAE) : {best['model']}  "
            f"MAE={best['mae']:.3f}  RMSE={best['rmse']:.3f}"
        )
        for _, row in forecast_metrics.sort_values("mae").iterrows():
            lines.append(f"  {row['model']:14s}: MAE={row['mae']:.3f}  RMSE={row['rmse']:.3f}")
    else:
        lines.append("Forecast metrics not available.")

    lines += [
        "",
        "=== METHODOLOGY ===",
        "Source        : GDELT v2, Feb–Apr 2025.",
        "Western group : English-language Western outlets (US, UK, CA, AU, EU).",
        "Chinese group : PRC and HK outlets.",
        "Global/Other  : all remaining domains.",
        "Tone scale    : machine-coded, −100 (very negative) to +100 (very positive).",
        "Keyword framing: contrastive TF-IDF — terms overrepresented in one group vs the other.",
    ]

    return "\n".join(l for l in lines if l is not None)
