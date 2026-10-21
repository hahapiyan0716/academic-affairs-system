/**
 * 前端呼叫後端 API 的唯一入口：api() 負責 fetch 與錯誤轉換，useApiQuery／useInvalidate 包裝 TanStack Query 的讀取與快取失效。
 */
// 含 Hook 且會用到 window，只能在 Client Component 中使用
"use client";

import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

/** 整頁導向站內路徑（登入／登出需要讓 proxy 與 Server Component 以新的 cookie 重新判斷） */
// 「強制整頁跳轉」的共用函式，主要用於登入或登出後切換頁面。
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
    * 例如：帳號被管理員停用，密碼在其他裝置被修改，JWT 已過期或無效，後端回傳 401 Unauthorized
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
  const { json, ...rest } = init ?? {};   // rest 是 RequestInit，json 是要序列化的物件
  const res = await fetch(path, {
    ...rest,
    headers: json !== undefined ? { "Content-Type": "application/json", ...rest.headers } : rest.headers,
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    // 同源請求才帶 cookie；所有 API 都經 rewrites 走同源，JWT cookie 會自動附上
    // credentials 是 fetch 的選項，意思是「同源請求才帶 cookie」；而跨源請求（例如前端呼叫第三方 API）不帶 cookie，避免洩漏 JWT
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
      if (typeof body?.detail === "string")
        detail = body.detail;
      else if (Array.isArray(body?.detail))
        detail = body.detail.map((d: { msg: string }) => d.msg).join("；");
    } catch {
      /* 回應不是 JSON 時沿用預設訊息 */
    }
    throw new ApiError(res.status, detail);
  }
  // 204 No Content（登出、修改密碼）沒有回應內容，呼叫 res.json() 會拋出例外
  // 所以用三元運算子回傳 undefined；其他狀況回傳 JSON 物件
  return (res.status === 204 ? undefined : await res.json()) as T;
}

/** 查詢參數：空字串與 undefined 視為「不篩選」，不會出現在網址與 query key 中 */
export type QueryParams = Record<string, string | undefined>;

/**
 * 以 TanStack Query 讀取 GET API。
 * query key 為 [path, 參數]，寫入後可用 useInvalidate(path) 讓同一路徑「所有參數組合」的快取一起失效。
 * path 為 null 時不發請求（用於「等其他資料載入後才知道要查什麼」的情況）。
 */
export function useApiQuery<T>(path: string | null, params?: QueryParams) {
  // 濾掉空參數並同時用於網址與 query key：{ q: "" } 與 {} 視為同一個查詢，共用快取
  const filtered = Object.fromEntries(Object.entries(params ?? {}).filter(([, v]) => v)) as Record<string, string>;
  const search = new URLSearchParams(filtered).toString();    // 轉成「q=xxx&teacher=yyy」的字串，空字串會被濾掉
  return useQuery({
    queryKey: [path, filtered],   // 快取識別碼
    // 實際發送請求的函式；path 為 null 時不會執行，signal 用於取消請求
    // signal：元件卸載或 query key 改變時取消進行中的請求；path! 安全，因為 path 為 null 時 enabled 為 false，不會執行
    queryFn: ({ signal }) => api<T>(search ? `${path}?${search}` : path!, { signal }),
    enabled: path !== null,   // 控制是否允許執行查詢。
    // 換篩選條件時保留上一份結果直到新資料回來，畫面不會閃回「載入中」
    placeholderData: keepPreviousData,
  });
}

/**
 * 資料來自 v_section_detail／v_student_transcript 的查詢（含課名、領域、人數、成績）。
 * 課程、班級、選課或成績變動時，這些畫面都可能需要更新
 */
export const SECTION_VIEWS = [
  "/api/sections",
  "/api/history/sections",
  "/api/teacher/sections",
  "/api/me/timetable",
  "/api/me/transcript",
];

/**
 * 回傳一個函式：讓指定路徑的查詢快取失效，畫面上正在使用的查詢會立即重新請求。
 * 寫入成功後呼叫，例如加退選後 invalidate("/api/sections", "/api/me/timetable")。
 * 不傳路徑時讓全部查詢失效，用於影響範圍很廣的變更（例如學期狀態）。
 * 後端資料已經改變，原本的快取可能過期，請把相關查詢標記為失效，並重新取得畫面目前正在使用的資料。
 */
export function useInvalidate() {
  // 取得 Provider 已經提供的 QueryClient (也就是在 layout 中提供的)，不會再建立一個。
  const client = useQueryClient();
  return useCallback(
    (...paths: string[]) =>
      paths.length === 0
        ? client.invalidateQueries()    // 不傳路徑時讓全部查詢失效
        // 有傳入路徑時只讓指定路徑的查詢失效，避免不必要的重新請求
        // queryKey: [p] 是前綴比對，符合所有以 p 開頭的 key，即同一路徑的所有參數組合
        : Promise.all(paths.map((p) => client.invalidateQueries({ queryKey: [p] }))),
    // useCallback 讓回傳的函式在 client 不變時維持同一個參考，可安全放進其他 Hook 的依賴陣列
    [client],
  );
}
