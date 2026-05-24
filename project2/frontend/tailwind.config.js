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
        primary: '#2563EB', // Electric Blue
        'primary-hover': '#3B82F6',
        secondary: '#84CC16', // Lime
        tertiary: '#F59E0B',
        success: '#22C55E',
        warning: '#F59E0B',
        error: '#EF4444',
        info: '#2563EB',
        neutral: '#71717A',
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
      },
      fontFamily: {
        mono: ['"Space Mono"', 'monospace'],
        sans: ['"DM Sans"', 'sans-serif'],
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
