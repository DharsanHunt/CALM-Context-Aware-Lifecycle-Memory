/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#f8f9fb',
        surface: '#ffffff',
        'surface-dim': '#edeef0',
        'surface-low': '#f2f4f6',
        'surface-high': '#e7e8ea',
        primary: '#004ac6',
        'primary-container': '#2563eb',
        'on-primary': '#ffffff',
        secondary: '#505f76',
        'outline-variant': '#e2e8f0',
        'state-active': '#16a34a',
        'state-cached': '#2563eb',
        'state-compressed': '#d97706',
        'state-archived': '#dc2626',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
        serif: ['Newsreader', 'Playfair Display', 'Georgia', 'serif'],
        display: ['Newsreader', 'Playfair Display', 'serif'],
      },
    },
  },
  plugins: [],
}
