/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0f1117',
        surface: '#1a1d27',
        card: '#212435',
        primary: '#4f8ef7',
        accent: '#a855f7',
      },
      keyframes: {
        wiggle: {
          '0%, 100%': { transform: 'rotate(0deg)' },
          '15%':      { transform: 'rotate(12deg)' },
          '45%':      { transform: 'rotate(-10deg)' },
          '65%':      { transform: 'rotate(8deg)' },
          '80%':      { transform: 'rotate(-5deg)' },
        },
      },
      animation: {
        wiggle: 'wiggle 0.6s ease-in-out',
      },
    },
  },
  plugins: [],
}
