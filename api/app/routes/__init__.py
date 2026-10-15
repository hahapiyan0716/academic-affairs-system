"""API 路由層（Route Layer）。

本套件依使用情境拆分認證、管理員、教師、學生與共用查詢等 FastAPI
``APIRouter``。路由函式負責定義 URL、HTTP Method、狀態碼與回應模型，接收
Path、Query、Cookie 或 JSON Body，並透過 Dependency Injection 取得目前使用者
及本次 Request 使用的資料庫 ``Session``。

Route 是 HTTP 與應用程式之間的入口：完成請求格式驗證與身分／角色依賴後，
將工作委派給 ``services``，再把結果轉成 HTTP Response；登入、登出等端點也會
在此設定或清除 cookie。Route 不直接撰寫 SQL，也不承擔選課資格、名額判斷等
業務規則。

``error_responses.py`` 只集中產生 OpenAPI／Swagger 文件使用的錯誤回應說明，
不負責攔截執行期例外；實際例外由 ``middleware/error_handler.py`` 處理。

主要呼叫方向：``HTTP Request → routes → services → repositories``。
"""
