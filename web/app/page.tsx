import { redirect } from "next/navigation";

// 首頁 /：實際導向由 proxy.ts 依登入狀態處理（未登入 → /login，已登入 → 自己的角色首頁），正常情況下不會渲染此頁
// 此頁僅作為保險：proxy 沒有攔截時（例如 matcher 被修改）一律導向 /login，已登入者再由 proxy 從 /login 導回角色首頁
// 這是 Server Component；redirect() 會丟出 Next.js 專用的例外中斷渲染並轉成導向回應，因此函式不需回傳 JSX
export default function Home() {
  redirect("/login");
}
