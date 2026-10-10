"use client";

import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, hardNavigate } from "@/lib/api";

/** 登出按鈕：請後端清除 cookie 後整頁導向登入頁 */
export function LogoutButton() {
  async function logout() {
    // 即使登出請求失敗（例如 cookie 早已過期）仍導向登入頁
    await api("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    // 整頁重新載入而非 router.push，讓 proxy 與 Server Component 以清除後的 cookie 重新判斷
    hardNavigate("/login");
  }
  return (
    <Button variant="outline" size="sm" onClick={logout}>
      <LogOut />
      登出
    </Button>
  );
}
