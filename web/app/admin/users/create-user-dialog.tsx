"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, useApi } from "@/lib/api";
import type { Department, Role } from "@/types";

/** 「新增帳號」按鈕與對話框；依身分顯示不同的個人資料欄位 */
export default function CreateUserDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<Role>("Student");
  // 教師與學生共用 id、name 欄位，送出時再依身分對應成 teacher_id／student_id 等
  const [form, setForm] = useState({
    username: "",
    password: "",
    id: "",
    name: "",
    dept_id: "",
    grade: "1",
    class_code: "A",
    degree: "0",
  });
  // 對話框開啟時才讀取系所清單
  const { data: depts } = useApi<Department[]>(open ? "/api/admin/departments" : null);
  // 產生 <Input> 的 onChange：set("username") 會更新 form.username
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const base = { role, username: form.username, password: form.password };
    // 請求格式依 role 而不同（對應後端 UserCreateIn 的 discriminated union）；教師的系所為選填
    const body =
      role === "Teacher"
        ? { ...base, profile: { teacher_id: form.id, teacher_name: form.name, dept_id: form.dept_id || null } }
        : role === "Student"
          ? {
              ...base,
              profile: {
                student_id: form.id,
                student_name: form.name,
                dept_id: form.dept_id,
                grade: Number(form.grade),
                class_code: form.class_code,
                degree: Number(form.degree),
              },
            }
          : base;
    try {
      await api("/api/admin/users", { method: "POST", json: body });
      toast.success(`已建立帳號 ${form.username}`);
      // 本對話框不會卸載，表單內容會保留到下次開啟
      setOpen(false);
      onCreated();
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus />
          新增帳號
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新增帳號</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-3">
          <div className="grid gap-1.5">
            <Label>身分</Label>
            <Select value={role} onValueChange={(v) => setRole(v as Role)}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Student">學生</SelectItem>
                <SelectItem value="Teacher">教師</SelectItem>
                <SelectItem value="Admin">管理員</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>帳號</Label>
              <Input value={form.username} onChange={set("username")} required minLength={3} />
            </div>
            <div className="grid gap-1.5">
              <Label>初始密碼</Label>
              <Input type="password" value={form.password} onChange={set("password")} required minLength={8} />
            </div>
          </div>
          {role !== "Admin" && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="grid gap-1.5">
                  <Label>{role === "Teacher" ? "教師代碼" : "學號"}</Label>
                  <Input value={form.id} onChange={set("id")} required maxLength={role === "Teacher" ? 6 : 10} />
                </div>
                <div className="grid gap-1.5">
                  <Label>姓名</Label>
                  <Input value={form.name} onChange={set("name")} required />
                </div>
              </div>
              <div className="grid gap-1.5">
                <Label>系所{role === "Teacher" && "（選填）"}</Label>
                <Select value={form.dept_id} onValueChange={(v) => setForm((f) => ({ ...f, dept_id: v }))}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="選擇系所" />
                  </SelectTrigger>
                  <SelectContent>
                    {depts?.map((d) => (
                      <SelectItem key={d.dept_id} value={d.dept_id}>
                        {d.dept_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
          {role === "Student" && (
            <div className="grid grid-cols-3 gap-3">
              <div className="grid gap-1.5">
                <Label>年級</Label>
                <Input type="number" min={1} max={7} value={form.grade} onChange={set("grade")} required />
              </div>
              <div className="grid gap-1.5">
                <Label>班別</Label>
                <Input value={form.class_code} onChange={set("class_code")} maxLength={2} required />
              </div>
              <div className="grid gap-1.5">
                <Label>學制</Label>
                <Select value={form.degree} onValueChange={(v) => setForm((f) => ({ ...f, degree: v }))}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="0">大學部</SelectItem>
                    <SelectItem value="1">碩博班</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button type="submit">建立</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
