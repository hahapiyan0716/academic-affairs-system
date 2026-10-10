"use client";

import { useState } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader, SemesterSelect } from "@/components/common";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/lib/api";
import { COURSE_TYPE, compactSchedule } from "@/lib/labels";
import type { Timetable } from "@/types";
import TimetableGrid from "./timetable-grid";

/** 我的課表：週課表格狀圖 + 選課清單 */
export default function TimetablePage() {
  // 空字串 = 未選擇，後端預設回傳目前學期的課表
  const [semester, setSemester] = useState("");
  const { data, error, loading } = useApi<Timetable>(
    `/api/me/timetable${semester ? `?semester_id=${semester}` : ""}`,
  );

  return (
    <>
      <PageHeader
        title="我的課表"
        description={data ? `共 ${data.sections.length} 門課、${data.total_credits} 學分` : undefined}
      >
        <SemesterSelect value={semester} onChange={setSemester} />
      </PageHeader>
      {loading && !data ? (
        <LoadingState />
      ) : error ? (
        <ErrorState message={error} />
      ) : !data?.sections.length ? (
        <Card>
          <EmptyState message="此學期沒有已選上的課程" />
        </Card>
      ) : (
        <div className="grid gap-6">
          <Card>
            <CardContent className="overflow-x-auto pt-6">
              <TimetableGrid timetable={data} />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">選課清單</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>課程</TableHead>
                    <TableHead>類型</TableHead>
                    <TableHead className="text-right">學分</TableHead>
                    <TableHead>授課教師</TableHead>
                    <TableHead>時段（教室）</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.sections.map((s) => (
                    <TableRow key={s.section_id}>
                      <TableCell>
                        <span className="font-medium">{s.course_name}</span>
                        <span className="ml-2 font-mono text-xs text-muted-foreground">
                          {s.course_no}-{s.section_code}
                        </span>
                      </TableCell>
                      <TableCell>{COURSE_TYPE[s.course_type]}</TableCell>
                      <TableCell className="text-right tabular-nums">{s.credit}</TableCell>
                      <TableCell>{s.teacher_names}</TableCell>
                      <TableCell className="text-sm">{compactSchedule(s.schedule_text)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </>
  );
}
