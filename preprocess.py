import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from pathlib import Path

DATA_PATH = Path(__file__).parent / "penguins.csv"
OUTPUT_PATH = Path(__file__).parent / "penguins_processed.csv"

NUMERIC_COLUMNS = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
CATEGORICAL_COLUMNS = ["species", "island", "sex"]


def load_raw_data():
    """Load the raw penguins dataset without any preprocessing."""
    df = pd.read_csv(DATA_PATH)
    df = df.drop(columns=["rowid"])
    return df


def load_clean_data(drop_na=True):
    """
    Load cleaned penguins dataset.
    
    Parameters:
        drop_na: If True, drops rows with any missing values.
    """
    df = load_raw_data()
    
    df["species"] = df["species"].astype("category")
    df["island"] = df["island"].astype("category")
    df["sex"] = df["sex"].astype("category")
    df["year"] = df["year"].astype("category")
    
    df = df.dropna()
    
    df = df.reset_index(drop=True)
    return df


def add_derived_features(df):
    """Add derived features useful for visualization and analysis."""
    df = df.copy()
    df["body_mass_kg"] = df["body_mass_g"] / 1000
    return df


def load_ml_ready_data():
    """
    Load data prepared for machine learning (clustering, PCA).
    
    Returns:
        df: Clean dataframe with derived features
        X_scaled: Scaled numeric features as numpy array
        feature_names: List of feature names used for scaling
    """
    df = load_clean_data(drop_na=True)
    df = add_derived_features(df)
    
    feature_names = NUMERIC_COLUMNS.copy()
    X = df[feature_names].values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    return df, X_scaled, feature_names


def get_numeric_columns():
    """Return list of numeric column names."""
    return NUMERIC_COLUMNS.copy()


def get_categorical_columns():
    """Return list of categorical column names."""
    return CATEGORICAL_COLUMNS.copy()


def get_dataset_summary(df=None):
    """
    Get summary statistics about the dataset.
    
    Returns a dictionary with counts and basic stats.
    """
    if df is None:
        df = load_clean_data()
    
    return {
        "total_rows": len(df),
        "species_counts": df["species"].value_counts().to_dict(),
        "island_counts": df["island"].value_counts().to_dict(),
        "sex_counts": df["sex"].value_counts().to_dict(),
        "year_counts": df["year"].value_counts().to_dict(),
        "numeric_stats": df[NUMERIC_COLUMNS].describe().to_dict(),
    }


def save_processed_data():
    """Save the cleaned data with derived features to CSV."""
    df = load_clean_data(drop_na=True)
    df = add_derived_features(df)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Saved processed data to {OUTPUT_PATH}")
    return df


if __name__ == "__main__":
    print(">>> Load raw data")
    raw = load_raw_data()
    print(f"Shape: {raw.shape}")
    print(f"Missing values:\n{raw.isna().sum()}\n")
    
    print(">>> Clean data")
    clean = load_clean_data()
    print(f"Shape: {clean.shape}")
    print(f"Dtypes:\n{clean.dtypes}\n")
    
    print(">>> ML ready data")
    df, X_scaled, features = load_ml_ready_data()
    print(f"DataFrame shape: {df.shape}")
    print(f"Scaled features shape: {X_scaled.shape}")
    print(f"Features: {features}\n")
    
    print(">>> Summary")
    summary = get_dataset_summary(clean)
    print(f"Total rows: {summary['total_rows']}")
    print(f"Species: {summary['species_counts']}")
    print(f"Islands: {summary['island_counts']}\n")
    save_processed_data()