"""Filtered events endpoint (for map markers)."""
import math

from fastapi import APIRouter, Query
from data_loader import filter_events, DATE_MIN, DATE_MAX, MEDIA_GROUPS

router = APIRouter(prefix="/api/events", tags=["events"])


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
