"""Word cloud endpoint — phrase extraction from event metadata."""
from collections import Counter

from fastapi import APIRouter, Query

try:
    from data_loader import EVENTS
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data_loader import EVENTS

router = APIRouter(prefix="/api/wordcloud", tags=["wordcloud"])


def _extract_phrases(row):
    """Extract unigrams, bigrams, and trigrams from event metadata."""
    phrases = []

    # Source domain
    domain = str(row.get("SourceDomain", "")).lower()
    if domain and domain not in ("unknown", "nan", "none"):
        parts = domain.split(".")
        if parts[0] and len(parts[0]) > 2:
            phrases.append((parts[0], "unigram"))

    # Event type
    et = str(row.get("EventTypeDesc", ""))
    if et and et not in ("Other", "nan", "none"):
        words = [w.lower() for w in et.replace("/", " ").split() if len(w) > 2]
        for w in words:
            phrases.append((w, "unigram"))
        for i in range(len(words) - 1):
            phrases.append((f"{words[i]} {words[i + 1]}", "bigram"))
        for i in range(len(words) - 2):
            phrases.append((f"{words[i]} {words[i + 1]} {words[i + 2]}", "trigram"))

    # Quad class
    qc = str(row.get("QuadClassDesc", ""))
    if qc and qc not in ("Unknown", "nan", "none"):
        words = [w.lower() for w in qc.split() if len(w) > 2]
        for w in words:
            phrases.append((w, "unigram"))
        for i in range(len(words) - 1):
            phrases.append((f"{words[i]} {words[i + 1]}", "bigram"))

    # Country code
    cc = str(row.get("ActionGeo_CountryCode", ""))
    if cc and cc not in ("UNK", "nan", "none", ""):
        phrases.append((cc.lower(), "unigram"))

    # Actor names
    for col in ("Actor1Name", "Actor2Name"):
        name = str(row.get(col, ""))
        if name and name not in ("nan", "none", ""):
            words = [w.lower() for w in name.split() if len(w) > 2]
            for w in words:
                phrases.append((w, "unigram"))
            for i in range(len(words) - 1):
                phrases.append((f"{words[i]} {words[i + 1]}", "bigram"))

    return phrases


def _compute_wordcloud(df, group_name):
    """Compute word cloud data for a media group."""
    group_df = df[df["MediaGroup"] == group_name]

    if len(group_df) == 0:
        return []

    phrase_counter = Counter()
    phrase_doc_counter = Counter()
    phrase_types = {}

    for _, row in group_df.iterrows():
        phrases = _extract_phrases(row)
        seen = set()
        for phrase, ptype in phrases:
            phrase_counter[phrase] += 1
            if phrase not in seen:
                phrase_doc_counter[phrase] += 1
                seen.add(phrase)
            phrase_types[phrase] = ptype

    if not phrase_counter:
        return []

    max_count = max(phrase_counter.values())

    results = []
    for phrase, count in phrase_counter.most_common(200):
        weight = count / max_count
        results.append({
            "word": phrase,
            "weight": round(weight, 4),
            "count": count,
            "type": phrase_types.get(phrase, "unigram"),
        })

    return results


# Pre-compute at import time
_WESTERN_CLOUD = _compute_wordcloud(EVENTS, "Western")
_CHINESE_CLOUD = _compute_wordcloud(EVENTS, "Chinese")


@router.get("")
def get_wordcloud(
    top_n: int = Query(default=50, ge=1, le=200),
):
    return {
        "groups": {
            "Western": _WESTERN_CLOUD[:top_n],
            "Chinese": _CHINESE_CLOUD[:top_n],
        },
    }
