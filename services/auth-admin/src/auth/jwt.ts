import jwt from "jsonwebtoken";
import { env, JWT_ISSUER } from "../env";

export type Role = "Admin" | "Teacher" | "Student";

/**
 * JWT 內容。FastAPI 端以相同欄位解析（見 services/academic/app/security.py）。
 * 刻意不放 can_open_section：權限可能隨時被管理員收回，必須每次查資料庫確認。
 */
export interface TokenPayload {
  sub: string; // user_id
  username: string;
  role: Role;
  teacher_id: string | null;
  student_id: string | null;
  name: string;
}

export function signToken(payload: TokenPayload): string {
  return jwt.sign(payload, env.JWT_SECRET, {
    algorithm: "HS256",
    issuer: JWT_ISSUER,
    expiresIn: `${env.JWT_EXPIRES_IN_HOURS}h`,
  });
}

export function verifyToken(token: string): TokenPayload {
  // 明確限定演算法，防止 alg=none 或演算法替換攻擊
  return jwt.verify(token, env.JWT_SECRET, {
    algorithms: ["HS256"],
    issuer: JWT_ISSUER,
  }) as TokenPayload;
}
