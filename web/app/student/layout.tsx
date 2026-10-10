import { AppShell } from "@/components/app-shell";

// 學生頁面的導覽列項目
const NAV = [
  { href: "/student", label: "加退選" },
  { href: "/student/timetable", label: "我的課表" },
  { href: "/student/transcript", label: "歷年成績" },
  { href: "/student/history", label: "歷年開課" },
];

/** /student 底下所有頁面的外框；AppShell 會確認登入者是學生 */
export default function StudentLayout({ children }: LayoutProps<"/student">) {
  return (
    <AppShell role="Student" nav={NAV}>
      {children}
    </AppShell>
  );
}
