/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      colors: {
        oma: {
          bg: "var(--oma-bg)",
          surface: "var(--oma-surface)",
          "surface-elevated": "var(--oma-surface-elevated)",
          border: "var(--oma-border)",
          text: "var(--oma-text)",
          muted: "var(--oma-muted)",
          primary: "var(--oma-primary)",
          "primary-hover": "var(--oma-primary-hover)",
        },
      },
    },
  },
  plugins: [],
};
