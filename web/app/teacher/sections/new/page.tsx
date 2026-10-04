"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingState, PageHeader } from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, useApi } from "@/lib/api";
import { semesterLabel } from "@/lib/labels";
import type { CourseBrief, Room, Section, Semester } from "@/types";
import SlotGrid from "./slot-grid";

export default function NewSectionPage() {
  const router = useRouter();
  const { data: me, loading } = useApi<{ teacher_id: string; can_open_section: boolean }>("/api/teacher/me");
  const { data: semesters } = useApi<Semester[]>("/api/semesters");
  const { data: courses } = useApi<CourseBrief[]>("/api/courses");
  const { data: rooms } = useApi<Room[]>("/api/rooms");
  const { data: teachers } = useApi<{ teacher_id: string; teacher_name: string }[]>("/api/teachers");

  const openable = useMemo(
    () => semesters?.filter((s) => s.status === "Planning" || s.status === "Enrolling") ?? [],
    [semesters],
  );

  const [semesterId, setSemesterId] = useState("");
  const [courseNo, setCourseNo] = useState("");
  const [sectionCode, setSectionCode] = useState("01");
  const [capacity, setCapacity] = useState("50");
  const [room, setRoom] = useState("");
  const [coTeachers, setCoTeachers] = useState<string[]>([]);
  const [slots, setSlots] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);

  if (loading) return <LoadingState />;
  if (!me?.can_open_section) {
    return (
      <>
        <PageHeader title="新增開課" />
        <ErrorState message="您目前沒有開課權限，請洽管理員授權。" />
      </>
    );
  }

  function toggleSlot(key: string) {
    setSlots((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!semesterId || !courseNo || !room) return toast.error("請選擇學期、課程與教室");
    if (slots.size === 0) return toast.error("請至少選擇一個上課時段");
    setSubmitting(true);
    try {
      const section = await api<Section>("/api/teacher/sections", {
        method: "POST",
        json: {
          course_no: courseNo,
          semester_id: semesterId,
          section_code: sectionCode,
          capacity: Number(capacity),
          co_teacher_ids: coTeachers,
          slots: [...slots].map((k) => {
            const [weekday, period] = k.split("-").map(Number);
            return { weekday, period, room_code: room };
          }),
        },
      });
      toast.success(`已開設 ${section.course_name}（${section.course_no}-${section.section_code}）`);
      router.push("/teacher");
    } catch (err) {
      toast.error((err as Error).message);
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="新增開課"
        description="系統會檢查：開課權限、學期是否開放、教師衝堂、教室是否已被同時段使用"
      />
      <form onSubmit={submit} className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">班級資訊</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="grid gap-1.5">
              <Label>學期</Label>
              <Select value={semesterId} onValueChange={setSemesterId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="選擇可開課的學期" />
                </SelectTrigger>
                <SelectContent>
                  {openable.map((s) => (
                    <SelectItem key={s.semester_id} value={s.semester_id}>
                      {semesterLabel(s.semester_id)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {semesters && openable.length === 0 && (
                <p className="text-xs text-destructive">目前沒有開放開課的學期</p>
              )}
            </div>
            <div className="grid gap-1.5">
              <Label>課程</Label>
              <Select value={courseNo} onValueChange={setCourseNo}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="從課程庫選擇" />
                </SelectTrigger>
                <SelectContent>
                  {courses?.map((c) => (
                    <SelectItem key={c.course_no} value={c.course_no}>
                      {c.course_no} {c.course_name}（{c.credit} 學分）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1.5">
                <Label>班別</Label>
                <Input value={sectionCode} onChange={(e) => setSectionCode(e.target.value)} maxLength={2} />
              </div>
              <div className="grid gap-1.5">
                <Label>人數上限</Label>
                <Input
                  type="number"
                  min={1}
                  max={500}
                  value={capacity}
                  onChange={(e) => setCapacity(e.target.value)}
                />
              </div>
            </div>
            <div className="grid gap-1.5">
              <Label>教室</Label>
              <Select value={room} onValueChange={setRoom}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="選擇教室" />
                </SelectTrigger>
                <SelectContent>
                  {rooms?.map((r) => (
                    <SelectItem key={r.room_code} value={r.room_code}>
                      {r.building_name} {r.room_code}
                      {r.seat_capacity ? `（${r.seat_capacity} 席）` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-1.5">
              <Label>合授教師（選填）</Label>
              <div className="grid grid-cols-2 gap-2 rounded-md border p-3">
                {teachers
                  ?.filter((t) => t.teacher_id !== me.teacher_id)
                  .map((t) => (
                    <label key={t.teacher_id} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={coTeachers.includes(t.teacher_id)}
                        onCheckedChange={(c) =>
                          setCoTeachers((prev) =>
                            c ? [...prev, t.teacher_id] : prev.filter((id) => id !== t.teacher_id),
                          )
                        }
                      />
                      {t.teacher_name}
                    </label>
                  ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">上課時段</CardTitle>
            <CardDescription>點選格子選擇時段（已選 {slots.size} 節）</CardDescription>
          </CardHeader>
          <CardContent>
            <SlotGrid selected={slots} onToggle={toggleSlot} />
            <Button type="submit" className="mt-4 w-full" disabled={submitting}>
              建立開課班級
            </Button>
          </CardContent>
        </Card>
      </form>
    </>
  );
}
