/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],
  darkMode: 'media',
  theme: {
    extend: {
      backgroundImage: {
        app: "url('/bg-stadium.webp')",
      },
    },
  },
  plugins: [],
}
