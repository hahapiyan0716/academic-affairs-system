"""資料存取層（Repository Layer）。

本套件集中封裝應用程式與資料庫之間的互動，並依領域拆分為帳號、學生、
教師、學期、課程、開課、教室與選課等 repository 模組。各模組接收
SQLAlchemy ``Session``，負責執行查詢、關聯查詢、彙總、資料新增／更新，
以及需要避免競爭條件時使用的 ``SELECT ... FOR UPDATE`` 鎖定查詢。

Repository 只處理「如何存取資料」，不解析 HTTP Request、不驗證使用者角色，
也不決定選課資格等業務規則。業務流程與交易邊界由 ``services`` 管理，因此
repository 不自行呼叫 ``commit()`` 或 ``rollback()``；``routes`` 則負責接收
API 請求、執行 Dependency Injection，並將結果轉成 HTTP Response。

主要呼叫方向：``routes → services → repositories → models／database``。
"""
