"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export interface NavItem {
  href: string;
  label: string;
}

/** 頂部導覽列（Client Component：需要 usePathname 判斷目前所在頁面） */
export function NavLinks({ items }: { items: NavItem[] }) {
  const pathname = usePathname();
  // 從符合目前網址的項目中，選擇 href 最長（最精確）的一個。
  // 例如 pathname 是 /student/timetable 時，/student 與 /student/timetable 都符合；
  // 最後選擇 /student/timetable，因此只標示「我的課表」，不會連「加退選」一起標示。
  const active = items
    .filter((i) => pathname === i.href || pathname.startsWith(`${i.href}/`))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <nav className="flex items-center gap-1 overflow-x-auto text-sm">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn(
            "rounded-md px-3 py-1.5 whitespace-nowrap transition-colors hover:bg-muted",
            active === item.href ? "bg-muted font-medium text-foreground" : "text-muted-foreground",
          )}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
