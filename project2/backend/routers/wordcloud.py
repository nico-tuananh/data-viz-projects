"""Word cloud endpoint — distinctive phrases from scraped headlines."""
from fastapi import APIRouter, Query

try:
    from data_loader import EVENTS
    from framing_terms import compute_distinctive_phrases, _is_usable_headline
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data_loader import EVENTS
    from framing_terms import compute_distinctive_phrases, _is_usable_headline

router = APIRouter(prefix="/api/wordcloud", tags=["wordcloud"])

_USABLE_HEADLINES = (
    "ArticleTitle" in EVENTS.columns
    and EVENTS.apply(_is_usable_headline, axis=1).any()
)

_WESTERN_CLOUD = compute_distinctive_phrases(EVENTS, "Western", "Chinese", top_n=200)
_CHINESE_CLOUD = compute_distinctive_phrases(EVENTS, "Chinese", "Western", top_n=200)


@router.get("")
def get_wordcloud(
    top_n: int = Query(default=50, ge=1, le=200),
):
    return {
        "textSource": "headlines" if _USABLE_HEADLINES else "metadata",
        "description": (
            "Contrastive TF-IDF on scraped article headlines — "
            "outlet names and event-type labels filtered; shows framing terms "
            "distinctive to each media group."
            if _USABLE_HEADLINES
            else "No usable scraped headlines found — re-run data_collection.py --scrape-only."
        ),
        "groups": {
            "Western": _WESTERN_CLOUD[:top_n],
            "Chinese": _CHINESE_CLOUD[:top_n],
        },
    }
