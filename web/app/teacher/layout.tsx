import { AppShell } from "@/components/app-shell";

// 教師頁面的導覽列項目
const NAV = [
  { href: "/teacher", label: "我的開課" },
  { href: "/teacher/sections/new", label: "新增開課" },
  { href: "/teacher/history", label: "歷年開課" },
];

/** /teacher 底下所有頁面的外框；AppShell 會確認登入者是教師 */
export default function TeacherLayout({ children }: LayoutProps<"/teacher">) {
  return (
    <AppShell role="Teacher" nav={NAV}>
      {children}
    </AppShell>
  );
}
