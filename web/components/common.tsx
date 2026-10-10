"use client";

import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useApi } from "@/lib/api";
import { ENROLLMENT_STATUS, SEMESTER_STATUS, semesterLabel } from "@/lib/labels";
import type { Semester } from "@/types";

// 各頁面共用的小型 UI 元件

/** 頁面標題列；children 會放在右側（篩選器、按鈕等） */
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

/** 資料載入中的提示 */
export function LoadingState() {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" />
      載入中…
    </div>
  );
}

/** 錯誤訊息框（通常顯示後端回傳的 detail） */
export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
      {message}
    </div>
  );
}

/** 查無資料時的提示 */
export function EmptyState({ message }: { message: string }) {
  return <div className="py-12 text-center text-sm text-muted-foreground">{message}</div>;
}

// 學期狀態 → Badge 樣式：「選課中」用實心強調，其餘較淡
const SEMESTER_BADGE: Record<string, "default" | "secondary" | "outline"> = {
  Planning: "outline",
  Enrolling: "default",
  InProgress: "secondary",
  Finished: "outline",
};

/** 學期狀態標籤；遇到未定義的狀態時直接顯示原值 */
export function SemesterStatusBadge({ status }: { status: string }) {
  return <Badge variant={SEMESTER_BADGE[status] ?? "outline"}>{SEMESTER_STATUS[status] ?? status}</Badge>;
}

/** 選課狀態標籤；有效選課（中選、人工加選）用實心強調 */
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
    // Radix Select 不允許空字串作為選項值，因此「全部學期」在元件內部以 "__all" 代表
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

/** 課程領域下拉選單；第一個選項「全部領域」的值為空字串 */
export function FieldSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { data } = useApi<string[]>("/api/fields");
  return (
    <Select value={value || "__all"} onValueChange={(v) => onChange(v === "__all" ? "" : v)}>
      <SelectTrigger className="w-36">
        <SelectValue placeholder="課程領域" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__all">全部領域</SelectItem>
        {data?.map((f) => (
          <SelectItem key={f} value={f}>
            {f}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
