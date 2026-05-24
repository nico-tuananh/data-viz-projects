"""Weekly geo aggregates endpoint (for choropleth map)."""
import math

from fastapi import APIRouter, Query
from backend.data_loader import filter_weekly_geo, DATE_MIN, DATE_MAX, MEDIA_GROUPS

router = APIRouter(prefix="/api/weekly_geo", tags=["weekly_geo"])


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
def get_weekly_geo(
    start: str = Query(default=DATE_MIN),
    end: str = Query(default=DATE_MAX),
    media: str = Query(default=",".join(MEDIA_GROUPS)),
    direction: str = Query(default="All"),
):
    media_groups = [m.strip() for m in media.split(",") if m.strip()]
    df = filter_weekly_geo(start, end, media_groups, direction)

    if df.empty:
        return {"count": 0, "records": []}

    grouped = (
        df.groupby(["ActionCountry", "MediaGroup"])
        .agg(
            TotalEvents=("TotalEvents", "sum"),
            TotalArticles=("TotalArticles", "sum"),
            AvgTone=("AvgTone", "mean"),
            AvgGoldstein=("AvgGoldstein", "mean"),
        )
        .reset_index()
    )

    records = []
    for row in grouped.to_dict(orient="records"):
        rec = {k: _safe_json(v) for k, v in row.items()}
        records.append(rec)

    return {"count": len(records), "records": records}
