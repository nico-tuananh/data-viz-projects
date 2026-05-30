"""Keywords endpoint — TF-IDF style extraction from event metadata."""
import math
from collections import Counter

from fastapi import APIRouter, Query

try:
    from data_loader import EVENTS
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data_loader import EVENTS

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


def _extract_terms(row):
    """Extract searchable terms from an event record."""
    terms = []

    # Source domain (main name, no TLD)
    domain = str(row.get("SourceDomain", "")).lower()
    if domain and domain not in ("unknown", "nan", "none"):
        parts = domain.split(".")
        if parts[0] and len(parts[0]) > 2:
            terms.append(parts[0])

    # Event type description
    et = str(row.get("EventTypeDesc", ""))
    if et and et not in ("Other", "nan", "none"):
        terms.extend(t.lower() for t in et.replace("/", " ").split() if len(t) > 2)

    # Quad class
    qc = str(row.get("QuadClassDesc", ""))
    if qc and qc not in ("Unknown", "nan", "none"):
        terms.extend(t.lower() for t in qc.split() if len(t) > 2)

    # Action country code
    cc = str(row.get("ActionGeo_CountryCode", ""))
    if cc and cc not in ("UNK", "nan", "none", ""):
        terms.append(cc.lower())

    # Actor names
    for col in ("Actor1Name", "Actor2Name"):
        name = str(row.get(col, ""))
        if name and name not in ("nan", "none", ""):
            terms.extend(t.lower() for t in name.split() if len(t) > 2)

    return terms


def _compute_group_keywords(df, group_name, other_group_name):
    """Compute distinctive keywords for a media group."""
    group_df = df[df["MediaGroup"] == group_name]
    other_df = df[df["MediaGroup"] == other_group_name]

    if len(group_df) == 0:
        return []

    # Count terms in each group
    group_counter = Counter()
    group_doc_counter = Counter()
    other_counter = Counter()

    for _, row in group_df.iterrows():
        terms = set(_extract_terms(row))
        for term in terms:
            group_counter[term] += 1
            group_doc_counter[term] += 1

    for _, row in other_df.iterrows():
        terms = set(_extract_terms(row))
        for term in terms:
            other_counter[term] += 1

    # Compute scores: frequency in group * distinctiveness ratio
    results = []
    group_total = max(len(group_df), 1)
    other_total = max(len(other_df), 1)

    for term, count in group_counter.items():
        group_freq = count / group_total
        other_freq = other_counter.get(term, 0) / other_total
        score = group_freq * math.log1p(group_freq / (other_freq + 0.001))

        results.append({
            "keyword": term,
            "tfidf_score": round(score, 6),
            "doc_count": group_doc_counter[term],
        })

    results.sort(key=lambda x: x["tfidf_score"], reverse=True)
    return results


# Pre-compute keywords at import time
_WESTERN_KEYWORDS = _compute_group_keywords(EVENTS, "Western", "Chinese")
_CHINESE_KEYWORDS = _compute_group_keywords(EVENTS, "Chinese", "Western")


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
