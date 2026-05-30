# Forecasting Model Comparison

## ToneGap Forecasting Results

We evaluated four forecasting models on the daily `ToneGap` series derived from the US-China tariff media dataset. The target series spans February 1, 2025 through April 30, 2025. Model performance was measured on a chronological 14-day holdout from April 17, 2025 to April 30, 2025 using Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE).

### Methods

The evaluation used 89 daily observations from `tone_gap_series.csv`, where `ToneGap` is defined as Western weighted tone minus Chinese weighted tone. The series contained 11 missing daily values, which were linearly imputed to preserve a regular daily index for forecasting. We trained each model on the first 75 days and evaluated forecasts on the final 14 days. ARIMA order was selected by AIC search over small `(p, d, q)` combinations, Holt-Winters used additive trend and additive weekly seasonality, Prophet used weekly seasonality, and TimesFM used the pretrained `google/timesfm-2.5-200m-pytorch` checkpoint.

### Comparison Table

| Model | MAE | RMSE | Notes |
|---|---:|---:|---|
| TimesFM | 1.7251 | 2.0532 | Pretrained `google/timesfm-2.5-200m-pytorch` |
| ARIMA | 1.6869 | 2.1741 | Best order: `(3, 1, 3)` |
| Prophet | 1.9773 | 2.4161 | Weekly seasonality enabled |
| Holt-Winters | 1.9901 | 2.4418 | Additive trend, additive seasonality, period = 7 |

### Interpretation

TimesFM achieved the lowest RMSE, indicating the best overall performance when larger forecast misses are penalized more strongly. ARIMA produced the lowest MAE, meaning it was slightly better on average absolute error. Prophet outperformed Holt-Winters on both metrics, but neither matched the performance of TimesFM or ARIMA on this evaluation split.

### Figures

The evaluation script also generates four forecast plots in `project2/`:

- `forecast_timesfm.png`
- `forecast_arima.png`
- `forecast_prophet.png`
- `forecast_holt_winters.png`

### Reproducibility

- Metrics: `forecast_metrics.csv`
- Predictions: `forecast_predictions.csv`
- Script: `forecast_models.py`
