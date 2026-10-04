"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { AdminCourse } from "@/types";

type FormState = {
  course_no: string;
  course_name: string;
  course_type: "Required" | "Elective";
  credit: string;
  fields: string;
};

const EMPTY: FormState = { course_no: "", course_name: "", course_type: "Elective", credit: "3", fields: "" };

export default function CourseDialog({
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
          fields: course.fields.join("、"),
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
