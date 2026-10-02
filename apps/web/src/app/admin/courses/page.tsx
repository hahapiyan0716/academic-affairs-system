"use client";

import { useState } from "react";
import { Pencil, Plus } from "lucide-react";
import { toast } from "sonner";
import { ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, useApi } from "@/lib/api";
import { COURSE_TYPE } from "@/lib/labels";
import type { AdminCourse } from "@/lib/types";

type FormState = {
  course_no: string;
  course_name: string;
  course_type: "Required" | "Elective";
  credit: string;
  fields: string;
};

const EMPTY: FormState = { course_no: "", course_name: "", course_type: "Elective", credit: "3", fields: "" };

export default function CoursesPage() {
  const { data, error, loading, reload } = useApi<AdminCourse[]>("/api/admin/courses");
  const [editing, setEditing] = useState<AdminCourse | "new" | null>(null);

  async function toggleActive(c: AdminCourse) {
    try {
      await api(`/api/admin/courses/${c.course_no}`, { method: "PATCH", json: { is_active: !c.is_active } });
      toast.success(`${c.course_name} 已${c.is_active ? "停用" : "啟用"}`);
      reload();
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  return (
    <>
      <PageHeader title="課程庫" description="維護課程代碼、課名與學分；停用的課程不能再開新班，但歷年紀錄會保留">
        <Button onClick={() => setEditing("new")}>
          <Plus />
          新增課程
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
                  <TableHead>課程代碼</TableHead>
                  <TableHead>課名</TableHead>
                  <TableHead>類型</TableHead>
                  <TableHead className="text-right">學分</TableHead>
                  <TableHead>領域</TableHead>
                  <TableHead className="text-right">歷年開班</TableHead>
                  <TableHead className="text-right">啟用</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.map((c) => (
                  <TableRow key={c.course_no} className={c.is_active ? "" : "opacity-60"}>
                    <TableCell className="font-mono">{c.course_no}</TableCell>
                    <TableCell className="font-medium">{c.course_name}</TableCell>
                    <TableCell>
                      <Badge variant={c.course_type === "Required" ? "default" : "secondary"}>
                        {COURSE_TYPE[c.course_type]}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{c.credit}</TableCell>
                    <TableCell className="space-x-1">
                      {c.fields.map((f) => (
                        <Badge key={f.field_name} variant="outline">
                          {f.field_name}
                        </Badge>
                      ))}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{c._count.sections}</TableCell>
                    <TableCell className="text-right">
                      <Switch checked={c.is_active} onCheckedChange={() => toggleActive(c)} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon-sm" onClick={() => setEditing(c)} aria-label="編輯">
                        <Pencil />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
      {editing && (
        <CourseDialog
          course={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </>
  );
}

function CourseDialog({
  course,
  onClose,
  onSaved,
}: {
  course: AdminCourse | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<FormState>(
    course
      ? {
          course_no: course.course_no,
          course_name: course.course_name,
          course_type: course.course_type,
          credit: String(course.credit),
          fields: course.fields.map((f) => f.field_name).join("、"),
        }
      : EMPTY,
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const body = {
      course_name: form.course_name,
      course_type: form.course_type,
      credit: Number(form.credit),
      fields: form.fields
        .split(/[、,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      if (course) {
        await api(`/api/admin/courses/${course.course_no}`, { method: "PATCH", json: body });
      } else {
        await api("/api/admin/courses", { method: "POST", json: { ...body, course_no: form.course_no } });
      }
      toast.success("課程已儲存");
      onSaved();
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{course ? `編輯課程 ${course.course_no}` : "新增課程"}</DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="grid gap-3">
          <div className="grid grid-cols-3 gap-3">
            <div className="grid gap-1.5">
              <Label>課程代碼</Label>
              <Input
                value={form.course_no}
                onChange={(e) => setForm({ ...form, course_no: e.target.value })}
                disabled={!!course}
                required
                minLength={5}
                maxLength={5}
                placeholder="A0008"
              />
            </div>
            <div className="col-span-2 grid gap-1.5">
              <Label>課名</Label>
              <Input
                value={form.course_name}
                onChange={(e) => setForm({ ...form, course_name: e.target.value })}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="grid gap-1.5">
              <Label>類型</Label>
              <Select
                value={form.course_type}
                onValueChange={(v) => setForm({ ...form, course_type: v as FormState["course_type"] })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Required">必修</SelectItem>
                  <SelectItem value="Elective">選修</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>學分</Label>
              <Input
                type="number"
                min={0}
                max={10}
                value={form.credit}
                onChange={(e) => setForm({ ...form, credit: e.target.value })}
                required
              />
            </div>
          </div>
          <div className="grid gap-1.5">
            <Label>課程領域（以頓號或逗號分隔）</Label>
            <Input
              value={form.fields}
              onChange={(e) => setForm({ ...form, fields: e.target.value })}
              placeholder="基礎知識、人工智慧"
            />
          </div>
          <DialogFooter>
            <Button type="submit">儲存</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
