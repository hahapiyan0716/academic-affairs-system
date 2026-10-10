"use client";

import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import { ROLE_LABEL, STUDENT_STATUS } from "@/lib/labels";
import type { AdminUser, Role } from "@/types";
import CreateUserDialog from "./create-user-dialog";

/** 帳號管理：依身分與關鍵字篩選帳號、建立帳號、啟用／停用、調整學籍 */
export default function UsersPage() {
  const [role, setRole] = useState<"" | Role>(""); // 空字串 = 全部身分
  const [q, setQ] = useState("");
  // 篩選條件直接組成查詢字串；條件改變 → path 改變 → useApi 自動重新請求
  const params = new URLSearchParams();
  if (role) params.set("role", role);
  if (q.trim()) params.set("q", q.trim());
  const { data, error, loading, reload } = useApi<AdminUser[]>(`/api/admin/users?${params}`);

  /** 啟用／停用登入（後端禁止停用自己） */
  async function toggleActive(u: AdminUser) {
    try {
      await api(`/api/admin/users/${u.user_id}`, { method: "PATCH", json: { is_active: !u.is_active } });
      toast.success(`${u.username} 已${u.is_active ? "停用" : "啟用"}`);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  /** 變更學籍（休學、退學的學生不可選課） */
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
        {/* Select 的選項值不可為空字串，「全部」以 "all" 代表 */}
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
