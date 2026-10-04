"use client";

import { useState } from "react";
import { EmptyState, ErrorState, LoadingState, PageHeader, SemesterSelect } from "@/components/common";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/lib/api";
import { COURSE_TYPE, WEEKDAYS, compactSchedule } from "@/lib/labels";
import type { Timetable, TimetableSlot } from "@/types";

const DAYS = [1, 2, 3, 4, 5, 6];
// 依課號給予固定色系，同一門課在課表上顏色一致
const PALETTE = [
  "bg-sky-100 text-sky-900 border-sky-200",
  "bg-emerald-100 text-emerald-900 border-emerald-200",
  "bg-amber-100 text-amber-900 border-amber-200",
  "bg-violet-100 text-violet-900 border-violet-200",
  "bg-rose-100 text-rose-900 border-rose-200",
  "bg-teal-100 text-teal-900 border-teal-200",
];

export default function TimetablePage() {
  const [semester, setSemester] = useState("");
  const { data, error, loading } = useApi<Timetable>(
    `/api/me/timetable${semester ? `?semester_id=${semester}` : ""}`,
  );

  const grid = new Map<string, TimetableSlot>();
  data?.slots.forEach((s) => grid.set(`${s.weekday}-${s.period}`, s));
  const maxPeriod = Math.max(8, ...(data?.slots.map((s) => s.period) ?? []));
  const colorOf = (sectionId: number) =>
    PALETTE[(data?.sections.findIndex((s) => s.section_id === sectionId) ?? 0) % PALETTE.length];

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
              <table className="w-full min-w-[640px] table-fixed border-collapse text-sm">
                <thead>
                  <tr>
                    <th className="w-12 border-b p-2 text-muted-foreground">節</th>
                    {DAYS.map((d) => (
                      <th key={d} className="border-b p-2 font-medium">
                        星期{WEEKDAYS[d - 1]}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Array.from({ length: maxPeriod }, (_, i) => i + 1).map((p) => (
                    <tr key={p}>
                      <td className="border-b p-2 text-center text-muted-foreground tabular-nums">{p}</td>
                      {DAYS.map((d) => {
                        const slot = grid.get(`${d}-${p}`);
                        return (
                          <td key={d} className="h-14 border-b p-1">
                            {slot && (
                              <div className={`h-full rounded-md border px-2 py-1 ${colorOf(slot.section_id)}`}>
                                <div className="truncate font-medium">{slot.course_name}</div>
                                <div className="truncate text-xs opacity-80">{slot.room_code}</div>
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
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
