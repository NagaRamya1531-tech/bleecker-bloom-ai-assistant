/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        app_orange_color: '#C9644B',
        app_ink: '#203B32',
        app_cream: '#F5F3E9',
        app_leaf: '#A9B98B',
        app_line: '#DEDCCF',
      },
    },
  },
  plugins: [],
}

