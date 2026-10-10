"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { ArrowLeft, Save } from "lucide-react";
import { toast } from "sonner";
import {
  EmptyState,
  EnrollmentBadge,
  ErrorState,
  LoadingState,
  PageHeader,
  SemesterStatusBadge,
} from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import { compactSchedule, semesterLabel } from "@/lib/labels";
import type { Roster } from "@/types";
import SectionSettings from "./section-settings";

/** 班級頁：班級設定、修課名單與登錄成績 */
export default function SectionRosterPage() {
  // 動態路由 [id]：網址中的班級 ID
  const { id } = useParams<{ id: string }>();
  const { data, error, loading, reload } = useApi<Roster>(`/api/teacher/sections/${id}/roster`);
  // 只記錄使用者修改過的欄位；未修改者顯示伺服器上的值
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  if (loading && !data) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "無法載入資料"} />;

  const { section, students, gradable } = data;
  // 班級設定只在開課期間（與後端 section_service 的 OPENABLE 一致）且班級未停開時顯示
  const editable = section.status === "Open" && ["Planning", "Enrolling"].includes(data.semester_status);
  // 畫面上每位學生的成績 = 修改中的值，否則為伺服器上的值
  const scoreOf = (sid: string, original: string | null) => edits[sid] ?? original ?? "";
  const scores = Object.fromEntries(students.map((s) => [s.student_id, scoreOf(s.student_id, s.score)]));
  // 與伺服器值不同的才送出；改了又改回原值的不算
  const dirty = students.filter((s) => (s.score ?? "") !== scores[s.student_id]);

  /** 送出有變動的成績；先在前端擋掉明顯錯誤的輸入，後端仍會再驗證一次 */
  async function saveGrades() {
    const invalid = dirty.find((s) => {
      const v = scores[s.student_id];
      return v !== "" && (Number.isNaN(Number(v)) || Number(v) < 0 || Number(v) > 100);
    });
    if (invalid) return toast.error(`${invalid.student_name} 的成績須介於 0–100`);
    setSaving(true);
    try {
      const res = await api<{ updated: number }>(`/api/teacher/sections/${id}/grades`, {
        method: "PUT",
        json: {
          grades: dirty.map((s) => ({
            student_id: s.student_id,
            // 清空欄位 = 清除成績（送出 null）；數值以字串送出，由後端轉成 Decimal
            score: scores[s.student_id] === "" ? null : scores[s.student_id],
          })),
        },
      });
      toast.success(`已更新 ${res.updated} 筆成績`);
      // 清空修改紀錄，改顯示重新讀取後的伺服器值
      setEdits({});
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Button variant="ghost" size="sm" asChild className="mb-2 -ml-2">
        <Link href="/teacher">
          <ArrowLeft />
          返回我的開課
        </Link>
      </Button>
      <PageHeader
        title={`${section.course_name}（${section.course_no}-${section.section_code}）`}
        description={`${semesterLabel(section.semester_id)}・${section.credit} 學分・${section.teacher_names}・${compactSchedule(section.schedule_text)}`}
      >
        <SemesterStatusBadge status={data.semester_status} />
      </PageHeader>

      {editable && <SectionSettings section={section} onChanged={reload} />}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">修課名單（{students.length} 人）</CardTitle>
          {gradable ? (
            <Button size="sm" onClick={saveGrades} disabled={saving || dirty.length === 0}>
              <Save />
              儲存成績{dirty.length ? `（${dirty.length}）` : ""}
            </Button>
          ) : (
            <span className="text-sm text-muted-foreground">僅上課中或已結束的學期可登錄成績</span>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {students.length === 0 ? (
            <EmptyState message="目前沒有學生選修" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>學號</TableHead>
                  <TableHead>姓名</TableHead>
                  <TableHead>系所</TableHead>
                  <TableHead>選課狀態</TableHead>
                  <TableHead className="text-right">教學評量</TableHead>
                  <TableHead className="w-32 text-right">成績</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {students.map((s) => (
                  <TableRow key={s.student_id}>
                    <TableCell className="font-mono">{s.student_id}</TableCell>
                    <TableCell>{s.student_name}</TableCell>
                    <TableCell>
                      {s.dept_name}
                      {s.degree === 1 && <span className="ml-1 text-xs text-muted-foreground">碩博</span>}
                    </TableCell>
                    <TableCell>
                      <EnrollmentBadge status={s.status} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{s.feedback_rank ?? "—"}</TableCell>
                    <TableCell className="text-right">
                      {gradable ? (
                        <Input
                          inputMode="decimal"
                          className="ml-auto h-8 w-24 text-right tabular-nums"
                          value={scores[s.student_id] ?? ""}
                          onChange={(e) => setEdits((prev) => ({ ...prev, [s.student_id]: e.target.value }))}
                          aria-label={`${s.student_name} 的成績`}
                        />
                      ) : (
                        <span className="tabular-nums">{s.score ?? "—"}</span>
                      )}
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
