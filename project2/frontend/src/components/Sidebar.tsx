import { useFilters } from '../hooks/useFilters';

const DIRECTIONS = ['All', 'CHN→USA', 'USA→CHN', 'Neutral'];

const GROUP_COLORS: Record<string, { bgChecked: string; borderHover: string; textChecked: string; textHover: string; glow: string }> = {
  Western: {
    bgChecked: 'bg-primary border-primary',
    textChecked: 'text-primary',
    textHover: 'group-hover:text-primary',
    borderHover: 'group-hover:border-primary',
    glow: 'shadow-[0_0_8px_rgba(37,99,235,0.25)]',
  },
  Chinese: {
    bgChecked: 'bg-error border-error',
    textChecked: 'text-error',
    textHover: 'group-hover:text-error',
    borderHover: 'group-hover:border-error',
    glow: 'shadow-[0_0_8px_rgba(239,68,68,0.25)]',
  },
  'Global/Other': {
    bgChecked: 'bg-neutral border-neutral',
    textChecked: 'text-neutral',
    textHover: 'group-hover:text-neutral',
    borderHover: 'group-hover:border-neutral',
    glow: 'shadow-[0_0_8px_rgba(113,113,122,0.25)]',
  },
};

export default function Sidebar() {
  const { filters, setFilters, isSidebarCollapsed, setIsSidebarCollapsed } = useFilters();

  const toggleMedia = (group: string) => {
    const next = filters.mediaGroups.includes(group)
      ? filters.mediaGroups.filter((g) => g !== group)
      : [...filters.mediaGroups, group];
    setFilters({ ...filters, mediaGroups: next });
  };

  const toggleCollapse = () => {
    const next = !isSidebarCollapsed;
    setIsSidebarCollapsed(next);
    
    // Animate and resize Plotly charts smoothly during the 300ms CSS width transition
    const interval = setInterval(() => {
      window.dispatchEvent(new Event('resize'));
    }, 20);
    
    setTimeout(() => {
      clearInterval(interval);
      window.dispatchEvent(new Event('resize'));
    }, 350);
  };

  return (
    <aside
      className={`flex-shrink-0 bg-surface border-r border-border h-screen sticky top-0 overflow-y-auto overflow-x-hidden transition-all duration-300 ease-in-out flex flex-col ${
        isSidebarCollapsed ? 'w-12 p-3' : 'w-72 p-6'
      }`}
    >
      {/* Sidebar Header */}
      <div className={`flex items-center justify-between mb-6 ${isSidebarCollapsed ? 'flex-col gap-4' : ''}`}>
        {!isSidebarCollapsed && (
          <h2 className="font-mono text-subhead font-bold tracking-wide text-text-primary">
            Filters
          </h2>
        )}
        <button
          onClick={toggleCollapse}
          className="p-1.5 rounded-lg border border-border bg-surface hover:bg-surface-elevated text-text-secondary hover:text-text-primary hover:shadow-glow-subtle hover:border-border-elevated transition-all cursor-pointer"
          title={isSidebarCollapsed ? 'Expand Filters' : 'Collapse Filters'}
        >
          {isSidebarCollapsed ? (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          )}
        </button>
      </div>

      {isSidebarCollapsed ? (
        <div className="flex-1 flex items-center justify-center select-none">
          <span
            className="font-mono text-overline text-text-muted font-bold tracking-[0.15em] whitespace-nowrap"
            style={{ writingMode: 'vertical-lr', transform: 'rotate(180deg)' }}
          >
            Filter Controls
          </span>
        </div>
      ) : (
        <div className="flex-1 flex flex-col justify-between transition-opacity duration-300 opacity-100">
          <div>
            {/* Date Range Filter */}
            <div className="mb-6">
              <label className="block text-text-secondary text-overline tracking-wider mb-2">
                Date Range
              </label>
              <div className="flex flex-col gap-2">
                <input
                  type="date"
                  className="h-9 bg-bg border border-border-elevated hover:border-[#52525B] focus:border-primary focus:shadow-glow-subtle focus:outline-none rounded-lg px-3 py-1.5 text-body-small text-text-primary w-full transition-all"
                  value={filters.start}
                  onChange={(e) => setFilters({ ...filters, start: e.target.value })}
                />
                <span className="text-text-muted text-caption self-center">to</span>
                <input
                  type="date"
                  className="h-9 bg-bg border border-border-elevated hover:border-[#52525B] focus:border-primary focus:shadow-glow-subtle focus:outline-none rounded-lg px-3 py-1.5 text-body-small text-text-primary w-full transition-all"
                  value={filters.end}
                  onChange={(e) => setFilters({ ...filters, end: e.target.value })}
                />
              </div>
            </div>

            {/* Media Groups Filter */}
            <div className="mb-6">
              <label className="block text-text-secondary text-overline tracking-wider mb-2">
                Media Groups
              </label>
              <div className="flex flex-col gap-1">
                {['Western', 'Chinese', 'Global/Other'].map((group) => {
                  const isChecked = filters.mediaGroups.includes(group);
                  const colors = GROUP_COLORS[group] || GROUP_COLORS['Global/Other'];
                  return (
                    <div
                      key={group}
                      className="flex items-center gap-3 py-1.5 cursor-pointer group select-none"
                      onClick={() => toggleMedia(group)}
                    >
                      <div
                        className={`w-4 h-4 rounded-[4px] border-[1.5px] flex items-center justify-center transition-all ${
                          isChecked
                            ? `${colors.bgChecked} ${colors.glow}`
                            : `border-border-elevated bg-bg ${colors.borderHover}`
                        }`}
                      >
                        {isChecked && (
                          <svg className="w-3 h-3 text-white" viewBox="0 0 20 20" fill="currentColor">
                            <path
                              fillRule="evenodd"
                              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                              clipRule="evenodd"
                            />
                          </svg>
                        )}
                      </div>
                      <span className={`text-body-medium ${isChecked ? colors.textChecked : 'text-text-primary'} ${colors.textHover} transition-colors`}>
                        {group}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Event Direction Filter */}
            <div className="mb-6">
              <label className="block text-text-secondary text-overline tracking-wider mb-2">
                Event Direction
              </label>
              <select
                className="h-9 w-full bg-bg border border-border-elevated hover:border-[#52525B] focus:border-primary focus:shadow-glow-subtle focus:outline-none rounded-lg px-3 py-1.5 text-body-small text-text-primary transition-all cursor-pointer"
                value={filters.direction}
                onChange={(e) => setFilters({ ...filters, direction: e.target.value })}
              >
                {DIRECTIONS.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <p className="text-text-muted text-caption leading-relaxed border-t border-border pt-4 mt-4">
            Use these controls to filter data across all interactive charts and the map view.
          </p>
        </div>
      )}
    </aside>
  );
}
