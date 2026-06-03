/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useFilters } from '../hooks/useFilters';
import { useTheme } from '../hooks/useTheme';
import { getEvents } from '../api';
import { GROUP_COLORS, GLOBAL, chartTheme, hoverLabel } from '../lib/colors';

export default function DistributionChart() {
  const { filters, mediaParam } = useFilters();
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    getEvents({
      start: filters.start,
      end: filters.end,
      media: mediaParam,
      direction: filters.direction,
      limit: 5000,
    })
      .then((res) => setData(res.records))
      .catch((err) => console.error('Error loading distribution data:', err));
  }, [filters.start, filters.end, mediaParam, filters.direction]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || data.length === 0) return;

    const groups = Array.from(new Set(data.map((d) => d.MediaGroup)));
    const traces = groups.map((group) => {
      const values = data.filter((d) => d.MediaGroup === group).map((d) => d.AvgTone);
      return {
        y: values,
        type: 'box' as const,
        name: group,
        marker: { color: GROUP_COLORS[group] || GLOBAL },
        boxpoints: 'outliers' as const,
        line: { width: 1 },
      };
    });

    const ct = chartTheme(theme);
    const { textColor, labelColor, gridColor } = ct;

    Plotly.react(containerRef.current, traces, {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: textColor, family: ct.fontFamily },
      margin: { t: 30, r: 30, b: 50, l: 60 },
      xaxis: {
        title: { text: 'Media Group', font: { color: labelColor, size: 12 } },
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
      <h3 className="font-display text-base font-semibold tracking-wide mb-1">Tone Distribution by Media Group</h3>
      <p className="text-text-muted text-[13px] mb-4">5,000-event sample showing spread and consistency of sentiment scores across each media bloc.</p>
      <div ref={containerRef} style={{ width: '100%', height: '360px' }} />
    </div>
  );
}
