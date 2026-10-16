/** @type {import('tailwindcss').Config} */
// Paleta oficial del club (Q-1): se usan los valores por defecto de Tailwind.
//   Institucional: Rojo = red-600 (#DC2626) · Negro = black (#000000) · Blanco = white (#FFFFFF)
//   Morosidad:     verde = green-600 (#16A34A) · naranjo = amber-500 (#F59E0B) · rojo = red-500 (#EF4444)
const colors = require("tailwindcss/colors");

module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        marca: {
          rojo: colors.red[600],
          negro: colors.black,
          blanco: colors.white,
        },
        morosidad: {
          verde: colors.green[600],
          naranjo: colors.amber[500],
          rojo: colors.red[500],
        },
      },
    },
  },
  plugins: [],
};
