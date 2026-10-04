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
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import { compactSchedule, semesterLabel } from "@/lib/labels";
import type { Roster } from "@/types";

export default function SectionRosterPage() {
  const { id } = useParams<{ id: string }>();
  const { data, error, loading, reload } = useApi<Roster>(`/api/teacher/sections/${id}/roster`);
  // 只記錄使用者修改過的欄位；未修改者顯示伺服器上的值
  const [edits, setEdits] = useState<Record<string, string>>({});
  const [capacityEdit, setCapacityEdit] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  if (loading && !data) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "無法載入資料"} />;

  const { section, students, gradable } = data;
  const editable = section.status === "Open" && ["Planning", "Enrolling"].includes(data.semester_status);
  const scoreOf = (sid: string, original: string | null) => edits[sid] ?? original ?? "";
  const scores = Object.fromEntries(students.map((s) => [s.student_id, scoreOf(s.student_id, s.score)]));
  const dirty = students.filter((s) => (s.score ?? "") !== scores[s.student_id]);
  const capacity = capacityEdit ?? String(section.capacity);

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
            score: scores[s.student_id] === "" ? null : scores[s.student_id],
          })),
        },
      });
      toast.success(`已更新 ${res.updated} 筆成績`);
      setEdits({});
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function patchSection(body: object, msg: string) {
    try {
      await api(`/api/teacher/sections/${id}`, { method: "PATCH", json: body });
      toast.success(msg);
      setCapacityEdit(null);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
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

      {editable && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-base">班級設定</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label>人數上限（目前已選 {section.enrolled_count} 人）</Label>
              <Input
                type="number"
                className="w-32"
                min={section.enrolled_count || 1}
                value={capacity}
                onChange={(e) => setCapacityEdit(e.target.value)}
              />
            </div>
            <Button variant="outline" onClick={() => patchSection({ capacity: Number(capacity) }, "人數上限已更新")}>
              更新上限
            </Button>
            <Button
              variant="destructive"
              className="ml-auto"
              disabled={section.enrolled_count > 0}
              title={section.enrolled_count > 0 ? "已有學生選修，不可停開" : undefined}
              onClick={() => {
                if (confirm("確定停開此班級？停開後無法恢復，教室時段會被釋放。")) {
                  patchSection({ status: "Cancelled" }, "班級已停開");
                }
              }}
            >
              停開班級
            </Button>
          </CardContent>
        </Card>
      )}

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
