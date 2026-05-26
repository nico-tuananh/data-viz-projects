from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path
from math import sqrt

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing


BASE_DIR = Path(__file__).parent
LOCAL_DATA_DIR = BASE_DIR / "data"
BACKEND_DATA_DIR = BASE_DIR / "backend" / "data"
TIMESFM_REPO_DIR = BASE_DIR.parent / "timesfm"
TIMESFM_PYTHON = TIMESFM_REPO_DIR / ".venv" / "bin" / "python"
PROPHET_PYTHON = BASE_DIR / ".venv-prophet" / "bin" / "python"
TEST_SIZE = 14


def resolve_tone_gap_path() -> Path:
    candidates = [
        LOCAL_DATA_DIR / "tone_gap_series.csv",
        BACKEND_DATA_DIR / "tone_gap_series.parquet",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find tone_gap_series data in project2/data or project2/backend/data.")


def load_series() -> pd.DataFrame:
    path = resolve_tone_gap_path()
    if path.suffix == ".csv":
        df = pd.read_csv(path, parse_dates=["Date"])
    else:
        df = pd.read_parquet(path)
        df["Date"] = pd.to_datetime(df["Date"])

    df = df[["Date", "ToneGap"]].sort_values("Date").drop_duplicates("Date")
    full_idx = pd.date_range(df["Date"].min(), df["Date"].max(), freq="D")
    series = (
        df.set_index("Date")
        .reindex(full_idx)
        .rename_axis("Date")
        .reset_index()
    )
    series["ToneGapObserved"] = series["ToneGap"]
    # Preserve a regular daily series for forecasting while keeping the original
    # observed values available for reporting.
    series["ToneGap"] = (
        series["ToneGap"]
        .interpolate(method="linear", limit_direction="both")
        .bfill()
        .ffill()
    )
    return series


def split_train_test(series: pd.DataFrame, test_size: int = TEST_SIZE) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(series) <= test_size:
        raise ValueError(f"Series length {len(series)} is too short for test size {test_size}.")
    train = series.iloc[:-test_size].copy()
    test = series.iloc[-test_size:].copy()
    return train, test


def select_arima_order(train_values: pd.Series) -> tuple[int, int, int]:
    best_order = None
    best_aic = np.inf
    for p in range(4):
        for d in range(3):
            for q in range(4):
                try:
                    fitted = ARIMA(train_values, order=(p, d, q)).fit()
                except Exception:
                    continue
                if fitted.aic < best_aic:
                    best_aic = fitted.aic
                    best_order = (p, d, q)
    if best_order is None:
        raise RuntimeError("ARIMA order search failed.")
    return best_order


def run_arima(train: pd.DataFrame, test: pd.DataFrame) -> tuple[pd.DataFrame, tuple[int, int, int]]:
    order = select_arima_order(train["ToneGap"])
    fitted = ARIMA(train["ToneGap"], order=order).fit()
    forecast = fitted.forecast(steps=len(test))
    result = pd.DataFrame({
        "Date": test["Date"].to_numpy(),
        "Actual": test["ToneGap"].to_numpy(),
        "Predicted": np.asarray(forecast),
        "Model": "ARIMA",
    })
    return result, order


def run_prophet(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    if not PROPHET_PYTHON.exists():
        raise FileNotFoundError(f"Prophet interpreter not found at {PROPHET_PYTHON}")

    payload = {
        "train_dates": train["Date"].dt.strftime("%Y-%m-%d").tolist(),
        "train_values": train["ToneGap"].astype(float).tolist(),
        "future_dates": test["Date"].dt.strftime("%Y-%m-%d").tolist(),
    }
    runner = """
import json
import os
import pandas as pd
from prophet import Prophet

payload = json.loads(os.environ["PROPHET_PAYLOAD"])
train = pd.DataFrame({
    "ds": pd.to_datetime(payload["train_dates"]),
    "y": payload["train_values"],
})
future = pd.DataFrame({"ds": pd.to_datetime(payload["future_dates"])})
model = Prophet(
    yearly_seasonality=False,
    weekly_seasonality=True,
    daily_seasonality=False,
    changepoint_prior_scale=0.1,
    seasonality_prior_scale=5.0,
)
model.fit(train)
forecast = model.predict(future)
print(json.dumps(forecast["yhat"].tolist()))
"""
    env = os.environ.copy()
    env["PROPHET_PAYLOAD"] = json.dumps(payload)
    env.setdefault("MPLCONFIGDIR", "/private/tmp/matplotlib")
    completed = subprocess.run(
        [str(PROPHET_PYTHON), "-c", runner],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    stdout = completed.stdout.strip().splitlines()
    if not stdout:
        raise RuntimeError("Prophet subprocess returned no forecast output.")
    forecast_values = json.loads(stdout[-1])
    result = pd.DataFrame({
        "Date": test["Date"].to_numpy(),
        "Actual": test["ToneGap"].to_numpy(),
        "Predicted": np.asarray(forecast_values, dtype=float),
        "Model": "Prophet",
    })
    return result


def run_holt_winters(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    fitted = ExponentialSmoothing(
        train["ToneGap"],
        trend="add",
        seasonal="add",
        seasonal_periods=7,
        initialization_method="estimated",
    ).fit(optimized=True)
    forecast = fitted.forecast(len(test))
    result = pd.DataFrame({
        "Date": test["Date"].to_numpy(),
        "Actual": test["ToneGap"].to_numpy(),
        "Predicted": np.asarray(forecast),
        "Model": "HoltWinters",
    })
    return result


def run_timesfm(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    if not TIMESFM_PYTHON.exists():
        raise FileNotFoundError(f"TimesFM interpreter not found at {TIMESFM_PYTHON}")

    payload = {
        "train_values": train["ToneGap"].astype(float).tolist(),
        "horizon": len(test),
    }
    runner = """
import json
import numpy as np
import torch
import timesfm

torch.set_float32_matmul_precision("high")
payload = json.loads(__import__("os").environ["TIMESFM_PAYLOAD"])
train_values = np.asarray(payload["train_values"], dtype=float)
horizon = int(payload["horizon"])

model = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
model.compile(
    timesfm.ForecastConfig(
        max_context=max(32, min(1024, len(train_values))),
        max_horizon=horizon,
        normalize_inputs=True,
        use_continuous_quantile_head=True,
        force_flip_invariance=True,
        infer_is_positive=False,
        fix_quantile_crossing=True,
    )
)
point_forecast, _ = model.forecast(horizon=horizon, inputs=[train_values])
print(json.dumps(point_forecast[0].tolist()))
"""
    env = os.environ.copy()
    env["TIMESFM_PAYLOAD"] = json.dumps(payload)
    env.setdefault("HF_HOME", str(TIMESFM_REPO_DIR / ".hf-cache"))
    env.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    completed = subprocess.run(
        [str(TIMESFM_PYTHON), "-c", runner],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    stdout = completed.stdout.strip().splitlines()
    if not stdout:
        raise RuntimeError("TimesFM subprocess returned no forecast output.")
    forecast = json.loads(stdout[-1])
    result = pd.DataFrame({
        "Date": test["Date"].to_numpy(),
        "Actual": test["ToneGap"].to_numpy(),
        "Predicted": np.asarray(forecast, dtype=float),
        "Model": "TimesFM",
    })
    return result


def score_forecast(result: pd.DataFrame, detail: str) -> dict[str, object]:
    mae = mean_absolute_error(result["Actual"], result["Predicted"])
    rmse = sqrt(mean_squared_error(result["Actual"], result["Predicted"]))
    return {
        "model": result["Model"].iloc[0],
        "mae": mae,
        "rmse": rmse,
        "details": detail,
    }


def plot_forecast(series: pd.DataFrame, train: pd.DataFrame, test: pd.DataFrame, result: pd.DataFrame, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(series["Date"], series["ToneGap"], color="#94a3b8", linewidth=1.5, label="ToneGap (imputed series)")
    ax.plot(train["Date"], train["ToneGap"], color="#0f172a", linewidth=2, label="Train")
    ax.plot(test["Date"], test["ToneGap"], color="#16a34a", linewidth=2, label="Actual test")
    ax.plot(result["Date"], result["Predicted"], color="#dc2626", linestyle="--", linewidth=2, label=f"{result['Model'].iloc[0]} forecast")
    ax.axvline(test["Date"].iloc[0], color="#64748b", linestyle=":", linewidth=1.5)
    ax.set_title(f"{result['Model'].iloc[0]} forecast on ToneGap")
    ax.set_xlabel("Date")
    ax.set_ylabel("ToneGap")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main() -> None:
    output_dir = BASE_DIR
    series = load_series()
    train, test = split_train_test(series)

    results = []
    metrics = []

    arima_result, arima_order = run_arima(train, test)
    results.append(arima_result)
    metrics.append(score_forecast(arima_result, f"order={arima_order}, test_size={len(test)}"))
    plot_forecast(series, train, test, arima_result, output_dir / "forecast_arima.png")

    holt_result = run_holt_winters(train, test)
    results.append(holt_result)
    metrics.append(score_forecast(holt_result, f"trend=add, seasonal=add, seasonal_periods=7, test_size={len(test)}"))
    plot_forecast(series, train, test, holt_result, output_dir / "forecast_holt_winters.png")

    timesfm_status = "not attempted"
    try:
        timesfm_result = run_timesfm(train, test)
        results.append(timesfm_result)
        metrics.append(score_forecast(timesfm_result, f"checkpoint=google/timesfm-2.5-200m-pytorch, test_size={len(test)}"))
        plot_forecast(series, train, test, timesfm_result, output_dir / "forecast_timesfm.png")
        timesfm_status = "completed"
    except Exception as exc:
        timesfm_status = f"failed: {type(exc).__name__}: {exc}"

    prophet_status = "not attempted"
    try:
        prophet_result = run_prophet(train, test)
        results.append(prophet_result)
        metrics.append(score_forecast(prophet_result, f"weekly_seasonality=True, test_size={len(test)}"))
        plot_forecast(series, train, test, prophet_result, output_dir / "forecast_prophet.png")
        prophet_status = "completed"
    except Exception as exc:
        prophet_status = f"failed: {type(exc).__name__}: {exc}"

    metrics_df = pd.DataFrame(metrics).sort_values(["rmse", "mae"]).reset_index(drop=True)
    metrics_df.to_csv(output_dir / "forecast_metrics.csv", index=False)

    comparison_df = pd.concat(results, ignore_index=True)
    comparison_df.to_csv(output_dir / "forecast_predictions.csv", index=False)

    summary_lines = [
        "Forecast evaluation summary",
        f"Input series: {resolve_tone_gap_path()}",
        f"Rows: {len(series)} | Missing ToneGap values imputed: {series['ToneGapObserved'].isna().sum()}",
        f"Train rows: {len(train)} | Test rows: {len(test)}",
        "",
    ]
    for row in metrics_df.itertuples(index=False):
        summary_lines.append(
            f"{row.model}: MAE={row.mae:.4f}, RMSE={row.rmse:.4f} ({row.details})"
        )
    summary_lines.append("")
    summary_lines.append(f"TimesFM: {timesfm_status}.")
    summary_lines.append(f"Prophet: {prophet_status}.")
    (output_dir / "forecast_summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="ascii")

    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
