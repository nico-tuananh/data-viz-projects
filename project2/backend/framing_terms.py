"""Shared phrase extraction and contrastive TF-IDF for media framing charts."""

import math
import re
from collections import Counter

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "have",
    "he", "her", "his", "in", "is", "it", "its", "of", "on", "or", "that", "the",
    "their", "they", "this", "to", "was", "were", "will", "with", "you", "your",
    "our", "we", "us", "but", "not", "can", "all", "more", "after", "over", "into",
    "about", "says", "said", "new", "just", "also", "may", "could", "would", "been",
    "one", "two", "first", "last", "year", "years", "day", "days", "week", "news",
    "report", "reports", "latest", "update", "read", "full", "story", "via", "com",
    "www", "http", "https", "html", "amp", "video", "photo", "photos", "live",
}

# GDELT metadata terms that dominate both sides — de-emphasized when article text exists
METADATA_GENERIC = {
    "verbal", "cooperation", "conflict", "diplomatic", "material", "disapprove",
    "reject", "appeal", "coerce", "threaten", "criticize", "denounce", "unknown",
    "other", "unk", "usa", "chn", "states", "united", "china", "chinese", "american",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS]


def _add_ngrams(words: list[str], phrases: list[tuple[str, str]]) -> None:
    for w in words:
        phrases.append((w, "unigram"))
    for i in range(len(words) - 1):
        phrases.append((f"{words[i]} {words[i + 1]}", "bigram"))
    for i in range(len(words) - 2):
        phrases.append((f"{words[i]} {words[i + 1]} {words[i + 2]}", "trigram"))


def _has_article_text(row) -> bool:
    title = str(row.get("ArticleTitle", "")).strip()
    return bool(title) and title.lower() not in ("nan", "none")


def extract_phrases(row) -> list[tuple[str, str]]:
    """Extract phrases from scraped article text, with metadata fallback."""
    phrases: list[tuple[str, str]] = []

    if _has_article_text(row):
        title = str(row.get("ArticleTitle", ""))
        snippet = str(row.get("ArticleSnippet", ""))
        words = _tokenize(f"{title} {snippet}")
        _add_ngrams(words, phrases)
        return phrases

    # Fallback: GDELT event metadata (same pool for both sides — less distinctive)
    domain = str(row.get("SourceDomain", "")).lower()
    if domain and domain not in ("unknown", "nan", "none"):
        parts = domain.split(".")
        if parts[0] and len(parts[0]) > 2 and parts[0] not in STOPWORDS:
            phrases.append((parts[0], "unigram"))

    for field in ("EventTypeDesc", "QuadClassDesc"):
        text = str(row.get(field, ""))
        if text and text.lower() not in ("other", "unknown", "nan", "none"):
            words = _tokenize(text.replace("/", " "))
            _add_ngrams(words, phrases)

    for col in ("Actor1Name", "Actor2Name"):
        name = str(row.get(col, ""))
        if name and name.lower() not in ("nan", "none", ""):
            words = _tokenize(name)
            _add_ngrams(words, phrases)

    cc = str(row.get("ActionGeo_CountryCode", "")).lower()
    if cc and cc not in ("unk", "nan", "none", ""):
        phrases.append((cc, "unigram"))

    return phrases


def extract_terms(row) -> list[str]:
    """Unigrams only — used by the keyword framing chart."""
    return [p for p, _ in extract_phrases(row) if " " not in p]


def compute_distinctive_phrases(
    df,
    group_name: str,
    other_group_name: str,
    top_n: int = 200,
    min_doc_count: int = 2,
) -> list[dict]:
    """
    Contrastive TF-IDF-style scoring: terms frequent in this group but not the other.
    score = group_freq * log1p(group_freq / (other_freq + epsilon))
    """
    group_df = df[df["MediaGroup"] == group_name]
    other_df = df[df["MediaGroup"] == other_group_name]

    if len(group_df) == 0:
        return []

    group_counter: Counter = Counter()
    group_doc_counter: Counter = Counter()
    other_counter: Counter = Counter()
    phrase_types: dict[str, str] = {}

    for _, row in group_df.iterrows():
        seen: set[str] = set()
        for phrase, ptype in extract_phrases(row):
            if phrase in METADATA_GENERIC and not _has_article_text(row):
                continue
            group_counter[phrase] += 1
            phrase_types[phrase] = ptype
            if phrase not in seen:
                group_doc_counter[phrase] += 1
                seen.add(phrase)

    for _, row in other_df.iterrows():
        for phrase, _ in extract_phrases(row):
            other_counter[phrase] += 1

    group_total = max(len(group_df), 1)
    other_total = max(len(other_df), 1)
    results = []

    for phrase, count in group_counter.items():
        if group_doc_counter[phrase] < min_doc_count:
            continue
        group_freq = count / group_total
        other_freq = other_counter.get(phrase, 0) / other_total
        score = group_freq * math.log1p(group_freq / (other_freq + 0.001))
        if score <= 0:
            continue
        results.append({
            "word": phrase,
            "keyword": phrase,
            "tfidf_score": round(score, 6),
            "count": count,
            "doc_count": group_doc_counter[phrase],
            "type": phrase_types.get(phrase, "unigram"),
        })

    results.sort(key=lambda x: x["tfidf_score"], reverse=True)
    results = results[:top_n]

    if results:
        max_score = results[0]["tfidf_score"] or 1.0
        for item in results:
            item["weight"] = round(item["tfidf_score"] / max_score, 4)

    return results


def compute_distinctive_keywords(df, group_name: str, other_group_name: str, top_n: int = 100) -> list[dict]:
    """Unigram-only distinctive terms for the keyword framing chart."""
    phrases = compute_distinctive_phrases(df, group_name, other_group_name, top_n=top_n * 3)
    unigrams = [p for p in phrases if p["type"] == "unigram"]
    return unigrams[:top_n]