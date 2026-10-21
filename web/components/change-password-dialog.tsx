"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { KeyRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";

const EMPTY = { current: "", next: "", confirm: "" };

/** 「修改密碼」按鈕與對話框（三種角色共用，放在頂部導覽列） */
export function ChangePasswordDialog() {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  /** 開關對話框；關閉時清空表單，不讓密碼留在元件狀態中 */
  function changeOpen(o: boolean) {
    setOpen(o);
    if (!o)
      setForm(EMPTY);
  }

  const change = useMutation({
    mutationFn: () =>
      api("/api/auth/password", {
        method: "POST",
        json: { current_password: form.current, new_password: form.next },
      }),
    onSuccess: () => {
      // 後端已為本裝置重新簽發 cookie，不需要重新登入，但其他裝置上的登入已失效
      toast.success("密碼已更新，其他裝置上的登入已失效");
      changeOpen(false);
    },
    // 目前密碼錯誤、新密碼不符規則等由後端判斷，訊息直接呈現
    onError: (e) => toast.error(e.message),
  });

  function submit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();   // 阻止表單送出後頁面重新整理
    if (form.next !== form.confirm) return toast.error("兩次輸入的新密碼不一致");
    change.mutate();      // 發送 API 請求，更新密碼
  }

  // 產生指定欄位的 onChange：set("current") 回傳一個只更新 form.current 的函式，三個輸入框共用同一段邏輯
  const set = (k: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <Dialog open={open} onOpenChange={changeOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <KeyRound />
          <span className="hidden sm:inline">修改密碼</span>
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>修改密碼</DialogTitle>
          <DialogDescription>修改後，其他裝置上的登入會失效，需要以新密碼重新登入。</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="current-password">目前的密碼</Label>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              value={form.current}
              onChange={set("current")}
              required
            />
          </div>
          {/* minLength 只是瀏覽器端的即時提示；密碼規則（8 字元以上、不超過 72 bytes）由後端 auth_schema.py 的 Password 驗證 */}
          <div className="grid gap-1.5">
            <Label htmlFor="new-password">新密碼（至少 8 個字元）</Label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={form.next}
              onChange={set("next")}
              required
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="confirm-password">再次輸入新密碼</Label>
            <Input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={form.confirm}
              onChange={set("confirm")}
              required
            />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={change.isPending}>
              更新密碼
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
