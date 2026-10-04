import { jwtVerify } from "jose";
import type { SessionUser } from "@/types";

export const AUTH_COOKIE = "access_token";
const JWT_ISSUER = "academic-affairs-system";

/** 各角色登入後的首頁 */
export const ROLE_HOME: Record<SessionUser["role"], string> = {
  Admin: "/admin",
  Teacher: "/teacher",
  Student: "/student",
};

/**
 * 驗證 JWT 並取出使用者資訊（伺服器端專用：proxy.ts 與 Server Component）。
 * 這裡的驗證只用於「頁面導向」；真正的資料存取權限由兩個後端各自再驗證一次。
 */
export async function verifySession(token: string | undefined): Promise<SessionUser | null> {
  const secret = process.env.JWT_SECRET;
  if (!token || !secret) return null;
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
