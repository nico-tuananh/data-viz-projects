import { useEffect, useState } from 'react';
import { getForecastMetrics, type ForecastMetricsResponse } from '../api';
import { MODEL_COLORS, GLOBAL } from '../lib/colors';

interface ForecastMetricsCardProps {
  selectedModels: string[];
  onToggleModel: (modelName: string) => void;
}

export default function ForecastMetricsCard({ selectedModels, onToggleModel }: ForecastMetricsCardProps) {
  const [data, setData] = useState<ForecastMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getForecastMetrics()
      .then((res) => { setData(res); setLoading(false); })
      .catch((err) => { console.error('Error loading forecast metrics:', err); setLoading(false); });
  }, []);

  const models = data?.models ?? [];
  const bestModel = models.length > 0
    ? models.reduce((best, m) => (m.mae < best.mae ? m : best), models[0])
    : null;

  return (
    <div className="bg-surface border border-border rounded-lg p-5 transition-all duration-300 hover:shadow-glow-subtle hover:border-border-elevated">
      <h3 className="font-display text-base font-semibold tracking-wide mb-1">Forecast Model Metrics</h3>
      <p className="text-text-muted text-[13px] mb-4">Accuracy evaluated on the Apr 17–30 holdout period — lower MAE/RMSE is better. Click a row to toggle its projection in the chart.</p>

      {loading && (
        <div className="text-text-muted text-sm font-sans">Loading metrics...</div>
      )}

      {!loading && models.length === 0 && (
        <div className="text-text-muted text-sm font-sans">No forecast data available.</div>
      )}

      {!loading && models.length > 0 && (
        <div className="space-y-3">
          {models.map((m) => {
            const isBest = bestModel?.name === m.name;
            const isSelected = selectedModels.includes(m.name);
            return (
              <div
                key={m.name}
                onClick={() => onToggleModel(m.name)}
                className={`flex items-center justify-between rounded-md px-3 py-2 border cursor-pointer select-none transition-all duration-200 hover:scale-[1.01] ${
                  isSelected
                    ? isBest
                      ? 'border-amber-500/60 bg-amber-500/5 shadow-glow-subtle'
                      : 'border-border-elevated bg-surface-elevated'
                    : 'border-border/30 bg-bg/50 opacity-40 hover:opacity-60'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-3.5 h-3.5 rounded-[4px] border flex items-center justify-center transition-all ${
                      isSelected
                        ? 'border-primary bg-primary text-white'
                        : 'border-border bg-bg'
                    }`}
                  >
                    {isSelected && (
                      <svg className="w-2.5 h-2.5" viewBox="0 0 20 20" fill="currentColor">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>
                  <div
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: isSelected ? (MODEL_COLORS[m.name] || GLOBAL) : GLOBAL }}
                  />
                  <span className={`text-sm font-semibold ${isSelected ? 'text-text-primary' : 'text-text-muted'}`}>{m.name}</span>
                  {isBest && isSelected && (
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600 bg-amber-500/10 px-1.5 py-0.5 rounded">
                      Best MAE
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-xs font-data">
                  <div className="text-right">
                    <div className="text-text-muted">MAE</div>
                    <div className="text-text-primary font-semibold">{m.mae.toFixed(4)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-text-muted">RMSE</div>
                    <div className="text-text-primary font-semibold">{m.rmse.toFixed(4)}</div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-3 pt-2 border-t border-border text-xs text-text-muted font-sans">
        14-day holdout evaluation (Apr 17 – Apr 30)
      </div>
    </div>
  );
}
