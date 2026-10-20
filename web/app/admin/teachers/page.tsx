"use client";

import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApiQuery, useInvalidate } from "@/lib/api";
import type { AdminTeacher } from "@/types";

/** 教師開課權限：列出教師與最近一次權限異動，可切換授予／收回 */
export default function TeacherPermissionPage() {
  const { data, error, isPending } = useApiQuery<AdminTeacher[]>("/api/admin/teachers");
  const invalidate = useInvalidate();

  /** 切換開課權限；後端會同時寫入稽核紀錄 */
  const toggle = useMutation({
    mutationFn: (t: AdminTeacher) =>
      api(`/api/admin/teachers/${t.teacher_id}/permission`, {
        method: "PATCH",
        json: { can_open_section: !t.can_open_section },
      }),
    // t 是送出前的教師資料，因此 can_open_section 為 true 代表這次是「收回」
    onSuccess: (_, t) => {
      toast.success(`已${t.can_open_section ? "收回" : "授予"} ${t.teacher_name} 的開課權限`);
      invalidate("/api/admin/teachers", "/api/admin/stats");
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader
        title="教師開課權限"
        description="只有被授權的教師可以自行新增開課班級；每次切換都會寫入稽核紀錄"
      />
      <Card>
        <CardContent className="p-0">
          {isPending ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error.message} />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>教師代碼</TableHead>
                  <TableHead>姓名</TableHead>
                  <TableHead>登入帳號</TableHead>
                  <TableHead>最近異動</TableHead>
                  <TableHead className="text-right">開課權限</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.map((t) => {
                  const log = t.latest_log;
                  return (
                    <TableRow key={t.teacher_id}>
                      <TableCell className="font-mono">{t.teacher_id}</TableCell>
                      <TableCell>{t.teacher_name}</TableCell>
                      <TableCell>
                        {t.user ? (
                          <span className={t.user.is_active ? "" : "text-muted-foreground line-through"}>
                            {t.user.username}
                          </span>
                        ) : (
                          <Badge variant="outline">未建立帳號</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {log
                          ? `${new Date(log.changed_at).toLocaleString("zh-TW")}・${log.admin.username} ${log.granted ? "授予" : "收回"}`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Switch
                          checked={t.can_open_section}
                          disabled={toggle.isPending}
                          onCheckedChange={() => toggle.mutate(t)}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
