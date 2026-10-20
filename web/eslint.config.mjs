// ESLint 設定（flat config）：`npm run lint` 使用
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  // Next.js 官方規則：React、React Hooks（含 react-hooks/set-state-in-effect）與 Core Web Vitals 相關檢查
  ...nextVitals,
  // TypeScript 規則（typescript-eslint）
  ...nextTs,
  // 明確列出不檢查的路徑，取代 eslint-config-next 的預設值（建置輸出與自動產生的型別檔）
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
