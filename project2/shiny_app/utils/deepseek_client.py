"""DeepSeek API client — key loaded from DEEPSEEK_API_KEY env var only."""
from __future__ import annotations

import os
import re
from pathlib import Path

import requests

# Load .env from project root without overriding already-set env vars
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
except ImportError:
    pass  # python-dotenv optional; fall back to os.environ

_API_URL = "https://api.deepseek.com/chat/completions"
_MODEL   = "deepseek-chat"

SYSTEM_PROMPT = (
    "You are a data visualization assistant for a dashboard analyzing 2025 US–China "
    "tariff-war media coverage using GDELT. "
    "Answer only using the provided dashboard context and methodology. "
    "Be concise, specific, and analytical. "
    "Do not invent numbers — only cite figures present in the context. "
    "If the context does not contain enough information, say what is missing. "
    "Explain charts in plain language. "
    "Avoid political claims beyond what the data directly supports."
)

# ── Local answers (answered instantly, no API call needed) ─────────────────
_LOCAL: dict[str, str] = {
    "tonegap": (
        "**ToneGap** = Western weighted tone − Chinese weighted tone.\n\n"
        "• Positive value → Western coverage is more positive than Chinese.\n"
        "• Negative value → Western coverage is more negative than Chinese.\n\n"
        "In the **Emotional Divergence** section, the amber line tracks this daily "
        "across the filtered date range."
    ),
    "map": (
        "The **Narrative Spread map** shows where GDELT tariff-war events are geocoded.\n\n"
        "• Marker colour = media group  (blue = Western · red/coral = Chinese · grey = Global/Other)\n"
        "• Marker size = event/article volume (log-scaled, capped)\n\n"
        "**Globe · US–China** centres on the Pacific corridor. "
        "**Flat World Map** shows global reach in one frame."
    ),
    "keyword": (
        "**Keyword framing** uses contrastive TF-IDF to score how distinctive a term is "
        "to one media group compared with the other.\n\n"
        "• High Western score → term strongly characterises Western coverage.\n"
        "• High Chinese score → term strongly characterises Chinese coverage.\n\n"
        "The word cloud shows the same signal — larger terms are more distinctive."
    ),
    "forecast": (
        "The **Narrative Gap Forecasting** section compares four models:\n"
        "ARIMA · Holt-Winters · Prophet · TimesFM\n\n"
        "Each is evaluated on a **14-day holdout window** of ToneGap observations. "
        "Lower MAE/RMSE means predictions stayed closer to observed ToneGap. "
        "The best model by MAE is highlighted in the metric cards."
    ),
    "limitation": (
        "Key limitations of this dashboard:\n\n"
        "• GDELT tone is machine-coded and noisy — not human-annotated.\n"
        "• Media group assignment is simplified by outlet domain (not article-level).\n"
        "• Article counts may undercount paywalled or non-English sources.\n"
        "• Event geocoding can be imprecise.\n"
        "• Tone scale (−100 to +100) is relative, not absolute.\n\n"
        "Interpret results as **media-pattern signals**, not ground truth about political intent."
    ),
    "gdelt": (
        "**GDELT** (Global Database of Events, Language, and Tone) monitors worldwide news "
        "and extracts events, actors, locations, and tone scores automatically.\n\n"
        "This dashboard uses GDELT v2 event data from **Feb–Apr 2025**, "
        "filtered to coverage related to the US–China tariff escalation."
    ),
    "mae": (
        "**MAE** (Mean Absolute Error) = average absolute difference between "
        "predicted and observed ToneGap over the 14-day holdout.\n\n"
        "Lower MAE = better predictions. "
        "**RMSE** (Root Mean Squared Error) penalises large errors more heavily than MAE."
    ),
    "western": (
        "**Western media** in this dashboard includes major English-language outlets "
        "from the US, UK, Canada, Australia, and Western Europe "
        "(e.g. Reuters, NYT, BBC, WSJ, FT).\n\n"
        "Western tone typically skews more negative in this dataset, "
        "reflecting economic-impact and trade-war framing."
    ),
    "chinese": (
        "**Chinese media** includes outlets from Mainland China and Hong Kong "
        "(e.g. Xinhua, Global Times, SCMP, China Daily, CGTN).\n\n"
        "Chinese framing often emphasises sovereignty, retaliation rights, and "
        "economic resilience — with a different tone distribution from Western coverage."
    ),
}

_MATCH: dict[str, list[str]] = {
    "tonegap":    ["tonegap", "tone gap", "tone-gap", "tone score"],
    "map":        ["what does the map", "map show", "globe show", "flat map", "narrative spread"],
    "keyword":    ["keyword framing", "keyword", "tf-idf", "tfidf", "contrastive", "framing term"],
    "forecast":   ["forecast model", "which model", "arima", "prophet", "holt", "timesfm",
                   "model perform", "best model", "performs best"],
    "limitation": ["limitation", "caveat", "problem with", "noisy", "reliable", "trust",
                   "main limitation"],
    "gdelt":      ["what is gdelt", "gdelt", "data source", "where does the data come from"],
    "mae":        ["mean absolute", "mae", "rmse", "root mean squared"],
    "western":    ["western media", "western outlet", "western coverage", "what is western"],
    "chinese":    ["chinese media", "chinese outlet", "chinese coverage", "what is chinese"],
}


def get_local_answer(question: str) -> str | None:
    """Return a pre-written answer if the question matches a known topic."""
    q = question.lower()
    for key, keywords in _MATCH.items():
        if any(kw in q for kw in keywords):
            return _LOCAL[key]
    return None


def format_message(text: str) -> str:
    """Convert minimal markdown to HTML for display in the chat panel."""
    # **bold**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Newlines → <br>
    text = text.replace("\n", "<br>")
    return text


def call_deepseek(
    system_prompt: str,
    user_question: str,
    context: str,
    timeout: int = 20,
) -> str:
    """Call DeepSeek chat API synchronously (run in a thread for async callers).

    API key is read from DEEPSEEK_API_KEY environment variable only.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        return (
            "⚙️ **AI assistant is unavailable** — `DEEPSEEK_API_KEY` is not configured.\n\n"
            "If you are running locally: add `DEEPSEEK_API_KEY=sk-...` to a `.env` file "
            "in the project root and restart the app.\n\n"
            "If this is the deployed version: the API key needs to be set as an environment "
            "variable in the shinyapps.io dashboard settings."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Dashboard context:\n{context}\n\nQuestion: {user_question}",
        },
    ]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       _MODEL,
        "messages":    messages,
        "max_tokens":  450,
        "temperature": 0.3,
        "stream":      False,
    }

    try:
        resp = requests.post(_API_URL, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        return "⏱️ Request timed out (>20 s). Try a shorter question or try again."
    except requests.exceptions.ConnectionError:
        return "🔌 Could not reach DeepSeek. Check your internet connection."
    except requests.exceptions.HTTPError:
        code = resp.status_code
        if code == 401:
            return "🔑 Invalid API key — check `DEEPSEEK_API_KEY` in your `.env` file."
        if code == 429:
            return "⏳ Rate limit reached. Wait a moment and try again."
        return f"❌ API error {code}. Please try again."
    except Exception as exc:
        return f"❌ Unexpected error: {str(exc)[:120]}"
