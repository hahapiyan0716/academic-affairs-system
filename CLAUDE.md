# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概要

輕量化教務管理系統（管理員／教師／學生三種角色），由三個獨立服務組成，共用一個 MySQL 8 資料庫。完整的設計理由見 `docs/系統架構筆記.md`；本機安裝流程見 `README.md`。

| 目錄 | 技術 | Port | 職責 |
| --- | --- | --- | --- |
| `apps/web` | Next.js 16 + React 19 + Tailwind + shadcn/ui | 3000 | UI；`next.config.ts` rewrites 轉發 API；`src/proxy.ts` 路由保護 |
| `services/auth-admin` | Express 5 + Prisma 7（TypeScript，ESM，以 `tsx` 執行） | 4000 | 登入（簽發 JWT）、`/api/admin/*`；**擁有資料庫 Schema** |
| `services/academic` | FastAPI + SQLAlchemy 2.1（Python 3.12） | 8000 | 開課、選課、成績、課表、歷年查詢 |

根目錄的 `3nf_table.sql`、`insert_data.sql` 是使用者原始的 3NF 設計，只作參考，不會被執行，也不要修改。

## 常用指令

Python 一律使用 conda 環境 `academic_system`（不使用 venv）。在 Claude 的 shell 中以 `conda run -n academic_system ...` 執行，不要依賴 `conda activate`。

```powershell
# --- services/auth-admin ---
npm run dev                       # tsx watch src/server.ts
npm run typecheck                 # tsc --noEmit
npm test                          # vitest run（整合測試，連 .env 的資料庫）
npx vitest run -t "不可停用自己"   # 單一測試（依名稱）
npx prisma generate               # 產生 Prisma Client 到 src/generated/prisma（已 gitignore，clone 後必跑）
npm run db:migrate                # prisma migrate dev
npm run db:reset                  # 清空 → 重跑 migration → seed
npm run db:export-sql             # 匯出完整 DDL 到 database/schema.generated.sql

# --- services/academic ---
conda run -n academic_system --no-capture-output python -m pytest -q
conda run -n academic_system --no-capture-output python -m pytest tests/test_enrollment.py::test_full_section_rejected
conda run -n academic_system --no-capture-output uvicorn app.main:app --reload --port 8000

# --- apps/web ---
npm run dev
npm run lint
npx tsc --noEmit                  # 需先 npx next typegen 產生 LayoutProps 等全域型別
npx next build
```

環境限制：

- 路徑含中文。**在 Git Bash 下 vitest 會找不到測試檔（顯示 no tests）**，Node／npm 相關指令請用 PowerShell 執行。
- 主機只有 8 GB 記憶體。三個開發伺服器同時運行時，`next build` 或 `tsc` 可能因記憶體不足而中止，建置前先停止開發伺服器。

## 架構重點（需跨多個檔案才看得出來的部分）

### API 路由與認證

- 瀏覽器只對 `localhost:3000` 發請求。`apps/web/next.config.ts` 的 rewrites 將 `/api/auth/*`、`/api/admin/*` 轉發到 Express，其餘 `/api/*` 轉發到 FastAPI。新增 API 時，路徑前綴決定請求會被送到哪個服務。
- Express 簽發 JWT（HS256），存在 httpOnly cookie `access_token`。FastAPI 與 Next.js 的 proxy 只負責驗證。以下三處的 `JWT_SECRET`、issuer `academic-affairs-system`、cookie 名稱必須一致：
  - `services/auth-admin/src/env.ts`
  - `services/academic/app/config.py`
  - `apps/web/src/lib/session.ts`
- JWT payload：`sub`（user_id）、`username`、`role`、`name`、`teacher_id`、`student_id`。**刻意不放 `can_open_section` 與學籍狀態**：權限可能隨時被收回，必須每次查資料庫。
- `proxy.ts` 只負責頁面導向，不是安全邊界。權限一律由後端檢查（Express `requireRole`、FastAPI `TeacherUser`／`StudentUser` 依賴）。
- 兩個後端的錯誤格式統一為 `{ "detail": string }`，前端的 `src/lib/api.ts` 依賴這個格式。

### Schema 主控權（修改資料表時最容易出錯）

- **唯一來源是 `services/auth-admin/prisma/schema.prisma`**，由 Prisma Migrate 產生 migration。不要手寫 DDL，也不要在 SQLAlchemy 呼叫 `create_all()`。
- Prisma 無法表達的 CHECK 約束與 View（`v_section_detail`、`v_student_transcript`）手寫在 `prisma/migrations/*_init/migration.sql` 末尾。新增此類物件時，用 `prisma migrate dev --create-only` 產生 migration 後再附加 SQL。
- **改了 `schema.prisma` 後，必須手動同步 `services/academic/app/models.py`**（欄位、ENUM 值、View 欄位）。ENUM 值兩邊必須完全相同。Prisma 的 `@updatedAt` 對 SQLAlchemy 無效，SQLAlchemy 端要用 `onupdate`。
- 表名 PascalCase、欄位 snake_case，Prisma、SQLAlchemy 與手寫 SQL 全部一致。Windows 的 MySQL 表名不分大小寫，Linux 會區分，所以一律照 schema 的大小寫寫。
- `SectionSchedule.semester_id` 是刻意的冗餘欄位：以複合 FK `(section_id, semester_id)` 綁定 Section，目的是讓 UNIQUE `uq_room_timeslot` 在資料庫層防止同學期教室重複借用。
- Prisma 7 使用 driver adapter（`@prisma/adapter-mariadb`），連線設定集中在 `src/db-config.ts`（只在連 localhost 時開啟 `allowPublicKeyRetrieval`，以應付 MySQL 8 的 caching_sha2_password）。CLI 設定在 `prisma.config.ts`。
- `prisma` 與 `@prisma/client` 鎖定 7.10.0（npm 的 latest 標籤指向 8.0 RC）。`package.json` 的 `overrides` 用來修補間接依賴的漏洞，不要移除。

### 業務規則

- 學期狀態決定可做的操作（檢查在 `app/services/sections.py` 與 `enrollment.py`）：
  - 開課：`Planning`／`Enrolling`
  - 加退選：`Enrolling`
  - 登分：`InProgress`／`Finished`
- 「目前學期」由 `Semester.is_current` 決定，全表只能有一筆為 true（Express 在交易中維護）。
- 「有效選課」= status 為 `Selected` 或 `Manual`（`models.ACTIVE_ENROLLMENT`）。人數、課表、成績單都只計算這兩種。`Registered`、`NotSelected` 是為未來「登記＋抽籤」預留的狀態。
- **選課併發控制**（`app/services/enrollment.py`）：
  - 依「學生列 → 班級列」的固定順序 `SELECT ... FOR UPDATE`，避免 Deadlock。
  - 名額必須在持有班級鎖時計算。
  - 連線隔離等級設為 READ COMMITTED（`app/db.py`）：RR 的快照可能早於取得鎖的時間點而超收，不要改回 RR。
- 停開班級會刪除其 `SectionSchedule` 以釋放教室，因為 UNIQUE 約束不分班級狀態。
- 權限切換與成績修改都必須在同一個交易內寫入稽核表（`TeacherPermissionLog`、`ScoreChangeLog`）。

### 種子資料與測試

- `prisma/seed.ts` 會逐句執行 `prisma/seed.sql`，再以 bcrypt 建立帳號（帳號 = `admin`／教師代碼／學號，密碼 = `.env` 的 `SEED_PASSWORD`）。seed.sql 以「行尾分號」切分敘述，字串內不可出現分號或 `--`。
- 種子學期：`1132`、`1141` 為已結束的歷史學期，`1151` 為目前學期（選課中）。section 16（演算法，上限 3、已選 2）用來展示額滿；section 12 與 14 在「五 4」衝堂。測試與展示都依賴這些資料。
- 兩邊的測試都直接連 `.env` 設定的開發資料庫：
  - pytest 只在測試學期 `9991` 中建立與刪除資料（`tests/conftest.py`）。
  - vitest 在 `finally` 中還原它改動的資料。
  - 新增測試時要維持這個隔離原則，不可留下資料。

### 前端

- Next.js 16：`middleware` 已更名為 `proxy`；`cookies()` 為非同步。`apps/web/AGENTS.md` 要求先閱讀 `node_modules/next/dist/docs/` 的對應文件再寫程式。
- 頁面多為 Client Component，以 `useApi()`（`src/lib/api.ts`）讀取資料；角色外框 `AppShell` 是 Server Component。
- ESLint 啟用 React 19 的 `react-hooks/set-state-in-effect`：不要在 effect 內同步呼叫 setState，改用從狀態推導值的寫法（參考 `useApi` 與 `teacher/sections/[id]/page.tsx` 的 `edits` 模式）。
- shadcn 元件從 `"cn"` 套件匯入 `cn`（shadcn 官方套件，取代 clsx + tailwind-merge）。
