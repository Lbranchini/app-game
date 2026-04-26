import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        vigor: "#dc2626",
        spirit: "#2563eb",
        mind: "#f3f4f6",
        blood: "#16a34a",
      },
    },
  },
  plugins: [],
} satisfies Config;
