"use client";

import { useEffect, useState } from "react";

/**
 * 延遲更新的值：value 停止變動 delay 毫秒後才回傳新值。
 * 用於搜尋框——輸入框綁定即時的 value，查詢條件改用延遲後的值，打字期間不會每個字都發請求。
 */
export function useDebouncedValue<T>(value: T, delay = 500): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    // setState 在計時器回呼中非同步執行，不違反 react-hooks/set-state-in-effect
    // 計時器結束後才更新 debounced，觸發使用者定義的 effect（例如發送 API 請求）
    // value 在計時器結束前又變動時，取消上一個計時器重新計算
    // setTimeout 會回傳計時器的 ID，clearTimeout 用這個 ID 取消計時器
    // setDebounced(value) 會觸發元件重新渲染，useEffect 會在下一個渲染後執行，形成「延遲」的效果
    const timer = setTimeout(() => setDebounced(value), delay);
    // value 在計時結束前又變動時，取消上一個計時器重新計算
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}
