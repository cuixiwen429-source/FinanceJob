import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        finance: {
          50: "#f0f5ff",
          100: "#e0ebff",
          200: "#b8d4fe",
          300: "#85b8fd",
          400: "#4a93fa",
          500: "#1a6df5",
          600: "#0a52d1",
          700: "#0d3fa6",
          800: "#103689",
          900: "#132f70",
          950: "#0d1e45",
        },
      },
    },
  },
  plugins: [],
};

export default config;
