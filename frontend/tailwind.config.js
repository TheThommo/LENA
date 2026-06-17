/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        lena: {
          50: '#E8F4F6',
          100: '#D1E9EE',
          200: '#A3D3DD',
          300: '#6FB8C8',
          400: '#3D9AAE',
          500: '#136B7A',
          600: '#105A67',
          700: '#0D4854',
          800: '#093640',
          900: '#06242B',
          950: '#031216',
        },
        brand: {
          DEFAULT: 'rgb(var(--brand-primary) / <alpha-value>)',
          light: 'rgb(var(--brand-primary-light) / <alpha-value>)',
          dark: 'rgb(var(--brand-primary-dark) / <alpha-value>)',
          accent: 'rgb(var(--brand-accent) / <alpha-value>)',
          surface: 'rgb(var(--brand-surface) / <alpha-value>)',
        },
        warm: {
          50: '#FAFAF8',
          100: '#F5F5F2',
          200: '#EBEBE6',
        },
        canvas: {
          50: '#F7F8FA',
          100: '#EEF1F5',
          200: '#E2E8F0',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', '-apple-system', 'BlinkMacSystemFont', "'Segoe UI'", 'sans-serif'],
      },
      boxShadow: {
        soft: '0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px rgba(15, 23, 42, 0.06)',
        card: '0 1px 3px rgba(15, 23, 42, 0.05), 0 12px 32px rgba(15, 23, 42, 0.08)',
      },
    },
  },
  plugins: [],
};
