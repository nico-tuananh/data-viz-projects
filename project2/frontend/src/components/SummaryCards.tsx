/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState } from 'react';
import { useFilters } from '../hooks/useFilters';
import { getSummary, type SummaryResponse } from '../api';
import { WESTERN, CHINESE, GLOBAL } from '../lib/colors';

// ─── Accent palette ────────────────────────────────────────────────────────────
const NEUTRAL_ACCENT = GLOBAL; // #9CA3AF — for the two count metrics

interface CardDef {
  label: string;
  value: string;
  accentColor: string; // top-border + icon tint
  valueColor: string;  // CSS color for the KPI number
  context: string;     // short non-truncating context label (≤ 25 chars)
  icon: React.ReactNode;
}

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

  // Short framing label — max 16 chars, never truncates
  const toneContext = (v: number) =>
    v > 0.1 ? 'Positive framing' : v < -0.1 ? 'Negative framing' : 'Neutral tone';

  const cards: CardDef[] = [
    {
      label: 'Total Events',
      value: data?.totalEvents.toLocaleString() ?? '--',
      accentColor: NEUTRAL_ACCENT,
      valueColor: 'var(--color-text-primary)',
      context: 'Indexed GDELT articles',
      icon: (
        // Document-text — universally understood as "article / indexed record"
        <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" strokeWidth={1.75} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      label: 'Unique Sources',
      value: data?.uniqueSources.toLocaleString() ?? '--',
      accentColor: NEUTRAL_ACCENT,
      valueColor: 'var(--color-text-primary)',
      context: 'Publication domains',
      icon: (
        // Globe — conveys global source diversity
        <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" strokeWidth={1.75} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
        </svg>
      ),
    },
    {
      label: 'Avg Tone · Western',
      value: data?.avgToneWestern != null ? data.avgToneWestern.toFixed(2) : '--',
      accentColor: WESTERN,
      valueColor: WESTERN,
      context: toneContext(westTone),
      icon: (
        // Chart-bar ascending — three bars representing sentiment analysis scale
        <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" strokeWidth={1.75} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
        </svg>
      ),
    },
    {
      label: 'Avg Tone · Chinese',
      value: data?.avgToneChinese != null ? data.avgToneChinese.toFixed(2) : '--',
      accentColor: CHINESE,
      valueColor: CHINESE,
      context: toneContext(chinTone),
      icon: (
        // Arrow-trending — flowing line with upward arrow, signals tone trajectory
        <svg className="w-[18px] h-[18px]" fill="none" stroke="currentColor" strokeWidth={1.75} viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round"
            d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
        </svg>
      ),
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`
            bg-surface border border-border rounded-xl p-5
            flex flex-col gap-2.5
            transition-all duration-300
            hover:shadow-glow-subtle hover:border-border-elevated
            ${loading ? 'opacity-50' : ''}
          `}
          style={{ borderTop: `3px solid ${card.accentColor}` }}
        >
          {/* ── Top: label + icon in tinted box ─────────────────────────── */}
          <div className="flex items-start justify-between gap-2">
            <span className="text-[11px] uppercase tracking-widest font-semibold text-text-muted leading-tight">
              {card.label}
            </span>
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: `${card.accentColor}1a` }}
            >
              <span style={{ color: card.accentColor }}>{card.icon}</span>
            </div>
          </div>

          {/* ── Middle: KPI number ───────────────────────────────────────── */}
          <div
            className="font-data text-3xl font-bold tabular-nums tracking-tight leading-none"
            style={{ color: card.valueColor }}
          >
            {card.value}
          </div>

          {/* ── Bottom: short context label ──────────────────────────────── */}
          <p className="text-[11px] text-text-muted font-sans leading-none mt-auto">
            {card.context}
          </p>
        </div>
      ))}
    </div>
  );
}
