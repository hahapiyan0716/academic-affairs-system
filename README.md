# 輕量化教務管理系統（Academic Affairs System）

以既有的 3NF 資料庫設計為基礎，延伸出具備「管理員／教師／學生」三種角色的教務系統。

| 層 | 技術 | 職責 |
| --- | --- | --- |
| 前端 | Next.js 16（React 19）+ Tailwind CSS + shadcn/ui | 三種角色的操作介面、路由保護 |
| 認證與管理 | Express 5 + Prisma 7（TypeScript） | 登入、帳號、開課權限、課程庫、學期；**擁有資料庫 Schema 主控權** |
| 教務核心 | FastAPI + SQLAlchemy 2.1（Python） | 開課、先搶先贏選課、成績、課表、歷年查詢 |
| 資料庫 | MySQL 8.0 | 15 張業務資料表、2 個 View、7 條 CHECK 約束 |

完整的架構說明、設計理由與實作細節請見 **[docs/系統架構筆記.md](docs/系統架構筆記.md)**。

## 目錄結構

```text
├─ 3nf_table.sql / insert_data.sql   原始 3NF 設計（保留作為參考，不會被執行）
├─ apps/web/                         Next.js 前端（port 3000）
├─ services/auth-admin/              Express 服務（port 4000），含 prisma/ schema 與 migrations
├─ services/academic/                FastAPI 服務（port 8000）
├─ database/schema.generated.sql     由 Prisma 匯出的完整建表 SQL（閱讀用）
├─ database/sql-examples.sql         SQL 操作範例
└─ docs/系統架構筆記.md
```

## 本機啟動

需求：Node.js 20+、Python 3.12+、MySQL 8.0。

### 1. 建立資料庫與專用帳號（以 root 執行一次）

```sql
CREATE DATABASE academic_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE academic_db_shadow CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'academic_app'@'localhost' IDENTIFIED BY '自訂密碼';
GRANT ALL PRIVILEGES ON academic_db.* TO 'academic_app'@'localhost';
GRANT ALL PRIVILEGES ON academic_db_shadow.* TO 'academic_app'@'localhost';
FLUSH PRIVILEGES;
```

### 2. 設定環境變數

將三個 `.env.example` 複製為實際設定檔並填值（三者的 `JWT_SECRET` 必須相同）：

| 範本 | 複製為 |
| --- | --- |
| `services/auth-admin/.env.example` | `services/auth-admin/.env` |
| `services/academic/.env.example` | `services/academic/.env` |
| `apps/web/.env.example` | `apps/web/.env.local` |

產生 JWT 密鑰：`node -e "console.log(require('crypto').randomBytes(48).toString('base64url'))"`

### 3. 安裝依賴並建立資料表

```bash
# Express + Prisma
cd services/auth-admin
npm install
npx prisma generate
npm run db:reset          # 套用 migration 並寫入種子資料

# FastAPI
cd ../academic
python -m venv .venv
.venv\Scripts\activate    # macOS / Linux：source .venv/bin/activate
pip install -r requirements.txt

# Next.js
cd ../../apps/web
npm install
```

### 4. 啟動三個服務（各開一個終端機）

```bash
cd services/auth-admin && npm run dev
cd services/academic   && .venv\Scripts\uvicorn app.main:app --reload --port 8000
cd apps/web            && npm run dev
```

開啟 <http://localhost:3000>。FastAPI 的 Swagger 文件在 <http://localhost:3000/api/docs>（登入後可直接試打 API）。

### 種子帳號

所有帳號的密碼皆為 `services/auth-admin/.env` 中的 `SEED_PASSWORD`。

| 身分 | 帳號 | 說明 |
| --- | --- | --- |
| 管理員 | `admin` | |
| 教師 | `T001`～`T008` | `T001` 岳飛、`T003` 劉邦具開課權限 |
| 學生 | `S001`～`S022` | `S002`、`S008` 休學，`S010` 退學（不可選課） |

學期：`1132`、`1141` 為已結束的歷史學期，`1151` 為目前學期（選課中）。

## 測試

```bash
cd services/auth-admin && npm test                    # vitest + supertest，9 項
cd services/academic   && .venv\Scripts\python -m pytest  # pytest，17 項（含併發搶課）
```

測試連線至 `.env` 設定的資料庫：Express 測試會還原其變更；FastAPI 測試只在專用的測試學期 `9991` 中建立與刪除資料。
