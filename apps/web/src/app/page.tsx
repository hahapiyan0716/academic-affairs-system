import { redirect } from "next/navigation";

// 實際導向由 proxy.ts 依登入狀態處理；此頁僅作為保險
export default function Home() {
  redirect("/login");
}
