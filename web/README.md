# web：Next.js 前端

教務系統的畫面：管理員、教師、學生三種角色的頁面。**資料全部透過 api 取得**，web 沒有資料庫連線。整個專案怎麼啟動見上一層的 `README.md`。

## 啟動

```powershell
Set-Location web
npm install                         # 第一次才需要
Copy-Item .env.example .env.local   # 第一次才需要：JWT_SECRET 要和 api\.env 相同
npm run dev                         # http://localhost:3000
```

api 必須同時開著（另一個終端機），否則登入與所有資料都會失敗。

## 和 api 的關係

- `next.config.ts` 的 rewrites 把 `/api/*` 轉發到 api（預設 `http://localhost:8000`，可在 `.env.local` 以 `API_URL` 修改）。瀏覽器只看到 `localhost:3000` 一個來源，因此 cookie 自動帶上、不需要 CORS。
- `proxy.ts` 以 `JWT_SECRET` 驗證 cookie，**只負責頁面導向**：未登入導向 `/login`、走錯角色導回自己的首頁。真正的權限由 api 檢查。
- `lib/api.ts` 的 `api()` 與 `useApi()` 是呼叫 API 的唯一入口；錯誤訊息取自回應的 `detail`。
- `types.ts` 的型別對應 api 的回應模型（`api\app\schemas\`），兩邊要一起改。

## 資料夾

```text
app\
├─ login\                登入
├─ admin\                管理員：總覽、帳號（users\create-user-dialog.tsx）、開課權限、課程庫（courses\course-dialog.tsx）、學期
├─ teacher\              教師：我的開課、新增開課（sections\new\slot-grid.tsx）、名單與登分（sections\[id]\section-settings.tsx）
├─ student\              學生：加退選、課表（timetable\timetable-grid.tsx）、歷年成績、歷年開課
├─ layout.tsx            全站版面
└─ globals.css
components\              跨頁共用：AppShell（各角色外框）、導覽列、登出、common（載入中、錯誤、徽章、學期選單）、ui\（shadcn）
lib\                     api.ts（呼叫 API）、session.ts（驗證 JWT）、labels.ts（列舉 → 中文）、utils.ts
proxy.ts                 路由保護（Next.js 16 起 middleware 更名為 proxy）
types.ts                 與 api 回應對應的型別
```

頁面專屬的對話框、表格區塊放在頁面旁的獨立檔案；跨頁共用的才放 `components\`。

## 指令

| 指令 | 作用 |
| --- | --- |
| `npm run dev` | 開發伺服器 |
| `npm run lint` | ESLint |
| `npx next typegen` → `npx tsc --noEmit` | 型別檢查（先產生 `LayoutProps` 等全域型別） |
| `npx next build` | 正式建置（記憶體不足時先停掉開發伺服器） |

Next.js 16 與過去版本有不少差異，寫程式前先查 `node_modules\next\dist\docs\` 的對應文件（見 `AGENTS.md`）。
