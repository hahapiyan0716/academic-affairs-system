import bcrypt from "bcryptjs";
import { Router } from "express";
import rateLimit from "express-rate-limit";
import { z } from "zod";
import { signToken, type TokenPayload } from "../auth/jwt";
import { prisma } from "../db";
import { AUTH_COOKIE, env } from "../env";
import { HttpError } from "../errors";
import { currentUser, requireAuth } from "../middleware/auth";

export const authRouter = Router();

// 登入限流：同一 IP 每 15 分鐘最多 20 次，降低暴力破解風險
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 20,
  standardHeaders: "draft-8",
  legacyHeaders: false,
  message: { detail: "登入嘗試次數過多，請稍後再試" },
});

const LoginBody = z.object({
  username: z.string().trim().min(1).max(30),
  password: z.string().min(1).max(100),
});

// 帳號不存在時仍執行一次 bcrypt 比對，避免以回應時間差推測帳號是否存在
const DUMMY_HASH = bcrypt.hashSync("dummy-password-for-timing", 10);

authRouter.post("/login", loginLimiter, async (req, res) => {
  const { username, password } = LoginBody.parse(req.body);

  const user = await prisma.userAccount.findUnique({
    where: { username },
    include: { teacher: true, student: true },
  });

  const ok = await bcrypt.compare(password, user?.password_hash ?? DUMMY_HASH);
  if (!user || !ok) throw new HttpError(401, "帳號或密碼錯誤");
  if (!user.is_active) throw new HttpError(403, "帳號已停用，請洽管理員");

  await prisma.userAccount.update({
    where: { user_id: user.user_id },
    data: { last_login_at: new Date() },
  });

  const payload: TokenPayload = {
    sub: String(user.user_id),
    username: user.username,
    role: user.role,
    teacher_id: user.teacher?.teacher_id ?? null,
    student_id: user.student?.student_id ?? null,
    name: user.teacher?.teacher_name ?? user.student?.student_name ?? "系統管理員",
  };

  res.cookie(AUTH_COOKIE, signToken(payload), {
    httpOnly: true, // JavaScript 讀不到，防止 XSS 竊取 token
    sameSite: "lax", // 跨站 POST 不會帶上 cookie，降低 CSRF 風險
    secure: env.COOKIE_SECURE,
    maxAge: env.JWT_EXPIRES_IN_HOURS * 60 * 60 * 1000,
    path: "/",
  });

  res.json({ user: payload });
});

authRouter.post("/logout", (_req, res) => {
  res.clearCookie(AUTH_COOKIE, { path: "/" });
  res.status(204).end();
});

authRouter.get("/me", requireAuth, (req, res) => {
  res.json({ user: currentUser(req) });
});
