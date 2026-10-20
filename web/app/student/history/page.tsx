import { HistorySections } from "@/components/history-sections";

/**
 * 學生的歷年開課紀錄（畫面與教師共用）。
 * 本檔是 Server Component，只負責渲染 Client Component 的 HistorySections；路由放在 /student 底下，是因為 proxy.ts 以路徑前綴判斷角色。
 */
export default function StudentHistoryPage() {
  return <HistorySections />;
}
