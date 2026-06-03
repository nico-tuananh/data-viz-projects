/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useFilters } from '../hooks/useFilters';
import { useTheme } from '../hooks/useTheme';
import { getDaily } from '../api';
import { GROUP_COLORS, GLOBAL, chartTheme, hoverLabel } from '../lib/colors';

export default function BubbleChart() {
  const { filters, mediaParam } = useFilters();
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    getDaily({
      start: filters.start,
      end: filters.end,
      media: mediaParam,
      direction: filters.direction,
    })
      .then((res) => setData(res.records))
      .catch((err) => console.error('Error loading bubble chart daily data:', err));
  }, [filters.start, filters.end, mediaParam, filters.direction]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || data.length === 0) return;

    const groups = ['Western', 'Chinese', 'Global/Other'];
    const traces = groups.map((group) => {
      const groupData = data.filter((d) => d.MediaGroup === group);
      if (groupData.length === 0) return null;
      return {
        x: groupData.map((d) => d.TotalArticles),
        y: groupData.map((d) => d.AvgTone),
        mode: 'markers' as const,
        name: group,
        marker: {
          color: GROUP_COLORS[group] || GLOBAL,
          size: groupData.map((d) => Math.max(6, Math.min(40, Math.sqrt(d.TotalEvents) * 3))),
          opacity: 0.6,
          line: { width: 0 },
        },
        text: groupData.map((d) => {
          const dateStr = new Date(d.Date).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          });
          return `<b>${dateStr}</b><br>` +
                 `Articles: <b>${d.TotalArticles}</b><br>` +
                 `Events: <b>${d.TotalEvents}</b>`;
        }),
        hovertemplate: '%{text}<br>Avg Tone: <b>%{y:.2f}</b><extra></extra>',
      };
    });

    const ct = chartTheme(theme);
    const { textColor, labelColor, gridColor } = ct;

    Plotly.react(containerRef.current, traces.filter((t): t is NonNullable<typeof t> => t !== null), {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: textColor, family: ct.fontFamily },
      margin: { t: 30, r: 30, b: 50, l: 60 },
      xaxis: {
        title: { text: 'Total Articles', font: { color: labelColor, size: 12 } },
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: textColor },
      },
      yaxis: {
        title: { text: 'AvgTone', font: { color: labelColor, size: 12 } },
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        tickfont: { color: textColor },
      },
      legend: {
        orientation: 'h' as const,
        y: 1.1,
        x: 0.5,
        xanchor: 'center' as const,
        font: { color: textColor },
      },
      hovermode: 'closest' as const,
      hoverlabel: hoverLabel(ct),
    }, {
      responsive: true,
      displayModeBar: false,
    });

    return () => {
      Plotly.purge(container!);
    };
  }, [data, theme]);

  return (
    <div className="bg-surface border border-border rounded-lg p-5 mb-6 transition-all duration-300 hover:shadow-glow-subtle hover:border-border-elevated">
      <h3 className="font-display text-base font-semibold tracking-wide mb-1">Tone vs Coverage Intensity</h3>
      <p className="text-text-muted text-[13px] mb-4">Full daily aggregate — each dot is one media-bloc day; bubble size reflects event count.</p>
      <div ref={containerRef} style={{ width: '100%', height: '360px' }} />
    </div>
  );
}
