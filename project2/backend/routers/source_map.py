"""Source-origin map endpoint."""
import math

from fastapi import APIRouter, Query

try:
    from data_loader import filter_source_map, DATE_MIN, DATE_MAX, MEDIA_GROUPS
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data_loader import filter_source_map, DATE_MIN, DATE_MAX, MEDIA_GROUPS

router = APIRouter(prefix="/api/source-map", tags=["source_map"])


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
def get_source_map(
    start: str = Query(default=DATE_MIN),
    end: str = Query(default=DATE_MAX),
    media: str = Query(default=",".join(MEDIA_GROUPS)),
):
    media_groups = [m.strip() for m in media.split(",") if m.strip()]
    df = filter_source_map(start, end, media_groups)

    if df.empty:
        return {"count": 0, "records": []}

    records = []
    for row in df.to_dict(orient="records"):
        rec = {k: _safe_json(v) for k, v in row.items()}
        records.append(rec)

    return {"count": len(records), "records": records}
