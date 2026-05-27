/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useTheme } from '../hooks/useTheme';
import { getKeywords, type KeywordEntry } from '../api';

const TOP_N_OPTIONS = [10, 15, 20, 30] as const;

export default function KeywordFramingChart() {
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [topN, setTopN] = useState<number>(20);
  const [western, setWestern] = useState<KeywordEntry[]>([]);
  const [chinese, setChinese] = useState<KeywordEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getKeywords(topN)
      .then((res) => {
        setWestern(res.groups?.Western ?? []);
        setChinese(res.groups?.Chinese ?? []);
      })
      .catch((err) => {
        console.error('Error loading keywords:', err);
        setError('Failed to load keyword data.');
      })
      .finally(() => setLoading(false));
  }, [topN]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || (western.length === 0 && chinese.length === 0)) return;

    const wMap = new Map(western.map((k) => [k.keyword, k.tfidf_score]));
    const cMap = new Map(chinese.map((k) => [k.keyword, k.tfidf_score]));
    const allKeywords = Array.from(new Set([...wMap.keys(), ...cMap.keys()]));

    // Sort ascending by (western - chinese) so most Western-dominant lands at top of horizontal chart
    const sorted = allKeywords
      .map((k) => ({ keyword: k, w: wMap.get(k) ?? 0, c: cMap.get(k) ?? 0 }))
      .sort((a, b) => (a.w - a.c) - (b.w - b.c));

    const labels = sorted.map((d) => d.keyword);
    const wScores = sorted.map((d) => d.w);
    const cScores = sorted.map((d) => -d.c); // negate so Chinese bars extend left

    const textColor = theme === 'dark' ? '#A1A1AA' : '#52525B';
    const labelColor = theme === 'dark' ? '#71717A' : '#8E8E93';
    const gridColor = theme === 'dark' ? '#27272A' : '#E4E4E7';
    const zeroColor = theme === 'dark' ? '#52525B' : '#A1A1AA';

    const westernTrace: any = {
      x: wScores,
      y: labels,
      type: 'bar',
      orientation: 'h',
      name: 'Western',
      marker: { color: '#2563EB', opacity: 0.85 },
      hovertemplate: '<b>%{y}</b><br>Western TF-IDF: %{x:.4f}<extra></extra>',
    };

    const chineseTrace: any = {
      x: cScores,
      y: labels,
      type: 'bar',
      orientation: 'h',
      name: 'Chinese',
      marker: { color: '#EF4444', opacity: 0.85 },
      customdata: sorted.map((d) => d.c),
      hovertemplate: '<b>%{y}</b><br>Chinese TF-IDF: %{customdata:.4f}<extra></extra>',
    };

    const maxScore = Math.max(...wScores, ...cScores.map(Math.abs)) * 1.15;
    const chartHeight = Math.max(380, labels.length * 24);

    Plotly.react(
      container,
      [chineseTrace, westernTrace],
      {
        barmode: 'overlay',
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: textColor, family: 'DM Sans, sans-serif' },
        margin: { t: 20, r: 20, b: 50, l: 120 },
        height: chartHeight,
        xaxis: {
          title: { text: 'TF-IDF Score  (Chinese ←  0  → Western)', font: { color: labelColor, size: 11 } },
          range: [-maxScore, maxScore],
          gridcolor: gridColor,
          zerolinecolor: zeroColor,
          zerolinewidth: 1.5,
          tickfont: { color: textColor, size: 10 },
          tickformat: '.3f',
        },
        yaxis: {
          gridcolor: gridColor,
          tickfont: { color: textColor, size: 11 },
          automargin: true,
        },
        legend: {
          orientation: 'h',
          y: 1.05,
          x: 0.5,
          xanchor: 'center',
          font: { color: textColor, size: 12 },
        },
      },
      { responsive: true, displayModeBar: false }
    );

    return () => {
      Plotly.purge(container!);
    };
  }, [western, chinese, theme]);

  return (
    <div className="bg-surface border border-border rounded-lg p-5 transition-all duration-300 hover:shadow-glow-subtle hover:border-border-elevated">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-mono text-base font-bold tracking-wide">
          Western vs Chinese Keyword Framing
        </h3>
        <div className="flex items-center gap-2 text-xs text-text-secondary">
          <span className="text-text-muted">Top keywords:</span>
          {TOP_N_OPTIONS.map((n) => (
            <button
              key={n}
              onClick={() => setTopN(n)}
              className={`px-2 py-0.5 rounded border text-xs font-mono transition-all cursor-pointer ${
                topN === n
                  ? 'bg-primary border-primary text-white'
                  : 'border-border-elevated bg-bg hover:border-primary hover:text-primary'
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      <p className="text-text-muted text-xs mb-4">
        TF-IDF computed over article-level proxies: URL slug keywords, actor names, event types, and locations.
        Bars extending right = Western emphasis; left = Chinese emphasis.
      </p>

      {loading && (
        <div className="flex items-center justify-center h-40 text-text-muted text-sm">
          Computing TF-IDF…
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center h-40 text-error text-sm">{error}</div>
      )}
      {!loading && !error && (
        <div ref={containerRef} style={{ width: '100%' }} />
      )}
    </div>
  );
}
