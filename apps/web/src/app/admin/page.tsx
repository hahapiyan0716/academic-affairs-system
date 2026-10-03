"use client";

import { BookOpen, CalendarDays, KeyRound, Users } from "lucide-react";
import { ErrorState, LoadingState, PageHeader, SemesterStatusBadge } from "@/components/common";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/lib/api";
import { semesterLabel } from "@/lib/labels";
import type { Semester } from "@/lib/types";

interface Stats {
  users: number;
  teachers_with_permission: number;
  enrolled_students: number;
  active_courses: number;
  current_semester: Semester | null;
}

export default function AdminDashboard() {
  const { data, error, loading } = useApi<Stats>("/api/admin/stats");

  if (loading) return <LoadingState />;
  if (error || !data) return <ErrorState message={error ?? "無法載入資料"} />;

  const tiles = [
    { label: "系統帳號", value: data.users, icon: Users },
    { label: "在學學生", value: data.enrolled_students, icon: Users },
    { label: "具開課權限教師", value: data.teachers_with_permission, icon: KeyRound },
    { label: "啟用中課程", value: data.active_courses, icon: BookOpen },
  ];

  return (
    <>
      <PageHeader title="管理總覽" description="系統帳號、開課權限、課程庫與學期設定" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((t) => (
          <Card key={t.label}>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-2">
                <t.icon className="size-4" />
                {t.label}
              </CardDescription>
              <CardTitle className="text-3xl tabular-nums">{t.value}</CardTitle>
            </CardHeader>
          </Card>
        ))}
      </div>
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarDays className="size-4" />
            目前學期
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          {data.current_semester ? (
            <div className="flex items-center gap-3">
              <span className="font-medium">{semesterLabel(data.current_semester.semester_id)}</span>
              <SemesterStatusBadge status={data.current_semester.status} />
              <span className="text-muted-foreground">
                已開 {data.current_semester.section_count ?? 0} 個班級
              </span>
            </div>
          ) : (
            <span className="text-muted-foreground">尚未設定目前學期，請至「學期管理」設定。</span>
          )}
        </CardContent>
      </Card>
    </>
  );
}
