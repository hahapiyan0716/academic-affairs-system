"use client";

import { WEEKDAYS } from "@/lib/labels";
import type { Timetable, TimetableSlot } from "@/types";

const DAYS = [1, 2, 3, 4, 5, 6];
// 依課號給予固定色系，同一門課在課表上顏色一致
const PALETTE = [
  "bg-sky-100 text-sky-900 border-sky-200",
  "bg-emerald-100 text-emerald-900 border-emerald-200",
  "bg-amber-100 text-amber-900 border-amber-200",
  "bg-violet-100 text-violet-900 border-violet-200",
  "bg-rose-100 text-rose-900 border-rose-200",
  "bg-teal-100 text-teal-900 border-teal-200",
];

/** 週課表格狀圖：至少顯示到第 8 節，有更晚的課就延伸 */
export default function TimetableGrid({ timetable }: { timetable: Timetable }) {
  const grid = new Map<string, TimetableSlot>();
  timetable.slots.forEach((s) => grid.set(`${s.weekday}-${s.period}`, s));
  const maxPeriod = Math.max(8, ...timetable.slots.map((s) => s.period));
  const colorOf = (sectionId: number) =>
    PALETTE[timetable.sections.findIndex((s) => s.section_id === sectionId) % PALETTE.length];

  return (
    <table className="w-full min-w-[640px] table-fixed border-collapse text-sm">
      <thead>
        <tr>
          <th className="w-12 border-b p-2 text-muted-foreground">節</th>
          {DAYS.map((d) => (
            <th key={d} className="border-b p-2 font-medium">
              星期{WEEKDAYS[d - 1]}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {Array.from({ length: maxPeriod }, (_, i) => i + 1).map((p) => (
          <tr key={p}>
            <td className="border-b p-2 text-center text-muted-foreground tabular-nums">{p}</td>
            {DAYS.map((d) => {
              const slot = grid.get(`${d}-${p}`);
              return (
                <td key={d} className="h-14 border-b p-1">
                  {slot && (
                    <div className={`h-full rounded-md border px-2 py-1 ${colorOf(slot.section_id)}`}>
                      <div className="truncate font-medium">{slot.course_name}</div>
                      <div className="truncate text-xs opacity-80">{slot.room_code}</div>
                    </div>
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
