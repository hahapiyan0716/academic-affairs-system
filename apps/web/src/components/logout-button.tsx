"use client";

import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, hardNavigate } from "@/lib/api";

export function LogoutButton() {
  async function logout() {
    await api("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    hardNavigate("/login");
  }
  return (
    <Button variant="outline" size="sm" onClick={logout}>
      <LogOut />
      登出
    </Button>
  );
}
