"""Keywords endpoint — contrastive TF-IDF from scraped headlines + metadata."""
from fastapi import APIRouter, Query

try:
    from data_loader import EVENTS
    from framing_terms import compute_distinctive_keywords
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data_loader import EVENTS
    from framing_terms import compute_distinctive_keywords

router = APIRouter(prefix="/api/keywords", tags=["keywords"])

_WESTERN_KEYWORDS = compute_distinctive_keywords(EVENTS, "Western", "Chinese", top_n=100)
_CHINESE_KEYWORDS = compute_distinctive_keywords(EVENTS, "Chinese", "Western", top_n=100)


@router.get("")
def get_keywords(
    top_n: int = Query(default=20, ge=1, le=100),
):
    return {
        "topN": top_n,
        "groups": {
            "Western": _WESTERN_KEYWORDS[:top_n],
            "Chinese": _CHINESE_KEYWORDS[:top_n],
        },
    }
