# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概要

輕量化教務管理系統（管理員／教師／學生三種角色），由兩個獨立服務組成，使用 MySQL 8 資料庫。資料夾結構參照使用者的 `筆記\前端後端系統\practice\todo-app`。

| 目錄 | 技術 | Port | 職責 |
| --- | --- | --- | --- |
| `web/` | Next.js 16 + React 19 + Tailwind + shadcn/ui | 3000 | 畫面；`next.config.ts` 將 `/api/*` 轉發到 api；`proxy.ts` 負責頁面導向 |
| `api/` | FastAPI + SQLAlchemy 2.1 + Alembic（Python 3.12） | 8000 | 認證（簽發 JWT）、管理員、開課、選課、成績、課表、歷年查詢；**擁有資料庫結構** |

文件分工（與 todo-app 相同；兩份筆記只存在使用者的電腦上，已列入 `.gitignore` 並從 git 歷史中移除，不要把它們加回版控）：

- `README.md`（根目錄、`api/`、`web/` 各一份）：怎麼啟動、資料夾在放什麼。
- `系統架構筆記.md`：現在的設計與理由。
- `演進紀錄.md`：舊寫法、改名、bug 怎麼發現與修掉。**程式碼註解只寫「現在」的邏輯**；需要記錄「原本這樣、後來改成那樣」時，寫進 `演進紀錄.md`（附 commit），不要寫在註解裡。

## 常用指令

Python 一律使用 conda 環境 `academic_system`（不使用 venv）。在 Claude 的 shell 中以 `conda run -n academic_system ...` 執行，不要依賴 `conda activate`。後端指令在 `api/` 下執行，前端指令在 `web/` 下執行。

```powershell
# --- api/ ---
conda run -n academic_system --no-capture-output python -m pytest -q
conda run -n academic_system --no-capture-output python -m pytest tests/test_enrollment.py::test_full_section_rejected
conda run -n academic_system --no-capture-output uvicorn app.main:app --reload --port 8000

conda run -n academic_system --no-capture-output alembic upgrade head
conda run -n academic_system --no-capture-output alembic revision --autogenerate -m "說明"
conda run -n academic_system --no-capture-output alembic current
conda run -n academic_system --no-capture-output python -m seed --reset   # downgrade base → upgrade head → 種子資料

# --- web/ ---
npm run dev
npm run lint
npx tsc --noEmit                  # 需先 npx next typegen 產生 LayoutProps 等全域型別
npx next build
```

環境限制：

- 路徑含中文，Node／npm 相關指令請用 PowerShell 執行（Git Bash 下部分工具無法正確解析路徑）。
- 主機只有 8 GB 記憶體，`next build` 前先停止開發伺服器。使用者的其他 Next.js 專案常佔用 port 3000，驗證時可改用 `next start --port 3100`。
- Windows PowerShell 5.1 以 cp950 讀取 `.ps1`，以 UTF-8 BOM 寫出 `>` 重導向的檔案。產生要給 Python 讀的檔案時，避免用 `>`。
- 前端改了資料夾或檔名後，`.next/dev/types` 的舊型別快取可能讓 `tsc` 報錯；那是建置快取，刪除前須先徵得使用者同意。

## 架構重點（需跨多個檔案才看得出來的部分）

### 後端分層（`api/app/`）

| 層 | 職責 | 不做的事 |
| --- | --- | --- |
| `routes/` | 宣告路徑、角色檢查依賴、呼叫 service、以 `response_model` 決定回應格式 | 不寫 SQL、不判斷業務規則 |
| `services/`（`*_service.py`） | 業務規則、交易邊界（`commit`）、稽核紀錄 | 不依賴 HTTP：錯誤一律丟出 `app/errors.py` 的業務錯誤 |
| `repositories/`（`*_repository.py`） | 查詢與新增，包含 `SELECT ... FOR UPDATE` | 不判斷業務規則、不 `commit` |
| `schemas/`（`*_schema.py`） | Pydantic 請求與回應模型，依領域分檔；共用基底在 `schemas/base.py` | — |
| `middleware/` | `require_auth`（`AdminUser`／`TeacherUser`／`StudentUser` 依賴）、`error_handler`、`rate_limit`、`security_headers` | — |

- 新增功能時依序加：schema → repository 查詢 → service 規則 → route。
- 業務錯誤（`NotFoundError`、`ConflictError`……）由 `middleware/error_handler.py` 轉成 `{ "detail": message }`。違反資料庫約束的 `DBAPIError` 依 MySQL 錯誤碼轉成 409／422。前端 `web/lib/api.ts` 依賴這個格式；錯誤訊息文字有測試在比對，不要隨意改字。
- Python 模組名稱不能有連字號，所以檔名是 `auth_schema.py`，而不是 todo-app 的 `auth-schema.ts`。後端程式碼資料夾維持 `app/`（FastAPI 慣例），不是 todo-app 的 `src/`。

### 請求路由與認證

- 瀏覽器只對 `localhost:3000` 發請求，`web/next.config.ts` 將所有 `/api/*` 轉發到 FastAPI（`API_URL`），因此 cookie 同源、不需 CORS。這點和 todo-app（瀏覽器直接呼叫 api）不同，是刻意保留的架構差異。
- `POST /api/auth/login` 簽發 JWT（HS256），存在 httpOnly cookie `access_token`。以下兩處的 `JWT_SECRET`、issuer `academic-affairs-system`、cookie 名稱必須一致：
  - `api/app/config.py` 與 `api/app/session.py`（`api/.env`）
  - `web/lib/session.ts`（`web/.env.local`）
- JWT payload：`sub`（user_id）、`username`、`role`、`name`、`teacher_id`、`student_id`。**刻意不放 `can_open_section` 與學籍狀態**：權限可能隨時被收回，必須每次查資料庫。帳號是否停用（`is_active`）同理，由 `require_auth.get_current_user` 在每個需登入的請求查詢，停用後舊 JWT 立即回 401。
- 前端 `lib/api.ts` 收到 401 時先呼叫 `/api/auth/logout` 清除 cookie 再導向 `/login`：被停用帳號的 JWT 仍通過 `proxy.ts` 驗證，若不清 cookie 會在登入頁與角色首頁之間無限導向。
- `web/proxy.ts` 只負責頁面導向，不是安全邊界；權限一律由後端檢查。
- 密碼以 `bcrypt` 雜湊。bcrypt 5.x 對超過 72 bytes 的輸入會拋出例外，因此密碼上限以 bytes 驗證（`schemas/auth_schema.py` 的 `Password`）。
- 登入限流存在單一 process 的記憶體中；只信任來自 loopback（Next.js rewrites）的 `X-Forwarded-For`。

### 資料庫結構（修改資料表時最容易出錯）

- **唯一來源是 `api/app/models.py`**。改表流程：改 models → `alembic revision --autogenerate` → 檢查產生的檔案 → `alembic upgrade head`。不要手寫 DDL，也不要呼叫 `create_all()`。
- **autogenerate 不會偵測 CHECK 約束與 View 的變更**：
  - CHECK 約束定義在 models 的 `__table_args__`。修改後要在 migration 裡手動加上 `op.drop_constraint`／`op.create_check_constraint`。
  - View（`v_section_detail`、`v_student_transcript`）以 `op.execute("CREATE VIEW ...")` 寫在 migration 中；ORM 對應類別帶 `info={"is_view": True}`，autogenerate 會略過。
- 約束與索引名稱沿用 `<表>_<欄位>_key／_idx／_fkey` 的格式，與既有資料庫一致，不要改名。
- `app/migration_support.py`：Windows MySQL（`lower_case_table_names=1`）反射回來的表名是小寫，此模組在比對時把表名換回 PascalCase。偵測查詢必須包在自己的 `connection.begin()` 中；若讓 autobegin 留下開啟的交易，Alembic 會視為外部交易而不 commit，`alembic_version` 的寫入會被 rollback。
- `alembic.ini` 必須維持純 ASCII（Windows 上 Alembic 以 cp950 讀取它）；說明文字寫在 `migrations/env.py`。
- 連線字串只從 `api/.env` 的 `DATABASE_URL` 讀取，可用同名環境變數臨時覆寫（例如對其他資料庫執行 `alembic upgrade`）。
- 表名 PascalCase、欄位 snake_case。Windows 的 MySQL 表名不分大小寫，Linux 會區分，所以 SQL 一律照 models 的大小寫寫。
- `SectionSchedule.semester_id` 是刻意的冗餘欄位：以複合 FK `(section_id, semester_id)` 綁定 Section，讓 UNIQUE `uq_room_timeslot` 在資料庫層防止同學期教室重複借用。
- 修改 `CurriculumField` 這類「整批取代」的子集合時，只刪除不再需要的、只新增新的。若全部清空再加回，同名資料會在同一次 flush 中先 INSERT 後 DELETE，觸發主鍵重複（參考 `services/course_service.py` 的 `update_course`）。

### 業務規則

- 學期狀態決定可做的操作（檢查在 `services/section_service.py` 與 `services/enrollment_service.py`）：
  - 開課：`Planning`／`Enrolling`
  - 加退選：`Enrolling`
  - 登分：`InProgress`／`Finished`
- 「目前學期」由 `Semester.is_current` 決定，全表只能有一筆為 true（`semester_service.update_semester` 在同一交易內維護）。
- 「有效選課」= status 為 `Selected` 或 `Manual`（`models.ACTIVE_ENROLLMENT`）。人數、課表、成績單只計算這兩種。`Registered`、`NotSelected` 是為未來「登記＋抽籤」預留的狀態。
- **選課併發控制**（`services/enrollment_service.py`）：
  - 依「學生列 → 班級列」的固定順序鎖定（`student_repository.lock` → `section_repository.lock`），避免 Deadlock。鎖定順序只由 service 決定，不要在 repository 裡合併或調換。
  - 名額必須在持有班級鎖時計算。
  - 連線隔離等級設為 READ COMMITTED（`app/db.py`）：RR 的快照可能早於取得鎖的時間點而超收，不要改回 RR。
- 停開班級會刪除其 `SectionSchedule` 以釋放教室，因為 UNIQUE 約束不分班級狀態。
- 權限切換與成績修改都必須在同一個交易內寫入稽核表（`TeacherPermissionLog`、`ScoreChangeLog`）。

### 種子資料與測試

- `python -m seed`（`api/seed/__main__.py`）會逐句執行 `seed/seed.sql`，再以 bcrypt 建立帳號：帳號為 `admin`／教師代碼／學號，密碼為 `.env` 的 `SEED_PASSWORD`。seed.sql 以「行尾分號」切分敘述，字串內不可出現分號或 `--`。
- 種子學期：`1131`、`1132`、`1141`、`1142` 為已結束的歷史學期，`1151` 為目前學期（選課中），`1152` 為下學期（規劃中，無選課資料；section 33 為停開班級）。section 16（演算法，上限 3、已選 2）用來展示額滿；section 12 與 14 在「五 4」衝堂。測試與展示都依賴這些資料。
- 測試直接連 `.env` 設定的開發資料庫，新增測試時要維持隔離原則，不可留下資料：
  - 選課與開課測試只在測試學期 `9991` 中建立與刪除資料（`tests/conftest.py`）。
  - 管理員測試在 `finally` 中還原它改動的資料。
  - `conftest.py` 的 `client_as(username, role=...)` 以 `app/session.py` 的 `create_token` 簽發 cookie，不必每次都走登入流程。

### 前端（`web/`）

- 不使用 `src/`；路徑別名 `@/*` 指向 `web/` 根目錄（`@/lib/api`、`@/types`、`@/components/...`）。
- **頁面專屬的元件放在頁面旁**，以 `export default` 匯出、用相對路徑 import（例如 `admin/users/create-user-dialog.tsx`、`student/timetable/timetable-grid.tsx`）；跨頁共用的才放 `web/components/`。
- Next.js 16：`middleware` 已更名為 `proxy`；`cookies()` 為非同步。`web/AGENTS.md` 要求先閱讀 `node_modules/next/dist/docs/` 的對應文件再寫程式。
- 頁面多為 Client Component，以 `useApi()`（`lib/api.ts`）讀取資料；角色外框 `AppShell` 是 Server Component。`types.ts` 的型別需與 `api/app/schemas/` 的回應模型保持一致。
- ESLint 啟用 React 19 的 `react-hooks/set-state-in-effect`：不要在 effect 內同步呼叫 setState，改用從狀態推導值的寫法（參考 `useApi` 與 `section-settings.tsx` 的 `capacityEdit`）。
- shadcn 元件從 `"cn"` 套件匯入 `cn`（shadcn 官方套件，取代 clsx + tailwind-merge）；`components.json` 的別名指向 `@/components`。
