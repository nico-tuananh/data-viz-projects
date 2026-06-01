"""Fetch article titles and snippets from GDELT SOURCEURL values."""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; COMP4010Research/1.0; +https://vinuni.edu.vn)"
DEFAULT_TIMEOUT = 10
DEFAULT_WORKERS = 8


def _extract_page_text(html: str) -> tuple[str, str]:
    """Return (title, snippet) from HTML."""
    soup = BeautifulSoup(html[:500_000], "html.parser")

    title = ""
    for tag in (
        soup.find("meta", property="og:title"),
        soup.find("meta", attrs={"name": "twitter:title"}),
    ):
        if tag and tag.get("content"):
            title = tag["content"].strip()
            break
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()

    snippet = ""
    for tag in (
        soup.find("meta", property="og:description"),
        soup.find("meta", attrs={"name": "description"}),
        soup.find("meta", attrs={"name": "twitter:description"}),
    ):
        if tag and tag.get("content"):
            snippet = tag["content"].strip()
            break

    return title[:500], snippet[:1000]


def _fetch_one(url: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """Fetch a single URL. Returns a cache row dict."""
    row = {
        "url": url,
        "title": "",
        "snippet": "",
        "status": "failed",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            allow_redirects=True,
        )
        if resp.status_code != 200 or not resp.text:
            row["status"] = f"http_{resp.status_code}"
            return row

        title, snippet = _extract_page_text(resp.text)
        if title or snippet:
            row["title"] = title
            row["snippet"] = snippet
            row["status"] = "ok"
        else:
            row["status"] = "empty"
    except requests.RequestException as exc:
        row["status"] = re.sub(r"[^a-z0-9_]", "_", str(exc).lower())[:40]

    return row


def load_url_cache(cache_path: Path) -> pd.DataFrame:
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    return pd.DataFrame(columns=["url", "title", "snippet", "status", "fetched_at"])


def save_url_cache(cache_path: Path, cache_df: pd.DataFrame) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_df.drop_duplicates(subset=["url"], keep="last").to_parquet(cache_path, index=False)


def scrape_urls(
    urls: list[str],
    cache_path: Path,
    workers: int = DEFAULT_WORKERS,
    timeout: int = DEFAULT_TIMEOUT,
    refresh_failed: bool = False,
) -> pd.DataFrame:
    """
    Scrape URLs with a persistent parquet cache.
    Only fetches URLs that are missing from cache (or failed, if refresh_failed=True).
    """
    urls = sorted({u.strip() for u in urls if u and str(u).startswith("http")})
    cache_df = load_url_cache(cache_path)

    if len(cache_df):
        cached_urls = set(cache_df["url"].astype(str))
        if refresh_failed:
            retry = set(
                cache_df.loc[cache_df["status"] != "ok", "url"].astype(str)
            )
            to_fetch = [u for u in urls if u not in cached_urls or u in retry]
        else:
            to_fetch = [u for u in urls if u not in cached_urls]
    else:
        to_fetch = urls

    print(f"URL scrape: {len(urls):,} target URLs, {len(to_fetch):,} to fetch "
          f"({len(cache_df):,} already cached)")

    if not to_fetch:
        return cache_df

    t0 = time.time()
    new_rows = []
    done = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_fetch_one, url, timeout): url for url in to_fetch}
        for fut in as_completed(futures):
            new_rows.append(fut.result())
            done += 1
            if done % 100 == 0 or done == len(to_fetch):
                ok = sum(1 for r in new_rows if r["status"] == "ok")
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed else 0
                remaining = (len(to_fetch) - done) / rate if rate else 0
                print(
                    f"  scraped {done:,}/{len(to_fetch):,} "
                    f"({ok:,} ok) — ~{remaining / 60:.1f} min left"
                )

    if new_rows:
        cache_df = pd.concat([cache_df, pd.DataFrame(new_rows)], ignore_index=True)
        cache_df = cache_df.drop_duplicates(subset=["url"], keep="last")
        save_url_cache(cache_path, cache_df)

    ok_total = (cache_df["status"] == "ok").sum()
    elapsed = time.time() - t0
    print(
        f"URL scrape done in {elapsed / 60:.1f} min — "
        f"{ok_total:,}/{len(cache_df):,} cached URLs with text"
    )
    return cache_df


def enrich_events_with_scraped_text(
    df: pd.DataFrame,
    cache_path: Path,
    media_groups: list[str] | None = None,
    scrape_all_urls: bool = False,
    workers: int = DEFAULT_WORKERS,
    timeout: int = DEFAULT_TIMEOUT,
) -> pd.DataFrame:
    """Join scraped title/snippet onto the events dataframe."""
    if scrape_all_urls:
        target = df
    elif media_groups:
        target = df[df["MediaGroup"].isin(media_groups)]
    else:
        target = df[df["MediaGroup"].isin(["Western", "Chinese"])]

    urls = target["SOURCEURL"].dropna().astype(str).tolist()
    cache_df = scrape_urls(urls, cache_path, workers=workers, timeout=timeout)

    title_map = dict(zip(cache_df["url"], cache_df["title"]))
    snippet_map = dict(zip(cache_df["url"], cache_df["snippet"]))
    status_map = dict(zip(cache_df["url"], cache_df["status"]))

    out = df.copy()
    out["ArticleTitle"] = out["SOURCEURL"].map(title_map).fillna("")
    out["ArticleSnippet"] = out["SOURCEURL"].map(snippet_map).fillna("")
    out["ScrapeStatus"] = out["SOURCEURL"].map(status_map).fillna("not_attempted")
    return out