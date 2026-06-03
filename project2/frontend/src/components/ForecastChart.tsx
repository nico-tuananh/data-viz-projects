/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useTheme } from '../hooks/useTheme';
import { getForecastEvaluation, regenerateForecast, type ForecastEvaluationResponse } from '../api';
import { MODEL_COLORS, GLOBAL, FORECAST_ACTUAL, FORECAST_FULL_SERIES, chartTheme, hoverLabel } from '../lib/colors';

interface ForecastChartProps {
  selectedModels: string[];
}

export default function ForecastChart({ selectedModels }: ForecastChartProps) {
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<ForecastEvaluationResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    getForecastEvaluation()
      .then((res) => { setData(res); setLoading(false); })
      .catch((err) => { console.error('Error loading forecast evaluation:', err); setLoading(false); });
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !data) return;

    const ct = chartTheme(theme);
    const { textColor, labelColor, gridColor } = ct;

    const traces: any[] = [];

    // Full series (grey thin line)
    if (data.fullSeries.length > 0) {
      traces.push({
        x: data.fullSeries.map((d) => d.date),
        y: data.fullSeries.map((d) => d.toneGap),
        mode: 'lines' as const,
        connectgaps: true,
        line: { color: FORECAST_FULL_SERIES, width: 1.5 },
        name: 'ToneGap (full series)',
        hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
      });
    }

    // Train/test split vertical line
    if (data.trainCutoff) {
      const yRange = data.fullSeries.length > 0
        ? [
            Math.min(...data.fullSeries.map((d) => d.toneGap).filter((v): v is number => v != null)) * 1.1,
            Math.max(...data.fullSeries.map((d) => d.toneGap).filter((v): v is number => v != null)) * 1.1,
          ]
        : [-5, 5];
      traces.push({
        x: [data.trainCutoff, data.trainCutoff],
        y: yRange,
        mode: 'lines' as const,
        line: { color: labelColor, width: 1.5, dash: 'dot' as const },
        name: 'Train/Test split',
        hoverinfo: 'skip' as const,
        showlegend: true,
      });
    }

    // Actual test values (green solid)
    if (data.predictions.length > 0) {
      const firstModel = data.predictions[0];
      // Find actuals from fullSeries matching prediction dates
      const actualMap = new Map(data.fullSeries.map((d) => [d.date, d.toneGap]));
      const actuals = firstModel.dates.map((date) => actualMap.get(date) ?? null);

      traces.push({
        x: firstModel.dates,
        y: actuals,
        mode: 'lines+markers' as const,
        line: { color: FORECAST_ACTUAL, width: 2.5 },
        marker: { size: 6, color: FORECAST_ACTUAL },
        name: 'Actual (test)',
        hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
      });
    }

    // Model predictions (dashed lines)
    data.predictions
      .filter((pred) => selectedModels.includes(pred.model))
      .forEach((pred) => {
        traces.push({
          x: pred.dates,
          y: pred.predicted,
          mode: 'lines' as const,
          line: {
            color: MODEL_COLORS[pred.model] || GLOBAL,
            width: 2,
            dash: 'dash' as const,
          },
          name: `${pred.model} forecast`,
          hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
        });
      });

    Plotly.react(containerRef.current, traces, {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: textColor, family: 'DM Sans, sans-serif' },
      margin: { t: 30, r: 30, b: 50, l: 60 },
      xaxis: {
        title: { text: 'Date', font: { color: labelColor, size: 12 } },
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: textColor },
        hoverformat: '%b %d, %Y',
      },
      yaxis: {
        title: { text: 'ToneGap', font: { color: labelColor, size: 12 } },
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: textColor },
      },
      legend: {
        orientation: 'h' as const,
        y: 1.12,
        x: 0.5,
        xanchor: 'center' as const,
        font: { color: textColor, size: 11 },
      },
      hovermode: 'x unified' as const,
      hoverlabel: hoverLabel(ct),
    }, {
      responsive: true,
      displayModeBar: 'hover' as any,
      modeBarButtonsToRemove: [
        'select2d',
        'lasso2d',
        'autoScale2d',
        'hoverClosestCartesian',
        'hoverCompareCartesian',
        'toggleSpikelines'
      ],
    });

    return () => {
      Plotly.purge(container!);
    };
  }, [data, theme, selectedModels]);

  const handleRegenerate = async () => {
    setRegenerating(true);
    try {
      await regenerateForecast();
      alert('Forecast regeneration started in the background. Refresh the page in a few minutes to see updated results.');
    } catch (err) {
      console.error('Regeneration request failed:', err);
      alert('Failed to start forecast regeneration.');
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-lg p-5 transition-all duration-300 hover:shadow-glow-subtle hover:border-border-elevated">
      <div className="flex items-center justify-between mb-1">
        <h3 className="font-display text-base font-semibold tracking-wide">Model Predictions vs Actual</h3>
        <button
          onClick={handleRegenerate}
          disabled={regenerating}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-bg hover:bg-surface-elevated transition-all text-xs font-semibold uppercase tracking-wider cursor-pointer disabled:opacity-50"
        >
          {regenerating ? (
            <>
              <svg className="animate-spin h-3 w-3 text-primary" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Running...
            </>
          ) : (
            <>
              <svg className="w-3 h-3 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Regenerate
            </>
          )}
        </button>
      </div>
      <p className="text-text-muted text-[13px] mb-4">Four models trained on the full Western–Chinese tone-gap series; dashed lines show each model's 14-day holdout projection against the actual values (solid green line).</p>

      {loading && (
        <div className="flex items-center justify-center" style={{ height: '360px' }}>
          <div className="text-text-muted text-sm font-sans flex items-center gap-2">
            <svg className="animate-spin h-4 w-4 text-primary" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading forecast evaluation...
          </div>
        </div>
      )}

      {!loading && (!data || data.predictions.length === 0) && (
        <div className="flex items-center justify-center text-text-muted text-sm font-sans" style={{ height: '360px' }}>
          No forecast predictions available.
        </div>
      )}

      <div ref={containerRef} style={{ width: '100%', height: '400px', display: loading || !data || data.predictions.length === 0 ? 'none' : 'block' }} />
    </div>
  );
}
