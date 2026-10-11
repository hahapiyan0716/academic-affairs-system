"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ApiError } from "@/lib/api";

/**
 * TanStack Query 的快取容器。快取只存在記憶體；登入與登出都會整頁重新載入（hardNavigate），
 * QueryClient 隨之重建，因此不會殘留前一位使用者的資料。
 */
export function QueryProvider({ children }: { children: React.ReactNode }) {
  // 以 useState 建立：每個瀏覽器分頁只有一個 QueryClient，重新渲染時不會被重建而清空快取
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // staleTime 維持預設 0：有快取時先顯示、同時在背景重新查詢。
            // 選課人數等資料必須即時，不設定「多久內視為新鮮」
            // 4xx 是業務錯誤（權限不足、找不到），重試也不會成功；只對網路或 5xx 錯誤重試一次
            retry: (failureCount, error) => !(error instanceof ApiError && error.status < 500) && failureCount < 1,
          },
        },
      }),
  );
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
