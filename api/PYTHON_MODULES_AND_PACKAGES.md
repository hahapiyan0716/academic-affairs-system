# Python 模組、套件與特殊名稱筆記

這份筆記說明 Python 的模組搜尋機制、`python -m`、`__init__.py`、`__main__.py` 與 `__xxx__`（dunder）名稱，並以本專案的 `seed` 與 `migrations` 目錄比較兩種不同用途的結構。

## 1. 模組與套件

### 模組（module）

一個可由 Python 載入的 `.py` 檔案通常是一個模組。例如：

```text
app/config.py
```

其完整模組名稱是 `app.config`，可以寫成：

```python
from app.config import get_settings
```

### 套件（package）

套件用來組織多個模組。傳統的一般套件是包含 `__init__.py` 的目錄：

```text
seed/
├── __init__.py
└── __main__.py
```

Python 3.3 之後也支援沒有 `__init__.py` 的 namespace package，但它有不同用途；不能因此假設每個含 `.py` 的目錄都應視為一般套件。

## 2. `python -m` 的意思

`-m` 後面接的是「模組名稱」，不是檔案路徑：

```powershell
python -m seed
```

Python 會透過 `sys.path` 尋找名為 `seed` 的模組或套件。`sys.path` 通常包含：

- 目前執行環境的搜尋起點。
- Python 標準函式庫。
- 目前 conda 環境已安裝的套件。
- `PYTHONPATH` 額外指定的路徑。

可以查看實際搜尋路徑：

```powershell
conda run -n academic_system python -c "import sys; print(*sys.path, sep='\n')"
```

這個專案應從 `api` 目錄執行：

```powershell
Set-Location C:\Users\ASUS\Desktop\教務資料庫系統\api
conda run -n academic_system python -m seed
```

因為 `api` 必須位於模組搜尋起點，Python 才能找到同一層的 `seed` 與 `app`。

### `-m` 與直接執行檔案的差異

```powershell
python path\to\script.py
```

表示直接執行指定路徑的檔案。

```powershell
python -m package.module
```

表示依照 Python 的模組與套件規則尋找並執行模組。`-m` 會保留正確的套件資訊，因此套件內的相對匯入通常可以正常運作。

本專案的 `seed` 是一個目錄，不是 `api/seed.py`，因此標準執行方式是 `python -m seed`，不應寫成 `python seed.py`。也不建議直接執行 `python seed/__main__.py`，因為這會改變模組搜尋起點與套件語意。

## 3. `__init__.py` 與 `__main__.py`

| 檔案 | 觸發時機 | 主要用途 |
| --- | --- | --- |
| `__init__.py` | 套件被載入或匯入時 | 初始化套件、整理公開介面 |
| `__main__.py` | 套件透過 `python -m 套件名稱` 執行時 | 定義套件的命令列進入點 |

### `__init__.py`

執行以下程式時：

```python
import seed
```

Python 會載入並執行 `seed/__init__.py`。這個檔案可以用來：

- 明確標記一般 Python 套件。
- 執行套件初始化。
- 從子模組匯出公開函式或類別。
- 定義套件層級資訊，例如版本。

例如：

```python
# example_package/__init__.py
from .calculator import calculate_total

__version__ = "1.0.0"
```

外部便能使用：

```python
from example_package import calculate_total
```

不過，不應為了填滿檔案而加入沒有必要的初始化程式。匯入套件時會執行 `__init__.py`，其中若有資料庫寫入、網路請求或其他昂貴操作，可能造成難以預期的副作用。

### `__main__.py`

若套件具有 `__main__.py`，便能透過以下方式作為程式執行：

```powershell
python -m package_name
```

Python 會執行：

```text
package_name/__main__.py
```

`__main__.py` 通常負責：

- 解析命令列參數。
- 呼叫應用程式的主要函式。
- 決定程式結束碼或錯誤訊息。

## 4. 本專案範例一：`api/seed`

目前結構如下：

```text
api/
└── seed/
    ├── __init__.py
    ├── __main__.py
    └── seed.sql
```

### 為什麼 `seed/__init__.py` 是空的？

這個檔案目前是 0 byte，仍然具有作用：它明確將 `seed` 宣告為一般 Python 套件。

它之所以不需要內容，是因為目前沒有以下需求：

- `import seed` 時執行初始化邏輯。
- 從 `seed` 套件直接匯出函式或類別。
- 定義套件層級設定。
- 在匯入時產生任何副作用。

因此，保持空白比加入不必要的程式碼更合適。保留檔案也能讓 IDE、測試工具與靜態分析工具清楚辨識一般套件，並避免意外採用 namespace package 語意。

### `python -m seed` 的執行流程

從 `api` 目錄執行：

```powershell
conda run -n academic_system python -m seed
```

概念上的流程是：

```text
Python 從 sys.path 找到 seed 套件
    ↓
載入 seed/__init__.py（目前沒有額外動作）
    ↓
將 seed/__main__.py 當成主要程式執行
    ↓
呼叫 main()
    ↓
解析 --reset、讀取設定、執行 seed.sql 並建立初始帳號
```

`seed/__main__.py` 最後包含：

```python
if __name__ == "__main__":
    main()
```

透過 `python -m seed` 執行時，該檔案中的 `__name__` 是 `"__main__"`，所以會呼叫 `main()`。如果只是：

```python
import seed.__main__
```

它的 `__name__` 會是 `"seed.__main__"`，條件不成立，因此不會自動開始寫入資料庫。

## 5. 本專案範例二：`api/migrations`

目前結構如下：

```text
api/
├── alembic.ini
└── migrations/
    ├── env.py
    ├── README
    ├── script.py.mako
    └── versions/
        ├── 0001_init.py
        └── 0002_field_names.py
```

### 它與 `seed` 的根本差異

`migrations` 目錄沒有：

```text
__init__.py
__main__.py
```

所以它不是像 `seed` 那樣設計成「可用 `python -m migrations` 執行的一般套件」。在現代 Python 中，它在特定搜尋路徑下可能被辨識為 namespace package，但這不是本專案使用它的方式。

它的主要身分是 Alembic 的 migration script directory。Alembic 透過 `api/alembic.ini` 的設定找到它：

```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .
```

- `script_location` 告訴 Alembic migration 腳本位於 `migrations`。
- `prepend_sys_path = .` 讓執行時的 `api` 目錄加入模組搜尋路徑，因此 `env.py` 可以匯入 `app.config`、`app.models` 等模組。

### Alembic migration 的執行流程

從 `api` 目錄執行：

```powershell
conda run -n academic_system alembic upgrade head
```

概念上的流程是：

```text
alembic CLI 讀取 alembic.ini
    ↓
由 script_location 找到 migrations/
    ↓
執行 migrations/env.py，建立資料庫連線與 migration context
    ↓
讀取 versions/ 中各 revision 的相依關係
    ↓
依順序呼叫尚未套用 revision 的 upgrade()
```

例如 `migrations/versions/0001_init.py` 定義：

```python
revision = "0001"
down_revision = None


def upgrade() -> None:
    ...


def downgrade() -> None:
    ...
```

這些名稱是 Alembic 約定的介面：

- `revision`：目前 migration 的識別碼。
- `down_revision`：上一個 migration 的識別碼。
- `upgrade()`：升級資料庫時執行。
- `downgrade()`：降級資料庫時執行。

它們不是因為檔名帶有 `__xxx__` 才被呼叫，而是 Alembic 載入 revision 檔案後，依自己的規則讀取與呼叫。

### 為什麼不能用 `python -m migrations`？

`python -m migrations` 要求 Python 找到 `migrations/__main__.py` 作為進入點，但本專案沒有這個檔案，因此這不是有效的 Alembic 執行方式。

正確指令是：

```powershell
conda run -n academic_system alembic upgrade head
```

也不應直接執行：

```powershell
python migrations/env.py
```

因為 `env.py` 依賴 Alembic CLI 預先建立的 `alembic.context` 與設定環境；直接執行無法完整重現這些條件。

## 6. `seed` 與 `migrations` 對照

| 項目 | `seed` | `migrations` |
| --- | --- | --- |
| 主要用途 | 寫入種子資料與初始帳號 | 管理資料庫結構版本 |
| 一般 Python 套件 | 是，有 `__init__.py` | 不是本專案的使用定位；沒有 `__init__.py` |
| 套件執行入口 | `seed/__main__.py` | 沒有 `migrations/__main__.py` |
| 啟動方式 | `python -m seed` | `alembic upgrade head` |
| 載入依據 | Python 的模組搜尋與套件規則 | `alembic.ini` 與 Alembic 的 script directory 規則 |
| 主要執行內容 | `main()`、`seed()` | `env.py` 與 revision 的 `upgrade()`／`downgrade()` |

這個比較也說明：資料夾名稱本身不能決定執行方式，必須同時查看檔案結構、設定檔，以及實際使用的工具。

## 7. `__xxx__`（dunder）命名規則

正確形式是前後各兩個底線：

```text
__xxx__
```

`dunder` 是 double underscore 的簡稱。`__xxx___` 結尾有三個底線，不是標準形式。

一般模組不需要使用 dunder 名稱，通常使用小寫 `snake_case`：

```text
auth_service.py
user_repository.py
migration_support.py
```

dunder 名稱通常保留給 Python 定義的特殊協定。

### 常見特殊屬性

| 名稱 | 意義 |
| --- | --- |
| `__name__` | 目前模組名稱；主要執行模組為 `"__main__"` |
| `__file__` | 目前模組的檔案路徑 |
| `__package__` | 目前模組所屬套件 |
| `__doc__` | 模組、類別或函式的文件字串 |
| `__all__` | 控制 `from module import *` 公開的名稱 |

`seed/__main__.py` 使用 `__file__` 定位檔案：

```python
SERVICE_DIR = Path(__file__).resolve().parent.parent
SEED_SQL = Path(__file__).resolve().parent / "seed.sql"
```

這樣路徑以程式檔案的位置為基準，不會因使用者從不同目錄啟動而任意改變。

### 常見特殊方法

| 名稱 | Python 何時使用 |
| --- | --- |
| `__init__` | 建立物件後初始化 |
| `__str__` | `str(obj)` 或 `print(obj)` |
| `__repr__` | `repr(obj)` 或互動式顯示物件 |
| `__len__` | `len(obj)` |
| `__iter__` | `iter(obj)` 或開始迭代 |
| `__next__` | `next(obj)` |
| `__enter__`、`__exit__` | 進入與離開 `with` 區塊 |
| `__call__` | 把物件當作函式呼叫 |
| `__eq__` | 使用 `==` 比較 |

不要自行發明沒有標準意義的 dunder 名稱：

```python
# 不建議：容易讓人誤以為 Python 會自動呼叫
def __calculate_score__(self):
    ...
```

一般自訂方法應寫成：

```python
def calculate_score(self):
    ...
```

若要表達「僅供內部使用」，慣例是使用單一前置底線：

```python
def _calculate_score(self):
    ...
```

單一底線是可見性慣例，不會像其他語言的 `private` 一樣強制禁止外部存取。

## 8. 判斷一個目錄如何執行

看到一個 Python 相關目錄時，可以依序確認：

1. 是否有 `__init__.py`：若有，通常是一般套件。
2. 是否有 `__main__.py`：若有，通常可以使用 `python -m 套件名稱`。
3. 是否由框架或工具的設定檔指定：例如本專案的 `migrations` 由 `alembic.ini` 指定。
4. README 寫的標準啟動指令是什麼。
5. 程式是否依賴特定工作目錄、環境變數或 conda 環境。

套用到本專案：

```text
seed       → 一般套件，具有 __main__.py → python -m seed
migrations → Alembic 腳本目錄          → alembic upgrade head
```
