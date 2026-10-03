import type { NextConfig } from "next";

// FastAPI 後端位址（僅在 Next.js 伺服器端使用，不會暴露給瀏覽器）
const API_URL = process.env.API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // 把 /api/* 轉發到 FastAPI：瀏覽器只看到同一個來源（localhost:3000），
  // 因此 httpOnly cookie 會自動帶上，也不需要處理 CORS
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
