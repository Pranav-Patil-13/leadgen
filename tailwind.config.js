/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./backend/templates/**/*.html",
    "./backend/**/*.py",
    "./backend/static/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'brand-bg': '#F2E9E4',
        'brand-primary': '#4A4E69',
        'brand-secondary': '#9A8C98',
        'brand-card': '#FFFFFF',
        'brand-text': '#22223B',
        'brand-border': '#C9ADA7',
        'brand-hover': '#E5DED3',
      }
    },
  },
  plugins: [],
}
