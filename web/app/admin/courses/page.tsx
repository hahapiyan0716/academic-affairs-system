"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApiQuery, useInvalidate } from "@/lib/api";
import { COURSE_TYPE } from "@/lib/labels";
import type { AdminCourse } from "@/types";
import CourseDialog from "./course-dialog";

/** 課程庫管理：列表、新增、編輯、停用／啟用 */
// 與教師開課頁（/teacher/sections/new）的課程選單不同：該選單來自 GET /api/courses，只列出啟用中的課程
// 管理員可以新增/編輯/啟用/停用課程，停用的課程不會出現在教師開課的課程選單中，但歷年紀錄仍然保留
export default function CoursesPage() {
  const { data, error, isPending } = useApiQuery<AdminCourse[]>("/api/admin/courses");
  // 編輯中的課程："new" = 新增、物件 = 編輯該課程、null = 對話框關閉
  const [editing, setEditing] = useState<AdminCourse | "new" | null>(null);
  const invalidate = useInvalidate();

  /** 切換課程啟用狀態；停用的課程不會出現在教師開課的課程選單（/api/courses） */
  const toggleActive = useMutation({
    mutationFn: (c: AdminCourse) =>
      api(`/api/admin/courses/${c.course_no}`, { method: "PATCH", json: { is_active: !c.is_active } }),
    onSuccess: (_, c) => {
      toast.success(`${c.course_name} 已${c.is_active ? "停用" : "啟用"}`);
      invalidate("/api/admin/courses", "/api/courses");
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader title="課程庫" description="維護課程代碼、課名與學分；停用的課程不能再開新班，但歷年紀錄會保留">
        {/* 修改 editing 狀態為 "new"，表示要新增課程，同時會渲染出新增課程對話框 */}
        <Button onClick={() => setEditing("new")}>
          <Plus />
          新增課程
        </Button>
      </PageHeader>
      <Card>
        <CardContent className="p-0">
          {/* 只在第一次載入時顯示載入中；之後重新查詢時保留舊資料，避免表格閃爍 */}
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
                  // 停用的課程以半透明顯示
                  <TableRow key={c.course_no} className={c.is_active ? "" : "opacity-50"}>
                    <TableCell className="font-mono">{c.course_no}</TableCell>
                    <TableCell className="font-medium">{c.course_name}</TableCell>
                    <TableCell>
                      {/* variant 指定 Badge 外觀：必修用主色的 default、選修用較淡的 secondary（皆為 badge.tsx 內建選項） */}
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
                      <Switch
                        checked={c.is_active}   // checked 代表開關的狀態，true = 啟用、false = 停用
                        disabled={toggleActive.isPending}
                        onCheckedChange={() => toggleActive.mutate(c)}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      {/* 修改 editing 狀態為該課程物件，表示要編輯課程，同時會渲染出編輯課程對話框 */}
                      {/* aria-label 是用來提供無障礙的提示文字 */}
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
      {/* 關閉時卸載對話框，下次開啟會以新的 course 重新初始化表單 */}
      {editing && (
        <CourseDialog
          course={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => setEditing(null)}
        />
      )}
    </>
  );
}
