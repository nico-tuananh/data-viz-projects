/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState } from 'react';
import { useFilters } from '../hooks/useFilters';
import { getSummary, type SummaryResponse } from '../api';

export default function SummaryCards() {
  const { filters, mediaParam } = useFilters();
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getSummary({
      start: filters.start,
      end: filters.end,
      media: mediaParam,
      direction: filters.direction,
    })
      .then(setData)
      .catch((err) => console.error('Error loading summary cards data:', err))
      .finally(() => setLoading(false));
  }, [filters.start, filters.end, mediaParam, filters.direction]);

  const westTone = data?.avgToneWestern ?? 0;
  const chinTone = data?.avgToneChinese ?? 0;

  const cards = [
    {
      label: 'Total Events',
      value: data?.totalEvents.toLocaleString() ?? '--',
      color: 'text-primary',
      hoverStyle: 'hover:border-primary/40 hover:shadow-glow-subtle',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
        </svg>
      ),
    },
    {
      label: 'Unique Sources',
      value: data?.uniqueSources.toLocaleString() ?? '--',
      color: 'text-secondary',
      hoverStyle: 'hover:border-secondary/40 hover:shadow-glow-medium',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
        </svg>
      ),
    },
    {
      label: 'Avg Tone (Western)',
      value: data?.avgToneWestern != null ? data.avgToneWestern.toFixed(2) : '--',
      color: westTone >= 0 ? 'text-success' : 'text-error',
      hoverStyle: westTone >= 0 
        ? 'hover:border-success/40 hover:shadow-glow-profit' 
        : 'hover:border-error/40 hover:shadow-glow-loss',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
    {
      label: 'Avg Tone (Chinese)',
      value: data?.avgToneChinese != null ? data.avgToneChinese.toFixed(2) : '--',
      color: chinTone >= 0 ? 'text-success' : 'text-error',
      hoverStyle: chinTone >= 0 
        ? 'hover:border-success/40 hover:shadow-glow-profit' 
        : 'hover:border-error/40 hover:shadow-glow-loss',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
        </svg>
      ),
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`bg-surface border border-border rounded-lg p-5 flex items-center gap-4 transition-all duration-300 ${
            card.hoverStyle
          } ${loading ? 'opacity-60' : ''}`}
        >
          <div className={`${card.color} opacity-90 transition-colors duration-300`}>
            {card.icon}
          </div>
          <div>
            <div className="text-text-muted text-overline mb-1.5">
              {card.label}
            </div>
            <div className="font-mono text-xl font-bold text-text-primary tabular-nums">
              {card.value}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
