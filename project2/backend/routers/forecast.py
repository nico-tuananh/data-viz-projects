"""Forecast model evaluation endpoints."""
import math
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, BackgroundTasks

try:
    from data_loader import TONE_GAP
except ImportError:
    # Allow import when running from backend/routers directly
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from data_loader import TONE_GAP

router = APIRouter(prefix="/api/forecast", tags=["forecast"])

# Paths relative to project2 root
MODEL_OUTPUT_DIR = Path(__file__).parent.parent.parent / "model" / "output"


def _safe_json(v):
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


@router.get("/metrics")
def get_forecast_metrics():
    """Return model comparison metrics (MAE / RMSE)."""
    csv = MODEL_OUTPUT_DIR / "forecast_metrics.csv"
    if not csv.exists():
        return {"models": []}

    df = pd.read_csv(csv)
    models = []
    for _, row in df.iterrows():
        models.append({
            "name": str(row["model"]),
            "mae": float(row["mae"]),
            "rmse": float(row["rmse"]),
            "details": str(row["details"]),
        })
    return {"models": models}


@router.get("/evaluation")
def get_forecast_evaluation():
    """Return full ToneGap series + 14-day test predictions for all models."""
    preds_csv = MODEL_OUTPUT_DIR / "forecast_predictions.csv"
    metrics_csv = MODEL_OUTPUT_DIR / "forecast_metrics.csv"

    # Full series (always fresh — reads from in-memory parquet loaded at startup)
    full_series = TONE_GAP[["Date", "ToneGap"]].copy()
    full_series = full_series.sort_values("Date").drop_duplicates("Date")
    full_idx = pd.date_range(full_series["Date"].min(), full_series["Date"].max(), freq="D")
    full_series = (
        full_series.set_index("Date")
        .reindex(full_idx)
        .rename_axis("Date")
        .reset_index()
    )
    full_series["ToneGap"] = (
        full_series["ToneGap"]
        .interpolate(method="linear", limit_direction="both")
        .bfill()
        .ffill()
    )
    full_series["Date"] = full_series["Date"].dt.strftime("%Y-%m-%d")
    full_series_list = [
        {"date": r["Date"], "toneGap": None if pd.isna(r["ToneGap"]) else float(r["ToneGap"])}
        for _, r in full_series.iterrows()
    ]

    if not preds_csv.exists():
        return {
            "fullSeries": full_series_list,
            "predictions": [],
            "trainCutoff": None,
            "metrics": {"models": []},
        }

    df = pd.read_csv(preds_csv, parse_dates=["Date"])
    predictions = []
    for model_name in df["Model"].unique():
        model_df = df[df["Model"] == model_name].sort_values("Date")
        predictions.append({
            "model": str(model_name),
            "dates": model_df["Date"].dt.strftime("%Y-%m-%d").tolist(),
            "predicted": model_df["Predicted"].astype(float).tolist(),
        })

    first_pred_date = df["Date"].min()
    train_cutoff = (first_pred_date - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    metrics = {"models": []}
    if metrics_csv.exists():
        mdf = pd.read_csv(metrics_csv)
        for _, row in mdf.iterrows():
            metrics["models"].append({
                "name": str(row["model"]),
                "mae": float(row["mae"]),
                "rmse": float(row["rmse"]),
                "details": str(row["details"]),
            })

    return {
        "fullSeries": full_series_list,
        "predictions": predictions,
        "trainCutoff": train_cutoff,
        "metrics": metrics,
    }


def _run_forecast_regeneration():
    """Background task: re-run model/forecast_models.py."""
    project_root = Path(__file__).parent.parent.parent
    env = os.environ.copy()
    env["MPLBACKEND"] = "Agg"
    try:
        subprocess.run(
            [sys.executable, str(project_root / "model" / "forecast_models.py")],
            cwd=str(project_root),
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[forecast] regeneration failed: {exc.stderr}")


@router.post("/regenerate")
async def regenerate_forecast(background_tasks: BackgroundTasks):
    """Trigger a background forecast re-generation. Returns immediately."""
    background_tasks.add_task(_run_forecast_regeneration)
    return {"status": "started"}
