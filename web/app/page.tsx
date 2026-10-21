import { redirect } from "next/navigation";

// app/ 是 Next.js App Router 寫死的路由根目錄（啟動時先找 web/app，沒有才找 web/src/app，名稱不可設定）。
// 資料夾決定網址、只有 page.tsx／layout.tsx 等特殊檔名有作用，因此本檔 app/page.tsx 對應網址 /；
// components/、lib/ 不在 app/ 內，不會成為路由。詳見系統架構筆記 9.1。
//
// 首頁 /：實際導向由 proxy.ts 依登入狀態處理（未登入 → /login，已登入 → 自己的角色首頁），正常情況下不會渲染此頁
// 此頁僅作為保險：proxy 沒有攔截時（例如 matcher 被修改）一律導向 /login，已登入者再由 proxy 從 /login 導回角色首頁
// 這是 Server Component；redirect() 會丟出 Next.js 專用的例外中斷渲染並轉成導向回應，因此函式不需回傳 JSX
export default function Home() {
  redirect("/login");
}
