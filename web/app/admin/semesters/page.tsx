"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApiQuery, useInvalidate } from "@/lib/api";
import { SEMESTER_STATUS, semesterLabel } from "@/lib/labels";
import type { Semester } from "@/types";

/** 學期管理：新增學期、切換學期狀態、設定目前學期 */
export default function SemestersPage() {
  const { data, error, isPending } = useApiQuery<Semester[]>("/api/admin/semesters");
  // 新增學期表單的學年與學期
  const [year, setYear] = useState("115");
  const [term, setTerm] = useState("2");
  const invalidate = useInvalidate();

  /** 修改學期（狀態或目前學期），成功後顯示 msg；msg 只供 onSuccess 使用，不會送到後端 */
  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: object; msg: string }) =>
      api(`/api/admin/semesters/${id}`, { method: "PATCH", json: body }),
    onSuccess: (_, { msg }) => {
      toast.success(msg);
      // 學期狀態與「目前學期」決定能否加退選、登分，以及各頁預設顯示的學期，影響範圍廣，全部失效
      invalidate();   // 不傳路徑 = 全部查詢失效：畫面上使用中的立即重抓，其餘等下次用到時才重抓
    },
    onError: (e) => toast.error(e.message),
  });

  /** 新增學期；學期代碼由後端組成，重複時後端回 409 */
  const create = useMutation({
    mutationFn: () =>
      api("/api/admin/semesters", { method: "POST", json: { acad_year: Number(year), term: Number(term) } }),
    onSuccess: () => {
      toast.success("已新增學期");
      invalidate("/api/admin/semesters", "/api/semesters");
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <>
      <PageHeader
        title="學期管理"
        description="規劃中、選課中可開課；選課中才可加退選；上課中才可登錄成績"
      >
        <Input className="w-20" value={year} onChange={(e) => setYear(e.target.value)} aria-label="學年" />
        <span className="text-sm text-muted-foreground">學年度第</span>
        <Select value={term} onValueChange={setTerm}>
          <SelectTrigger className="w-16">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="1">1</SelectItem>
            <SelectItem value="2">2</SelectItem>
            <SelectItem value="3">3</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-sm text-muted-foreground">學期</span>
        <Button onClick={() => create.mutate()} disabled={create.isPending}>
          {/* + 的 icon */}
          <Plus />
          新增
        </Button>
      </PageHeader>
      <Card>
        <CardContent className="p-0">
          {isPending ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error.message} />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>學期</TableHead>
                  <TableHead className="text-right">開班數</TableHead>
                  <TableHead>狀態</TableHead>
                  <TableHead className="text-right">目前學期</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.map((s) => (
                  <TableRow key={s.semester_id}>
                    <TableCell className="font-medium">
                      {semesterLabel(s.semester_id)}
                      <span className="ml-2 font-mono text-xs text-muted-foreground">{s.semester_id}</span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{s.section_count ?? 0}</TableCell>
                    <TableCell>
                      {/* 受控元件：選取後立即送出；後端拒絕時（例如已有其他學期為選課中）value 仍是伺服器的值，選單自動回到原狀態 */}
                      <Select
                        value={s.status}
                        onValueChange={(v) =>
                          patch.mutate({
                            id: s.semester_id,
                            body: { status: v },
                            msg: `狀態已改為「${SEMESTER_STATUS[v]}」`,
                          })
                        }
                      >
                        <SelectTrigger size="sm" className="w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {Object.entries(SEMESTER_STATUS).map(([k, v]) => (
                            <SelectItem key={k} value={k}>
                              {v}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-right">
                      {s.is_current ? (
                        <Badge>目前學期</Badge>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={patch.isPending}
                          onClick={() =>
                            patch.mutate({ id: s.semester_id, body: { is_current: true }, msg: "已切換目前學期" })
                          }
                        >
                          設為目前
                        </Button>
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
