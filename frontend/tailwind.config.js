/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        lena: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc8fb',
          400: '#36adf6',
          500: '#0c93e7',
          600: '#0074c5',
          700: '#015da0',
          800: '#064f84',
          900: '#0b426e',
          950: '#072a49',
        },
        brand: {
          DEFAULT: 'rgb(var(--brand-primary) / <alpha-value>)',
          light: 'rgb(var(--brand-primary-light) / <alpha-value>)',
          dark: 'rgb(var(--brand-primary-dark) / <alpha-value>)',
          accent: 'rgb(var(--brand-accent) / <alpha-value>)',
          surface: 'rgb(var(--brand-surface) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
