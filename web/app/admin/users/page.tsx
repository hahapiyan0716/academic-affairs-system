"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { KeyRound } from "lucide-react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApiQuery, useInvalidate } from "@/lib/api";
import { ROLE_LABEL, STUDENT_STATUS } from "@/lib/labels";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import type { AdminUser, Role, SessionUser } from "@/types";
import CreateUserDialog from "./create-user-dialog";
import ResetPasswordDialog from "./reset-password-dialog";

/** 帳號管理：依身分與帳號、代號、學號或姓名篩選，並可建立帳號、啟用／停用、調整學籍、重設密碼 */
export default function UsersPage() {
  const [role, setRole] = useState<"" | Role>(""); // 空字串 = 全部身分
  // 關鍵字搜尋
  const [q, setQ] = useState("");
  // 關鍵字停止輸入後才套用；身分是下拉選單，切換時立即生效
  const keyword = useDebouncedValue(q.trim());
  // 篩選條件改變 → query key 改變 → 自動重新請求
  const { data, error, isPending } = useApiQuery<AdminUser[]>("/api/admin/users", { role, q: keyword });
  // 自己的密碼只能經由頂部的「修改密碼」變更（需驗證目前密碼），因此不在自己那一列顯示重設按鈕
  const { data: me } = useApiQuery<{ user: SessionUser }>("/api/auth/me");
  // 重設密碼中的帳號；null = 對話框關閉
  const [resetting, setResetting] = useState<AdminUser | null>(null);
  const invalidate = useInvalidate();

  /** 啟用／停用登入（後端禁止停用自己） */
  const toggleActive = useMutation({
    mutationFn: (u: AdminUser) =>
      // 送出 API 之後會再 Service 層檢查是否為自己，若是則回傳 400；前端不會顯示停用自己的按鈕
      api(`/api/admin/users/${u.user_id}`, { method: "PATCH", json: { is_active: !u.is_active } }),
    onSuccess: (_, u) => {
      toast.success(`${u.username} 已${u.is_active ? "停用" : "啟用"}`);
      // 教師權限頁也顯示帳號是否停用
      invalidate("/api/admin/users", "/api/admin/teachers");
    },
    onError: (e) => toast.error(e.message),
  });

  /** 變更學籍（休學、退學的學生不可選課） */
  const changeStudentStatus = useMutation({
    mutationFn: ({ studentId, status }: { studentId: string; status: string }) =>
      // API 更改學籍狀態之後，學生的選課權限會立即生效（休學、退學的學生不可選課），因此不需要額外呼叫 /api/teachers 重新整理選單
      // 學生之後在選課會根據學籍狀態被拒絕，或在課程頁面被隱藏
      api(`/api/admin/users/students/${studentId}/status`, { method: "PATCH", json: { status } }),
    onSuccess: (_, { status }) => {
      toast.success(`學籍已更新為「${STUDENT_STATUS[status]}」`);
      // 總覽的「在學學生數」也會改變
      invalidate("/api/admin/users", "/api/admin/stats");
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader title="帳號管理" description="建立帳號、停用登入、調整學生學籍狀態">
        <Input placeholder="搜尋帳號、代號、學號或姓名" value={q} onChange={(e) => setQ(e.target.value)} className="w-56" />
        {/* Select 的選項值不可為空字串，「全部」以 "all" 代表 */}
        <Select value={role || "all"} onValueChange={(v) => setRole(v === "all" ? "" : (v as Role))}>
          <SelectTrigger className="w-32">
            {/* SelectValue 會顯示目前選取的值 */}
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部身分</SelectItem>
            <SelectItem value="Admin">管理員</SelectItem>
            <SelectItem value="Teacher">教師</SelectItem>
            <SelectItem value="Student">學生</SelectItem>
          </SelectContent>
        </Select>
        <CreateUserDialog />
      </PageHeader>

      <Card>
        <CardContent className="p-0">
          {isPending ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error.message} />
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
                  <TableHead />
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
                          // 外層已判斷 u.student 存在，但 TypeScript 的型別收窄不會延續到回呼函式內，因此以 ! 標示非 null
                          onValueChange={(v) =>
                            changeStudentStatus.mutate({ studentId: u.student!.student_id, status: v })
                          }
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
                      <Switch
                        checked={u.is_active}
                        disabled={toggleActive.isPending}
                        onCheckedChange={() => toggleActive.mutate(u)}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      {me && me.user.sub !== String(u.user_id) && (
                        <Button variant="ghost" size="sm" onClick={() => setResetting(u)}>
                          <KeyRound />
                          重設密碼
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {/* 關閉時卸載對話框，下次開啟時表單是空的 */}
      {resetting && <ResetPasswordDialog user={resetting} onClose={() => setResetting(null)} />}
    </>
  );
}
