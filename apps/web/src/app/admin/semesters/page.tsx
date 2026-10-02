"use client";

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
import { api, useApi } from "@/lib/api";
import { SEMESTER_STATUS, semesterLabel } from "@/lib/labels";
import type { Semester } from "@/lib/types";

export default function SemestersPage() {
  const { data, error, loading, reload } = useApi<Semester[]>("/api/admin/semesters");
  const [year, setYear] = useState("115");
  const [term, setTerm] = useState("2");

  async function patch(id: string, body: object, msg: string) {
    try {
      await api(`/api/admin/semesters/${id}`, { method: "PATCH", json: body });
      toast.success(msg);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function create() {
    try {
      await api("/api/admin/semesters", {
        method: "POST",
        json: { acad_year: Number(year), term: Number(term) },
      });
      toast.success("已新增學期");
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader
        title="學期管理"
        description="規劃中、選課中可開課；選課中才可加退選；上課中、已結束才可登錄成績"
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
        <Button onClick={create}>
          <Plus />
          新增
        </Button>
      </PageHeader>
      <Card>
        <CardContent className="p-0">
          {loading && !data ? (
            <LoadingState />
          ) : error ? (
            <div className="p-4">
              <ErrorState message={error} />
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
                    <TableCell className="text-right tabular-nums">{s._count?.sections ?? 0}</TableCell>
                    <TableCell>
                      <Select
                        value={s.status}
                        onValueChange={(v) =>
                          patch(s.semester_id, { status: v }, `狀態已改為「${SEMESTER_STATUS[v]}」`)
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
                          onClick={() => patch(s.semester_id, { is_current: true }, "已切換目前學期")}
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
