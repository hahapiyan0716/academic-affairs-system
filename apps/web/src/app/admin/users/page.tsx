"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import { ROLE_LABEL, STUDENT_STATUS } from "@/lib/labels";
import type { AdminUser, Department, Role } from "@/lib/types";

export default function UsersPage() {
  const [role, setRole] = useState<"" | Role>("");
  const [q, setQ] = useState("");
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (q.trim()) params.set("q", q.trim());
  const { data, error, loading, reload } = useApi<AdminUser[]>(`/api/admin/users?${params}`);

  async function toggleActive(u: AdminUser) {
    try {
      await api(`/api/admin/users/${u.user_id}`, { method: "PATCH", json: { is_active: !u.is_active } });
      toast.success(`${u.username} 已${u.is_active ? "停用" : "啟用"}`);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function changeStudentStatus(studentId: string, status: string) {
    try {
      await api(`/api/admin/users/students/${studentId}/status`, { method: "PATCH", json: { status } });
      toast.success(`學籍已更新為「${STUDENT_STATUS[status]}」`);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader title="帳號管理" description="建立帳號、停用登入、調整學生學籍狀態">
        <Input placeholder="搜尋帳號或姓名" value={q} onChange={(e) => setQ(e.target.value)} className="w-48" />
        <Select value={role || "all"} onValueChange={(v) => setRole(v === "all" ? "" : (v as Role))}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部身分</SelectItem>
            <SelectItem value="Admin">管理員</SelectItem>
            <SelectItem value="Teacher">教師</SelectItem>
            <SelectItem value="Student">學生</SelectItem>
          </SelectContent>
        </Select>
        <CreateUserDialog onCreated={reload} />
      </PageHeader>

      <Card>
        <CardContent className="p-0">
          {loading && !data ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error} />
            </div>
          ) : !data?.length ? (
            <EmptyState message="沒有符合條件的帳號" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>帳號</TableHead>
                  <TableHead>身分</TableHead>
                  <TableHead>姓名</TableHead>
                  <TableHead>學籍</TableHead>
                  <TableHead>最後登入</TableHead>
                  <TableHead className="text-right">啟用</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((u) => (
                  <TableRow key={u.user_id}>
                    <TableCell className="font-mono">{u.username}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{ROLE_LABEL[u.role]}</Badge>
                    </TableCell>
                    <TableCell>{u.teacher?.teacher_name ?? u.student?.student_name ?? "—"}</TableCell>
                    <TableCell>
                      {u.student ? (
                        <Select
                          value={u.student.status}
                          onValueChange={(v) => changeStudentStatus(u.student!.student_id, v)}
                        >
                          <SelectTrigger size="sm" className="w-24">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Object.entries(STUDENT_STATUS).map(([k, v]) => (
                              <SelectItem key={k} value={k}>
                                {v}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleString("zh-TW") : "從未登入"}
                    </TableCell>
                    <TableCell className="text-right">
                      <Switch checked={u.is_active} onCheckedChange={() => toggleActive(u)} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function CreateUserDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<Role>("Student");
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
  const { data: depts } = useApi<Department[]>(open ? "/api/admin/departments" : null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const base = { role, username: form.username, password: form.password };
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
