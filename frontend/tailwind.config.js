/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#1E3A5F", dark: "#142a46", light: "#2f5583", pale: "#e3eaf3" },
        ochre: { DEFAULT: "#B7791F", dark: "#935f14", light: "#e0a94f" },
        sand: { DEFAULT: "#F7F3EA", dark: "#ece5d3", line: "#ddd3bc" },
        ink: "#1f2933",
      },
      fontFamily: {
        sans: ["Segoe UI", "system-ui", "-apple-system", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
