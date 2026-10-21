import { HistorySections } from "@/components/history-sections";

/**
 * 學生的歷年開課紀錄（畫面與教師共用）。
 * 本檔是 Server Component，只負責渲染 Client Component 的 HistorySections
    * 也就是說，這個 page.tsx 只是建立 /student/history 這個網址入口；搜尋、API 查詢、篩選和表格顯示等真正功能，都交給瀏覽器端的 HistorySections 元件處理。
 * 本頁面的路由放在 /student 底下，是因為 proxy.ts 以路徑前綴判斷角色。
    * 產生 /student/history 網址
    * 套用 app/student/layout.tsx
    * 顯示學生版導覽列
    * 由 AppShell role="Student" 再次確認角色
 */
export default function StudentHistoryPage() {
  return <HistorySections />;
}
