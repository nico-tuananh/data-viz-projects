"""
Query GDELT v2 from Google BigQuery, filters US-China tariff-related events, cleans the data, labels media groups, and prepares dashboard-ready datasets
Data Source: GDELT v2 (gdelt-bq.gdeltv2.events)
Time Window: Feb 1 – Apr 30, 2025
Focus: US–China Tariff Escalation
Media Groups: Western Media, Chinese State-Affiliated Media, Global/Other
"""

import os
import json
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery
import pandas as pd
import numpy as np
from datetime import datetime

# .env lives one directory up (in project2/), not in backend/
load_dotenv(Path(__file__).parent.parent / ".env")

# Support Railway-style JSON credentials in env var (GOOGLE_APPLICATION_CREDENTIALS_JSON)
# Takes priority over file-based GOOGLE_APPLICATION_CREDENTIALS
_creds_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if _creds_json:
    try:
        _creds_data = json.loads(_creds_json)
        _tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(_creds_data, _tmp)
        _tmp.flush()
        _tmp.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tmp.name
        print(f"[credentials] Loaded from GOOGLE_APPLICATION_CREDENTIALS_JSON -> {_tmp.name}")
    except (json.JSONDecodeError, OSError) as e:
        print(f"[credentials] WARNING: Failed to parse GOOGLE_APPLICATION_CREDENTIALS_JSON: {e}")
elif "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
    creds_path = Path(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
    if not creds_path.is_absolute():
        # Resolve relative to the project root (project2/)
        creds_path = (Path(__file__).parent.parent / creds_path).resolve()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)


# =============================================================================
# Configuration
# =============================================================================

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")

START_DATE = "20250201"
END_DATE = "20250430"

OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

# CAMEO event codes for diplomacy, sanctions, retaliation, criticism, rejection, threats
# Reference: https://www.gdeltproject.org/data/lookups/CAMEO.eventcodes.txt
CAMEO_CODES = [
    # Diplomatic cooperation (01x)
    "010", "011", "012", "013", "014",
    # Appeal (02x) 
    "020", "021", "022", "023", "024", "025", "026", "027", "028",
    # Disapproval / Rejection (11x)
    "110", "111", "112", "113", "114", "115", "116",
    # Criticism / Denounce (12x)
    "120", "121", "122", "123", "124", "125", "126", "127", "128", "129",
    # Threaten (13x)
    "130", "131", "132", "133", "134", "135", "136", "137", "138", "139",
    # Sanctions / Restrictions (16x)
    "160", "161", "162", "163", "164",
    # Coerce (17x)
    "170", "171", "172", "173", "174", "175", "176",
    # Assault (18x) - less relevant but included for completeness
    "180", "181", "182", "183", "184", "185", "186",
]

# Western media domains (major Western news outlets)
WESTERN_MEDIA_DOMAINS = [
    # US
    "nytimes.com", "washingtonpost.com", "wsj.com", "cnn.com", "foxnews.com",
    "nbcnews.com", "abcnews.go.com", "cbsnews.com", "usatoday.com", "latimes.com",
    "chicagotribune.com", "bostonglobe.com", "nypost.com", "politico.com",
    "thehill.com", "axios.com", "vox.com", "huffpost.com", "buzzfeednews.com",
    "npr.org", "pbs.org", "bloomberg.com", "reuters.com", "apnews.com",
    # UK
    "bbc.com", "bbc.co.uk", "theguardian.com", "telegraph.co.uk", "independent.co.uk",
    "dailymail.co.uk", "thetimes.co.uk", "ft.com", "economist.com", "sky.com",
    # Europe
    "dw.com", "france24.com", "euronews.com", "spiegel.de", "lemonde.fr",
    # Australia/Canada
    "abc.net.au", "smh.com.au", "theaustralian.com.au", "cbc.ca", "globalnews.ca",
]

# Chinese state-affiliated media domains
CHINESE_STATE_MEDIA_DOMAINS = [
    "xinhuanet.com", "news.xinhuanet.com", "xinhua.net",
    "chinadaily.com.cn", "chinadaily.com",
    "globaltimes.cn", "global.chinadaily.com.cn",
    "cgtn.com", "english.cctv.com",
    "china.org.cn", "en.people.cn", "people.com.cn",
    "ecns.cn", "chinanews.com",
    "cri.cn", "english.cri.cn",
    "scmp.com",  # South China Morning Post (Hong Kong, but often aligned)
    "caixin.com", "yicai.com",
]


# =============================================================================
# BigQuery GDELT Query
# =============================================================================

def build_gdelt_query():
    """Build the BigQuery SQL query for GDELT v2 events."""
    
    cameo_codes_str = ", ".join([f"'{code}'" for code in CAMEO_CODES])
    
    query = f"""
    SELECT
        GLOBALEVENTID,
        SQLDATE,
        MonthYear,
        Year,
        FractionDate,
        
        -- Actor 1 (usually the initiator)
        Actor1Code,
        Actor1Name,
        Actor1CountryCode,
        Actor1Type1Code,
        Actor1Type2Code,
        Actor1Type3Code,
        
        -- Actor 2 (usually the target)
        Actor2Code,
        Actor2Name,
        Actor2CountryCode,
        Actor2Type1Code,
        Actor2Type2Code,
        Actor2Type3Code,
        
        -- Event details
        IsRootEvent,
        EventCode,
        EventBaseCode,
        EventRootCode,
        QuadClass,
        GoldsteinScale,
        NumMentions,
        NumSources,
        NumArticles,
        AvgTone,
        
        -- Geographic info
        Actor1Geo_Type,
        Actor1Geo_FullName,
        Actor1Geo_CountryCode,
        Actor1Geo_Lat,
        Actor1Geo_Long,
        Actor2Geo_Type,
        Actor2Geo_FullName,
        Actor2Geo_CountryCode,
        Actor2Geo_Lat,
        Actor2Geo_Long,
        ActionGeo_Type,
        ActionGeo_FullName,
        ActionGeo_CountryCode,
        ActionGeo_Lat,
        ActionGeo_Long,
        
        -- Source info
        DATEADDED,
        SOURCEURL
        
    FROM `gdelt-bq.gdeltv2.events`
    
    WHERE
        -- Time filter: Feb 1 - Apr 30, 2025
        SQLDATE >= {START_DATE}
        AND SQLDATE <= {END_DATE}
        
        -- US-China involvement filter (either direction)
        AND (
            (Actor1CountryCode = 'USA' AND Actor2CountryCode = 'CHN')
            OR (Actor1CountryCode = 'CHN' AND Actor2CountryCode = 'USA')
            OR (Actor1Code LIKE '%USA%' AND Actor2Code LIKE '%CHN%')
            OR (Actor1Code LIKE '%CHN%' AND Actor2Code LIKE '%USA%')
        )
        
        -- CAMEO event codes for relevant event types
        AND (
            EventRootCode IN ('01', '02', '11', '12', '13', '16', '17', '18')
            OR EventBaseCode IN ({cameo_codes_str})
        )
        
    ORDER BY SQLDATE, GLOBALEVENTID
    """
    
    return query


def query_gdelt_events(client: bigquery.Client) -> pd.DataFrame:
    """Execute the GDELT query and return results as DataFrame."""
    
    print("Building GDELT query...")
    query = build_gdelt_query()
    
    print("Executing BigQuery query (this may take a few minutes)...")
    query_job = client.query(query)
    
    df = query_job.to_dataframe(create_bqstorage_client=False)
    print(f"Retrieved {len(df):,} events from GDELT")
    
    return df


# =============================================================================
# Data Cleaning Functions
# =============================================================================

def clean_date_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize date fields."""
    
    df = df.copy()
    
    # Convert SQLDATE to proper datetime
    df["Date"] = pd.to_datetime(df["SQLDATE"].astype(str), format="%Y%m%d")
    df["DateStr"] = df["Date"].dt.strftime("%Y-%m-%d")
    df["Week"] = df["Date"].dt.isocalendar().week
    df["WeekStart"] = df["Date"] - pd.to_timedelta(df["Date"].dt.dayofweek, unit="d")
    df["WeekStr"] = df["WeekStart"].dt.strftime("%Y-%m-%d")
    df["DayOfWeek"] = df["Date"].dt.day_name()
    
    # Parse DATEADDED timestamp
    df["DateAdded"] = pd.to_datetime(
        df["DATEADDED"].astype(str), 
        format="%Y%m%d%H%M%S", 
        errors="coerce"
    )
    
    return df


def clean_country_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize country/actor fields."""
    
    df = df.copy()
    
    # Fill missing country codes
    df["Actor1CountryCode"] = df["Actor1CountryCode"].fillna("UNK")
    df["Actor2CountryCode"] = df["Actor2CountryCode"].fillna("UNK")
    
    # Create simplified actor direction field
    def get_event_direction(row):
        a1 = str(row["Actor1CountryCode"]).upper()
        a2 = str(row["Actor2CountryCode"]).upper()
        if a1 == "USA" and a2 == "CHN":
            return "USA→CHN"
        elif a1 == "CHN" and a2 == "USA":
            return "CHN→USA"
        else:
            return "Other"
    
    df["EventDirection"] = df.apply(get_event_direction, axis=1)
    
    # Create action country field based on ActionGeo
    df["ActionCountry"] = df["ActionGeo_CountryCode"].fillna("UNK")
    
    return df


def clean_source_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and extract source domain from SOURCEURL."""
    
    df = df.copy()
    
    def extract_domain(url):
        if pd.isna(url) or not url:
            return "unknown"
        try:
            url = str(url).lower()
            # Remove protocol
            if "://" in url:
                url = url.split("://")[1]
            # Get domain
            domain = url.split("/")[0]
            # Remove www.
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except:
            return "unknown"
    
    df["SourceDomain"] = df["SOURCEURL"].apply(extract_domain)
    
    return df


# =============================================================================
# Media Group Labeling
# =============================================================================

def label_media_groups(df: pd.DataFrame) -> pd.DataFrame:
    """Label each event with its media group classification."""
    
    df = df.copy()
    
    western_set = set(d.lower() for d in WESTERN_MEDIA_DOMAINS)
    chinese_set = set(d.lower() for d in CHINESE_STATE_MEDIA_DOMAINS)
    
    def classify_media(domain):
        domain = str(domain).lower()
        
        # Check for exact match
        if domain in western_set:
            return "Western"
        if domain in chinese_set:
            return "Chinese"
        
        # Check for partial match (subdomains)
        for wd in western_set:
            if domain.endswith("." + wd) or domain == wd:
                return "Western"
        for cd in chinese_set:
            if domain.endswith("." + cd) or domain == cd:
                return "Chinese"
        
        return "Global/Other"
    
    df["MediaGroup"] = df["SourceDomain"].apply(classify_media)
    
    # Add numeric coding for analysis
    media_map = {"Western": 1, "Chinese": 2, "Global/Other": 0}
    df["MediaGroupCode"] = df["MediaGroup"].map(media_map)
    
    return df


# =============================================================================
# Feature Engineering for Dashboard
# =============================================================================

def engineer_dashboard_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add computed features useful for dashboard visualizations."""
    
    df = df.copy()
    
    # Classify event sentiment based on GoldsteinScale
    def classify_goldstein(score):
        if pd.isna(score):
            return "Neutral"
        if score >= 3:
            return "Cooperative"
        elif score <= -3:
            return "Conflictual"
        else:
            return "Neutral"
    
    df["EventSentiment"] = df["GoldsteinScale"].apply(classify_goldstein)
    
    # Classify tone
    def classify_tone(tone):
        if pd.isna(tone):
            return "Neutral"
        if tone >= 2:
            return "Positive"
        elif tone <= -2:
            return "Negative"
        else:
            return "Neutral"
    
    df["ToneCategory"] = df["AvgTone"].apply(classify_tone)
    
    # Create event type descriptions based on CAMEO root codes
    cameo_descriptions = {
        "01": "Diplomatic Cooperation",
        "02": "Appeal",
        "03": "Express Intent to Cooperate",
        "04": "Consult",
        "05": "Diplomatic Cooperation",
        "06": "Material Cooperation",
        "07": "Provide Aid",
        "08": "Yield",
        "09": "Investigate",
        "10": "Demand",
        "11": "Disapprove/Reject",
        "12": "Criticize/Denounce",
        "13": "Threaten",
        "14": "Protest",
        "15": "Exhibit Force Posture",
        "16": "Reduce Relations/Sanctions",
        "17": "Coerce",
        "18": "Assault",
        "19": "Fight",
        "20": "Use Unconventional Violence",
    }
    
    df["EventTypeDesc"] = df["EventRootCode"].map(cameo_descriptions).fillna("Other")
    
    # Quad class descriptions (conflict/cooperation classification)
    quad_descriptions = {
        1: "Verbal Cooperation",
        2: "Material Cooperation",
        3: "Verbal Conflict",
        4: "Material Conflict",
    }
    df["QuadClassDesc"] = df["QuadClass"].map(quad_descriptions).fillna("Unknown")
    
    # Coverage intensity (log-scaled article count)
    df["CoverageIntensity"] = np.log1p(df["NumArticles"])
    
    return df


# =============================================================================
# Aggregation Functions for Dashboard
# =============================================================================

def create_daily_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Create daily aggregated metrics for timeline visualizations."""
    
    daily = df.groupby(["DateStr", "MediaGroup"]).agg(
        TotalEvents=("GLOBALEVENTID", "count"),
        TotalArticles=("NumArticles", "sum"),
        TotalMentions=("NumMentions", "sum"),
        TotalSources=("NumSources", "sum"),
        AvgTone=("AvgTone", "mean"),
        WeightedTone=("AvgTone", lambda x: np.average(x, weights=df.loc[x.index, "NumArticles"].clip(lower=1))),
        AvgGoldstein=("GoldsteinScale", "mean"),
        MinTone=("AvgTone", "min"),
        MaxTone=("AvgTone", "max"),
        StdTone=("AvgTone", "std"),
    ).reset_index()
    
    daily["Date"] = pd.to_datetime(daily["DateStr"])
    
    return daily


def create_weekly_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Create weekly aggregated metrics for map/geo visualizations."""
    
    weekly = df.groupby(["WeekStr", "ActionCountry", "MediaGroup"]).agg(
        TotalEvents=("GLOBALEVENTID", "count"),
        TotalArticles=("NumArticles", "sum"),
        AvgTone=("AvgTone", "mean"),
        AvgGoldstein=("GoldsteinScale", "mean"),
    ).reset_index()
    
    weekly["WeekStart"] = pd.to_datetime(weekly["WeekStr"])
    
    return weekly


def create_tone_gap_series(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily tone gap between Western and Chinese media."""
    
    # Pivot to get Western and Chinese tones side by side
    pivot = daily_df.pivot_table(
        index="DateStr",
        columns="MediaGroup",
        values=["WeightedTone", "TotalArticles"],
        aggfunc="first"
    ).reset_index()
    
    # Flatten column names
    pivot.columns = ["_".join(col).strip("_") if col[1] else col[0] for col in pivot.columns]
    
    # Calculate tone gap (Western - Chinese)
    tone_gap = pd.DataFrame()
    tone_gap["DateStr"] = pivot["DateStr"]
    tone_gap["Date"] = pd.to_datetime(tone_gap["DateStr"])
    
    tone_gap["WesternTone"] = pivot.get("WeightedTone_Western", np.nan)
    tone_gap["ChineseTone"] = pivot.get("WeightedTone_Chinese", np.nan)
    tone_gap["GlobalTone"] = pivot.get("WeightedTone_Global/Other", np.nan)
    
    tone_gap["WesternArticles"] = pivot.get("TotalArticles_Western", 0)
    tone_gap["ChineseArticles"] = pivot.get("TotalArticles_Chinese", 0)
    tone_gap["GlobalArticles"] = pivot.get("TotalArticles_Global/Other", 0)
    
    # ToneGap = Western - Chinese (positive means Western more positive)
    tone_gap["ToneGap"] = tone_gap["WesternTone"] - tone_gap["ChineseTone"]
    tone_gap["AbsToneGap"] = tone_gap["ToneGap"].abs()
    
    return tone_gap.sort_values("Date")


# =============================================================================
# Main Pipeline
# =============================================================================

def run_pipeline(save_outputs: bool = True) -> dict:
    """Run the complete data collection and preprocessing pipeline."""
    
    print("=" * 60)
    print("GDELT Data Collection Pipeline for US-China Tariff Analysis")
    print("=" * 60)
    print(f"Time window: {START_DATE} to {END_DATE}")
    print()
    
    # Initialize BigQuery client
    print("Initializing BigQuery client...")
    client = bigquery.Client(project=PROJECT_ID)
    
    # Query GDELT
    df_raw = query_gdelt_events(client)
    
    if len(df_raw) == 0:
        print("WARNING: No events found. Check your query parameters.")
        return {}
    
    # Cleaning pipeline
    print("\nCleaning data...")
    df = clean_date_fields(df_raw)
    df = clean_country_fields(df)
    df = clean_source_fields(df)
    
    # Label media groups
    print("Labeling media groups...")
    df = label_media_groups(df)
    
    # Feature engineering
    print("Engineering dashboard features...")
    df = engineer_dashboard_features(df)
    
    # Create aggregates
    print("Creating aggregated datasets...")
    daily_agg = create_daily_aggregates(df)
    weekly_agg = create_weekly_aggregates(df)
    tone_gap = create_tone_gap_series(daily_agg)
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    print(f"Total events: {len(df):,}")
    print(f"Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"Unique sources: {df['SourceDomain'].nunique():,}")
    print(f"\nMedia group distribution:")
    print(df["MediaGroup"].value_counts().to_string())
    print(f"\nEvent direction distribution:")
    print(df["EventDirection"].value_counts().to_string())
    print(f"\nTop 10 source domains:")
    print(df["SourceDomain"].value_counts().head(10).to_string())
    
    # Save outputs
    if save_outputs:
        print(f"\nSaving outputs to {OUTPUT_DIR}...")
        
        df.to_parquet(OUTPUT_DIR / "gdelt_events_cleaned.parquet", index=False)
        df.to_csv(OUTPUT_DIR / "gdelt_events_cleaned.csv", index=False)
        
        daily_agg.to_parquet(OUTPUT_DIR / "daily_aggregates.parquet", index=False)
        daily_agg.to_csv(OUTPUT_DIR / "daily_aggregates.csv", index=False)
        
        weekly_agg.to_parquet(OUTPUT_DIR / "weekly_aggregates.parquet", index=False)
        weekly_agg.to_csv(OUTPUT_DIR / "weekly_aggregates.csv", index=False)
        
        tone_gap.to_parquet(OUTPUT_DIR / "tone_gap_series.parquet", index=False)
        tone_gap.to_csv(OUTPUT_DIR / "tone_gap_series.csv", index=False)
        
        print("Saved files:")
        for f in OUTPUT_DIR.glob("*"):
            print(f"  - {f.name}")
    
    print("\nPipeline complete!")
    
    return {
        "events": df,
        "daily": daily_agg,
        "weekly": weekly_agg,
        "tone_gap": tone_gap,
    }


# =============================================================================
# Alternative: Load from local files (if BigQuery not available)
# =============================================================================

def load_processed_data() -> dict:
    """Load previously processed data from local files."""
    
    return {
        "events": pd.read_parquet(OUTPUT_DIR / "gdelt_events_cleaned.parquet"),
        "daily": pd.read_parquet(OUTPUT_DIR / "daily_aggregates.parquet"),
        "weekly": pd.read_parquet(OUTPUT_DIR / "weekly_aggregates.parquet"),
        "tone_gap": pd.read_parquet(OUTPUT_DIR / "tone_gap_series.parquet"),
    }


if __name__ == "__main__":
    data = run_pipeline()