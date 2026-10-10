"use client";

import { useState } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/lib/api";
import { COURSE_TYPE, compactSchedule, semesterLabel } from "@/lib/labels";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import type { HistorySection } from "@/types";

/** 歷年開課紀錄：依課名／課號與教師姓名搜尋跨學期的開課資料 */
export default function HistoryPage() {
  const [q, setQ] = useState("");
  const [teacher, setTeacher] = useState("");
  // 兩個搜尋框合併成一個字串再延遲，連續在兩個欄位間輸入時也只發一次請求。
  // 用字串而非物件：物件每次渲染都是新的參考，會讓 useDebouncedValue 的 effect 不斷重跑。
  // 單行輸入框無法輸入換行，因此以 \n 分隔不會與內容衝突。
  const filters = useDebouncedValue(`${q.trim()}\n${teacher.trim()}`);
  const [keyword, teacherName] = filters.split("\n");
  // 搜尋條件改變 → path 改變 → useApi 自動重新請求
  const params = new URLSearchParams();
  if (keyword) params.set("q", keyword);
  if (teacherName) params.set("teacher", teacherName);
  const { data, error, loading } = useApi<HistorySection[]>(`/api/history/sections?${params}`);

  return (
    <>
      <PageHeader title="歷年開課紀錄" description="查詢各學期的開課內容、授課教師、修課人數與平均成績">
        <Input placeholder="課名或課號" value={q} onChange={(e) => setQ(e.target.value)} className="w-40" />
        <Input placeholder="教師姓名" value={teacher} onChange={(e) => setTeacher(e.target.value)} className="w-32" />
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
            <EmptyState message="查無開課紀錄" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>學期</TableHead>
                  <TableHead>課程</TableHead>
                  <TableHead>類型</TableHead>
                  <TableHead>授課教師</TableHead>
                  <TableHead>時段（教室）</TableHead>
                  <TableHead className="text-right">修課人數</TableHead>
                  <TableHead className="text-right">平均成績</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((s) => (
                  <TableRow key={s.section_id}>
                    <TableCell className="whitespace-nowrap">{semesterLabel(s.semester_id)}</TableCell>
                    <TableCell>
                      <span className="font-medium">{s.course_name}</span>
                      <span className="ml-2 font-mono text-xs text-muted-foreground">
                        {s.course_no}-{s.section_code}
                      </span>
                    </TableCell>
                    <TableCell>{COURSE_TYPE[s.course_type]}</TableCell>
                    <TableCell>{s.teacher_names}</TableCell>
                    {/* 停開的班級時段已被刪除（釋放教室），改顯示「已停開」 */}
                    <TableCell className="text-sm">
                      {s.status === "Cancelled" ? <Badge variant="outline">已停開</Badge> : compactSchedule(s.schedule_text)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{s.enrolled_count}</TableCell>
                    <TableCell className="text-right tabular-nums">{s.avg_score ?? "—"}</TableCell>
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
