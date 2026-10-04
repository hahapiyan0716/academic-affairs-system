"use client";

import { useState } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/lib/api";
import { COURSE_TYPE, compactSchedule, semesterLabel } from "@/lib/labels";
import type { HistorySection } from "@/types";

export default function HistoryPage() {
  const [q, setQ] = useState("");
  const [teacher, setTeacher] = useState("");
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (teacher.trim()) params.set("teacher", teacher.trim());
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
