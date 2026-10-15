"""API 資料契約層（Schema Layer）。

本套件使用 Pydantic 模型定義 API 的輸入與輸出格式，並依認證、帳號、教師、
學期、課程、開課及選課等領域拆分。名稱以 ``In`` 結尾的模型通常表示 Request
Body，以 ``Out`` 結尾的模型通常表示 Response；共用設定則放在 ``base.py``。

FastAPI 會在呼叫 route 前，依輸入 schema 驗證型別、必填欄位、長度、範圍及
自訂規則，並在格式不符時自動回傳 HTTP 422。輸出 schema 負責限制及序列化
回應欄位；繼承 ``ORMModel`` 的模型可透過 ``from_attributes`` 讀取 ORM 物件。

Schema 描述的是 API 對外資料契約，不是資料庫資料表。資料表、關聯及約束定義
在 ``models.py``；跨資料查詢與持久化由 ``repositories`` 處理；需要查詢資料庫
才能判斷的選課資格、權限或其他業務規則則由 ``services`` 處理。
"""
