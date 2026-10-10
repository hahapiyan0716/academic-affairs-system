import { AppShell } from "@/components/app-shell";

// 管理員頁面的導覽列項目
const NAV = [
  { href: "/admin", label: "總覽" },
  { href: "/admin/users", label: "帳號管理" },
  { href: "/admin/teachers", label: "開課權限" },
  { href: "/admin/courses", label: "課程庫" },
  { href: "/admin/semesters", label: "學期管理" },
];

/** /admin 底下所有頁面的外框；AppShell 會確認登入者是管理員 */
export default function AdminLayout({ children }: LayoutProps<"/admin">) {
  return (
    <AppShell role="Admin" nav={NAV}>
      {children}
    </AppShell>
  );
}
