import { useEffect, useRef, useState } from 'react';
import cloud from 'd3-cloud';
import { getWordCloud, type WordCloudEntry } from '../api';

// ─── Layout canvas dimensions ─────────────────────────────────────────────────
const PANEL_W = 620;
const PANEL_H = 460;

// ─── Color palettes: index 0 = darkest (high TF-IDF), 5 = lightest ───────────
const BLUE_PALETTE = ['#1e3a8a', '#1d4ed8', '#2563eb', '#0ea5e9', '#38bdf8', '#7dd3fc'];
const RED_PALETTE  = ['#7f1d1d', '#b91c1c', '#dc2626', '#ef4444', '#f87171', '#fca5a5'];

// ─── d3-cloud word shape ──────────────────────────────────────────────────────
// Extends d3-cloud's Word interface (which uses `weight` for css font-weight)
interface D3Word {
  text: string;
  size: number;           // font-size px, used by d3-cloud for layout
  weight: number;         // css font-weight (400/500/700/800), d3-cloud reads this for canvas measurement
  rotate: number;         // pre-computed rotation angle
  x?: number;             // set by d3-cloud after layout
  y?: number;
  // custom fields carried through
  color: string;
  opacity: number;
  tfidf: number;          // original TF-IDF weight from API
  docCount: number;
  termType: string;
}

// ─── Build word list from API data ────────────────────────────────────────────
function buildWords(entries: WordCloudEntry[], palette: string[]): D3Word[] {
  if (!entries.length) return [];

  const wts  = entries.map(w => w.weight);
  const mn   = Math.min(...wts);
  const mx   = Math.max(...wts);
  const norm = (v: number) => mx === mn ? 0.5 : (v - mn) / (mx - mn);

  return entries.map(w => {
    const t         = norm(w.weight);
    const isPhrase  = (w.type ?? 'unigram') !== 'unigram';

    // Font size: unigrams can be largest; trigrams are capped to avoid extreme width
    const maxFs = w.type === 'trigram' ? 36 : isPhrase ? 46 : 60;
    const size  = Math.round(14 + t * (maxFs - 14));

    // CSS font-weight — heavier words look bolder AND d3-cloud measures them wider
    const fontW = t > 0.72 ? 800 : t > 0.48 ? 700 : t > 0.24 ? 500 : 400;

    // Color: highest TF-IDF → index 0 (darkest), lowest → index 5 (lightest)
    const colorIdx = Math.min(palette.length - 1, Math.floor((1 - t) * palette.length));

    // Rotation: phrases always horizontal; unigrams get hash-based vertical/horizontal mix
    let rotate = 0;
    if (!isPhrase) {
      const hash = w.word.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
      // 60% horizontal, 20% +90°, 20% -90°
      const opts = [0, 0, 0, 90, -90] as const;
      rotate = opts[hash % opts.length];
    }

    return {
      text:     w.word,
      size,
      weight:   fontW,
      rotate,
      color:    palette[colorIdx],
      opacity:  0.65 + t * 0.35,
      tfidf:    w.weight,
      docCount: w.count,
      termType: w.type ?? 'unigram',
    };
  });
}

// ─── Seeded PRNG (xorshift32) — deterministic layout on every render ──────────
function makeRng(seed: number): () => number {
  let s = seed;
  return () => {
    s ^= s << 13; s ^= s >>> 17; s ^= s << 5;
    return (s >>> 0) / 0x100000000;
  };
}

// ─── Panel component ──────────────────────────────────────────────────────────
interface PanelProps {
  entries: WordCloudEntry[];
  palette: string[];
  title: string;
}

function CloudPanel({ entries, palette, title }: PanelProps) {
  const [placed, setPlaced] = useState<D3Word[]>([]);
  const [computing, setComputing] = useState(true);
  const layoutRef = useRef<{ stop: () => void } | null>(null);

  useEffect(() => {
    if (!entries.length) { setComputing(false); return; }
    setComputing(true);

    const words = buildWords(entries, palette);

    const layout = cloud<D3Word>()
      .size([PANEL_W, PANEL_H])
      .words(words)
      .padding(5)
      .rotate((d) => d.rotate)
      .font('"DM Sans", sans-serif')
      .fontWeight((d) => d.weight)
      .fontSize((d) => d.size)
      .spiral('archimedean')
      .random(makeRng(0xcafebabe))
      .on('end', (drawn) => {
        setPlaced(drawn as D3Word[]);
        setComputing(false);
      });

    layoutRef.current = layout;
    layout.start();

    return () => {
      layoutRef.current?.stop();
      layoutRef.current = null;
    };
  }, [entries, palette]);

  const phrases = placed.filter(p => p.termType !== 'unigram').length;

  return (
    <div className="flex-1 min-w-[300px]">
      {/* Panel header */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className="font-mono text-sm font-bold" style={{ color: palette[2] }}>
          {title}
        </span>
        <span className="text-text-muted text-xs">
          {computing
            ? 'computing layout…'
            : `${placed.length}/${entries.length} terms · ${phrases} phrases`}
        </span>
      </div>

      {/* SVG cloud — viewBox makes it scale responsively */}
      <svg
        viewBox={`0 0 ${PANEL_W} ${PANEL_H}`}
        style={{ width: '100%', display: 'block' }}
        role="img"
        aria-label={`${title} word cloud`}
      >
        {/* d3-cloud centers layout at (0,0), so we translate to panel center */}
        <g transform={`translate(${PANEL_W / 2},${PANEL_H / 2})`}>
          {placed.map(w => (
            <text
              key={w.text}
              transform={`translate(${w.x ?? 0},${w.y ?? 0}) rotate(${w.rotate})`}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={w.size}
              fontWeight={w.weight}
              fontFamily='"DM Sans", sans-serif'
              fill={w.color}
              fillOpacity={w.opacity}
              style={{ cursor: 'default', userSelect: 'none' }}
            >
              <title>{`${w.termType} · TF-IDF: ${w.tfidf.toFixed(5)} · ${w.docCount} docs`}</title>
              {w.text}
            </text>
          ))}
        </g>
      </svg>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function WordCloudSection() {
  const [western, setWestern] = useState<WordCloudEntry[]>([]);
  const [chinese, setChinese] = useState<WordCloudEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    getWordCloud(80)
      .then(res => {
        setWestern(res.groups?.Western ?? []);
        setChinese(res.groups?.Chinese ?? []);
      })
      .catch(err => {
        console.error('Word cloud error:', err);
        setError('Failed to load word cloud data.');
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="bg-surface border border-border rounded-lg p-5 transition-all duration-300 hover:shadow-glow-subtle hover:border-border-elevated">
      {/* Section header */}
      <div className="mb-4">
        <h3 className="font-mono text-base font-bold tracking-wide">Phrase Word Cloud</h3>
        <p className="text-text-muted text-xs mt-1">
          TF-IDF phrase clouds — size and color depth reflect term distinctiveness.
          Hover any term for type, weight, and document count.
        </p>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-48 text-text-muted text-sm">
          Loading word cloud data…
        </div>
      )}
      {error && (
        <div className="flex items-center justify-center h-48 text-error text-sm">{error}</div>
      )}

      {!loading && !error && (
        <>
          <div className="flex gap-8 flex-wrap">
            <CloudPanel
              title="Western Media"
              entries={western}
              palette={BLUE_PALETTE}
            />
            <CloudPanel
              title="Chinese Media"
              entries={chinese}
              palette={RED_PALETTE}
            />
          </div>

          <div className="mt-3 pt-3 border-t border-border flex flex-wrap gap-x-5 gap-y-1 text-xs text-text-muted">
            <span>◉ Size + color depth = TF-IDF weight (larger/darker = more distinctive)</span>
            <span>◉ Vertical words = individual terms · horizontal = phrases</span>
            <span>◉ Hover any term for score details</span>
          </div>
        </>
      )}
    </div>
  );
}
