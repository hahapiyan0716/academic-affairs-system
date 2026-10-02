"use client";

import { toast } from "sonner";
import { ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import type { AdminTeacher } from "@/lib/types";

export default function TeacherPermissionPage() {
  const { data, error, loading, reload } = useApi<AdminTeacher[]>("/api/admin/teachers");

  async function toggle(t: AdminTeacher) {
    try {
      await api(`/api/admin/teachers/${t.teacher_id}/permission`, {
        method: "PATCH",
        json: { can_open_section: !t.can_open_section },
      });
      toast.success(`已${t.can_open_section ? "收回" : "授予"} ${t.teacher_name} 的開課權限`);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader
        title="教師開課權限"
        description="只有被授權的教師可以自行新增開課班級；每次切換都會寫入稽核紀錄"
      />
      <Card>
        <CardContent className="p-0">
          {loading && !data ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error} />
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
                  const log = t.permission_logs[0];
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
                        <Switch checked={t.can_open_section} onCheckedChange={() => toggle(t)} />
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
