// PostCSS 設定：Next.js 處理 CSS 時套用；Tailwind CSS v4 以 PostCSS 外掛的形式編譯 globals.css 的 @import "tailwindcss"、@theme 等語法
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
