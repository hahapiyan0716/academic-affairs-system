# 輕量化教務管理系統（Academic Affairs System）

以 3NF 資料庫設計為基礎，延伸出具備「管理員／教師／學生」三種角色的教務系統。專案分成兩個獨立的服務：

```text
瀏覽器 ──→ web（Next.js，:3000）  畫面：頁面、表單、按鈕
              │  rewrites：/api/* 由 Next.js 伺服器轉發（瀏覽器只看到同一個來源）
              └──→ api（FastAPI，:8000）  資料：登入、權限、驗證、交易 ──→ MySQL（academic_db）
```

- 登入狀態是 api 簽發的 httpOnly cookie（`access_token`，內容是 JWT）。
- 只有 api 會連資料庫；web 沒有資料庫密碼。

| 資料夾／檔案                                | 內容                                          | 說明                                                         |
| ------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------ |
| `api/`                                    | FastAPI、SQLAlchemy 2.1、Alembic、PyMySQL     | 詳見[`api/README.md`](api/README.md)                        |
| `web/`                                    | Next.js 16、React 19、Tailwind CSS、shadcn/ui | 詳見[`web/README.md`](web/README.md)                        |
| `系統架構筆記.md`（本機筆記，未納入版控） |                                               | 架構、資料庫設計、認證、選課交易的完整說明（只寫現在的設計） |
| `演進紀錄.md`（本機筆記，未納入版控）     |                                               | 舊寫法、改名、bug 怎麼發現與修掉的經過                       |

---

## 第一次啟動

需要：Python 3.12（以 conda 管理環境）、Node.js 20 以上、MySQL 8.0。

### 1. 建立資料庫與專用帳號（以 root 執行一次）

```sql
CREATE DATABASE academic_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'academic_app'@'localhost' IDENTIFIED BY '自訂密碼';
GRANT ALL PRIVILEGES ON academic_db.* TO 'academic_app'@'localhost';
FLUSH PRIVILEGES;
```

### 2. api：安裝套件、設定 .env、建立資料表

```powershell
Set-Location api
conda create -n academic_system python=3.12   # 只需建立一次
conda activate academic_system
pip install -r requirements.txt               # 依賴皆來自 PyPI，因此用 pip 安裝
Copy-Item .env.example .env                   # 打開 .env 填入 DATABASE_URL、JWT_SECRET、SEED_PASSWORD
alembic upgrade head                          # 建立資料表與 View
python -m seed                                # 寫入種子資料
```

### 3. web：安裝套件、設定 .env.local

```powershell
Set-Location ..\web
npm install
Copy-Item .env.example .env.local             # JWT_SECRET 要和 api\.env 相同
```

產生 JWT 密鑰：`python -c "import secrets; print(secrets.token_urlsafe(48))"`

## 每天開發：開兩個終端機

```powershell
# 終端機 1：api（看到 Uvicorn running on http://127.0.0.1:8000 就好了）
Set-Location api
conda activate academic_system
uvicorn app.main:app --reload --port 8000
```

```powershell
# 終端機 2：web
Set-Location web
npm run dev
```

| 網址                                                            | 內容                                      |
| --------------------------------------------------------------- | ----------------------------------------- |
| [http://localhost:3000](http://localhost:3000)                   | 網站本身                                  |
| [http://localhost:3000/api/docs](http://localhost:3000/api/docs) | API 文件（Swagger）；登入後可直接試打 API |

### 種子帳號

所有帳號的密碼皆為 `api\.env` 中的 `SEED_PASSWORD`。

| 身分   | 帳號               | 說明                                               |
| ------ | ------------------ | -------------------------------------------------- |
| 管理員 | `admin`          |                                                    |
| 教師   | `T001`～`T008` | `T001` 岳飛、`T003` 劉邦具開課權限             |
| 學生   | `S001`～`S022` | `S002`、`S008` 休學，`S010` 退學（不可選課） |

學期：`1131`、`1132`、`1141`、`1142` 為已結束的歷史學期，`1151` 為目前學期（選課中），`1152` 為下學期（規劃中，只有開課資料）。

### 常見卡關

| 症狀                                                            | 原因與處理                                                                                 |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| 在專案最外層執行`npm run dev` 出現 `ENOENT … package.json` | 最外層不是 npm 專案，要先`Set-Location web`                                              |
| 登入失敗、或所有頁面的資料都載入失敗                            | api 沒開。看終端機 1 有沒有在跑                                                            |
| web 啟動時說 3000 已被使用                                      | 有其他 Next.js 專案正在使用 3000；關掉它，或改用`npm run dev -- -p 3100`                 |
| 登入後馬上被導回登入頁                                          | `web\.env.local` 與 `api\.env` 的 `JWT_SECRET` 不一致                                |
| `alembic` 指令出現 `UnicodeDecodeError`                     | `alembic.ini` 裡出現了中文；這個檔案必須維持純 ASCII（說明見 `api\migrations\env.py`） |
| `next build` 中途當掉                                         | 記憶體不足。先停掉開發伺服器再建置                                                         |

## 測試

```powershell
Set-Location api
conda activate academic_system
pytest            # 39 項，含 8 人同時搶 3 個名額的併發測試
```

測試連線至 `api\.env` 設定的資料庫：選課與開課測試只在專用的測試學期 `9991` 中建立與刪除資料，管理員測試會還原自己造成的變更。
