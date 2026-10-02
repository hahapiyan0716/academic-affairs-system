import type { NextConfig } from "next";

// 兩個後端服務的位址（僅在 Next.js 伺服器端使用，不會暴露給瀏覽器）
const AUTH_API_URL = process.env.AUTH_API_URL ?? "http://localhost:4000";
const ACADEMIC_API_URL = process.env.ACADEMIC_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // 依路徑把 /api/* 轉發到對應後端：瀏覽器只看到同一個來源（localhost:3000），
  // 因此 httpOnly cookie 會自動帶上，也不需要處理 CORS
  async rewrites() {
    return [
      { source: "/api/auth/:path*", destination: `${AUTH_API_URL}/api/auth/:path*` },
      { source: "/api/admin/:path*", destination: `${AUTH_API_URL}/api/admin/:path*` },
      // 其餘 /api/* 一律交給 FastAPI（順序在後，前兩條優先比對）
      { source: "/api/:path*", destination: `${ACADEMIC_API_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
