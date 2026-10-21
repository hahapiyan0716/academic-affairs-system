"use client";

import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, hardNavigate } from "@/lib/api";

/** 登出按鈕：請後端清除 cookie 後整頁導向登入頁 */
export function LogoutButton() {
  async function logout() {
    // 即使登出請求失敗（例如 cookie 早已過期）仍導向登入頁
    await api("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    // 使用完整頁面導覽，不採用 router.push 的 Client-side navigation：
    // 這會重建 React 狀態與 TanStack Query 記憶體快取，並讓新請求帶上登出回應更新後的 cookie，
    // 再由 proxy 與 Server Components 根據最新登入狀態重新渲染 /login。
    hardNavigate("/login");
  }
  return (
    <Button variant="outline" size="sm" onClick={logout}>
      <LogOut />
      登出
    </Button>
  );
}
