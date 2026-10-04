// 前後端共用的資料型別（對應 FastAPI 的回應格式，見 api/app/schemas/）

export type Role = "Admin" | "Teacher" | "Student";

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
  teacher_names: string | null;
  schedule_text: string | null;
  enrolled_count: number;
}

export interface BrowseSection extends Section {
  my_status: string | null;
  conflict: boolean;
}

export interface HistorySection extends Section {
  avg_score: string | null;
}

export interface Room {
  room_code: string;
  building_name: string;
  seat_capacity: number | null;
}

export interface CourseBrief {
  course_no: string;
  course_name: string;
  course_type: string;
  credit: number;
}

export interface TimetableSlot {
  weekday: number;
  period: number;
  room_code: string;
  section_id: number;
  course_no: string;
  course_name: string;
}

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
  passed: number | null;
}

export interface Transcript {
  semesters: {
    semester_id: string;
    rows: TranscriptRow[];
    credits_taken: number;
    credits_earned: number;
    average: string | null;
  }[];
  total_credits_earned: number;
  overall_average: string | null;
}

export interface RosterEntry {
  student_id: string;
  student_name: string;
  dept_name: string;
  degree: number;
  status: string;
  score: string | null;
  feedback_rank: number | null;
}

export interface Roster {
  section: Section;
  semester_status: SemesterStatus;
  gradable: boolean;
  students: RosterEntry[];
}

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

export interface AdminTeacher {
  teacher_id: string;
  teacher_name: string;
  dept_id: string | null;
  can_open_section: boolean;
  user: { username: string; is_active: boolean } | null;
  latest_log: { log_id: number; changed_at: string; granted: boolean; admin: { username: string } } | null;
}

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
