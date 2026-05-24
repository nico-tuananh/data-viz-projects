/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useFilters } from '../hooks/useFilters';
import { useTheme } from '../hooks/useTheme';
import { getEvents } from '../api';

const GROUP_COLORS: Record<string, string> = {
  Western: '#2563EB',
  Chinese: '#EF4444',
  'Global/Other': '#71717A',
};

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
        marker: { color: GROUP_COLORS[group] || '#71717A' },
        boxpoints: 'outliers' as const,
        line: { width: 1 },
      };
    });

    const textColor = theme === 'dark' ? '#A1A1AA' : '#52525B';
    const labelColor = theme === 'dark' ? '#71717A' : '#8E8E93';
    const gridColor = theme === 'dark' ? '#27272A' : '#E4E4E7';

    Plotly.react(containerRef.current, traces, {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: textColor, family: 'DM Sans, sans-serif' },
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
      <h3 className="font-mono text-base font-bold tracking-wide mb-4">Tone Distribution by Media Group</h3>
      <div ref={containerRef} style={{ width: '100%', height: '360px' }} />
    </div>
  );
}
