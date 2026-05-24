"""Overview / summary statistics endpoint."""
import math

from fastapi import APIRouter, Query
from backend.data_loader import filter_events, DATE_MIN, DATE_MAX, MEDIA_GROUPS
import pandas as pd

router = APIRouter(prefix="/api/summary", tags=["summary"])


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
def get_summary(
    start: str = Query(default=DATE_MIN),
    end: str = Query(default=DATE_MAX),
    media: str = Query(default=",".join(MEDIA_GROUPS)),
    direction: str = Query(default="All"),
):
    media_groups = [m.strip() for m in media.split(",") if m.strip()]
    df = filter_events(start, end, media_groups, direction)

    western = df[df["MediaGroup"] == "Western"]
    chinese = df[df["MediaGroup"] == "Chinese"]

    w_tone = western["AvgTone"].mean() if len(western) else None
    c_tone = chinese["AvgTone"].mean() if len(chinese) else None

    breakdown = (
        df.groupby("MediaGroup")
        .agg(Events=("GLOBALEVENTID", "count"), Sources=("SourceDomain", "nunique"))
        .reset_index()
        .to_dict(orient="records")
    )

    return {
        "totalEvents": int(len(df)),
        "uniqueSources": int(df["SourceDomain"].nunique()),
        "avgToneWestern": round(float(w_tone), 2) if pd.notna(w_tone) else None,
        "avgToneChinese": round(float(c_tone), 2) if pd.notna(c_tone) else None,
        "mediaBreakdown": breakdown,
    }
