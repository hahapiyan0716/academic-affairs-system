"use client";

import { WEEKDAYS } from "@/lib/labels";
import { cn } from "@/lib/utils";

// 畫面提供第 1–10 節、星期一到六；後端允許的範圍較大（1–14 節、星期一到日）
const PERIODS = Array.from({ length: 10 }, (_, i) => i + 1);
const DAYS = [1, 2, 3, 4, 5, 6];

/** 週 × 節次的時段選擇格；key 格式為「星期-節次」，例如 "4-5" */
export default function SlotGrid({ selected, onToggle }: { selected: Set<string>; onToggle: (key: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="w-10 p-1 text-muted-foreground">節</th>
            {DAYS.map((d) => (
              <th key={d} className="p-1 font-medium">
                {WEEKDAYS[d - 1]}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PERIODS.map((p) => (
            <tr key={p}>
              <td className="p-1 text-center text-muted-foreground tabular-nums">{p}</td>
              {DAYS.map((d) => {
                const key = `${d}-${p}`;
                const on = selected.has(key);
                return (
                  <td key={key} className="p-0.5">
                    <button
                      type="button"
                      onClick={() => onToggle(key)}
                      aria-pressed={on}
                      aria-label={`星期${WEEKDAYS[d - 1]}第 ${p} 節`}
                      className={cn(
                        "h-8 w-full rounded border transition-colors",
                        on ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted",
                      )}
                    >
                      {on ? "✓" : ""}
                    </button>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
