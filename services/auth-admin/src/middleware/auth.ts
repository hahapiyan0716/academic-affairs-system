import type { NextFunction, Request, Response } from "express";
import { AUTH_COOKIE } from "../env";
import { verifyToken, type Role, type TokenPayload } from "../auth/jwt";
import { HttpError } from "../errors";

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      user?: TokenPayload;
    }
  }
}

export function requireAuth(req: Request, _res: Response, next: NextFunction) {
  const token: string | undefined = req.cookies?.[AUTH_COOKIE];
  if (!token) throw new HttpError(401, "尚未登入");
  try {
    req.user = verifyToken(token);
  } catch {
    throw new HttpError(401, "登入已失效，請重新登入");
  }
  next();
}

export function requireRole(...roles: Role[]) {
  return (req: Request, _res: Response, next: NextFunction) => {
    if (!req.user || !roles.includes(req.user.role)) {
      throw new HttpError(403, "權限不足");
    }
    next();
  };
}

/** 取得目前登入者（只能在 requireAuth 之後呼叫） */
export function currentUser(req: Request): TokenPayload {
  if (!req.user) throw new HttpError(401, "尚未登入");
  return req.user;
}
