/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Manrope",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Consolas",
          "monospace",
        ],
      },
      colors: {
        // Paper-studio base surfaces (light)
        ink: {
          DEFAULT: "#f6f6f4",
          900: "#ffffff",
          800: "#efefec",
          700: "#e7e7e2",
          600: "#dbdbd5",
        },
        hairline: "rgba(0,0,0,0.09)",
      },
    },
  },
  plugins: [],
};
