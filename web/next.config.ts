import type { NextConfig } from "next";

// FastAPI 後端位址（僅在 Next.js 伺服器端使用，不會暴露給瀏覽器）
const API_URL = process.env.API_URL ?? "http://localhost:8000";

/**
 * 安全標頭：與 FastAPI 的 api/app/middleware/security_headers.py 相同的三個。
 * 頁面（/login、/student……）與 /_next/static/ 的 JS、CSS 由 Next.js 自己回應，不經過 FastAPI，
 * 所以要在這裡另外加上；/api/* 的回應則由 FastAPI 的中介層負責。
 */
const SECURITY_HEADERS = [
  // 瀏覽器必須照 Content-Type 處理，不准自己猜類型（MIME sniffing），防止內容被當成 HTML／JS 執行（XSS）
  { key: "X-Content-Type-Options", value: "nosniff" },
  // 不准被任何網頁用 iframe 嵌入，防止點擊劫持（Clickjacking）：
  // 攻擊者把已登入使用者的頁面疊在透明 iframe 下，誘使他點到「退選」等按鈕
  { key: "X-Frame-Options", value: "DENY" },
  // 不送 Referer（來源網址），避免網址中的資訊（例如 /admin/users?q=搜尋的姓名）洩漏給外部網站
  { key: "Referrer-Policy", value: "no-referrer" },
];

// Next.js 設定
const nextConfig: NextConfig = {
  // 不送出 X-Powered-By: Next.js，避免透露網站使用的技術
  poweredByHeader: false,

  // 把 /api/* 轉發到 FastAPI：瀏覽器只看到同一個來源（localhost:3000），
  // 因此 httpOnly cookie 會自動帶上，也不需要處理 CORS
  // source: /api/:path* 會匹配 /api/ 後的所有路徑，並把 :path* 的值傳給 destination
  // 例如 /api/users 會轉發到 http://localhost:8000/api/users
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },

  // /:path* 符合所有路徑（含首頁 /），因此頁面與 /_next/static/ 的 JS、CSS 都會加上 SECURITY_HEADERS，不必另外列出
  // 經 rewrites 轉發的 /api/* 實測每個安全標頭只出現一次（來自 FastAPI），不會重複
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
