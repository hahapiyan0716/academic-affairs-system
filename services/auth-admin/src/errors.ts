import type { ErrorRequestHandler } from "express";
import { z } from "zod";
import { Prisma } from "./generated/prisma/client";

export class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/**
 * 統一錯誤處理：回應格式與 FastAPI 一致 { detail: string }，前端只需處理一種格式
 */
export const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {
  if (err instanceof HttpError) {
    res.status(err.status).json({ detail: err.message });
    return;
  }
  if (err instanceof z.ZodError) {
    res.status(400).json({ detail: z.prettifyError(err) });
    return;
  }
  if (err instanceof Prisma.PrismaClientKnownRequestError) {
    // P2002：違反 UNIQUE；P2003：違反外鍵；P2025：找不到要更新的資料
    if (err.code === "P2002") {
      res.status(409).json({ detail: "資料重複，違反唯一性約束" });
      return;
    }
    if (err.code === "P2003") {
      res.status(409).json({ detail: "參照的資料不存在，或仍被其他資料使用" });
      return;
    }
    if (err.code === "P2025") {
      res.status(404).json({ detail: "找不到指定的資料" });
      return;
    }
  }
  console.error(err);
  res.status(500).json({ detail: "伺服器內部錯誤" });
};
