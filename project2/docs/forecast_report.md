# Forecasting Model Comparison

## ToneGap Forecasting Results

We evaluated four forecasting models on the daily `ToneGap` series derived from the US-China tariff media dataset. The target series spans February 1, 2025 through April 30, 2025. Model performance was measured on a chronological 14-day holdout from April 17, 2025 to April 30, 2025 using Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).

### Methods

The evaluation used 89 daily observations from `tone_gap_series.csv`, where `ToneGap` is defined as Western weighted tone minus Chinese weighted tone. The series contained 11 missing daily values, which were linearly imputed to preserve a regular daily index for forecasting. We trained each model on the first 75 days and evaluated forecasts on the final 14 days. ARIMA order was selected by AIC search over small `(p, d, q)` combinations, Holt-Winters used additive trend and additive weekly seasonality, Prophet used weekly seasonality, and TimesFM used the pretrained `google/timesfm-2.5-200m-pytorch` checkpoint.

### Comparison Table

| Model | MAE | RMSE | Notes |
|---|---:|---:|---|
| ARIMA | 1.6871 | 2.1743 | Best order: `(3, 1, 3)` · **lowest MAE** |
| TimesFM | 1.8350 | 2.1177 | Pretrained `google/timesfm-2.5-200m-pytorch` · **lowest RMSE** |
| Prophet | 1.9500 | 2.3908 | Weekly seasonality enabled |
| Holt-Winters | 1.9901 | 2.4418 | Additive trend, additive seasonality, period = 7 |

### Interpretation

TimesFM achieved the lowest RMSE, indicating the best overall performance when larger forecast misses are penalized more strongly. ARIMA produced the lowest MAE, meaning it was slightly better on average absolute error. Prophet outperformed Holt-Winters on both metrics, but neither matched the performance of TimesFM or ARIMA on this evaluation split.

### Figures

The evaluation script generates four forecast plots saved to `forecasting/images/`:

- `forecasting/images/forecast_timesfm.png`
- `forecasting/images/forecast_arima.png`
- `forecasting/images/forecast_prophet.png`
- `forecasting/images/forecast_holt_winters.png`

### Reproducibility

- Metrics: `forecasting/output/forecast_metrics.csv`
- Predictions: `forecasting/output/forecast_predictions.csv`
- Script: `forecasting/forecast_models.py`
