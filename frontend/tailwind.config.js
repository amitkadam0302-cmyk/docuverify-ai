/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        apple: {
          bg: "#F5F5F7",
          surface: "#FFFFFF",
          text: "#1D1D1F",
          muted: "#6E6E73",
          blue: "#007AFF",
          green: "#34C759",
          orange: "#FF9500",
          red: "#FF3B30",
          purple: "#AF52DE",
          dark: {
            bg: "#000000",
            surface: "#1C1C1E",
            text: "#F5F5F7",
            muted: "#A1A1A6",
            blue: "#0A84FF",
            green: "#30D158",
            orange: "#FF9F0A",
            red: "#FF453A",
            purple: "#BF5AF2"
          }
        }
      },
      borderRadius: {
        apple: "24px",
        "apple-lg": "32px"
      },
      boxShadow: {
        apple: "0 18px 55px rgb(0 0 0 / 0.07)",
        "apple-sm": "0 8px 26px rgb(0 0 0 / 0.06)"
      }
    }
  },
  plugins: [],
};
