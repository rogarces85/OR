/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        club: {
          red: '#C1121F',
          dark: '#111827',
        },
      },
    },
  },
  plugins: [],
}
