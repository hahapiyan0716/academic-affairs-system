"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  EmptyState,
  EnrollmentBadge,
  ErrorState,
  FieldSelect,
  LoadingState,
  PageHeader,
  SemesterStatusBadge,
} from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import { COURSE_TYPE, compactSchedule, semesterLabel } from "@/lib/labels";
import type { BrowseSection, Semester } from "@/types";

const ACTIVE = ["Selected", "Manual"];

export default function EnrollPage() {
  const [q, setQ] = useState("");
  const [field, setField] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const { data: semesters } = useApi<Semester[]>("/api/semesters");
  const current = semesters?.find((s) => s.is_current);
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  if (field) params.set("field", field);
  const { data, error, loading, reload } = useApi<BrowseSection[]>(`/api/sections?${params}`);
  const enrolling = current?.status === "Enrolling";

  async function act(s: BrowseSection, withdraw: boolean) {
    setBusy(s.section_id);
    try {
      if (withdraw) {
        await api(`/api/enrollments/${s.section_id}`, { method: "DELETE" });
        toast.success(`已退選 ${s.course_name}`);
      } else {
        await api("/api/enrollments", { method: "POST", json: { section_id: s.section_id } });
        toast.success(`加選成功：${s.course_name}`);
      }
    } catch (e) {
      // 額滿、衝堂、重複修課等規則由後端判斷，訊息直接呈現
      toast.error((e as Error).message);
    } finally {
      setBusy(null);
      reload();
    }
  }

  return (
    <>
      <PageHeader
        title="加退選"
        description={
          current ? `${semesterLabel(current.semester_id)}・即時先搶先贏，加選當下即確定是否選上` : undefined
        }
      >
        {current && <SemesterStatusBadge status={current.status} />}
        <FieldSelect value={field} onChange={setField} />
        <Input
          placeholder="搜尋課名、課號、教師"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-56"
        />
      </PageHeader>
      {current && !enrolling && (
        <div className="mb-4 rounded-lg border bg-background px-4 py-3 text-sm text-muted-foreground">
          目前學期不在選課期間，僅供瀏覽。
        </div>
      )}
      <Card>
        <CardContent className="p-0">
          {loading && !data ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error} />
            </div>
          ) : !data?.length ? (
            <EmptyState message="沒有符合條件的開課班級" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>課程</TableHead>
                  <TableHead>類型</TableHead>
                  <TableHead>領域</TableHead>
                  <TableHead>授課教師</TableHead>
                  <TableHead>時段（教室）</TableHead>
                  <TableHead className="text-right">已選／上限</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((s) => {
                  const mine = s.my_status !== null && ACTIVE.includes(s.my_status);
                  const full = s.enrolled_count >= s.capacity;
                  return (
                    <TableRow key={s.section_id}>
                      <TableCell>
                        <div className="font-medium">{s.course_name}</div>
                        <div className="font-mono text-xs text-muted-foreground">
                          {s.course_no}-{s.section_code}・{s.credit} 學分
                        </div>
                      </TableCell>
                      <TableCell>{COURSE_TYPE[s.course_type]}</TableCell>
                      <TableCell className="text-sm">{s.field_names ?? "—"}</TableCell>
                      <TableCell>{s.teacher_names}</TableCell>
                      <TableCell className="text-sm">{compactSchedule(s.schedule_text)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        <span className={full ? "font-medium text-destructive" : ""}>{s.enrolled_count}</span> /{" "}
                        {s.capacity}
                      </TableCell>
                      <TableCell className="space-x-1">
                        {s.my_status && <EnrollmentBadge status={s.my_status} />}
                        {s.conflict && <Badge variant="destructive">衝堂</Badge>}
                        {!mine && full && <Badge variant="outline">額滿</Badge>}
                      </TableCell>
                      <TableCell className="text-right">
                        {mine ? (
                          <Button
                            variant="outline"
                            size="sm"
                            disabled={!enrolling || busy === s.section_id}
                            onClick={() => act(s, true)}
                          >
                            退選
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            disabled={!enrolling || busy === s.section_id}
                            onClick={() => act(s, false)}
                          >
                            加選
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  );
}
