import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0B0B0B",
          900: "#151515",
          800: "#1D1D1D",
          700: "#262626",
          500: "#737373",
          400: "#A3A3A3",
          100: "#F5F5F5",
        },
        signal: {
          success: "#22C55E",
          warning: "#F59E0B",
          danger: "#EF4444",
        },
      },
      boxShadow: {
        panel: "0 20px 70px rgba(0,0,0,0.45)",
        soft: "0 12px 40px rgba(0,0,0,0.28)",
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "SF Pro Display",
          "SF Pro Text",
          "Segoe UI",
          "system-ui",
          "sans-serif",
        ],
        mono: ["SFMono-Regular", "Cascadia Code", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
