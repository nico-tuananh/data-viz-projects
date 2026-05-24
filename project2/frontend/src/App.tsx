import { FiltersProvider } from './hooks/useFilters';
import { ThemeProvider, useTheme } from './hooks/useTheme';
import Sidebar from './components/Sidebar';
import SummaryCards from './components/SummaryCards';
import MapSection from './components/MapSection';
import TimelineChart from './components/TimelineChart';
import ToneGapChart from './components/ToneGapChart';
import DistributionChart from './components/DistributionChart';
import BubbleChart from './components/BubbleChart';

function Dashboard() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen bg-bg text-text-primary">
      <Sidebar />
      <main className="flex-1 p-6 overflow-y-auto transition-all duration-300">
        <header className="flex justify-between items-center mb-6 pb-4 border-b border-border">
          <div>
            <h1 className="text-headline text-text-primary mb-1">
              GDELT Tariff Narrative Dashboard
            </h1>
            <p className="text-text-muted text-body-small">
              Narrative Asymmetry in the 2025 US–China Tariff Conflict
            </p>
          </div>
          
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
        </header>

        <SummaryCards />
        <MapSection />

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <TimelineChart />
          <ToneGapChart />
          <DistributionChart />
          <BubbleChart />
        </div>

        <footer className="mt-8 pt-4 border-t border-border text-text-muted text-caption">
          Data sourced from GDELT Project. Dashboard styled with CoinPulse Design System. Built with FastAPI + React + Leaflet + Plotly.
        </footer>
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
