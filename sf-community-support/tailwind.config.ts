import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: {
          cream: "#FDFDF9", // Very light, clean cream
          white: "#FFFFFF",
          grid: "#E2E0D4",  // Sharper contrast for grid lines
        },
        tape: {
          base: "#EBE6D8",  // Lighter tape from image
          light: "#F5F2EA",
        },
        ink: {
          dark: "#2D3748",
          medium: "#4A5568",
          light: "#718096",
        },
        accent: {
          dark: "#1A202C", // Off-black
          "dark-hover": "#000000",
        },
        risk: {
          low: "#6B8E6B",
          medium: "#D4A03C",
          high: "#C53030",
          critical: "#7f1d1d",
        },
        kraft: "#C4A77D",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "var(--font-work-sans)", "sans-serif"],
        display: ["var(--font-work-sans)", "sans-serif"],
        script: ["var(--font-caveat)", "cursive"],
      },
      backgroundImage: {
        "paper-pattern": "url('/textures/paper-noise.svg')",
        "grid-pattern": "url('/textures/paper-grid.svg')",
        "tape-gradient": "linear-gradient(135deg, #EBE6D8 0%, #F5F2EA 25%, #E6E1D1 50%, #F7F5EF 75%, #EBE6D8 100%)",
      },
      boxShadow: {
        "paper": "0 2px 8px rgba(0,0,0,0.06)",
        "tape": "0 1px 2px rgba(0,0,0,0.1)",
        "polaroid": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
      }
    },
  },
  plugins: [],
};
export default config;
