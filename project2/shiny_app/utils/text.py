"""Headline cleanup and contrastive framing terms."""

from __future__ import annotations

import math
import re
from collections import Counter

import pandas as pd


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

FRENCH_STOPWORDS = {
    "les", "des", "etats", "unis", "aux", "pour", "sur", "dans", "une", "qui", "est",
    "chine", "affaires", "entre", "avec", "sont", "par", "cette", "ces", "son", "ses",
}

METADATA_GENERIC = {
    "verbal", "cooperation", "conflict", "diplomatic", "material", "disapprove",
    "reject", "appeal", "coerce", "threaten", "criticize", "denounce", "unknown",
    "other", "unk", "usa", "chn", "states", "united", "china", "chinese", "american",
    "verbal cooperation", "diplomatic cooperation", "verbal conflict", "material conflict",
    "disapprove reject", "material cooperation",
}

JUNK_TITLE_ONLY = {
    "zerohedge", "yahoo", "yahoo news", "yahoo finance", "bbc news", "cnn news",
    "people's daily online", "people's daily", "global times", "xinhua news",
    "the guardian", "huffpost", "boston globe", "boston herald", "newsweek",
}

SITE_BOILERPLATE_PHRASES = {
    "people's daily online", "daily online", "people's daily", "china org",
    "yahoo finance", "bbc news", "cnn news", "the guardian",
    "boston globe", "boston herald",
}


def _domain_stem(domain: str) -> str:
    return str(domain).lower().replace("www.", "").split(".")[0]


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS and w not in FRENCH_STOPWORDS]


def _is_usable_headline(row: pd.Series) -> bool:
    title = str(row.get("ArticleTitle", "")).strip()
    if not title or title.lower() in {"nan", "none"}:
        return False
    title_lower = title.lower()
    domain_stem = _domain_stem(row.get("SourceDomain", ""))
    if title_lower in JUNK_TITLE_ONLY or title_lower == domain_stem:
        return False
    if title_lower.replace(" ", "") == domain_stem.replace("the", ""):
        return False
    if len(title_lower.split()) <= 2 and domain_stem in title_lower:
        return False
    return len(_tokenize(title)) >= 3


def _is_blocked_phrase(phrase: str) -> bool:
    phrase_lower = phrase.lower().strip()
    if phrase_lower in METADATA_GENERIC or phrase_lower in SITE_BOILERPLATE_PHRASES:
        return True
    parts = phrase_lower.split()
    return all(p in STOPWORDS | FRENCH_STOPWORDS | METADATA_GENERIC for p in parts)


def extract_phrases(row: pd.Series) -> list[tuple[str, str]]:
    if not _is_usable_headline(row):
        return []

    words = _tokenize(f"{row.get('ArticleTitle', '')} {row.get('ArticleSnippet', '')}")
    phrases: list[tuple[str, str]] = [(w, "unigram") for w in words]
    phrases.extend((f"{words[i]} {words[i + 1]}", "bigram") for i in range(len(words) - 1))
    phrases.extend(
        (f"{words[i]} {words[i + 1]} {words[i + 2]}", "trigram")
        for i in range(len(words) - 2)
    )
    return [(p, t) for p, t in phrases if not _is_blocked_phrase(p)]


def compute_distinctive_phrases(
    df: pd.DataFrame,
    group_name: str,
    other_group_name: str,
    top_n: int = 100,
    min_doc_count: int = 2,
) -> list[dict]:
    group_df = df[df["MediaGroup"] == group_name] if "MediaGroup" in df else pd.DataFrame()
    other_df = df[df["MediaGroup"] == other_group_name] if "MediaGroup" in df else pd.DataFrame()
    if group_df.empty:
        return []

    group_counter: Counter[str] = Counter()
    group_doc_counter: Counter[str] = Counter()
    other_counter: Counter[str] = Counter()
    phrase_types: dict[str, str] = {}

    for _, row in group_df.iterrows():
        seen: set[str] = set()
        for phrase, ptype in extract_phrases(row):
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
    results: list[dict] = []
    for phrase, count in group_counter.items():
        if group_doc_counter[phrase] < min_doc_count:
            continue
        group_freq = count / group_total
        other_freq = other_counter.get(phrase, 0) / other_total
        score = group_freq * math.log1p(group_freq / (other_freq + 0.001))
        if score > 0:
            results.append({
                "term": phrase,
                "score": score,
                "count": count,
                "doc_count": group_doc_counter[phrase],
                "type": phrase_types.get(phrase, "unigram"),
                "group": group_name,
            })

    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_n]


def framing_dataframe(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    rows = []
    for group, other, sign in [("Western", "Chinese", 1), ("Chinese", "Western", -1)]:
        group_count = 0
        for item in compute_distinctive_phrases(df, group, other, top_n=top_n * 3):
            if item["type"] != "unigram":
                continue
            item = item.copy()
            item["signed_score"] = item["score"] * sign
            rows.append(item)
            group_count += 1
            if group_count >= top_n:
                break
    return pd.DataFrame(rows)


def word_cloud_terms(df: pd.DataFrame, top_n: int = 80) -> pd.DataFrame:
    rows = []
    for group, other in [("Western", "Chinese"), ("Chinese", "Western")]:
        rows.extend(compute_distinctive_phrases(df, group, other, top_n=top_n))
    return pd.DataFrame(rows)
