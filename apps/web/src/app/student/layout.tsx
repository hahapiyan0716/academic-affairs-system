import { AppShell } from "@/components/app-shell";

const NAV = [
  { href: "/student", label: "加退選" },
  { href: "/student/timetable", label: "我的課表" },
  { href: "/student/transcript", label: "歷年成績" },
  { href: "/student/history", label: "歷年開課" },
];

export default function StudentLayout({ children }: LayoutProps<"/student">) {
  return (
    <AppShell role="Student" nav={NAV}>
      {children}
    </AppShell>
  );
}
