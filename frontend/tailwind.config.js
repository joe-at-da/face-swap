/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0076C0", // Parliament blue
          dark: "#005A8E",
          light: "#3D9AD1",
        },
        secondary: {
          DEFAULT: "#6C0D10", // Parliament red
          dark: "#4E090C",
          light: "#8A3538",
        },
        neutral: {
          DEFAULT: "#333333",
          dark: "#1A1A1A",
          light: "#666666",
        },
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        serif: ["Georgia", "serif"],
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        parliament: {
          primary: "#0076C0",
          secondary: "#6C0D10",
          accent: "#37CDBE",
          neutral: "#333333",
          "base-100": "#FFFFFF",
          info: "#3ABFF8",
          success: "#36D399",
          warning: "#FBBD23",
          error: "#F87272",
        },
        parliamentDark: {
          primary: "#0076C0",
          secondary: "#6C0D10",
          accent: "#37CDBE",
          neutral: "#e0e0e0",
          "base-100": "#1f2937",
          "base-200": "#111827",
          "base-300": "#0f172a",
          info: "#3ABFF8",
          success: "#36D399",
          warning: "#FBBD23",
          error: "#F87272",
        },
      },
    ],
    darkTheme: "parliamentDark",
  },
}
