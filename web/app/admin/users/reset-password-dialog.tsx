"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { AdminUser } from "@/types";

/** 管理員重設帳號密碼（處理忘記密碼）；父元件只在開啟時渲染本元件，關閉即卸載，表單不會殘留密碼 */
export default function ResetPasswordDialog({ user, onClose }: { user: AdminUser; onClose: () => void }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");

  const reset = useMutation({
    mutationFn: () => api(`/api/admin/users/${user.user_id}`, { method: "PATCH", json: { password } }),
    onSuccess: () => {
      toast.success(`已重設 ${user.username} 的密碼`);
      onClose();
    },
    onError: (e) => toast.error(e.message),
  });

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) return toast.error("兩次輸入的密碼不一致");
    reset.mutate();
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>重設 {user.username} 的密碼</DialogTitle>
          <DialogDescription>
            重設後，該帳號在所有裝置上的登入都會失效。請以安全的方式告知使用者新密碼，並請對方登入後自行修改。
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="reset-password">新密碼（至少 8 個字元）</Label>
            <Input
              id="reset-password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="reset-confirm">再次輸入新密碼</Label>
            <Input
              id="reset-confirm"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={reset.isPending}>
              重設密碼
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
