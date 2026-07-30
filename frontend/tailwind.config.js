/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: { extend: {
    colors: {
      brand: '#15803d', bg: '#f4f6fa', card: '#ffffff', line: '#e3e8f0',
      txt: '#1a2433', sub: '#6b7a90', up: '#16a34a', down: '#ca8a04',
    },
  }},
  plugins: [],
};
