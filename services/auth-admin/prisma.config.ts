// Prisma 7 設定檔：連線字串、migration 路徑與 seed 指令都集中於此
// Prisma 7 起不會自動讀 .env，因此手動載入 dotenv
import "dotenv/config";
import { defineConfig } from "prisma/config";

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
    seed: "tsx prisma/seed.ts",
  },
  datasource: {
    url: process.env["DATABASE_URL"],
    // 開發專用帳號沒有 CREATE DATABASE 權限，因此預先建立固定的 shadow DB
    shadowDatabaseUrl: process.env["SHADOW_DATABASE_URL"],
  },
});
