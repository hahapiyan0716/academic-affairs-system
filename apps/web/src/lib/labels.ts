// 列舉值 → 中文顯示文字

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

/** '1132' → '113 學年度第 2 學期' */
export function semesterLabel(id: string): string {
  return `${id.slice(0, 3)} 學年度第 ${id.slice(3)} 學期`;
}

/** '一5@O313,一6@O313' → '一5,6 (O313)' 的精簡顯示 */
export function compactSchedule(text: string | null): string {
  if (!text) return "—";
  const groups = new Map<string, number[]>();
  for (const part of text.split(",")) {
    const [slot, room] = part.split("@");
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
