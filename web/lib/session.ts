/**
 * 登入狀態（伺服器端專用）：驗證瀏覽器 cookie 中由 FastAPI 簽發的 JWT。
 * 這裡的 session 指 HTTP 層的「登入狀態」，與後端 api/app/db.py 的 SQLAlchemy Session（資料庫連線與交易）無關。
 * JWT 的簽發與 cookie 寫入在 api/app/session.py；這裡只驗證 JWT 以決定頁面導向，不連資料庫。
 */
import { jwtVerify } from "jose";
import type { SessionUser } from "@/types";

// cookie 名稱與 issuer 必須與後端 api/app/config.py 一致；JWT_SECRET 取自 .env.local
export const AUTH_COOKIE = "access_token";        // cookie 名稱（JWT 存放在瀏覽器的 cookie 中，名稱必須與後端 api/app/config.py 一致）
const JWT_ISSUER = "academic-affairs-system";     // JWT 的 issuer（簽發者）必須與後端 api/app/config.py 一致

/** 各角色登入後的首頁 */
export const ROLE_HOME: Record<SessionUser["role"], string> = {
  Admin: "/admin",
  Teacher: "/teacher",
  Student: "/student",
};

/**
 * 驗證 JWT 並取出使用者資訊（伺服器端專用：proxy.ts 與 Server Component）。
 * 這裡的驗證只用於「頁面導向」；真正的資料存取權限由後端（FastAPI）再驗證一次。
 * 驗證失敗（過期、簽章不符、未設定 JWT_SECRET）一律回傳 null，視為未登入。
 */
export async function verifySession(token: string | undefined): Promise<SessionUser | null> {
  const secret = process.env.JWT_SECRET;    // 會拿這個 secret 去驗證
  if (!token || !secret)
    return null;
  try {
    const { payload } = await jwtVerify(token, new TextEncoder().encode(secret), {
      algorithms: ["HS256"],
      issuer: JWT_ISSUER,
    });
    return payload as unknown as SessionUser;
  } catch {
    return null;
  }
}
