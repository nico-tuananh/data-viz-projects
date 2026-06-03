"""Load and cache parquet datasets for the dashboard backend."""
import math
from pathlib import Path

import pandas as pd

# Railway deploys backend/ only — data lives in backend/data/.
# Fall back to project2/data/ when running locally before the first sync.
DATA_DIR = Path(__file__).parent / "data"
if not (DATA_DIR / "gdelt_events_cleaned.parquet").exists():
    DATA_DIR = Path(__file__).parent.parent / "data"

# Cached DataFrames loaded once at import time
EVENTS = pd.read_parquet(DATA_DIR / "gdelt_events_cleaned.parquet")
DAILY = pd.read_parquet(DATA_DIR / "daily_aggregates.parquet")
WEEKLY = pd.read_parquet(DATA_DIR / "weekly_aggregates.parquet")
TONE_GAP = pd.read_parquet(DATA_DIR / "tone_gap_series.parquet")

# Ensure Date columns are Timestamp
EVENTS["Date"] = pd.to_datetime(EVENTS["Date"])
DAILY["Date"] = pd.to_datetime(DAILY["Date"])
WEEKLY["WeekStart"] = pd.to_datetime(WEEKLY["WeekStart"])
TONE_GAP["Date"] = pd.to_datetime(TONE_GAP["Date"])

MEDIA_GROUPS = EVENTS["MediaGroup"].unique().tolist()
EVENT_DIRECTIONS = EVENTS["EventDirection"].unique().tolist()
DATE_MIN = EVENTS["Date"].min().date().isoformat()
DATE_MAX = EVENTS["Date"].max().date().isoformat()


# ---------------------------------------------------------------------------
# Source-country inference for the Source Origin map
# ---------------------------------------------------------------------------

COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "US": (39.8283, -98.5795),
    "GB": (54.0, -2.0),
    "DE": (51.1657, 10.4515),
    "FR": (46.2276, 2.2137),
    "AU": (-25.2744, 133.7751),
    "CA": (56.1304, -106.3468),
    "CN": (35.8617, 104.1954),
    "JP": (36.2048, 138.2529),
    # Expanded set for TLD-based inference
    "IN": (20.5937, 78.9629),
    "RU": (61.5240, 105.3188),
    "IR": (32.4279, 53.6880),
    "UA": (48.3794, 31.1656),
    "PL": (51.9194, 19.1451),
    "BG": (42.7339, 25.4858),
    "GR": (39.0742, 21.8243),
    "RO": (45.9432, 24.9668),
    "IT": (41.8719, 12.5674),
    "HU": (47.1625, 19.5033),
    "CZ": (49.8175, 15.4730),
    "SK": (48.6690, 19.6990),
    "HR": (45.1000, 15.2000),
    "RS": (44.0165, 21.0059),
    "MK": (41.6086, 21.7453),
    "FI": (61.9241, 25.7482),
    "SE": (60.1282, 18.6435),
    "NO": (60.4720, 8.4689),
    "DK": (56.2639, 9.5018),
    "IE": (53.1424, -7.6921),
    "CH": (46.8182, 8.2275),
    "AT": (47.5162, 14.5501),
    "BE": (50.5039, 4.4699),
    "NL": (52.1326, 5.2913),
    "PT": (39.3999, -8.2245),
    "ES": (40.4637, -3.7492),
    "BR": (-14.2350, -51.9253),
    "MX": (23.6345, -102.5528),
    "NZ": (-40.9006, 174.8860),
    "PK": (30.3753, 69.3451),
    "BD": (23.6850, 90.3563),
    "NG": (9.0820, 8.6753),
    "KE": (-0.0236, 37.9062),
    "ZA": (-30.5595, 22.9375),
    "AZ": (40.1431, 47.5769),
    "TR": (38.9637, 35.2433),
    "SG": (1.3521, 103.8198),
    "MY": (4.2105, 101.9758),
    "TH": (15.8700, 100.9925),
    "PH": (12.8797, 121.7740),
    "HK": (22.3193, 114.1694),
    "MO": (22.1987, 113.5439),
    "TW": (23.6978, 120.9605),
    "KR": (35.9078, 127.7669),
    "PE": (-9.1900, -75.0152),
    "IL": (31.0461, 34.8516),
    "SA": (23.8859, 45.0792),
    "AE": (23.4241, 53.8475),
    "IS": (64.9631, -19.0208),
    "BS": (25.0343, -77.3963),
    "GL": (72.0, -40.0),
    "QA": (25.3553, 51.1839),
}

# Country-code TLD → ISO country mapping for domain inference
TLD_COUNTRY: dict[str, str] = {
    ".uk": "GB", ".au": "AU", ".ca": "CA", ".cn": "CN", ".jp": "JP",
    ".in": "IN", ".ru": "RU", ".ir": "IR", ".ua": "UA", ".pl": "PL",
    ".bg": "BG", ".gr": "GR", ".ro": "RO", ".it": "IT", ".hu": "HU",
    ".cz": "CZ", ".sk": "SK", ".hr": "HR", ".rs": "RS", ".mk": "MK",
    ".fi": "FI", ".se": "SE", ".no": "NO", ".dk": "DK", ".ie": "IE",
    ".ch": "CH", ".at": "AT", ".be": "BE", ".nl": "NL", ".pt": "PT",
    ".es": "ES", ".br": "BR", ".mx": "MX", ".nz": "NZ", ".pk": "PK",
    ".bd": "BD", ".ng": "NG", ".ke": "KE", ".za": "ZA", ".az": "AZ",
    ".tr": "TR", ".sg": "SG", ".my": "MY", ".th": "TH", ".ph": "PH",
    ".hk": "HK", ".mo": "MO", ".tw": "TW", ".kr": "KR", ".pe": "PE",
    ".il": "IL", ".sa": "SA", ".ae": "AE", ".is": "IS", ".fr": "FR",
    ".de": "DE", ".bs": "BS",
}

# Domains that should map to a specific country despite their TLD
DOMAIN_OVERRIDES: dict[str, tuple[str, float, float]] = {
    # Hong Kong outlets (SCMP is HK, not mainland China)
    "scmp.com": ("HK", *COUNTRY_COORDS["HK"]),
    # The Diplomat is HQ'd in Tokyo
    "thediplomat.com": ("JP", *COUNTRY_COORDS["JP"]),
    # Radio Free Europe / Radio Liberty — Prague
    "slobodnaevropa.org": ("CZ", *COUNTRY_COORDS["CZ"]),
    "rferl.org": ("CZ", *COUNTRY_COORDS["CZ"]),
    # .gov.cn always Chinese state
    "gov.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # news.cn is Xinhua
    "news.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # .edu.cn always Chinese
    "edu.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # ce.cn is China Economic Net (Xinhua)
    "ce.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # .com.cn always Chinese
    "com.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # org.cn always Chinese
    "org.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # people.com.cn is People's Daily
    "people.com.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # chinamil.com.cn is PLA
    "chinamil.com.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # bjreview.com.cn is Beijing Review
    "bjreview.com.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # shine.cn is Shanghai Daily
    "shine.cn": ("CN", *COUNTRY_COORDS["CN"]),
    # Indian outlets on .com
    "ndtv.com": ("IN", *COUNTRY_COORDS["IN"]),
    "indiatimes.com": ("IN", *COUNTRY_COORDS["IN"]),
    "thehindu.com": ("IN", *COUNTRY_COORDS["IN"]),
    # Pakistani outlet on .tv TLD
    "samaa.tv": ("PK", *COUNTRY_COORDS["PK"]),
    # Bulgarian outlet on .com
    "standartnews.com": ("BG", *COUNTRY_COORDS["BG"]),
    # Deutsche Welle on .com
    "dw.com": ("DE", *COUNTRY_COORDS["DE"]),
    # France 24 on .com
    "france24.com": ("FR", *COUNTRY_COORDS["FR"]),
    # Euronews on .com
    "euronews.com": ("FR", *COUNTRY_COORDS["FR"]),
    # Al Jazeera
    "aljazeera.com": ("QA", *COUNTRY_COORDS["QA"]),
}


def _infer_source_country(domain: str) -> tuple[str, float, float] | None:
    """Map a news domain to an approximate (country, lat, lon)."""
    d = str(domain).lower()
    # Strip port suffixes like :443
    d = d.split(":")[0]

    # 1. Domain-specific overrides (exact or suffix match, longest first)
    for suffix, override in sorted(DOMAIN_OVERRIDES.items(), key=lambda x: -len(x[0])):
        if d == suffix or d.endswith("." + suffix) or d.endswith(suffix):
            return override

    # 2. Keyword-based detection for outlets where TLD is ambiguous
    chinese_keywords = [
        "xinhuanet", "chinadaily", "globaltimes", "cgtn", "cctv",
        "china.org.cn", "people.cn", "ecns", "chinanews", "cri.cn",
        "caixin", "yicai",
    ]
    if any(kw in d for kw in chinese_keywords):
        return "CN", *COUNTRY_COORDS["CN"]

    uk_keywords = [
        "bbc.com", "theguardian.com", "telegraph",
        "independent.co.uk", "dailymail", "thetimes", "ft.com",
        "economist.com", "sky.com",
    ]
    if any(kw in d for kw in uk_keywords):
        return "GB", *COUNTRY_COORDS["GB"]

    # 3. TLD-based inference (most reliable for country-code TLDs)
    for tld, country in sorted(TLD_COUNTRY.items(), key=lambda x: -len(x[0])):
        if d.endswith(tld):
            if country in COUNTRY_COORDS:
                return country, *COUNTRY_COORDS[country]

    # 4. Default Western to US
    return "US", *COUNTRY_COORDS["US"]


def filter_events(start: str, end: str, media_groups: list[str], event_direction: str):
    df = EVENTS.copy()
    mask = (
        (df["Date"] >= pd.Timestamp(start))
        & (df["Date"] <= pd.Timestamp(end))
        & (df["MediaGroup"].isin(media_groups))
    )
    if event_direction != "All":
        mask &= df["EventDirection"] == event_direction
    return df[mask]


def filter_daily(start: str, end: str, media_groups: list[str], _event_direction: str):
    df = DAILY.copy()
    mask = (
        (df["Date"] >= pd.Timestamp(start))
        & (df["Date"] <= pd.Timestamp(end))
        & (df["MediaGroup"].isin(media_groups))
    )
    # Daily aggregates do not have EventDirection; skip filtering by direction
    return df[mask]


def filter_weekly_geo(start: str, end: str, media_groups: list[str], _event_direction: str):
    df = WEEKLY.copy()
    mask = (
        (df["WeekStart"] >= pd.Timestamp(start))
        & (df["WeekStart"] <= pd.Timestamp(end))
        & (df["MediaGroup"].isin(media_groups))
    )
    # Weekly aggregates do not have EventDirection; skip filtering by direction
    return df[mask]


def filter_tone_gap(start: str, end: str):
    df = TONE_GAP.copy()
    mask = (df["Date"] >= pd.Timestamp(start)) & (df["Date"] <= pd.Timestamp(end))
    return df[mask]


def filter_source_map(start: str, end: str, media_groups: list[str]):
    """Aggregate events by inferred source-country of the publishing outlet."""
    df = EVENTS.copy()
    mask = (
        (df["Date"] >= pd.Timestamp(start))
        & (df["Date"] <= pd.Timestamp(end))
        & (df["MediaGroup"].isin(media_groups))
    )
    df = df[mask].copy()

    source_info = df["SourceDomain"].apply(_infer_source_country)
    df["source_country"] = source_info.apply(lambda x: x[0] if x else None)
    df["source_lat"] = source_info.apply(lambda x: x[1] if x else None)
    df["source_lon"] = source_info.apply(lambda x: x[2] if x else None)
    df = df.dropna(subset=["source_country"])

    grouped = (
        df.groupby(["source_country", "MediaGroup"])
        .agg(
            TotalEvents=("GLOBALEVENTID", "count"),
            TotalArticles=("NumArticles", "sum"),
            AvgTone=("AvgTone", "mean"),
            UniqueDomains=("SourceDomain", "nunique"),
            TopDomains=("SourceDomain", lambda x: ", ".join(x.value_counts().head(5).index.astype(str))),
            source_lat=("source_lat", "first"),
            source_lon=("source_lon", "first"),
        )
        .reset_index()
    )

    # Add jitter so same-country markers from different MediaGroups don't stack
    # Offset each group within a country by a fixed angle around the centroid
    jitter_radius = 1.5  # degrees
    media_group_order = ["Western", "Chinese", "Global/Other"]
    for country, grp in grouped.groupby("source_country"):
        for i, idx in enumerate(grp.index):
            group_name = grouped.at[idx, "MediaGroup"]
            order = media_group_order.index(group_name) if group_name in media_group_order else i
            angle = order * (2 * 3.14159 / 3)  # 120 degrees apart
            grouped.at[idx, "source_lat"] = grouped.at[idx, "source_lat"] + jitter_radius * math.cos(angle)
            grouped.at[idx, "source_lon"] = grouped.at[idx, "source_lon"] + jitter_radius * math.sin(angle)

    return grouped
