# api：FastAPI 後端

教務系統的後端 API：登入、管理員、開課、選課、成績與歷年查詢。**資料庫只有 api 會連**；`web\` 只透過 HTTP 呼叫這裡。整個專案怎麼啟動見上一層的 `README.md`。

## 啟動

需要本機的 MySQL，資料庫與帳號要先建立好（見上一層 README 的步驟 1）。

```powershell
Set-Location api
conda activate academic_system
pip install -r requirements.txt   # 第一次才需要
Copy-Item .env.example .env       # 第一次才需要：填入 DATABASE_URL、JWT_SECRET、SEED_PASSWORD（說明寫在檔案裡）
alembic upgrade head              # 第一次才需要：依 migrations\ 建立資料表與 View
python -m seed                    # 第一次才需要：寫入種子資料
uvicorn app.main:app --reload --port 8000
```

## API 一覽

| 方法與網址 | 需要登入 | 說明 |
| --- | --- | --- |
| `POST /api/auth/login` | | 登入；成功時回應帶 `Set-Cookie: access_token=…`（httpOnly）；同一 IP 15 分鐘最多 20 次 |
| `POST /api/auth/logout` | | 登出；清掉 cookie |
| `GET /api/auth/me` | ✅ | 目前登入者 |
| `GET /api/semesters`、`/api/rooms`、`/api/courses`、`/api/teachers` | ✅ | 下拉選單用的基礎資料 |
| `GET /api/sections?semester_id=&q=` | ✅ | 某學期（預設目前學期）的開放班級；學生會多得到選課狀態與衝堂標記 |
| `GET /api/history/sections?course_no=&teacher=&q=` | ✅ | 歷年開課紀錄（含修課人數、平均成績） |
| `GET /api/teacher/me`、`GET POST /api/teacher/sections` | ✅ 教師 | 教師資料、我的開課、新增開課 |
| `PATCH /api/teacher/sections/{id}` | ✅ 教師 | 調整人數上限、停開 |
| `GET /api/teacher/sections/{id}/roster`、`PUT …/grades` | ✅ 教師 | 修課名單、批次登分 |
| `POST /api/enrollments`、`DELETE /api/enrollments/{section_id}` | ✅ 學生 | 加選（先搶先贏）、退選 |
| `GET /api/me/timetable`、`GET /api/me/transcript` | ✅ 學生 | 課表、歷年成績 |
| `/api/admin/*` | ✅ 管理員 | 帳號、教師開課權限、課程庫、學期、統計（完整清單見 Swagger） |

錯誤回應格式一律是 `{ "detail": "訊息" }`；輸入驗證失敗時 `detail` 是錯誤清單（422）。

## API 文件（Swagger）

FastAPI 會依路由與 Pydantic 模型自動產生文件，不需要另外手寫。

- 透過前端開 **<http://localhost:3000/api/docs>**：先在網站登入，cookie 會自動帶上，可直接 **Try it out**。
- 直接開 <http://localhost:8000/api/docs> 也可以，但需要先在文件頁呼叫 `POST /api/auth/login`。
- 規格原始檔：`/api/openapi.json`。

## 資料夾

```text
app\
├─ main.py            進入點：建立 app、依序掛 middleware、錯誤處理與路由
├─ config.py          讀取 .env（以 api\ 為基準，不受目前所在目錄影響）
├─ db.py              資料庫連線（隔離等級 READ COMMITTED，理由見檔案內註解）
├─ session.py         登入 cookie 的簽發、驗證與屬性
├─ errors.py          業務錯誤（services 只丟這些，不依賴 HTTP）
├─ models.py          SQLAlchemy 模型：資料庫結構的唯一來源
├─ middleware\        require_auth（認證與角色）、error_handler（錯誤 → HTTP 回應）、rate_limit、security_headers
├─ routes\            auth、admin、teacher、student、common（Controller 層：只處理 HTTP）
├─ services\          業務規則與交易（enrollment_service：先搶先贏選課）
├─ repositories\      資料存取（所有 SQL 查詢，含 SELECT ... FOR UPDATE）
├─ schemas\           Pydantic 請求與回應模型，依領域分檔
└─ migration_support.py  Alembic 在 Windows MySQL 上的表名大小寫修正
migrations\           Alembic：env.py 與 versions\（0001_init：15 張表、CHECK 約束、2 個 View）
seed\                 seed.sql（種子資料）與 python -m seed
tests\                pytest（35 項）
database\             schema.generated.sql（完整建表 SQL，閱讀用）、sql-examples.sql（SQL 操作範例）、
                      Relational Database Schema.png（現行結構的關聯綱要圖）
database\original-design\  專案一開始的 3NF 設計（ER 圖、關聯綱要、原始資料 xlsx），非現行結構
```

## 資料庫維護

| 指令 | 作用 |
| --- | --- |
| `alembic upgrade head` | 套用所有尚未執行的 migration |
| `alembic revision --autogenerate -m "說明"` | 修改 `app\models.py` 後，自動產生 migration；CHECK 約束與 View 的變更需手動補上 |
| `alembic current` | 查看資料庫目前的版本 |
| `python -m seed --reset` | 清空並重建資料庫、重新寫入種子資料 |
| `alembic upgrade head --sql` | 只輸出 SQL、不執行（`database\schema.generated.sql` 由此產生） |

## 測試

```powershell
pytest                                                    # 全部 35 項
pytest tests/test_enrollment.py::test_full_section_rejected   # 單一測試
```

測試直接連 `.env` 的資料庫：選課與開課測試只在測試學期 `9991` 中建立與刪除資料，管理員測試會在結束時還原。
