"use client";

import { useState } from "react";
import { Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import { COURSE_TYPE } from "@/lib/labels";
import type { AdminCourse } from "@/types";
import CourseDialog from "./course-dialog";

export default function CoursesPage() {
  const { data, error, loading, reload } = useApi<AdminCourse[]>("/api/admin/courses");
  const [editing, setEditing] = useState<AdminCourse | "new" | null>(null);

  async function toggleActive(c: AdminCourse) {
    try {
      await api(`/api/admin/courses/${c.course_no}`, { method: "PATCH", json: { is_active: !c.is_active } });
      toast.success(`${c.course_name} 已${c.is_active ? "停用" : "啟用"}`);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader title="課程庫" description="維護課程代碼、課名與學分；停用的課程不能再開新班，但歷年紀錄會保留">
        <Button onClick={() => setEditing("new")}>
          <Plus />
          新增課程
        </Button>
      </PageHeader>
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
                  <TableHead>課程代碼</TableHead>
                  <TableHead>課名</TableHead>
                  <TableHead>類型</TableHead>
                  <TableHead className="text-right">學分</TableHead>
                  <TableHead>領域</TableHead>
                  <TableHead className="text-right">歷年開班</TableHead>
                  <TableHead className="text-right">啟用</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.map((c) => (
                  <TableRow key={c.course_no} className={c.is_active ? "" : "opacity-60"}>
                    <TableCell className="font-mono">{c.course_no}</TableCell>
                    <TableCell className="font-medium">{c.course_name}</TableCell>
                    <TableCell>
                      <Badge variant={c.course_type === "Required" ? "default" : "secondary"}>
                        {COURSE_TYPE[c.course_type]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{c.credit}</TableCell>
                    <TableCell className="space-x-1">
                      {c.fields.map((f) => (
                        <Badge key={f} variant="outline">
                          {f}
                        </Badge>
                      ))}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{c.section_count}</TableCell>
                    <TableCell className="text-right">
                      <Switch checked={c.is_active} onCheckedChange={() => toggleActive(c)} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon-sm" onClick={() => setEditing(c)} aria-label="編輯">
                        <Pencil />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {editing && (
        <CourseDialog
          course={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </>
  );
}
