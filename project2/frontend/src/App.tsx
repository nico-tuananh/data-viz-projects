import { useState, useRef, useEffect } from 'react';
import { FiltersProvider } from './hooks/useFilters';
import { ThemeProvider, useTheme } from './hooks/useTheme';
import { refreshData } from './api';
import Sidebar from './components/Sidebar';
import SummaryCards from './components/SummaryCards';
import MapSection from './components/MapSection';
import TimelineChart from './components/TimelineChart';
import ToneGapChart from './components/ToneGapChart';
import DistributionChart from './components/DistributionChart';
import BubbleChart from './components/BubbleChart';
import ForecastMetricsCard from './components/ForecastMetricsCard';
import ForecastChart from './components/ForecastChart';
import KeywordFramingChart from './components/KeywordFramingChart';
import WordCloudSection from './components/WordCloudSection';

const NAV_SECTIONS = [
  { id: 'timeline', label: 'Conflict Timeline' },
  { id: 'spread',   label: 'Narrative Spread' },
  { id: 'divergence', label: 'Emotional Divergence' },
  { id: 'framing',  label: 'Keyword Framing' },
  { id: 'forecast', label: 'Narrative Gap Forecasting' },
] as const;

type SectionId = (typeof NAV_SECTIONS)[number]['id'];

interface SectionHeaderProps {
  index: number;
  sectionId: SectionId;
  question: string;
  description: string;
}

function SectionHeader({ index, sectionId, question, description }: SectionHeaderProps) {
  const label = NAV_SECTIONS.find((s) => s.id === sectionId)?.label ?? '';
  return (
    <div className="mb-6 pb-4 border-b border-border">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-mono text-[11px] text-text-muted tracking-widest">
          {String(index).padStart(2, '0')}
        </span>
        <span className="w-px h-3 bg-border-elevated" />
        <span className="text-overline text-primary" style={{ opacity: 0.75 }}>
          {label}
        </span>
      </div>
      <h2 className="text-subhead text-text-primary mb-2">{question}</h2>
      <p className="text-body-small text-text-muted max-w-3xl">{description}</p>
    </div>
  );
}

function Dashboard() {
  const { theme, toggleTheme } = useTheme();
  const [refreshing, setRefreshing] = useState(false);
  const [activeSection, setActiveSection] = useState<SectionId>('timeline');
  const [selectedModels, setSelectedModels] = useState<string[]>([
    'ARIMA',
    'HoltWinters',
    'Prophet',
    'TimesFM',
  ]);

  const timelineRef  = useRef<HTMLElement>(null);
  const spreadRef    = useRef<HTMLElement>(null);
  const divergenceRef = useRef<HTMLElement>(null);
  const framingRef   = useRef<HTMLElement>(null);
  const forecastRef  = useRef<HTMLElement>(null);

  const sectionRefMap: Record<SectionId, React.RefObject<HTMLElement | null>> = {
    timeline:   timelineRef,
    spread:     spreadRef,
    divergence: divergenceRef,
    framing:    framingRef,
    forecast:   forecastRef,
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id as SectionId);
          }
        });
      },
      { rootMargin: '-5% 0px -50% 0px', threshold: 0 }
    );
    [timelineRef, spreadRef, divergenceRef, framingRef, forecastRef].forEach((ref) => {
      if (ref.current) observer.observe(ref.current);
    });
    return () => observer.disconnect();
  }, []);

  const scrollToSection = (id: SectionId) => {
    sectionRefMap[id].current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleToggleModel = (modelName: string) => {
    setSelectedModels((prev) =>
      prev.includes(modelName)
        ? prev.filter((m) => m !== modelName)
        : [...prev, modelName]
    );
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refreshData();
      alert('Data refresh started in the background. Reload the page in a few minutes to see updated data.');
    } catch (err) {
      console.error('Refresh failed:', err);
      alert('Failed to start data refresh.');
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="flex h-screen bg-bg text-text-primary">
      <Sidebar />
      <main className="flex-1 min-h-0 overflow-y-auto transition-all duration-300">

        {/* ── Hero + KPI opening brief ─────────────────────────────────────── */}
        <div className="max-w-[1700px] mx-auto w-full p-6">
          <header className="hero-banner mb-8 px-6 py-10 sm:px-10 sm:py-14">
            <div className="relative z-10 flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-2xl">
                <h1 className="text-headline text-white mb-3">
                  Tariff Tensions, Narrative Divides
                </h1>
                <p className="text-[15px] text-white/80 leading-relaxed max-w-xl">
                  The 2025 US–China tariff escalation was both an economic and a media narrative
                  battle. Five sections trace when coverage surged, where it spread, how each side's
                  tone diverged, what language defined the framing, and whether that divergence was
                  foreseeable.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/20 bg-white/10 text-white hover:bg-white/20 hover:border-white/40 backdrop-blur-sm transition-all text-xs font-semibold uppercase tracking-wider cursor-pointer disabled:opacity-50"
                  title="Fetch latest GDELT data from BigQuery"
                >
                  {refreshing ? (
                    <>
                      <svg className="animate-spin h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      Refreshing...
                    </>
                  ) : (
                    <>
                      <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Refresh Data
                    </>
                  )}
                </button>

                <button
                  onClick={toggleTheme}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/20 bg-white/10 text-white hover:bg-white/20 hover:border-white/40 backdrop-blur-sm transition-all text-xs font-semibold uppercase tracking-wider cursor-pointer"
                  title="Toggle theme"
                >
                  {theme === 'dark' ? (
                    <>
                      <svg className="w-4 h-4 text-amber-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
                      </svg>
                      <span>Light Mode</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                      </svg>
                      <span>Dark Mode</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </header>

          <p className="text-overline text-text-muted mb-4">Situation Brief</p>
          <SummaryCards />
        </div>

        {/* ── Sticky section navigation ────────────────────────────────────── */}
        <nav className="sticky top-0 z-20 bg-surface border-b border-border shadow-sm">
          <div className="max-w-[1700px] mx-auto w-full px-6">
            <div className="flex items-stretch overflow-x-auto">
              {NAV_SECTIONS.map(({ id, label }, i) => (
                <button
                  key={id}
                  onClick={() => scrollToSection(id)}
                  className={`relative flex items-center gap-2 px-5 py-3 text-overline whitespace-nowrap transition-all duration-200 cursor-pointer border-b-2 -mb-px ${
                    activeSection === id
                      ? 'text-primary border-primary'
                      : 'text-text-muted border-transparent hover:text-text-secondary hover:border-border-elevated'
                  }`}
                >
                  <span className="font-mono text-[10px] opacity-35">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  {label}
                </button>
              ))}
            </div>
          </div>
        </nav>

        {/* ── Story sections ───────────────────────────────────────────────── */}
        <div className="max-w-[1700px] mx-auto w-full px-6 pb-6">

          {/* Section 1 — Conflict Timeline */}
          <section id="timeline" ref={timelineRef} className="mt-10 scroll-mt-14">
            <SectionHeader
              index={1}
              sectionId="timeline"
              question="When did the tariff conflict intensify?"
              description="Spikes in daily article volume mark when the tariff conflict drew global media attention."
            />
            <TimelineChart />
          </section>

          {/* Section 2 — Narrative Spread */}
          <section id="spread" ref={spreadRef} className="mt-14 scroll-mt-14">
            <SectionHeader
              index={2}
              sectionId="spread"
              question="Where did the narrative spread?"
              description="Switch between three views: event locations (Event Markers), coverage origin by country (Source Origin), and country-level aggregate tone (Country View)."
            />
            <MapSection />
          </section>

          {/* Section 3 — Emotional Divergence */}
          <section id="divergence" ref={divergenceRef} className="mt-14 scroll-mt-14">
            <SectionHeader
              index={3}
              sectionId="divergence"
              question="How did Western and Chinese media emotionally diverge?"
              description="Three charts compare Western and Chinese sentiment: tone gap over time, score distribution by group, and daily tone against coverage volume."
            />
            <div className="flex flex-col gap-6">
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <ToneGapChart />
                <DistributionChart />
              </div>
              <BubbleChart />
            </div>
          </section>

          {/* Section 4 — Keyword Framing */}
          <section id="framing" ref={framingRef} className="mt-14 scroll-mt-14">
            <SectionHeader
              index={4}
              sectionId="framing"
              question="Which words did each side use to frame the conflict?"
              description="TF-IDF terms that most distinguish Western from Chinese coverage, shown as a diverging bar chart and word clouds."
            />
            <div className="flex flex-col gap-6">
              <KeywordFramingChart />
              <WordCloudSection />
            </div>
          </section>

          {/* Section 5 — Narrative Gap Forecasting */}
          <section id="forecast" ref={forecastRef} className="mt-14 scroll-mt-14">
            <SectionHeader
              index={5}
              sectionId="forecast"
              question="Can short-term forecasting anticipate narrative divergence?"
              description="ARIMA, Holt-Winters, Prophet, and TimesFM trained on the full tone-gap series and evaluated on a 14-day holdout window."
            />
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              <div className="xl:col-span-1">
                <ForecastMetricsCard
                  selectedModels={selectedModels}
                  onToggleModel={handleToggleModel}
                />
              </div>
              <div className="xl:col-span-2">
                <ForecastChart selectedModels={selectedModels} />
              </div>
            </div>
          </section>

          <footer className="mt-14 pt-4 border-t border-border text-text-muted text-caption">
            Data: The GDELT Project · Built with FastAPI, React, MapLibre GL & Plotly for a university data-visualization project.
          </footer>
        </div>
      </main>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <FiltersProvider>
        <Dashboard />
      </FiltersProvider>
    </ThemeProvider>
  );
}

export default App;
