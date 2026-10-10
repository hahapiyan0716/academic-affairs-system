import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { GraduationCap } from "lucide-react";
import { LogoutButton } from "@/components/logout-button";
import { NavLinks, type NavItem } from "@/components/nav-links";
import { AUTH_COOKIE, verifySession } from "@/lib/session";
import { ROLE_LABEL } from "@/lib/labels";
import type { Role } from "@/types";

/** 各角色共用的頁面外框（Server Component：在伺服器端讀取 cookie 取得登入者） */
export async function AppShell({
  role,
  nav,
  children,
}: {
  role: Role;
  nav: NavItem[];
  children: React.ReactNode;
}) {
  // Next.js 16 的 cookies() 為非同步
  const user = await verifySession((await cookies()).get(AUTH_COOKIE)?.value);
  // proxy.ts 已先擋過一次；這裡再檢查，確保取得 user 後的畫面不會以錯誤身分渲染
  if (!user || user.role !== role) redirect("/login");

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-4">
          <div className="flex items-center gap-2 font-semibold">
            <GraduationCap className="size-5 text-primary" />
            <span className="hidden sm:inline">教務管理系統</span>
          </div>
          <NavLinks items={nav} />
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span className="hidden text-muted-foreground md:inline">
              {ROLE_LABEL[user.role]}・{user.name}（{user.username}）
            </span>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
