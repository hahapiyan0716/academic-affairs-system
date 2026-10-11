# migrations/

Alembic 的 migration 目錄。資料庫結構的唯一來源是 `app/models.py`；這裡存放的是「如何把資料庫從舊結構一步步改成新結構」的紀錄。

## 檔案

| 檔案               | 內容                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `env.py`         | Alembic 執行環境：連線字串取自`.env` 的 `DATABASE_URL`，比對目標為 `app.models` 的 `Base.metadata`（見下方「env.py 的運作」） |
| `script.py.mako` | `alembic revision` 產生新 migration 檔時使用的樣板                                                                                  |
| `versions/`      | 各版本的 migration，每個檔案有`upgrade()`（升級）與 `downgrade()`（還原）                                                         |

## 版本鏈

每個 migration 以 `down_revision` 指向前一版，串成一條鏈：

| 版本 | 檔案                      | 內容                                   | 產生方式                                                                                  |
| ---- | ------------------------- | -------------------------------------- | ----------------------------------------------------------------------------------------- |
| 0001 | `0001_init.py`          | 15 張資料表、CHECK 約束、2 個 View     | 對空資料庫執行`alembic revision --autogenerate`，View 手寫（見下方「0001 的產生方式」） |
| 0002 | `0002_field_names.py`   | 兩個 View 加入`field_names` 欄位     | 手寫（autogenerate 不處理 View）                                                          |
| 0003 | `0003_token_version.py` | `UserAccount` 新增 `token_version` | `alembic revision --autogenerate`                                                       |

- 0001 的 `down_revision = None`，表示它前面沒有版本（Alembic 稱為 `base`，即空資料庫）。
- 資料庫目前的版本記在 `alembic_version` 表（只有一欄 `version_num`）。`alembic upgrade` 依此決定從哪一版開始執行；`alembic current` 讀的也是它。

## env.py 的運作

每個 alembic 指令（`upgrade`、`revision --autogenerate`、`current`……）都會先執行 `env.py`。Alembic 依 `alembic.ini` 的 `script_location` 找到 `migrations/`；`prepend_sys_path = .` 把目前目錄加入 `sys.path`，`env.py` 才能 `import app.models`，所以 alembic 指令一律在 `api/` 下執行。

### 執行順序

1. `config = context.config`：取得 `alembic.ini` 的內容。
2. `fileConfig(...)`：依 `alembic.ini` 的 `[loggers]` 等區段設定 Alembic 與 SQLAlchemy 的 log 輸出（例如 `INFO [alembic.runtime.migration] Running upgrade ...`）。
3. `target_metadata = Base.metadata`：`import app.models` 時，每個繼承 `Base` 的類別都會把自己的資料表登記到 `Base.metadata`。autogenerate 以它為「應有的結構」。
4. 依 `context.is_offline_mode()` 選擇其中一種模式，設定好 `context` 後呼叫 `context.run_migrations()`，依版本鏈逐一執行各 migration 的 `upgrade()` 或 `downgrade()`。

### 兩種模式

|                   | 離線模式`run_migrations_offline()`                                    | 一般模式`run_migrations_online()`  |
| ----------------- | ----------------------------------------------------------------------- | ------------------------------------ |
| 觸發方式          | 指令加上`--sql`（例如 `alembic upgrade head --sql`）                | 其他所有指令                         |
| 是否連線          | 不連線，把 SQL 印到終端機                                               | 以`create_engine` 連上資料庫並執行 |
| 連線字串的用途    | 只用來判斷方言（MySQL），決定 SQL 語法                                  | 實際連線                             |
| 參數值            | `literal_binds=True`：值直接寫進 SQL 字串，因為沒有連線可以另外傳參數 | 照一般方式以參數傳送                 |
| 能否 autogenerate | 不能（沒有資料庫可以反射比對）                                          | 能                                   |

### 各項設定

| 設定                                                                  | 模式 | 作用                                                                                                                                                     |
| --------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_settings().database_url`                                       | 兩者 | 連線字串取自`app/config.py`（`.env` 的 `DATABASE_URL`，可用同名環境變數覆寫），不寫在 `alembic.ini`，避免密碼進入版控                            |
| `target_metadata=target_metadata`                                   | 兩者 | autogenerate 比對的「應有結構」                                                                                                                          |
| `include_object`（`app/migration_support.py`）                    | 兩者 | 決定哪些物件納入比對：① 略過帶`info={"is_view": True}` 的 View 類別；② 資料庫有、models 沒有的表（`alembic_version`、View）不提議刪除              |
| `poolclass=pool.NullPool`                                           | 一般 | migration 是一次性指令，用完即關，不需要連線池                                                                                                           |
| `patch_case_insensitive_reflection`（`app/migration_support.py`） | 一般 | 偵測到`lower_case_table_names` 不為 0（Windows 預設為 1）時，把反射回來的小寫表名換回 models 的 PascalCase；否則 autogenerate 會把所有表判定為「缺少」 |
| `compare_type=True`                                                 | 一般 | 欄位型別的差異（例如`CHAR(4)` → `CHAR(6)`）納入比對                                                                                                 |
| `compare_server_default=True`                                       | 一般 | `server_default` 的差異納入比對（Alembic 預設不比對）                                                                                                  |
| `with context.begin_transaction():`                                 | 兩者 | 由 Alembic 開啟並 commit 交易；`alembic_version` 的寫入在這個交易中完成                                                                                |

### 交易的注意事項

- MySQL 的 DDL（`CREATE TABLE`、`ALTER TABLE`）會自動 commit，無法 rollback（log 中的 `Will assume non-transactional DDL`）。migration 執行到一半失敗時，已執行的 DDL 會留在資料庫，需要手動處理。
- `alembic_version` 的寫入是一般的 `INSERT`／`UPDATE`，靠 `context.begin_transaction()` commit。若在它之前用同一條連線查詢而沒有結束交易（SQLAlchemy 2.x 的 autobegin），Alembic 會視為外部交易而不 commit，版本紀錄會在連線關閉時被 rollback。因此 `patch_case_insensitive_reflection` 的偵測查詢包在自己的 `with connection.begin():` 中。
- 在 `env.py` 新增任何要先查詢資料庫的設定時，同樣要包在自己的 `connection.begin()` 中。

## models.py、migration 與 schema.generated.sql 的關係

```
① 修改 models.py
   寫下希望資料庫最終具有的結構
   ↓
② 執行 alembic revision --autogenerate
   env.py 使用 Online 模式：
   - 讀取 models.py 的應有結構
   - 連線讀取資料庫的目前結構
   - 比較兩者的差異
   ↓
③ 產生 versions/*.py
   內容是 op.create_table()、op.add_column() 等 migration 指令，必須先人工檢查
   因為 View 等等一些結構不出現，所以要先手寫加上去再 alembic upgrade head
   ↓
④ 選擇一種執行方式

   A. 直接套用資料庫（一般開發使用）
      alembic upgrade head
      versions/*.py → env.py（Online）→ 執行 SQL → 資料庫完成更新

   B. 只產生 SQL 檔（預覽或交給 DBA）
      alembic upgrade head --sql > database/schema.generated.sql
      versions/*.py → env.py（Offline）→ database/schema.generated.sql
      此時資料庫尚未改變；必須另外用 MySQL client 執行 SQL 檔才會套用
```

`env.py` 是每次執行 Alembic 指令時的入口，不是流程產生的新檔案。沒有 `--sql` 時使用 Online 模式；加上 `--sql` 時使用 Offline 模式。

- `alembic upgrade head --sql` 是離線模式：不連資料庫，只把會執行的 SQL 依序印出。每個 migration 開頭會有一行 `-- Running upgrade <原版本> -> <新版本>`，結尾以 `INSERT`／`UPDATE alembic_version` 記錄版本。
- `schema.generated.sql` 重新產生時會整份覆蓋，手寫在裡面的註解不會保留。

## 一般 migration 的產生方式

1. 修改 `app/models.py`
2. `alembic revision --autogenerate -m "說明"`
   - Alembic 讀取 models.py（應有的結構），連上資料庫反射目前的結構，把差異寫成 `op.add_column`、`op.create_table` 等指令，套用 `script.py.mako` 產生 `versions/` 下的新檔。
   - 自動產生的指令包在 `# ### commands auto generated by Alembic - please adjust! ###` 與 `# ### end Alembic commands ###` 之間。`please adjust!` 表示產生結果不保證正確，必須人工檢查。
3. 檢查產生的檔案，補上 autogenerate 偵測不到的部分（見下一節）
4. `alembic upgrade head` 套用到資料庫

## autogenerate 偵測不到、需要手動處理的變更

| 變更                    | 原因                                                                                                             | 手動寫法                                                                                                             |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 修改 CHECK 約束         | Alembic 不比對 CHECK 約束                                                                                        | `op.drop_constraint(..., type_="check")` + `op.create_check_constraint(...)`                                     |
| 新增或修改 View         | View 不是資料表；ORM 類別帶`info={"is_view": True}`，`app/migration_support.py` 的 `include_object` 會略過 | `op.execute("CREATE OR REPLACE VIEW ...")`；downgrade 要還原舊定義（參考 0002 的 `section_detail(with_fields)`） |
| 從 models.py 刪除資料表 | `include_object` 對「資料庫有、models 沒有」的表一律不提議刪除（避免誤刪 `alembic_version` 與 View）         | `op.drop_table(...)`，downgrade 寫回 `op.create_table(...)`                                                      |
| 欄位或資料表改名        | Alembic 無法分辨「改名」與「刪除舊的＋新增新的」，會產生 drop + add，**資料會遺失**                        | 改成`op.alter_column(..., new_column_name=...)` 或 `op.rename_table(...)`                                        |

另外，models.py 中的 `server_default`（寫進 DDL）會被比對（`env.py` 設定了 `compare_server_default=True`）；只在 Python 端生效的 `default=` 不會出現在 migration 中。

## 0001 的產生方式

0001 是第一版，產生時資料庫裡還沒有任何資料表：

1. **寫好 models.py**：定義全部資料表、約束與索引。
2. **對空資料庫執行 `alembic revision --autogenerate -m "初始結構"`**：models 有 15 張表、資料庫一張都沒有，差異就是「15 張表全部要建立」，因此每張表都輸出成 `op.create_table`。CHECK 約束隨 `create_table` 一起輸出（autogenerate 偵測不到的是「修改」既有的 CHECK 約束，不是新表上的）。
3. **手動補上 View**：`v_section_detail`、`v_student_transcript` 以 `op.execute("CREATE VIEW ...")` 寫在 `# ### end Alembic commands ###` 之後；`downgrade()` 中的 `DROP VIEW` 也是手寫，且要排在刪除資料表之前（View 依賴資料表）。
4. **`alembic upgrade head`**：實際建立資料表與 View，並在 `alembic_version` 寫入 `0001`。

autogenerate 只會產生「models 與資料庫的差異」。若資料庫裡已經有同樣結構的表，差異為 0，產生的 migration 會是空的；所以第一版必須對空資料庫產生。

## 常用指令（在 `api/` 下執行）

```powershell
conda activate academic_system

alembic upgrade head                 # 升級到最新版本
alembic upgrade head --sql           # 只輸出 SQL、不執行（離線模式）
alembic current                      # 資料庫目前的版本
alembic history                      # 所有版本與順序
alembic downgrade -1                 # 還原一個版本（執行該版的 downgrade()，可能刪除欄位與資料）
alembic stamp <版本>                 # 只改寫 alembic_version，不執行任何 migration
python -m seed --reset               # downgrade base → upgrade head → 寫入種子資料（會清空所有資料）
```

對其他資料庫執行時，以環境變數覆寫連線字串（優先於 `.env`）：

```powershell
$env:DATABASE_URL = "mysql+pymysql://..."; alembic upgrade head
```

## 撰寫 migration 的注意事項

- **不要修改已經套用過的 migration**。其他資料庫的 `alembic_version` 已記錄為該版本，不會重新執行；要調整結構請新增下一版。
- **`downgrade()` 必須能完整還原 `upgrade()`**。`python -m seed --reset` 依賴 `downgrade base` 從最新版一路還原到空資料庫。
- **`alembic.ini` 必須維持純 ASCII**：Windows 上 Alembic 以 cp950 讀取它，含中文會讓所有指令失敗。說明文字寫在 `env.py`。
- **不要用 PowerShell 的 `>` 產生 migration 檔**：Windows PowerShell 5.1 會加上 UTF-8 BOM，Python 載入時出現 `SyntaxError: invalid non-printable character U+FEFF`。
- **Windows 的 MySQL 表名大小寫**：`lower_case_table_names=1` 時反射回來的表名是小寫，`app/migration_support.py` 在比對時換回 models 的 PascalCase；否則 autogenerate 會把所有表判定為「缺少」。
