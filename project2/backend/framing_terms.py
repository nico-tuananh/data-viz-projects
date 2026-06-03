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

# French function words common in Chinese-state-media French editions
FRENCH_STOPWORDS = {
    "les", "des", "etats", "unis", "aux", "pour", "sur", "dans", "une", "qui", "est",
    "chine", "affaires", "entre", "avec", "sont", "par", "cette", "ces", "son", "ses",
}

# GDELT event-type labels — not headline framing
METADATA_GENERIC = {
    "verbal", "cooperation", "conflict", "diplomatic", "material", "disapprove",
    "reject", "appeal", "coerce", "threaten", "criticize", "denounce", "unknown",
    "other", "unk", "usa", "chn", "states", "united", "china", "chinese", "american",
    "verbal cooperation", "diplomatic cooperation", "verbal conflict", "material conflict",
    "disapprove reject", "material cooperation",
}

# Site branding / outlet names that aren't story framing
SITE_BOILERPLATE = {
    "people's daily online", "people's daily", "daily online", "people's",
    "china org", "xinhua news", "global times", "zerohedge", "yahoo news",
    "yahoo finance", "bbc news", "cnn news", "the guardian", "huffpost",
    "boston globe", "boston herald",
}

# Domain stems for known outlets (first label before the TLD)
OUTLET_STEMS = {
    "yahoo", "zerohedge", "newsweek", "marketscreener", "nypost", "cnn", "aol",
    "ibtimes", "reuters", "bbc", "foxnews", "bloomberg", "forbes", "cnbc",
    "theguardian", "dailymail", "independent", "breitbart", "businessinsider",
    "foreignpolicy", "theepochtimes", "globalsecurity", "digitaljournal",
    "rttnews", "scmp", "xinhuanet", "chinadaily", "globaltimes", "cgtn",
    "people", "chinanews", "ecns", "thestandard", "caixin", "voanews",
    "economist", "telegraph", "mirror", "express", "newsmax", "politico",
    "thehill", "axios", "npr", "nbcnews", "cbsnews", "abcnews", "usatoday",
    "nytimes", "washingtonpost", "wsj", "latimes", "bostonglobe", "time",
    "news", "finance", "english", "french", "arabic", "online", "daily",
    "xinhua", "globe", "boston",
}


def _domain_stem(domain: str) -> str:
    domain = str(domain).lower().replace("www.", "")
    return domain.split(".")[0]


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if len(w) > 2 and w not in STOPWORDS and w not in FRENCH_STOPWORDS]


def _add_ngrams(words: list[str], phrases: list[tuple[str, str]]) -> None:
    for w in words:
        phrases.append((w, "unigram"))
    for i in range(len(words) - 1):
        phrases.append((f"{words[i]} {words[i + 1]}", "bigram"))
    for i in range(len(words) - 2):
        phrases.append((f"{words[i]} {words[i + 1]} {words[i + 2]}", "trigram"))


def _is_usable_headline(row) -> bool:
    """True when scraped title looks like a real headline, not a site name."""
    title = str(row.get("ArticleTitle", "")).strip()
    if not title or title.lower() in ("nan", "none"):
        return False

    title_lower = title.lower()
    domain_stem = _domain_stem(row.get("SourceDomain", ""))

    if title_lower in SITE_BOILERPLATE or title_lower == domain_stem:
        return False
    if title_lower.replace(" ", "") == domain_stem.replace("the", ""):
        return False
    if title_lower in OUTLET_STEMS or domain_stem in title_lower.split() and len(title_lower.split()) <= 2:
        return False

    words = _tokenize(title)
    return len(words) >= 3


def _is_blocked_phrase(phrase: str, source_domain: str = "") -> bool:
    phrase_lower = phrase.lower().strip()
    if phrase_lower in METADATA_GENERIC or phrase_lower in SITE_BOILERPLATE:
        return True
    if phrase_lower in OUTLET_STEMS:
        return True

    stem = _domain_stem(source_domain)
    if phrase_lower == stem or phrase_lower.replace("the", "") == stem.replace("the", ""):
        return True

    parts = phrase_lower.split()
    if len(parts) == 1 and parts[0] in OUTLET_STEMS:
        return True
    if all(p in STOPWORDS | FRENCH_STOPWORDS | OUTLET_STEMS | METADATA_GENERIC for p in parts):
        return True

    return False


def extract_phrases(row) -> list[tuple[str, str]]:
    """Extract phrases from usable scraped headlines only."""
    phrases: list[tuple[str, str]] = []

    if not _is_usable_headline(row):
        return phrases

    title = str(row.get("ArticleTitle", ""))
    snippet = str(row.get("ArticleSnippet", ""))
    words = _tokenize(f"{title} {snippet}")
    _add_ngrams(words, phrases)

    domain = str(row.get("SourceDomain", ""))
    return [(p, t) for p, t in phrases if not _is_blocked_phrase(p, domain)]


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
    Only uses rows with usable scraped headlines (real article titles).
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
