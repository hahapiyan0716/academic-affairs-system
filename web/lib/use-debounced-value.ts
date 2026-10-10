"use client";

import { useEffect, useState } from "react";

/**
 * 延遲更新的值：value 停止變動 delay 毫秒後才回傳新值。
 * 用於搜尋框——輸入框綁定即時的 value，查詢條件改用延遲後的值，打字期間不會每個字都發請求。
 */
export function useDebouncedValue<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    // setState 在計時器回呼中非同步執行，不違反 react-hooks/set-state-in-effect
    const timer = setTimeout(() => setDebounced(value), delay);
    // value 在計時結束前又變動時，取消上一個計時器重新計算
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
