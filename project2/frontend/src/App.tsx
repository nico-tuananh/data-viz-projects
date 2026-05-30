import { useState } from 'react';
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

function Dashboard() {
  const { theme, toggleTheme } = useTheme();
  const [refreshing, setRefreshing] = useState(false);
  const [selectedModels, setSelectedModels] = useState<string[]>([
    'ARIMA',
    'HoltWinters',
    'Prophet',
    'TimesFM',
  ]);

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
    <div className="flex min-h-screen bg-bg text-text-primary">
      <Sidebar />
      <main className="flex-1 overflow-y-auto transition-all duration-300">
        <div className="max-w-[1700px] mx-auto w-full p-6">
        <header className="flex justify-between items-center mb-6 pb-4 border-b border-border">
          <div>
            <h1 className="text-headline text-text-primary mb-1">
              GDELT Tariff Narrative Dashboard
            </h1>
            <p className="text-text-muted text-body-small">
              Narrative Asymmetry in the 2025 US–China Tariff Conflict
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-elevated hover:shadow-glow-subtle hover:border-border-elevated transition-all text-xs font-semibold uppercase tracking-wider cursor-pointer disabled:opacity-50"
              title="Fetch latest GDELT data from BigQuery"
            >
              {refreshing ? (
                <>
                  <svg className="animate-spin h-3 w-3 text-primary" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Refreshing...
                </>
              ) : (
                <>
                  <svg className="w-3 h-3 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Refresh Data
                </>
              )}
            </button>

            <button
              onClick={toggleTheme}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-border bg-surface hover:bg-surface-elevated hover:shadow-glow-subtle hover:border-border-elevated transition-all text-xs font-semibold uppercase tracking-wider cursor-pointer"
              title="Toggle theme"
            >
            {theme === 'dark' ? (
              <>
                <svg className="w-4 h-4 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
                </svg>
                <span>Light Mode</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
                <span>Dark Mode</span>
              </>
            )}
          </button>
          </div>
        </header>

        <SummaryCards />
        <MapSection />

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <TimelineChart />
          <ToneGapChart />
          <DistributionChart />
          <BubbleChart />
        </div>

        {/* Tab 4: Keyword Framing — Which words did each side use to frame the conflict? */}
        <section className="mt-8">
          <div className="flex flex-wrap items-baseline gap-3 mb-5 pb-3 border-b border-border">
            <h2 className="font-mono text-subhead font-bold tracking-wide text-text-primary">
              Keyword Framing
            </h2>
            <p className="text-text-muted text-body-small">
              Which words did each side use to frame the conflict?
            </p>
          </div>
          <div className="flex flex-col gap-6">
            <KeywordFramingChart />
            <WordCloudSection />
          </div>
        </section>

        {/* Forecast Evaluation */}
        <section className="mt-8">
          <div className="flex flex-wrap items-baseline gap-3 mb-5 pb-3 border-b border-border">
            <h2 className="font-mono text-subhead font-bold tracking-wide text-text-primary">
              Forecast Evaluation
            </h2>
            <p className="text-text-muted text-body-small">
              Model predictions on 14-day holdout overlay on full Feb–Apr series
            </p>
          </div>
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

        <footer className="mt-8 pt-4 border-t border-border text-text-muted text-caption">
          Data sourced from GDELT Project. Dashboard styled with CoinPulse Design System. Built with FastAPI + React + Leaflet + Plotly.
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
