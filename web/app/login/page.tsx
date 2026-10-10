"use client";

import { useState } from "react";
import { GraduationCap, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, hardNavigate } from "@/lib/api";
import type { SessionUser } from "@/types";

// 內容與 lib/session.ts 的 ROLE_HOME 相同，修改時需同步
const ROLE_HOME = { Admin: "/admin", Teacher: "/teacher", Student: "/student" } as const;

/** 登入頁：登入成功後導向原本要去的頁面，或該角色的首頁 */
export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const { user } = await api<{ user: SessionUser }>("/api/auth/login", {
        method: "POST",
        json: { username, password },
      });
      // next 由 proxy.ts 在導向登入頁時帶入
      const next = new URLSearchParams(window.location.search).get("next");
      const home = ROLE_HOME[user.role];
      // 只接受自己角色底下的站內路徑，避免開放式重新導向（Open Redirect）
      hardNavigate(next && next.startsWith(`${home}/`) ? next : home);
    } catch (err) {
      setError((err as Error).message);
      // 只在失敗時解除送出狀態；成功時頁面即將整頁跳轉，保持按鈕停用以免重複送出
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <div className="mx-auto mb-2 flex size-11 items-center justify-center rounded-full bg-primary/10">
            <GraduationCap className="size-6 text-primary" />
          </div>
          <CardTitle className="text-xl">教務管理系統</CardTitle>
          <CardDescription>請以學號、教師代碼或管理員帳號登入</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">帳號</Label>
              <Input
                id="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="例如 S001、T001、admin"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密碼</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting && <Loader2 className="animate-spin" />}
              登入
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
