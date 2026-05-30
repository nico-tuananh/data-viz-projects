"""Filtered events endpoint (for map markers)."""
import math

import pandas as pd
from fastapi import APIRouter, Query
from data_loader import filter_events, DATE_MIN, DATE_MAX, MEDIA_GROUPS

router = APIRouter(prefix="/api/events", tags=["events"])

# GDELT country centroids that fall in water bodies — replace with capital-city coords.
# Key: (ActionGeo_CountryCode, original_lat, original_lon) → (corrected_lat, corrected_lon)
_BAD_CENTROIDS = {
    ("CA", 60.0, -96.0): (45.4215, -75.6972),    # Hudson Bay → Ottawa
    ("UK", 54.0, -4.0): (51.5074, -0.1278),        # Irish Sea → London
    ("AS", -25.0, 135.0): (-35.2809, 149.1300),    # Outback → Canberra
    ("PM", 9.0, -80.0): (9.0, -79.5),              # Near Canal → Panama City area
    ("CH", 35.0, 105.0): (39.9042, 116.4074),      # Bare Gobi centroid → Beijing
    ("RS", 60.0, 100.0): (55.7558, 37.6173),       # Siberian centroid → Moscow
}


def _safe_json(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


@router.get("")
def get_events(
    start: str = Query(default=DATE_MIN),
    end: str = Query(default=DATE_MAX),
    media: str = Query(default=",".join(MEDIA_GROUPS)),
    direction: str = Query(default="All"),
    limit: int = Query(default=5000, le=10000),
):
    media_groups = [m.strip() for m in media.split(",") if m.strip()]
    df = filter_events(start, end, media_groups, direction)

    # Filter out events with extreme-latitude coordinates (Arctic/Antarctic ocean artifacts)
    if "ActionGeo_Lat" in df.columns:
        lat = pd.to_numeric(df["ActionGeo_Lat"], errors="coerce")
        df = df[lat.between(-60, 70)]

    # Fix GDELT country centroids that land in water bodies
    if "ActionGeo_CountryCode" in df.columns:
        for (cc, bad_lat, bad_lon), (good_lat, good_lon) in _BAD_CENTROIDS.items():
            mask = (
                (df["ActionGeo_CountryCode"] == cc)
                & (df["ActionGeo_Lat"].round(4) == bad_lat)
                & (df["ActionGeo_Long"].round(4) == bad_lon)
            )
            df.loc[mask, "ActionGeo_Lat"] = good_lat
            df.loc[mask, "ActionGeo_Long"] = good_lon

    cols = [
        "GLOBALEVENTID", "Date", "MediaGroup", "EventDirection",
        "ActionGeo_Lat", "ActionGeo_Long", "ActionGeo_CountryCode",
        "SourceDomain", "AvgTone", "GoldsteinScale", "NumArticles",
        "EventTypeDesc", "QuadClassDesc",
    ]
    available = [c for c in cols if c in df.columns]
    df = df[available].head(limit)

    records = []
    for row in df.to_dict(orient="records"):
        rec = {k: _safe_json(v) for k, v in row.items()}
        records.append(rec)

    return {"count": int(len(df)), "records": records}
