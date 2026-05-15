/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],

  // 'class' strategy: dark mode is driven by the `dark` class on <html>,
  // applied and persisted by ThemeToggle.tsx.
  darkMode: 'class',

  theme: {
    extend: {
      colors: {
        primary: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
      // Smooth background/color transitions when theme switches
      transitionProperty: {
        theme: 'background-color, border-color, color, fill, stroke',
      },
      transitionDuration: {
        theme: '200ms',
      },
    },
  },
  plugins: [],
}