"""Word cloud endpoint — distinctive phrases from scraped headlines + metadata."""
from fastapi import APIRouter, Query

try:
    from data_loader import EVENTS
    from framing_terms import compute_distinctive_phrases
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data_loader import EVENTS
    from framing_terms import compute_distinctive_phrases

router = APIRouter(prefix="/api/wordcloud", tags=["wordcloud"])

_HAS_SCRAPED = (
    "ArticleTitle" in EVENTS.columns
    and (EVENTS["ArticleTitle"].astype(str).str.len() > 0).any()
)

_WESTERN_CLOUD = compute_distinctive_phrases(EVENTS, "Western", "Chinese", top_n=200)
_CHINESE_CLOUD = compute_distinctive_phrases(EVENTS, "Chinese", "Western", top_n=200)


@router.get("")
def get_wordcloud(
    top_n: int = Query(default=50, ge=1, le=200),
):
    return {
        "textSource": "headlines" if _HAS_SCRAPED else "metadata",
        "description": (
            "Contrastive TF-IDF on scraped article titles/snippets — "
            "terms distinctive to each media group vs the other."
            if _HAS_SCRAPED
            else "Contrastive TF-IDF on GDELT event metadata (re-run pipeline with scraping for headlines)."
        ),
        "groups": {
            "Western": _WESTERN_CLOUD[:top_n],
            "Chinese": _CHINESE_CLOUD[:top_n],
        },
    }
