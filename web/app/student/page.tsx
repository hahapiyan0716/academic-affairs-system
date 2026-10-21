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

/**
 * 學生加退選：瀏覽選課中學期的開放班級，即時加選或退選。
 * 選課中的學期不一定是目前學期（例如本學期上課中、下學期先開放選課），後端保證最多只有一個；
 * 沒有學期在選課中時改為瀏覽目前學期
 */
export default function EnrollPage() {
  const [q, setQ] = useState("");
  // 停止輸入後才送出搜尋，避免每打一個字就查一次
  const keyword = useDebouncedValue(q.trim());
  // 領域為下拉選單，選定即查詢，不需延遲
  const [field, setField] = useState("");
  // 學期清單與開課班級清單分開查詢，避免先查到預設的目前學期、再換成選課中的學期
  // 所以先找學期清單，找出選課中的學期或目前學期，再查詢該學期的開課班級
  const { data: semesters } = useApiQuery<Semester[]>("/api/semesters");
  // 先找選課中的學期，沒有的話找目前學期；兩者都沒有時 semester 為 undefined，查詢時不帶學期篩選
  const semester = semesters?.find((s) => s.status === "Enrolling") ?? semesters?.find((s) => s.is_current);
  // 學期清單載入前不查詢（path 為 null），以免先查到預設的目前學期、再換成選課中的學期
  const { data, error, isPending } = useApiQuery<BrowseSection[]>(semesters ? "/api/sections" : null, {
    semester_id: semester?.semester_id ?? "",
    q: keyword,
    field,
  });
  // 只用來決定按鈕是否可按；真正的限制由後端檢查
  const enrolling = semester?.status === "Enrolling";
  const invalidate = useInvalidate();

  /** 加選（withdraw = false）或退選（withdraw = true） */
  // useMutation 會自動處理 loading、error、success 狀態，並提供 mutate() 觸發請求
  const enrollment = useMutation({
    // s 是要加退選的班級，withdraw 決定是加選還是退選
    mutationFn: ({ s, withdraw }: { s: BrowseSection; withdraw: boolean }) =>
      withdraw
        ? api(`/api/enrollments/${s.section_id}`, { method: "DELETE" })
        : api("/api/enrollments", { method: "POST", json: { section_id: s.section_id } }),
    // _ 是 mutationFn 的回傳值，{ s, withdraw } 是 mutate() 的參數
    onSuccess: (_, { s, withdraw }) =>
      toast.success(withdraw ? `已退選 ${s.course_name}` : `加選成功：${s.course_name}`),
    // 額滿、衝堂、重複修課等規則由後端判斷，訊息直接呈現
    onError: (e) => toast.error(e.message),
    // onSettled: 在請求完成後執行，無論成功或失敗
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
          semester ? `${semesterLabel(semester.semester_id)}・即時先搶先贏，加選當下即確定是否選上` : undefined
        }
      >
        {semester && <SemesterStatusBadge status={semester.status} />}
        <FieldSelect value={field} onChange={setField} />
        <Input
          placeholder="搜尋課名、課號、教師"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="w-56"
        />
      </PageHeader>
      {semester && !enrolling && (
        <div className="mb-4 rounded-lg border bg-background px-4 py-3 text-sm text-muted-foreground">
          目前沒有開放加退選的學期，以下為目前學期的開課，僅供瀏覽。
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
