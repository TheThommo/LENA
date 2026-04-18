/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        lena: {
          50: '#E8F4F8',
          100: '#D1E9F1',
          200: '#A3D3E3',
          300: '#75BDD5',
          400: '#47A7C7',
          500: '#1B6B93',
          600: '#1B6B93',
          700: '#145372',
          800: '#0E3C52',
          900: '#072631',
          950: '#031319',
        },
        brand: {
          DEFAULT: 'rgb(var(--brand-primary) / <alpha-value>)',
          light: 'rgb(var(--brand-primary-light) / <alpha-value>)',
          dark: 'rgb(var(--brand-primary-dark) / <alpha-value>)',
          accent: 'rgb(var(--brand-accent) / <alpha-value>)',
          surface: 'rgb(var(--brand-surface) / <alpha-value>)',
        },
        warm: {
          50: '#FFFBF0',
          100: '#FFF7E0',
          200: '#FFEFC2',
        },
        canvas: {
          50: '#ECF4F1',
          100: '#DDEBE6',
          200: '#C3DCD4',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', "'Segoe UI'", 'sans-serif'],
      },
    },
  },
  plugins: [],
};
