# 原始設計資料

這個資料夾保存專案一開始的資料庫設計，**不是現在的資料表結構**。現在的結構以 `api/app/models.py` 為準，ERD 與設計說明見根目錄 `系統架構筆記.md` §3。

| 檔案 | 內容 |
| --- | --- |
| `原始資料.xlsx` | 工作表「原始資料」：正規化前的單一大表（一列 = 一筆選課，課程、教室、教師、學生資訊全部重複出現）；工作表「3NF」：正規化時整理欄位用的表格（資料型態、主鍵／外鍵、相依資訊、欄位說明） |
| `ER-diagram.png` | 原始 3NF 設計的 ER 圖 |
| `Relational Database Schema.png` | 原始 3NF 設計的關聯綱要（主鍵與外鍵） |

人名皆為虛構（三國人物、歷史人物），不含真實個資。

## 與現在結構的主要差異

原始設計中，`Course` 同時包含課程本身（課名、學分）與某次開課的資訊（人數上限、狀態），時段與授課教師也掛在課程上，因此無法表達「同一門課在不同學期、由不同教師開設」。現在拆成：

| 原始設計 | 現在 |
| --- | --- |
| `Course`（含 capacity、status） | `Course`（課程庫）＋ `Section`（某學期的開課班級） |
| `CourseSchedule`（time_slot 字串，例如 `一5`） | `SectionSchedule`（`weekday` + `period`，掛在班級上） |
| `CourseTeacher` | `SectionTeacher`（掛在班級上，可區分主授與合授） |
| `CourseSelection`（select_result：中選／人工加選／落選） | `Enrollment`（另外區分「落選」與「退選」） |
| — | 新增 `UserAccount`、`Semester`、權限與成績的稽核表 |

完整的差異與理由見 `系統架構筆記.md` §3.1。原始資料在 1132 學期的種子資料中完整保留（`api/seed/seed.sql`），轉換結果已逐欄比對一致。
