"use client";

import Link from "next/link";
import { useState } from "react";
import { Plus, Users } from "lucide-react";
import { EmptyState, ErrorState, LoadingState, PageHeader, SemesterSelect } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/lib/api";
import { COURSE_TYPE, compactSchedule, semesterLabel } from "@/lib/labels";
import type { Section } from "@/types";

export default function TeacherHome() {
  const [semester, setSemester] = useState("");
  const { data: me } = useApi<{ teacher_name: string; can_open_section: boolean }>("/api/teacher/me");
  const { data, error, loading } = useApi<Section[]>(
    `/api/teacher/sections${semester ? `?semester_id=${semester}` : ""}`,
  );

  return (
    <>
      <PageHeader title="我的開課" description="您授課（含合授）的所有班級；點選班級可查看名單與登錄成績">
        <SemesterSelect value={semester} onChange={setSemester} allowAll />
        {me?.can_open_section ? (
          <Button asChild>
            <Link href="/teacher/sections/new">
              <Plus />
              新增開課
            </Link>
          </Button>
        ) : (
          <Badge variant="outline">尚未取得開課權限</Badge>
        )}
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
            <EmptyState message="此條件下沒有授課班級" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>學期</TableHead>
                  <TableHead>課程</TableHead>
                  <TableHead>類型</TableHead>
                  <TableHead>授課教師</TableHead>
                  <TableHead>時段</TableHead>
                  <TableHead className="text-right">人數</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((s) => (
                  <TableRow key={s.section_id} className={s.status === "Cancelled" ? "opacity-50" : ""}>
                    <TableCell className="whitespace-nowrap">{semesterLabel(s.semester_id)}</TableCell>
                    <TableCell>
                      <div className="font-medium">{s.course_name}</div>
                      <div className="font-mono text-xs text-muted-foreground">
                        {s.course_no}-{s.section_code}・{s.credit} 學分
                      </div>
                    </TableCell>
                    <TableCell>{COURSE_TYPE[s.course_type]}</TableCell>
                    <TableCell>{s.teacher_names}</TableCell>
                    <TableCell className="text-sm">
                      {s.status === "Cancelled" ? <Badge variant="outline">已停開</Badge> : compactSchedule(s.schedule_text)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {s.enrolled_count} / {s.capacity}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/teacher/sections/${s.section_id}`}>
                          <Users />
                          名單與成績
                        </Link>
                      </Button>
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
