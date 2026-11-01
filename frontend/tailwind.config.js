/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        soc: {
          bg: '#070A12',
          surface: '#0D1424',
          elevated: '#131C31',
          border: 'rgba(255, 255, 255, 0.08)',
          hover: '#192542',
          indigo: '#6366F1',
          cyan: '#06B6D4',
          emerald: '#10B981',
          amber: '#F59E0B',
          crimson: '#EF4444',
          violet: '#8B5CF6'
        }
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      }
    },
  },
  plugins: [],
}

