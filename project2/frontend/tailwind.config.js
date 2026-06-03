/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // Enable class-based dark mode
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        'surface-elevated': 'var(--color-surface-elevated)',
        border: 'var(--color-border)',
        'border-elevated': 'var(--color-border-elevated)',
        // Muted tariff-tension palette — mirrors src/lib/colors.ts (canonical source)
        primary: '#2C5282', // Western slate navy (was #2563EB electric blue)
        'primary-hover': '#3D6494',
        secondary: '#C8893E', // tension ochre (was #84CC16 lime)
        tertiary: '#C8893E',
        success: '#3D8168', // muted teal-green (was #22C55E)
        warning: '#C8893E', // ochre (was #F59E0B amber)
        error: '#B23A48', // muted brick (was #EF4444)
        info: '#2C5282',
        neutral: '#8A8D91', // warm gray (was #71717A)
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
        
        // Shadcn / mapcn mappings
        background: 'var(--color-bg)',
        foreground: 'var(--color-text-primary)',
        popover: 'var(--color-surface)',
        'popover-foreground': 'var(--color-text-primary)',
        muted: 'var(--color-surface-elevated)',
        'muted-foreground': 'var(--color-text-muted)',
        accent: 'var(--color-surface-elevated)',
        'accent-foreground': 'var(--color-text-primary)',
      },
      fontFamily: {
        // Three-role system: serif headlines, sans body/UI, mono numbers/data
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
        // Premium upgrade: section/chart titles and KPI data values
        display: ['"Plus Jakarta Sans"', '"DM Sans"', 'sans-serif'],
        data: ['"Space Grotesk"', '"IBM Plex Mono"', 'monospace'],
      },
      boxShadow: {
        'glow-subtle': 'var(--shadow-glow-subtle)',
        'glow-medium': 'var(--shadow-glow-medium)',
        'glow-large': 'var(--shadow-glow-large)',
        'glow-profit': 'var(--shadow-glow-profit)',
        'glow-loss': 'var(--shadow-glow-loss)',
      },
    },
  },
  plugins: [],
}
