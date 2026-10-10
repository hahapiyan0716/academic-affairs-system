import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE, ROLE_HOME, verifySession } from "@/lib/session";

/**
 * 路由保護（Next.js 16 起 middleware 更名為 proxy）
 *   - 未登入：導向 /login
 *   - 已登入但進入其他角色的頁面：導回自己的首頁
 *   - 已登入卻進入 /login：導回自己的首頁
 */
export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const user = await verifySession(request.cookies.get(AUTH_COOKIE)?.value);

  if (pathname === "/login") {
    return user ? NextResponse.redirect(new URL(ROLE_HOME[user.role], request.url)) : NextResponse.next();
  }

  if (!user) {
    const url = new URL("/login", request.url);
    // 記下原本要去的頁面，登入後可導回
    if (pathname !== "/") url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  // 角色首頁即該角色所有頁面的路徑前綴（/admin、/teacher、/student）
  const home = ROLE_HOME[user.role];
  if (pathname === "/" || !pathname.startsWith(home)) {
    return NextResponse.redirect(new URL(home, request.url));
  }
  return NextResponse.next();
}

export const config = {
  // 只保護頁面；/api 由後端自行驗證，靜態資源不經過 proxy
  matcher: ["/", "/login", "/admin/:path*", "/teacher/:path*", "/student/:path*"],
};
