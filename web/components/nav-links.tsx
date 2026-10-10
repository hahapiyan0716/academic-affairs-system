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
  // 最長前綴者為目前所在頁（避免 /admin 與 /admin/users 同時被標示）
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
