/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useFilters } from '../hooks/useFilters';
import { useTheme } from '../hooks/useTheme';
import { getToneGap } from '../api';

export default function ToneGapChart() {
  const { filters } = useFilters();
  const { theme } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    getToneGap({
      start: filters.start,
      end: filters.end,
      media: '',
      direction: filters.direction,
    })
      .then((res) => setData(res.records))
      .catch((err) => console.error('Error loading tone gap data:', err));
  }, [filters.start, filters.end, filters.direction]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || data.length === 0) return;

    const westernTrace = {
      x: data.map((d) => d.Date),
      y: data.map((d) => d.WesternTone),
      mode: 'lines' as const,
      line: { color: '#2563EB', width: 2 },
      name: 'Western Tone',
      hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
    };

    const chineseTrace = {
      x: data.map((d) => d.Date),
      y: data.map((d) => d.ChineseTone),
      mode: 'lines' as const,
      line: { color: '#EF4444', width: 2 },
      name: 'Chinese Tone',
      hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
    };

    const gapTrace = {
      x: data.map((d) => d.Date),
      y: data.map((d) => d.ToneGap),
      mode: 'lines' as const,
      fill: 'tozeroy' as const,
      line: { color: '#84CC16', width: 2 }, // CoinPulse Secondary Lime indicator
      fillcolor: 'rgba(132, 204, 22, 0.15)', // Lime at 15% opacity
      name: 'Tone Gap',
      hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
    };

    const textColor = theme === 'dark' ? '#A1A1AA' : '#52525B';
    const labelColor = theme === 'dark' ? '#71717A' : '#8E8E93';
    const gridColor = theme === 'dark' ? '#27272A' : '#E4E4E7';

    const zeroLine = {
      x: data.map((d) => d.Date),
      y: data.map(() => 0),
      mode: 'lines' as const,
      line: { color: labelColor, width: 1, dash: 'dash' as const },
      hoverinfo: 'skip' as const,
      showlegend: false,
    };

    Plotly.react(containerRef.current, [westernTrace, chineseTrace, gapTrace, zeroLine], {
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
      hovermode: 'x unified' as const,
      hoverlabel: {
        bgcolor: theme === 'dark' ? '#18181b' : '#ffffff',
        bordercolor: theme === 'dark' ? '#27272a' : '#e4e4e7',
        font: {
          family: 'DM Sans, sans-serif',
          size: 12,
          color: theme === 'dark' ? '#fafafa' : '#09090b',
        },
        align: 'left' as const,
      },
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
      <h3 className="font-mono text-base font-bold tracking-wide mb-4">Western vs Chinese Tone Gap</h3>
      <div ref={containerRef} style={{ width: '100%', height: '360px' }} />
    </div>
  );
}
