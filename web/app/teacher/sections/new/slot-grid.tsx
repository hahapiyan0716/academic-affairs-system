"use client";

import { WEEKDAYS } from "@/lib/labels";
import { cn } from "@/lib/utils";

// 畫面提供第 1–10 節、星期一到日；後端允許的節次範圍較大（1–14 節，見 section_schema.py 的 TimeSlotIn）
const PERIODS = Array.from({ length: 10 }, (_, i) => i + 1);
const DAYS = [1, 2, 3, 4, 5, 6, 7];

/** 週 × 節次的時段選擇格；key 格式為「星期-節次」，例如 "4-5" */
export default function SlotGrid({ selected, onToggle }: { selected: Set<string>; onToggle: (key: string) => void }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          {/* <tr> 是表格的列，<th> 是表格的標題欄位 */}
          <tr>
            {/* <th> 是表格的標題欄位：左上角為「節」，其後為星期一到日 */}
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
              {/* <td> 是表格的資料欄位；每列第一格顯示節次 */}
              <td className="p-1 text-center text-muted-foreground tabular-nums">{p}</td>
              {DAYS.map((d) => {
                const key = `${d}-${p}`;
                const on = selected.has(key);
                return (
                  <td key={key} className="p-0.5">
                    {/* 本元件放在開課表單內；<button> 預設 type 為 submit，必須指定 type="button"，點格子才不會送出表單 */}
                    <button
                      type="button"
                      onClick={() => onToggle(key)}
                      aria-pressed={on}     // aria-pressed 讓螢幕閱讀器知道格子是否被選取
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
