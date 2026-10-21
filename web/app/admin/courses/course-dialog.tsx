"use client";

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, SECTION_VIEWS, useInvalidate } from "@/lib/api";
import type { AdminCourse } from "@/types";

// 表單狀態一律存字串（與 <input> 的值一致），送出時才轉成 API 需要的型別
type FormState = {
  course_no: string;
  course_name: string;
  course_type: "Required" | "Elective";
  credit: string;
  fields: string; // 多個領域以分隔符號串成一個字串
};

const EMPTY: FormState = { course_no: "", course_name: "", course_type: "Elective", credit: "3", fields: "" };

/** 新增／編輯課程的對話框；course 為 null 時是新增模式 */
export default function CourseDialog({
  course,
  onClose,
  onSaved,
}: {
  course: AdminCourse | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  // 初始值只在元件掛載時使用一次；父元件在關閉時卸載本元件，因此每次開啟都會重新帶入
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

  const invalidate = useInvalidate();
  const save = useMutation({
    mutationFn: (body: object) =>
      // 課號只在新增時送出；編輯時課號不可修改
      course
        ? api(`/api/admin/courses/${course.course_no}`, { method: "PATCH", json: body })
        : api("/api/admin/courses", { method: "POST", json: { ...body, course_no: form.course_no } }),
    onSuccess: () => {
      toast.success("課程已儲存");
      // 課名、學分、領域會出現在課程選單、領域選單與所有班級列表中
      invalidate("/api/admin/courses", "/api/courses", "/api/fields", ...SECTION_VIEWS);
      onSaved();
    },
    onError: (err) => toast.error(err.message),
  });

  function submit(e: React.SubmitEvent<HTMLFormElement>) {
    e.preventDefault();
    save.mutate({
      course_name: form.course_name,
      course_type: form.course_type,
      credit: Number(form.credit),
      // 接受頓號、半形／全形逗號與空白作為分隔
      fields: form.fields
        .split(/[、,，\s]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    });
  }

  return (
    // 對話框是否顯示由父元件決定（是否渲染本元件），這裡固定 open，關閉時通知父元件
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
            <Button type="submit" disabled={save.isPending}>
              儲存
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
