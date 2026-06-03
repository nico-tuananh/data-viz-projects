/* eslint-disable @typescript-eslint/no-explicit-any */
import { useEffect, useRef, useState } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useFilters } from '../hooks/useFilters';
import { useTheme } from '../hooks/useTheme';
import { getToneGap } from '../api';
import { WESTERN, CHINESE, TENSION, TENSION_FILL, chartTheme, hoverLabel } from '../lib/colors';

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
      line: { color: WESTERN, width: 2 },
      name: 'Western Tone',
      hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
    };

    const chineseTrace = {
      x: data.map((d) => d.Date),
      y: data.map((d) => d.ChineseTone),
      mode: 'lines' as const,
      line: { color: CHINESE, width: 2 },
      name: 'Chinese Tone',
      hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
    };

    const gapTrace = {
      x: data.map((d) => d.Date),
      y: data.map((d) => d.ToneGap),
      mode: 'lines' as const,
      fill: 'tozeroy' as const,
      line: { color: TENSION, width: 2 }, // champagne gold tension accent
      fillcolor: TENSION_FILL, // ochre at 15% opacity
      name: 'Tone Gap',
      hovertemplate: '%{fullData.name}: <b>%{y:.3f}</b><extra></extra>',
    };

    const ct = chartTheme(theme);
    const { textColor, labelColor, gridColor } = ct;

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
      font: { color: textColor, family: ct.fontFamily },
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
      <h3 className="font-display text-base font-semibold tracking-wide mb-1">Western vs Chinese Tone Gap</h3>
      <p className="text-text-muted text-[13px] mb-4">GDELT AvgTone (−10 to +10); the shaded area shows divergence between Western and Chinese sentiment.</p>
      <div ref={containerRef} style={{ width: '100%', height: '360px' }} />
    </div>
  );
}
