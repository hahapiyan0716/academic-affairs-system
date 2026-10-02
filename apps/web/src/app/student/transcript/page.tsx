"use client";

import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useApi } from "@/lib/api";
import { COURSE_TYPE, semesterLabel } from "@/lib/labels";
import type { Transcript } from "@/lib/types";

export default function TranscriptPage() {
  const { data, error, loading } = useApi<Transcript>("/api/me/transcript");

  if (loading && !data) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "無法載入資料"} />;

  return (
    <>
      <PageHeader title="歷年成績" description="學分加權平均只計入已有成績的課程；大學部 60 分、碩博班 70 分及格">
        <div className="flex gap-6 text-sm">
          <div>
            <div className="text-muted-foreground">實得學分</div>
            <div className="text-xl font-semibold tabular-nums">{data.total_credits_earned}</div>
          </div>
          <div>
            <div className="text-muted-foreground">總平均</div>
            <div className="text-xl font-semibold tabular-nums">{data.overall_average ?? "—"}</div>
          </div>
        </div>
      </PageHeader>
      {data.semesters.length === 0 ? (
        <Card>
          <EmptyState message="尚無修課紀錄" />
        </Card>
      ) : (
        <div className="grid gap-6">
          {data.semesters.map((sem) => (
            <Card key={sem.semester_id}>
              <CardHeader>
                <CardTitle className="text-base">{semesterLabel(sem.semester_id)}</CardTitle>
                <CardDescription>
                  修習 {sem.credits_taken} 學分・實得 {sem.credits_earned} 學分・學期平均 {sem.average ?? "—"}
                </CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>課號</TableHead>
                      <TableHead>課名</TableHead>
                      <TableHead>類型</TableHead>
                      <TableHead className="text-right">學分</TableHead>
                      <TableHead className="text-right">成績</TableHead>
                      <TableHead className="text-right">結果</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sem.rows.map((r) => (
                      <TableRow key={r.section_id}>
                        <TableCell className="font-mono">{r.course_no}</TableCell>
                        <TableCell>{r.course_name}</TableCell>
                        <TableCell>{COURSE_TYPE[r.course_type]}</TableCell>
                        <TableCell className="text-right tabular-nums">{r.credit}</TableCell>
                        <TableCell className="text-right tabular-nums">{r.score ?? "—"}</TableCell>
                        <TableCell className="text-right">
                          {r.passed === null ? (
                            <Badge variant="outline">未評分</Badge>
                          ) : r.passed ? (
                            <Badge>及格</Badge>
                          ) : (
                            <Badge variant="destructive">不及格</Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
