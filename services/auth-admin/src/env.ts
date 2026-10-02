import "dotenv/config";
import { z } from "zod";

// 啟動時驗證環境變數；缺漏或格式錯誤直接中止，避免帶著錯誤設定上線
const EnvSchema = z.object({
  DATABASE_URL: z.string().startsWith("mysql://"),
  JWT_SECRET: z.string().min(32, "JWT_SECRET 至少需要 32 個字元"),
  JWT_EXPIRES_IN_HOURS: z.coerce.number().int().positive().default(8),
  PORT: z.coerce.number().int().default(4000),
  // 正式環境（HTTPS）需設為 true，Cookie 才會加上 Secure 屬性
  COOKIE_SECURE: z
    .enum(["true", "false"])
    .default("false")
    .transform((v) => v === "true"),
});

const parsed = EnvSchema.safeParse(process.env);
if (!parsed.success) {
  console.error("環境變數設定錯誤：", z.prettifyError(parsed.error));
  process.exit(1);
}

export const env = parsed.data;

/** 兩個後端共用的 JWT 設定，必須與 FastAPI 端一致 */
export const JWT_ISSUER = "academic-affairs-system";
export const AUTH_COOKIE = "access_token";
