/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useTheme } from '../hooks/useTheme';
import { getKeywords, type KeywordEntry } from '../api';
import { WESTERN, CHINESE, chartTheme, hoverLabel } from '../lib/colors';

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

    const ct = chartTheme(theme);
    const { textColor, labelColor, gridColor, zeroColor } = ct;

    const westernTrace: any = {
      x: wScores,
      y: labels,
      type: 'bar',
      orientation: 'h',
      name: 'Western',
      marker: { color: WESTERN, opacity: 0.85 },
      hovertemplate: '<b>%{y}</b><br>Western TF-IDF: <b>%{x:.4f}</b><extra></extra>',
    };

    const chineseTrace: any = {
      x: cScores,
      y: labels,
      type: 'bar',
      orientation: 'h',
      name: 'Chinese',
      marker: { color: CHINESE, opacity: 0.85 },
      customdata: sorted.map((d) => d.c),
      hovertemplate: '<b>%{y}</b><br>Chinese TF-IDF: <b>%{customdata:.4f}</b><extra></extra>',
    };

    const maxScore = Math.max(...wScores, ...cScores.map(Math.abs)) * 1.15;
    // Lower the floor so 10-keyword charts don't over-allocate vertical space.
    // 24 px per row × N rows; minimum 260 px prevents tiny charts at very low N.
    const chartHeight = Math.max(260, labels.length * 24);

    Plotly.react(
      container,
      [chineseTrace, westernTrace],
      {
        barmode: 'overlay',
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: textColor, family: 'DM Sans, sans-serif' },
        // Legend is now an HTML element above the chart, so no SVG top margin needed for it.
        margin: { t: 10, r: 20, b: 50, l: 120 },
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
        showlegend: false,
        hovermode: 'closest' as const,
        hoverlabel: hoverLabel(ct),
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
        <h3 className="font-display text-base font-semibold tracking-wide">
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

      <p className="text-text-muted text-[13px] mb-4">
        TF-IDF on scraped headlines (GDELT metadata as fallback) — bar length reflects how overrepresented each term is in that bloc's framing.
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
        <>
          {/* Fixed HTML legend — decoupled from chart height so spacing never shifts */}
          <div className="flex items-center justify-center gap-5 mb-2">
            {([{ label: 'Chinese', color: CHINESE }, { label: 'Western', color: WESTERN }] as const).map(({ label, color }) => (
              <div key={label} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: color, opacity: 0.85 }} />
                <span className="text-xs font-medium" style={{ color }}>{label}</span>
              </div>
            ))}
          </div>
          <div ref={containerRef} style={{ width: '100%' }} />
        </>
      )}
    </div>
  );
}
