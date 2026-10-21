import { HistorySections } from "@/components/history-sections";

/**
 * 教師的歷年開課紀錄（畫面與學生共用）。
 * 本檔是 Server Component，只負責渲染 Client Component 的 HistorySections
 * 路由放在 /teacher 底下，是因為 proxy.ts 以路徑前綴判斷角色。
 */
export default function TeacherHistoryPage() {
  return <HistorySections />;
}
