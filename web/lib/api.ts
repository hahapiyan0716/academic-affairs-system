"use client";

import { useCallback, useEffect, useState } from "react";

/** 整頁導向站內路徑（登入／登出需要讓 proxy 與 Server Component 以新的 cookie 重新判斷） */
export function hardNavigate(path: string) {
  window.location.assign(new URL(path, window.location.origin));
}

/** API 回應非 2xx 時拋出；message 為後端的 detail，可直接顯示給使用者 */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// 同一頁面常同時發出多個請求，避免每個 401 都各自清除 cookie 與跳轉
let redirecting = false;

/**
 * 登入失效：先請後端清除 cookie，再整頁重新載入登入頁。
 * 必須先清 cookie：帳號被停用時 JWT 本身仍有效，proxy 只驗 JWT 會把使用者導回角色首頁，
 * 首頁的 API 又回 401，形成無限導向。
 */
async function redirectToLogin() {
  if (redirecting) return;
  redirecting = true;
  // 直接用 fetch 而非 api()，避免登出請求本身失敗時再次進入這裡
  await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" }).catch(() => undefined);
  hardNavigate("/login");
}

/**
 * 呼叫後端 API（同源，經 Next.js rewrites 轉發；cookie 由瀏覽器自動帶上）。
 * 後端的錯誤格式統一為 { detail: string }（見 api/app/middleware/error_handler.py）。
 * 傳入 init.json 時自動序列化為 JSON 並加上 Content-Type。
 */
export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  const res = await fetch(path, {
    ...rest,
    headers: json !== undefined ? { "Content-Type": "application/json", ...rest.headers } : rest.headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    credentials: "same-origin",
  });

  // 登入 API 本身回 401 代表「帳號或密碼錯誤」，要顯示訊息而不是導向登入頁
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/login")) {
    await redirectToLogin();
  }
  if (!res.ok) {
    let detail = `請求失敗（${res.status}）`;
    try {
      const body = await res.json();
      // 業務錯誤的 detail 是字串；FastAPI 輸入驗證失敗（422）的 detail 是錯誤清單，合併各項的 msg
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join("；");
    } catch {
      /* 回應不是 JSON 時沿用預設訊息 */
    }
    throw new ApiError(res.status, detail);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

/**
 * 簡易資料讀取 hook：回傳資料、錯誤、載入中狀態，以及重新讀取的函式。
 * path 為 null 時不發請求（用於「等其他資料載入後才知道要查什麼」的情況）。
 */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 每次 reload 加 1，讓 key 改變而觸發 effect 重新請求同一個 path
  const [version, setVersion] = useState(0);
  // 記錄「最後完成的是哪一次請求」，載入中狀態由此推導，不需在 effect 內同步 setState
  const [settledKey, setSettledKey] = useState<string | null>(null);
  const key = path === null ? null : `${path}#${version}`;

  useEffect(() => {
    if (path === null || key === null) return;
    // path 改變或元件卸載時，舊請求的結果不再寫入狀態，避免慢回應覆蓋新資料
    let cancelled = false;
    api<T>(path)
      .then((d) => {
        if (cancelled) return;
        setData(d);
        setError(null);
      })
      .catch((e: Error) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setSettledKey(key));
    return () => {
      cancelled = true;
    };
  }, [path, key]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data, error, loading: key !== null && settledKey !== key, reload };
}
