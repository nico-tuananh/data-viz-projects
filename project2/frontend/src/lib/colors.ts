/**
 * Centralized color palette — single source of truth for all chart / map / theme
 * colors used at runtime (Plotly, MapLibre, d3-cloud, inline styles).
 *
 * Phase 1: muted "tariff-tension" editorial palette replacing the original
 * template colors (bright #2563EB blue, #EF4444 red, #84CC16 lime) with
 * desaturated, journalistic equivalents.
 *
 * NOTE: Tailwind utility tokens (tailwind.config.js) and CSS custom properties
 * (index.css) mirror these values but cannot import this module directly, so
 * they are kept in sync by hand. This file is canonical for any JS-driven color.
 */

// ─── Media-group / bloc colors ────────────────────────────────────────────────
export const WESTERN = '#5A8FCA'; // balanced slate-blue — calm, legible, premium
export const CHINESE = '#D96B6B'; // muted crimson-coral — geopolitical weight, not piercing
export const GLOBAL  = '#9CA3AF'; // warm neutral gray

export const GROUP_COLORS: Record<string, string> = {
  Western: WESTERN,
  Chinese: CHINESE,
  'Global/Other': GLOBAL,
};

// ─── Sentiment / tone ─────────────────────────────────────────────────────────
export const TONE_POSITIVE = '#3D8168'; // muted teal-green (was #22C55E / #16A34A)
export const TONE_NEGATIVE = '#B23A48'; // brick (reuses CHINESE; was #EF4444)
export const TONE_NEUTRAL = '#A8A29E'; // warm taupe (was #9CA3AF)

// ─── Tension / escalation accent ──────────────────────────────────────────────
export const TENSION      = '#E2B25B'; // soft ochre / sage-amber — refined mid-tone
export const TENSION_FILL = 'rgba(226, 178, 91, 0.15)'; // ochre @ 15% — glass area fill
export const MIXED        = '#E2B25B'; // mixed-bloc cluster fallback (mirrors TENSION)

// ─── Choropleth tone ramp (positive → neutral → negative) ──────────────────────
// Muted teal family for positive tone, brick family for negative.
export function choroplethColor(avgTone: number): string {
  if (avgTone > 1.5) return '#2E6B57'; // deep teal
  if (avgTone > 0.5) return '#3D8168'; // teal
  if (avgTone > 0.1) return '#5C9A82'; // light teal
  if (avgTone > -0.1) return TONE_NEUTRAL; // neutral taupe
  if (avgTone > -0.5) return '#C57F88'; // light brick
  if (avgTone > -1.5) return '#B23A48'; // brick
  return '#8F2D39'; // deep brick
}

// Choropleth legend swatches (representative buckets)
export const CHOROPLETH_POSITIVE = '#3D8168';
export const CHOROPLETH_NEUTRAL = TONE_NEUTRAL;
export const CHOROPLETH_NEGATIVE = '#B23A48';

// ─── Forecast model categorical colors ─────────────────────────────────────────
export const MODEL_COLORS: Record<string, string> = {
  ARIMA: WESTERN, //   was #2563EB
  HoltWinters: TENSION, // was #F59E0B amber
  Prophet: '#7C6BA8', // muted plum (was #8B5CF6 violet)
  TimesFM: CHINESE, // was #EF4444
};
export const FORECAST_ACTUAL = '#3D8168'; // muted teal (was #16A34A green)
export const FORECAST_FULL_SERIES = '#94A3B8'; // slate gray (unchanged, neutral)

// ─── Word-cloud TF-IDF ramps (index 0 = darkest / highest weight → lightest) ───
// Aligned to the new WESTERN (#5A8FCA) and CHINESE (#D96B6B) mid-tone palette.
export const WESTERN_RAMP = ['#1D3C5E', '#2B5190', '#3D6DA0', '#5A8FCA', '#7AAAD6', '#C1D8EE'];
export const CHINESE_RAMP = ['#7A2828', '#A03434', '#C24848', '#D96B6B', '#E89595', '#F4C0C0'];

// ─── Neutral chart theme (Plotly text / grid / hover) ──────────────────────────
// These are theme-aware neutral grays, identical across every Plotly chart.
// Centralized to remove duplication; values are unchanged (not part of the
// bright blue/red/lime palette being replaced).
export interface ChartTheme {
  textColor: string;
  labelColor: string;
  gridColor: string;
  zeroColor: string;
  hoverBg: string;
  hoverBorder: string;
  hoverText: string;
  fontFamily: string;
}

export function chartTheme(theme: 'light' | 'dark'): ChartTheme {
  const dark = theme === 'dark';
  return {
    textColor:   dark ? '#A8A8B0' : '#52525B',
    labelColor:  dark ? '#6E6E78' : '#8E8E93',
    gridColor:   dark ? '#252528' : '#E4E4E7',
    zeroColor:   dark ? '#4A4A52' : '#A1A1AA',
    hoverBg:     dark ? '#1a1a1c' : '#ffffff', // matches --color-surface
    hoverBorder: dark ? '#2e2e32' : '#e4e4e7',
    hoverText:   dark ? '#e2e2e5' : '#09090b', // matches new --color-text-primary
    fontFamily: 'Plus Jakarta Sans, DM Sans, sans-serif',
  };
}

// Plotly hoverlabel block built from a ChartTheme (used by most charts).
export function hoverLabel(t: ChartTheme) {
  return {
    bgcolor: t.hoverBg,
    bordercolor: t.hoverBorder,
    font: { family: t.fontFamily, size: 12, color: t.hoverText },
    align: 'left' as const,
  };
}

// ─── Neutral map surfaces ──────────────────────────────────────────────────────
export const MAP_EMPTY_FILL_DARK = '#1c1c24';
export const MAP_EMPTY_FILL_LIGHT = '#E4E4E7';
