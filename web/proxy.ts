import { NextResponse, type NextRequest } from "next/server";
import { ROLE_HOME } from "@/lib/labels";
import { AUTH_COOKIE, verifySession } from "@/lib/session";

/**
 * 路由保護（Next.js 16 起 middleware 更名為 proxy）
 *   - 未登入：導向 /login
 *   - 已登入但進入其他角色的頁面：導回自己的首頁
 *   - 已登入卻進入 /login：導回自己的首頁
 *
 * 執行時機：符合 config.matcher 的請求進入 Next.js 之後、頁面渲染之前；不屬於 React 元件生命週期。
 * 直接輸入網址或重新整理、<Link>／router.push() 切換頁面、正式版中 <Link> 進入視窗時的 prefetch，
 * 以及 redirect 後瀏覽器請求的新網址（若仍符合 matcher）都會觸發。
 * 只做「角色區域」層級的導向，不是安全邊界：verifySession() 不查資料庫，不知道帳號是否已停用；
 * 細部權限（例如教師只能管理自己的班、開課權限）一律由 FastAPI 檢查。
 */
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const user = await verifySession(request.cookies.get(AUTH_COOKIE)?.value);

  // 已登入卻進入 /login，導回自己的首頁
  if (pathname === "/login") {
    return user ? NextResponse.redirect(new URL(ROLE_HOME[user.role], request.url)) : NextResponse.next();    // NextResponse.next() 讓 /login 頁面繼續渲染
  }

  // 未登入，導向 /login
  if (!user) {
    const url = new URL("/login", request.url);
    // 記下原本要去的頁面，登入後可導回
    if (pathname !== "/") url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // 已登入但進入其他角色的頁面，導回自己的首頁
  // 角色首頁即該角色所有頁面的路徑前綴（/admin、/teacher、/student）
  // 例如 Student 進入 /student/timetable 放行；進入 /admin/users 或 / 則導回 /student
  const home = ROLE_HOME[user.role];
  if (pathname === "/" || !pathname.startsWith(home)) {
    return NextResponse.redirect(new URL(home, request.url));
  }
  return NextResponse.next();
}

export const config = {
  // 只保護頁面；/api 由後端自行驗證，靜態資源不經過 proxy
  // matcher 只比對 pathname：/admin/users?page=2 仍符合 /admin/:path*；:path* 可為零段，所以 /admin 本身也符合
  matcher: ["/", "/login", "/admin/:path*", "/teacher/:path*", "/student/:path*"],
};
