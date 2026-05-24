"""Tone gap series endpoint."""
import math

from fastapi import APIRouter, Query
from backend.data_loader import filter_tone_gap, DATE_MIN, DATE_MAX

router = APIRouter(prefix="/api/tone_gap", tags=["tone_gap"])


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
def get_tone_gap(
    start: str = Query(default=DATE_MIN),
    end: str = Query(default=DATE_MAX),
):
    df = filter_tone_gap(start, end)

    if df.empty:
        return {"count": 0, "records": []}

    records = []
    for row in df.to_dict(orient="records"):
        rec = {k: _safe_json(v) for k, v in row.items()}
        records.append(rec)

    return {"count": len(records), "records": records}
