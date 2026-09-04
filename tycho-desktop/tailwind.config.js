/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // A escala institucional do portal Tycho Brahe: azul luminoso sobre
        // superfícies brancas e azul-claras. Mantemos as classes `indigo-*`
        // existentes para que a interface inteira herde a identidade sem
        // alterar as cores semânticas dos dados linguísticos.
        indigo: {
          50: "#eff7ff",
          100: "#d9edff",
          200: "#b8ddfb",
          300: "#85c3f3",
          400: "#4f9cde",
          500: "#2e7fca",
          600: "#2567b5",
          700: "#1e528f",
          800: "#1a4272",
          900: "#14355f",
          950: "#0d233f",
        },
      },
      fontFamily: {
        sans: ["Inter", "Segoe UI", "Arial", "sans-serif"],
        display: ["Georgia", "Times New Roman", "serif"],
      },
    },
  },
  plugins: [],
}
