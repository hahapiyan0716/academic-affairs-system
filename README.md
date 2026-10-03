# 輕量化教務管理系統（Academic Affairs System）

以既有的 3NF 資料庫設計為基礎，延伸出具備「管理員／教師／學生」三種角色的教務系統。

| 層 | 技術 | 職責 |
| --- | --- | --- |
| 前端 | Next.js 16（React 19）+ Tailwind CSS + shadcn/ui | 三種角色的操作介面、路由保護 |
| 後端 | FastAPI + SQLAlchemy 2.1 + Alembic（Python 3.12） | 認證、管理員、開課、先搶先贏選課、成績、課表、歷年查詢；**擁有資料庫結構** |
| 資料庫 | MySQL 8.0 | 15 張業務資料表、2 個 View、7 條 CHECK 約束 |

完整的架構說明、設計理由與實作細節請見 **[docs/系統架構筆記.md](docs/系統架構筆記.md)**。

## 目錄結構

```text
├─ 3nf_table.sql / insert_data.sql   原始 3NF 設計（保留作為參考，不會被執行）
├─ apps/web/                         Next.js 前端（port 3000）
├─ services/api/                     FastAPI 後端（port 8000）
│  ├─ app/models.py                  ★ 資料庫結構的唯一來源
│  ├─ migrations/                    Alembic migration
│  └─ seed/                          種子資料（seed.sql + python -m seed）
├─ database/schema.generated.sql     由 Alembic 產生的完整建表 SQL（閱讀用）
├─ database/sql-examples.sql         SQL 操作範例
└─ docs/系統架構筆記.md
```

## 本機啟動

需求：Node.js 20+、Python 3.12（以 conda 管理環境）、MySQL 8.0。

### 1. 建立資料庫與專用帳號（以 root 執行一次）

```sql
CREATE DATABASE academic_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'academic_app'@'localhost' IDENTIFIED BY '自訂密碼';
GRANT ALL PRIVILEGES ON academic_db.* TO 'academic_app'@'localhost';
FLUSH PRIVILEGES;
```

### 2. 設定環境變數

將兩個 `.env.example` 複製為實際設定檔並填值（兩者的 `JWT_SECRET` 必須相同）：

| 範本 | 複製為 |
| --- | --- |
| `services/api/.env.example` | `services/api/.env` |
| `apps/web/.env.example` | `apps/web/.env.local` |

產生 JWT 密鑰：`python -c "import secrets; print(secrets.token_urlsafe(48))"`

### 3. 安裝依賴並建立資料表

```bash
# 後端（conda 環境）
cd services/api
conda create -n academic_system python=3.12   # 只需建立一次
conda activate academic_system
pip install -r requirements.txt               # 依賴皆來自 PyPI，因此用 pip 安裝
alembic upgrade head                          # 建立資料表與 View
python -m seed                                # 寫入種子資料

# 前端
cd ../../apps/web
npm install
```

### 4. 啟動（各開一個終端機）

```bash
cd services/api && conda activate academic_system && uvicorn app.main:app --reload --port 8000
cd apps/web     && npm run dev
```

開啟 <http://localhost:3000>。API 的 Swagger 文件在 <http://localhost:3000/api/docs>（登入後可直接試打 API）。

### 種子帳號

所有帳號的密碼皆為 `services/api/.env` 中的 `SEED_PASSWORD`。

| 身分 | 帳號 | 說明 |
| --- | --- | --- |
| 管理員 | `admin` | |
| 教師 | `T001`～`T008` | `T001` 岳飛、`T003` 劉邦具開課權限 |
| 學生 | `S001`～`S022` | `S002`、`S008` 休學，`S010` 退學（不可選課） |

學期：`1132`、`1141` 為已結束的歷史學期，`1151` 為目前學期（選課中）。

## 資料庫維護（在 services/api 下）

| 指令 | 作用 |
| --- | --- |
| `alembic upgrade head` | 套用所有尚未執行的 migration |
| `alembic revision --autogenerate -m "說明"` | 修改 `app/models.py` 後，自動產生 migration |
| `alembic current` | 查看資料庫目前的版本 |
| `python -m seed --reset` | 清空並重建資料庫、重新寫入種子資料 |
| `alembic upgrade head --sql` | 只輸出 SQL、不執行（`database/schema.generated.sql` 由此產生） |

## 測試

```bash
cd services/api && conda activate academic_system && pytest   # 35 項（含併發搶課）
```

測試連線至 `.env` 設定的資料庫：選課與開課測試只在專用的測試學期 `9991` 中建立與刪除資料，管理員測試會還原自己造成的變更。
