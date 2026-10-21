// 列舉值 → 中文顯示文字（鍵值需與後端 api/app/models.py 的列舉一致）
// 本模組沒有伺服器端依賴，伺服器端（proxy.ts）與瀏覽器端（Client Component）都可以匯入
import type { Role } from "@/types";

// 索引 0 = 星期一；後端的 weekday 從 1 開始，取用時要減 1
export const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"] as const;

export const SEMESTER_STATUS: Record<string, string> = {
  Planning: "規劃中",
  Enrolling: "選課中",
  InProgress: "上課中",
  Finished: "已結束",
};

export const ENROLLMENT_STATUS: Record<string, string> = {
  Registered: "已登記",
  Selected: "中選",
  Manual: "人工加選",
  NotSelected: "落選",
  Withdrawn: "已退選",
};

export const COURSE_TYPE: Record<string, string> = {
  Required: "必修",
  Elective: "選修",
};

export const STUDENT_STATUS: Record<string, string> = {
  Enrolled: "在學",
  Suspended: "休學",
  Dropped: "退學",
};

export const ROLE_LABEL: Record<string, string> = {
  Admin: "管理員",
  Teacher: "教師",
  Student: "學生",
};

/**
 * 各角色登入後的首頁，同時也是該角色所有頁面的路徑前綴。
 * proxy.ts 以它導向與檢查角色區域，登入頁以它決定登入後的去處。
 */
export const ROLE_HOME: Record<Role, string> = {
  Admin: "/admin",
  Teacher: "/teacher",
  Student: "/student",
};

/** '1132' → '113 學年度第 2 學期' */
export function semesterLabel(id: string): string {
  return `${id.slice(0, 3)} 學年度第 ${id.slice(3)} 學期`;
}

/** '一5@O-313,一6@O-313' → '一5,6 (O-313)' 的精簡顯示 */
export function compactSchedule(text: string | null): string {
  if (!text) return "—";
  // 以「星期 + 教室」分組，把同組的節次收集在一起；Map 保留插入順序，輸出順序與原字串一致
  const groups = new Map<string, number[]>();
  for (const part of text.split(",")) {
    const [slot, room] = part.split("@");
    // slot 第一個字是星期（一～日），其後是節次數字
    const key = `${slot[0]}|${room}`;
    groups.set(key, [...(groups.get(key) ?? []), Number(slot.slice(1))]);
  }
  return [...groups]
    .map(([key, periods]) => {
      const [day, room] = key.split("|");
      return `${day}${periods.join(",")}（${room}）`;
    })
    .join("、");
}
