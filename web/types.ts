// 前後端共用的資料型別（對應 FastAPI 的回應格式，見 api/app/schemas/）
// 後端的 Decimal 欄位（成績、平均）經 Pydantic 序列化後是字串，因此這裡宣告為 string

export type Role = "Admin" | "Teacher" | "Student";

/** JWT payload 中的登入者（後端 app/session.py 的 CurrentUser.to_public） */
export interface SessionUser {
  sub: string;
  username: string;
  role: Role;
  name: string;
  teacher_id: string | null;
  student_id: string | null;
}

export type SemesterStatus = "Planning" | "Enrolling" | "InProgress" | "Finished";

export interface Semester {
  semester_id: string;
  acad_year: number;
  term: number;
  status: SemesterStatus;
  is_current: boolean;
  /** 只有管理員 API（/api/admin/semesters、/api/admin/stats）會回傳 */
  section_count?: number;
}

/** 開課班級明細（後端 SectionOut，資料來自 v_section_detail） */
export interface Section {
  section_id: number;
  semester_id: string;
  course_no: string;
  course_name: string;
  course_type: "Required" | "Elective";
  credit: number;
  section_code: string;
  capacity: number;
  status: "Open" | "Cancelled";
  teacher_names: string | null; // 多位教師以「、」分隔
  schedule_text: string | null; // 例如 "一5@O313,一6@O313"，顯示時用 compactSchedule 轉換
  enrolled_count: number;
}

/** 選課瀏覽的班級；my_status、conflict 只有學生查詢時才有意義 */
export interface BrowseSection extends Section {
  my_status: string | null;
  conflict: boolean;
}

/** 歷年開課查詢的班級 */
export interface HistorySection extends Section {
  avg_score: string | null;
}

export interface Room {
  room_code: string;
  building_name: string;
  seat_capacity: number | null;
}

/** 啟用中課程的摘要（教師開課時的下拉選單） */
export interface CourseBrief {
  course_no: string;
  course_name: string;
  course_type: string;
  credit: number;
}

/** 課表中的一格（某星期某節） */
export interface TimetableSlot {
  weekday: number; // 1 = 星期一 … 7 = 星期日
  period: number;
  room_code: string;
  section_id: number;
  course_no: string;
  course_name: string;
}

/** 學生某學期的課表 */
export interface Timetable {
  semester_id: string;
  total_credits: number;
  sections: Section[];
  slots: TimetableSlot[];
}

export interface TranscriptRow {
  semester_id: string;
  section_id: number;
  course_no: string;
  course_name: string;
  course_type: string;
  credit: number;
  status: string;
  score: string | null;
  passed: number | null; // 1 = 及格、0 = 不及格、null = 尚未登分
}

/** 學生歷年成績單 */
export interface Transcript {
  semesters: {
    semester_id: string;
    rows: TranscriptRow[];
    credits_taken: number; // 修習學分
    credits_earned: number; // 實得學分（只計及格）
    average: string | null; // 學分加權平均
  }[];
  total_credits_earned: number;
  overall_average: string | null;
}

export interface RosterEntry {
  student_id: string;
  student_name: string;
  dept_name: string;
  degree: number; // 0 = 大學部、1 = 碩博班
  status: string;
  score: string | null;
  feedback_rank: number | null;
}

/** 教師查看的班級修課名單 */
export interface Roster {
  section: Section;
  semester_status: SemesterStatus;
  gradable: boolean; // 學期狀態是否允許登分
  students: RosterEntry[];
}

/** 管理員帳號列表的一筆；teacher／student 依角色只有一個有值 */
export interface AdminUser {
  user_id: number;
  username: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  last_login_at: string | null;
  teacher: { teacher_id: string; teacher_name: string; can_open_section: boolean } | null;
  student: { student_id: string; student_name: string; dept_id: string; status: string } | null;
}

/** 管理員的教師列表：含登入帳號與最近一次權限異動 */
export interface AdminTeacher {
  teacher_id: string;
  teacher_name: string;
  dept_id: string | null;
  can_open_section: boolean;
  user: { username: string; is_active: boolean } | null;
  latest_log: { log_id: number; changed_at: string; granted: boolean; admin: { username: string } } | null;
}

/** 管理員的課程列表：含領域與歷年開班次數 */
export interface AdminCourse {
  course_no: string;
  course_name: string;
  course_type: "Required" | "Elective";
  credit: number;
  dept_id: string | null;
  dept_name: string | null;
  is_active: boolean;
  fields: string[];
  section_count: number;
}

export interface Department {
  dept_id: string;
  dept_name: string;
}
