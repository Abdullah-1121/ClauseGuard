/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
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
        // Audit-studio base surfaces
        ink: {
          DEFAULT: "#0a0a0b",
          900: "#0d0d0f",
          800: "#131316",
          700: "#1a1a1e",
          600: "#232329",
        },
        hairline: "rgba(255,255,255,0.08)",
      },
      // Risk levels — desaturated, readable on dark
      // (kept in JS for badge composition; these are helper tokens)
    },
  },
  plugins: [],
};
