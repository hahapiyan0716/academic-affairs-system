"use client";

import { useMutation } from "@tanstack/react-query";
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
import { api, useApiQuery, useInvalidate } from "@/lib/api";
import { COURSE_TYPE, compactSchedule, semesterLabel } from "@/lib/labels";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import type { BrowseSection, Semester } from "@/types";

// 有效選課狀態，與後端 models.ACTIVE_ENROLLMENT 一致
const ACTIVE = ["Selected", "Manual"];

/** 學生加退選：瀏覽目前學期的開放班級，即時加選或退選 */
export default function EnrollPage() {
  const [q, setQ] = useState("");
  // 停止輸入後才送出搜尋，避免每打一個字就查一次
  const keyword = useDebouncedValue(q.trim());
  // 領域為下拉選單，選定即查詢，不需延遲
  const [field, setField] = useState("");
  const { data: semesters } = useApiQuery<Semester[]>("/api/semesters");
  const current = semesters?.find((s) => s.is_current);
  // 不帶 semester_id 時，後端預設查詢目前學期
  const { data, error, isPending } = useApiQuery<BrowseSection[]>("/api/sections", { q: keyword, field });
  // 只用來決定按鈕是否可按；真正的限制由後端檢查
  const enrolling = current?.status === "Enrolling";
  const invalidate = useInvalidate();

  /** 加選（withdraw = false）或退選（withdraw = true） */
  const enrollment = useMutation({
    mutationFn: ({ s, withdraw }: { s: BrowseSection; withdraw: boolean }) =>
      withdraw
        ? api(`/api/enrollments/${s.section_id}`, { method: "DELETE" })
        : api("/api/enrollments", { method: "POST", json: { section_id: s.section_id } }),
    onSuccess: (_, { s, withdraw }) =>
      toast.success(withdraw ? `已退選 ${s.course_name}` : `加選成功：${s.course_name}`),
    // 額滿、衝堂、重複修課等規則由後端判斷，訊息直接呈現
    onError: (e) => toast.error(e.message),
    // 失敗時也重新讀取：例如額滿是因為別人剛搶走名額，需要更新畫面上的人數。
    // 課表與成績單也列出本學期已選的課，一併失效，切換到那些頁面時才不會看到舊資料
    onSettled: () => invalidate("/api/sections", "/api/me/timetable", "/api/me/transcript"),
  });
  // 正在送出請求的那一列停用按鈕，防止重複點擊
  const busy = (s: BrowseSection) => enrollment.isPending && enrollment.variables?.s.section_id === s.section_id;

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
          {isPending ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error.message} />
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
                  // mine：目前已選上此班（顯示退選按鈕）；full：已額滿（僅作提示，仍可嘗試加選）
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
                            disabled={!enrolling || busy(s)}
                            onClick={() => enrollment.mutate({ s, withdraw: true })}
                          >
                            退選
                          </Button>
                        ) : (
                          <Button
                            size="sm"
                            disabled={!enrolling || busy(s)}
                            onClick={() => enrollment.mutate({ s, withdraw: false })}
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
