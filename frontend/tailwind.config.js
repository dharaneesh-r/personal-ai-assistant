/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        gray: {
          950: '#0d0d0d',
          925: '#111111',
          900: '#171717',
          850: '#1c1c1c',
          800: '#212121',
          750: '#2a2a2a',
          700: '#2f2f2f',
          600: '#3f3f3f',
          500: '#4f4f4f',
          400: '#8e8ea0',
          300: '#acacbe',
          200: '#c5c5d2',
          100: '#ececec',
        },
      },
    },
  },
  plugins: [],
}
