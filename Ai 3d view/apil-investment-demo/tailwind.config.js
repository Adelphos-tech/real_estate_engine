/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        apil: {
          blue: '#0A47B7',
          'blue-dark': '#1B4E83',
          gold: '#C2A349',
          'gold-light': '#D8B45A',
          'gold-pale': '#F2E2AF',
          dark: '#0a0a0f',
          'gray-50': '#f8f9fa',
          'gray-100': '#f1f3f5',
          'gray-200': '#e9ecef',
          'gray-300': '#dee2e6',
          'gray-400': '#adb5bd',
          'gray-500': '#868e96',
          'gray-600': '#495057',
          'gray-700': '#343a40',
          'gray-800': '#212529',
          'gray-900': '#16191d',
        },
        score: {
          excellent: '#16a34a',
          strong: '#22c55e',
          fair: '#f59e0b',
          caution: '#f97316',
          risk: '#ef4444',
        },
      },
    },
  },
  plugins: [],
}
