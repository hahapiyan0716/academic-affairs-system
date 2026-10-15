"""業務邏輯層（Service Layer）。

本套件集中實作認證、帳號、教師、學期、課程、開課、選課與統計等 Use Case。
Service 接收 route 已完成基本格式驗證的資料，依業務規則協調一個或多個
``repositories`` 查詢或修改資料，例如檢查選課期間、學生狀態、重複修課、
衝堂、班級名額、教師權限及成績輸入限制。

Service 是主要的交易邊界：需要寫入資料時，由此決定何時 ``commit()``；若流程
需要特別處理資料庫錯誤，則在此執行 ``rollback()``。找不到資源、狀態衝突或
權限不足時，Service 丟出 ``errors.py`` 定義的 ``AppError`` 子類別，再由全域
error handler 統一轉成 HTTP 回應。

Service 不解析 HTTP Request、不設定 cookie，也不直接組合原始 SQL；HTTP 細節
屬於 ``routes``，資料存取細節屬於 ``repositories``。這項分工讓同一套業務流程
可以被不同 endpoint 重複使用及獨立測試。

主要呼叫方向：``routes → services → repositories → models／database``。
"""
