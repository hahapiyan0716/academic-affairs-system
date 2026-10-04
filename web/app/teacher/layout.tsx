import { AppShell } from "@/components/app-shell";

const NAV = [
  { href: "/teacher", label: "我的開課" },
  { href: "/teacher/sections/new", label: "新增開課" },
];

export default function TeacherLayout({ children }: LayoutProps<"/teacher">) {
  return (
    <AppShell role="Teacher" nav={NAV}>
      {children}
    </AppShell>
  );
}
