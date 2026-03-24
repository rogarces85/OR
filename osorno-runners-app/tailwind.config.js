/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#060e20',
        surface: {
          dim: '#060e20',
          DEFAULT: '#060e20',
          bright: '#1f2b49',
          'container-lowest': '#000000',
          'container-low': '#091328',
          container: '#0f1930',
          'container-high': '#141f38',
          'container-highest': '#192540',
        },
        primary: {
          DEFAULT: '#ff9157',
          container: '#ff7a2c',
          dim: '#ff7520',
        },
        tertiary: {
          DEFAULT: '#47c4ff',
          container: '#2db7f2',
        },
        outline: {
          DEFAULT: '#6d758c',
          variant: '#40485d',
        },
        on: {
          surface: '#dee5ff',
          'surface-variant': '#a3aac4',
        }
      },
      fontFamily: {
        display: ['Manrope', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
