"use client";

import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/lib/api";
import { ENROLLMENT_STATUS, SEMESTER_STATUS, semesterLabel } from "@/lib/labels";
import type { Semester } from "@/lib/types";

export function PageHeader({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
      </div>
      {children && <div className="flex flex-wrap items-center gap-2">{children}</div>}
    </div>
  );
}

export function LoadingState() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      載入中…
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
      {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return <div className="py-12 text-center text-sm text-muted-foreground">{message}</div>;
}

const SEMESTER_BADGE: Record<string, "default" | "secondary" | "outline"> = {
  Planning: "outline",
  Enrolling: "default",
  InProgress: "secondary",
  Finished: "outline",
};

export function SemesterStatusBadge({ status }: { status: string }) {
  return <Badge variant={SEMESTER_BADGE[status] ?? "outline"}>{SEMESTER_STATUS[status] ?? status}</Badge>;
}

export function EnrollmentBadge({ status }: { status: string }) {
  const variant = status === "Selected" || status === "Manual" ? "default" : "outline";
  return <Badge variant={variant}>{ENROLLMENT_STATUS[status] ?? status}</Badge>;
}

/** 學期下拉選單；allowAll 時多一個「全部學期」選項（值為空字串） */
export function SemesterSelect({
  value,
  onChange,
  allowAll = false,
}: {
  value: string;
  onChange: (v: string) => void;
  allowAll?: boolean;
}) {
  const { data } = useApi<Semester[]>("/api/semesters");
  return (
    <Select value={value || "__all"} onValueChange={(v) => onChange(v === "__all" ? "" : v)}>
      <SelectTrigger className="w-56">
        <SelectValue placeholder="選擇學期" />
      </SelectTrigger>
      <SelectContent>
        {allowAll && <SelectItem value="__all">全部學期</SelectItem>}
        {data?.map((s) => (
          <SelectItem key={s.semester_id} value={s.semester_id}>
            {semesterLabel(s.semester_id)}
            {s.is_current ? "（目前）" : ""}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
