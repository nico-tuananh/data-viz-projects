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

# Word-cloud-only noise filters — applied in word_cloud_terms() only.
# framing_dataframe() and extract_phrases() are unaffected.
_WC_NOISE_UNIGRAMS: frozenset[str] = frozenset({
    # Timestamp prefix artifacts (e.g. "Jan 2025: headline text…")
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
    "2025", "2024", "2023",
    # Domain / outlet name leakage past JUNK_TITLE_ONLY
    "aol", "cnn", "globe", "marketscreener",
    # Timezone / wire-service boilerplate
    "edt", "pst", "gmt", "utc", "est",
    # Generic discourse tokens — high frequency, zero narrative content
    "what", "why", "how", "who", "off", "out", "most", "them", "sen",
    # Named-entity first-name / standalone-title noise: no narrative meaning alone.
    # "donald" + "president" also cascade to block any phrase containing them
    # via _is_wordcloud_noise (e.g. "donald trump", "president trump" are suppressed).
    "donald", "former", "president",
    # Dataset-specific noise: not part of the tariff / trade-war narrative
    "canton", "karen", "shen", "yun", "boston", "healey",
    # Journalist / byline names that leak into MarketScreener/outlet headlines
    "alicja", "hagopian", "millie",
    # French tokens not caught by FRENCH_STOPWORDS (Chinese state-media FR editions)
    "porte", "parole", "exhorte", "cesser", "iowan",
    # Domain artifact
    "org",
    # Outlet name components leaking as standalone tokens
    "online",    # "People's Daily Online"
    # Generic function words that slip past STOPWORDS in this dataset
    "which", "lacks", "justification",
    # Niche topics unrelated to tariff narrative in this dataset
    "museum",
})

_WC_NOISE_PHRASES: frozenset[str] = frozenset({
    "shen yun",
    "daily signal",        # outlet name, not a narrative phrase
    "jan 2025",
    "boston globe",
    "2025 edt",
    "edt marketscreener",
    "2025 edt marketscreener",
    "chinese communist",   # fragment of "chinese communist party"; suppress in favour of full trigram
    "united state",        # singularized "united states"; generic geo-ref, not a narrative signal
})


# Generic title/role prefix tokens stripped before computing a phrase's anchor.
# "president" / "former" are already in _WC_NOISE_UNIGRAMS so they never reach
# this stage; kept here as a safety net for future additions.
_TITLE_TOKENS: frozenset[str] = frozenset({
    "president", "former", "vice", "prime", "minister", "secretary",
    "director", "general", "chief", "senior",
})


def _anchor_token(term: str, unigram_scores: dict[str, float]) -> str:
    """
    Return the dominant token of a phrase for entity-cluster assignment.

    Strips generic title prefixes, then picks whichever remaining token has
    the highest unigram distinctiveness score.  This keeps topic words like
    "tariffs" and "war" from bridging unrelated clusters — only the
    highest-scoring proper-noun token drives grouping.

    Example: "trump tariffs" → trump (score 0.42) beats tariffs (0.13).
    """
    tokens = [w for w in term.split() if w not in _TITLE_TOKENS]
    if not tokens:
        return term
    return max(tokens, key=lambda w: unigram_scores.get(w, 0.0))


def _deduplicate_by_entity(
    terms: list[dict],
    unigram_scores: dict[str, float],
    max_per_entity: int = 2,
) -> list[dict]:
    """
    Keep at most ``max_per_entity`` terms per entity cluster.

    Cluster identity is the anchor token (highest-scoring unigram component of
    the phrase).  Within each cluster the top terms by contrastive-TF-IDF score
    survive; the rest are suppressed.

    Because the anchor is score-driven, topic words like "tariffs" or "war"
    cannot bridge disparate clusters — only the dominant entity token does.
    """
    clusters: dict[str, list[dict]] = {}
    for t in terms:
        anchor = _anchor_token(t["term"], unigram_scores)
        clusters.setdefault(anchor, []).append(t)

    result: list[dict] = []
    for cluster_terms in clusters.values():
        top = sorted(cluster_terms, key=lambda t: -t["score"])[:max_per_entity]
        result.extend(top)
    return result


# Two-token named entities (person names, place names, institutions).
# When the full-phrase form is present in the selection, its isolated component
# unigrams are suppressed — they add no information beyond the full name.
# Suppression only fires if the full phrase was actually selected; standalone
# components are kept unchanged when no full phrase exists.
_CANONICAL_ENTITY_TOKENS: tuple[frozenset[str], ...] = (
    frozenset({"elon", "musk"}),       # Elon Musk
    frozenset({"hong", "kong"}),       # Hong Kong
    frozenset({"xi", "jinping"}),      # Xi Jinping
    frozenset({"joe", "biden"}),       # Joe Biden
    frozenset({"white", "house"}),     # White House
    frozenset({"united", "states"}),   # United States
    frozenset({"people", "daily"}),    # People's Daily (Chinese state media)
)


def _suppress_entity_fragments(terms: list[dict]) -> list[dict]:
    """
    Remove unigrams that are mere name-fragments of a full entity phrase
    already present in the set.

    For each canonical entity pair (e.g. {"elon", "musk"}), if any multi-word
    phrase containing all tokens of the pair is in the selected terms, the
    standalone unigrams for those tokens are dropped.  The full phrase ("elon
    musk") is retained; the isolated fragments ("elon", "musk") are not.

    This pass runs after anchor-based dedup and handles the case where two
    roughly equal-scoring component tokens cannot be anchored to each other
    by score alone (e.g. hong ≈ kong, elon < musk but both meaningful).
    """
    term_set = {t["term"] for t in terms}
    to_suppress: set[str] = set()
    for entity_tokens in _CANONICAL_ENTITY_TOKENS:
        full_phrase_present = any(
            entity_tokens.issubset(set(phrase.split()))
            for phrase in term_set
            if " " in phrase
        )
        if full_phrase_present:
            to_suppress.update(entity_tokens)
    return [t for t in terms if not (t["type"] == "unigram" and t["term"] in to_suppress)]


def _suppress_subphrase_bigrams(terms: list[dict]) -> list[dict]:
    """
    Suppress bigrams that are contiguous sub-sequences of a trigram already
    in the set when the trigram's score is at least as high as the bigram's.

    Examples that ARE suppressed:
      "communist party"  (score 0.008) ← "chinese communist party" (0.018)
      "jinping four"     (score 0.085) ← "jinping four decade"     (0.085)
      "american firms"   (score 0.044) ← "dialogues american firms" (0.044)

    Examples that are NOT suppressed (bigram scores higher than parent trigram):
      "regular press"    (score 0.049)   "regular press conference" (0.046)
      "trade war"        (score 0.054) — no trigram in set contains it
    """
    trigrams = [t for t in terms if t["type"] == "trigram"]
    if not trigrams:
        return terms

    to_suppress: set[str] = set()
    for bigram_t in [t for t in terms if t["type"] == "bigram"]:
        b_tok = bigram_t["term"].split()   # always 2 tokens
        for tri_t in trigrams:
            t_tok = tri_t["term"].split()  # always 3 tokens
            is_sub = (b_tok == t_tok[:2]) or (b_tok == t_tok[1:])
            if is_sub and tri_t["score"] >= bigram_t["score"]:
                to_suppress.add(bigram_t["term"])
                break

    return [t for t in terms if t["term"] not in to_suppress]


def _domain_stem(domain: str) -> str:
    return str(domain).lower().replace("www.", "").split(".")[0]


# Matches singular possessive: Trump's / China's (straight and curly apostrophe)
_POSSESSIVE_S_RE = re.compile(r"['']\s*s\b")
# Matches plural possessive trailing apostrophe: countries' / exporters'
_PLURAL_POSS_RE = re.compile(r"(?<=s)['']\b")


def _normalize_possessives(text: str) -> str:
    """Strip possessive suffixes: Trump's → Trump, countries' → countries."""
    text = _POSSESSIVE_S_RE.sub("", text)
    text = _PLURAL_POSS_RE.sub("", text)
    return text


# Words that look plural but are already singular (or are mass/invariant nouns).
# The singularize rules below are conservative and handle most of these through
# suffix guards (-ss, -is, -us, -ics, -esses), but explicit exceptions cover
# the remaining edge cases.
_PLURAL_EXCEPTIONS: frozenset[str] = frozenset({
    "news", "means", "series", "species", "corps", "times",
    "headquarters", "crossroads",
})


def _singularize(word: str) -> str:
    """
    Conservative English plural → singular normalization.

    Applied per-token inside _tokenize so that all downstream phrase
    extraction and TF-IDF scoring operates on canonical singular forms,
    preventing duplicate unigrams such as tariff/tariffs.

    Rules (in priority order):
      -ies  → -y       policies → policy, countries → country
      -xes  → -x       taxes → tax, foxes → fox
      -s    → ''       tariffs → tariff, sanctions → sanction
                       (guarded: no change for -ss, -is, -us, -ics, -esses endings)
    Words of 3 chars or fewer are never modified (protects "us", "has", etc.).
    """
    if len(word) <= 3 or word in _PLURAL_EXCEPTIONS:
        return word
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("xes") and len(word) > 4:
        return word[:-2]
    if (word.endswith("s")
            and not word.endswith(("ss", "is", "us", "ias", "eas", "ics", "esses"))
            and len(word) > 4):
        return word[:-1]
    return word


def _tokenize(text: str) -> list[str]:
    text = _normalize_possessives(text.lower())
    raw = re.findall(r"[a-z0-9]+", text)
    result: list[str] = []
    for w in raw:
        if len(w) <= 2:
            continue
        # Stopword check on the ORIGINAL token so that French/English stopwords
        # for plural forms (e.g. "etats" in FRENCH_STOPWORDS) are not bypassed
        # after singularization produces a form not in the stopword set.
        if w in STOPWORDS or w in FRENCH_STOPWORDS:
            continue
        result.append(_singularize(w))
    return result


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


def _is_wordcloud_noise(item: dict) -> bool:
    term = item["term"].lower()
    if item["type"] == "unigram":
        return term in _WC_NOISE_UNIGRAMS
    if term in _WC_NOISE_PHRASES:
        return True
    # Block multi-word phrases whose any component word is noise — catches
    # journalist bylines, timestamp fragments, and French tokens that leaked
    # in via sliding-window n-gram generation.
    return any(w in _WC_NOISE_UNIGRAMS for w in term.split())


def _noise_filtered_candidates(
    df: pd.DataFrame,
    group: str,
    other: str,
    pool_n: int,
) -> tuple[list[dict], dict[str, float]]:
    """
    Shared pipeline used by both word_cloud_terms() and framing_dataframe().

    Returns (candidates, unigram_scores) after noise filtering.
    The three dedup passes are intentionally left to the caller so each
    function can apply them to its own final selection.
    """
    candidates = [
        t for t in compute_distinctive_phrases(df, group, other, top_n=pool_n)
        if not _is_wordcloud_noise(t)
    ]
    unigram_scores = {t["term"]: t["score"] for t in candidates if t["type"] == "unigram"}
    return candidates, unigram_scores


def _apply_dedup_passes(
    selection: list[dict],
    unigram_scores: dict[str, float],
) -> list[dict]:
    """Apply the three deduplication passes in order."""
    selection = _deduplicate_by_entity(selection, unigram_scores, max_per_entity=2)
    selection = _suppress_entity_fragments(selection)
    selection = _suppress_subphrase_bigrams(selection)
    return selection


def word_cloud_terms(df: pd.DataFrame, top_n: int = 80) -> pd.DataFrame:
    """
    Slot-allocated word cloud terms.

    Bigrams and trigrams receive guaranteed slots so meaningful phrases are
    not buried under high-frequency unigrams in the contrastive-TF-IDF ranking.

    Slot split (per media group, of top_n):
      unigrams  35 %  — key single-word signals
      bigrams   45 %  — primary 2-word phrase layer
      trigrams  20 %  — contextual 3-word phrases (remainder)

    If a tier has fewer clean candidates than its quota the shortfall is filled
    from the remaining scored candidates in score order, so total is always top_n.
    """
    n_uni = max(1, round(top_n * 0.35))
    n_bi  = max(1, round(top_n * 0.45))
    n_tri = top_n - n_uni - n_bi  # remainder ensures exact total

    rows: list[dict] = []
    for group, other in [("Western", "Chinese"), ("Chinese", "Western")]:
        candidates, unigram_scores = _noise_filtered_candidates(
            df, group, other, pool_n=top_n * 8
        )

        unigrams = [t for t in candidates if t["type"] == "unigram"]
        bigrams  = [t for t in candidates if t["type"] == "bigram"]
        # Require ≥3 docs for trigrams to suppress sliding-window fragments
        # that score high from a single multi-sentence article.
        trigrams = [t for t in candidates if t["type"] == "trigram" and t["doc_count"] >= 3]

        taken = unigrams[:n_uni] + bigrams[:n_bi] + trigrams[:n_tri]

        # Fill any shortfall from the remaining pool in score order.
        shortfall = top_n - len(taken)
        if shortfall > 0:
            seen = {t["term"] for t in taken}
            extras = sorted(
                (t for t in candidates if t["term"] not in seen),
                key=lambda x: -x["score"],
            )
            taken.extend(extras[:shortfall])

        taken = _apply_dedup_passes(taken, unigram_scores)
        rows.extend(taken)

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def framing_dataframe(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """
    Ranked TF-IDF terms for the diverging bar chart.

    Uses the same noise-filtered candidate pool and deduplication passes as
    word_cloud_terms() so both visuals draw from an identical cleaned term set.
    Includes unigrams, bigrams, and trigrams (not unigrams only).
    """
    rows: list[dict] = []
    for group, other, sign in [("Western", "Chinese", 1), ("Chinese", "Western", -1)]:
        candidates, unigram_scores = _noise_filtered_candidates(
            df, group, other, pool_n=top_n * 8
        )
        # Pre-select a generous window before dedup to give the passes enough
        # context (dedup can only remove, never add terms).
        pre = sorted(candidates, key=lambda t: -t["score"])[: top_n * 3]
        selection = _apply_dedup_passes(pre, unigram_scores)
        # Final top_n by score after dedup.
        selection = sorted(selection, key=lambda t: -t["score"])[:top_n]
        for item in selection:
            item = item.copy()
            item["signed_score"] = item["score"] * sign
            rows.append(item)
    return pd.DataFrame(rows)
