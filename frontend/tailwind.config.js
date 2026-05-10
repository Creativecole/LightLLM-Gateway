/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#101828',
        panel: '#ffffff',
        line: '#d6dee8',
      },
    },
  },
  plugins: [],
};
