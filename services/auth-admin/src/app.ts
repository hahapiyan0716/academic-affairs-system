import cookieParser from "cookie-parser";
import express from "express";
import helmet from "helmet";
import { errorHandler } from "./errors";
import { adminRouter } from "./routes/admin";
import { authRouter } from "./routes/auth";

export function createApp() {
  const app = express();

  // 只信任本機的反向代理（Next.js rewrites），讓限流能取得真實的用戶端 IP
  app.set("trust proxy", "loopback");
  app.use(helmet());
  app.use(express.json({ limit: "100kb" }));
  app.use(cookieParser());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", service: "auth-admin" });
  });
  app.use("/api/auth", authRouter);
  app.use("/api/admin", adminRouter);

  app.use((_req, res) => {
    res.status(404).json({ detail: "找不到此 API" });
  });
  app.use(errorHandler);
  return app;
}
