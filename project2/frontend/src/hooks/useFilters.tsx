import { createContext, useContext, useState, type ReactNode } from 'react';

export interface Filters {
  start: string;
  end: string;
  mediaGroups: string[];
  direction: string;
}

const defaultFilters: Filters = {
  start: '2025-02-01',
  end: '2025-04-30',
  mediaGroups: ['Western', 'Chinese', 'Global/Other'],
  direction: 'All',
};

interface FiltersContextValue {
  filters: Filters;
  setFilters: (f: Filters) => void;
  mediaParam: string;
  isSidebarCollapsed: boolean;
  setIsSidebarCollapsed: (c: boolean) => void;
}

const FiltersContext = createContext<FiltersContextValue | null>(null);

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const mediaParam = filters.mediaGroups.join(',');

  return (
    <FiltersContext.Provider
      value={{
        filters,
        setFilters,
        mediaParam,
        isSidebarCollapsed,
        setIsSidebarCollapsed,
      }}
    >
      {children}
    </FiltersContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useFilters() {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error('useFilters must be used inside FiltersProvider');
  return ctx;
}
