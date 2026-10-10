"""
業務錯誤：services 只丟出這些例外，不依賴 HTTP；
middleware/error_handler.py 負責把它們轉成 HTTP 回應 { "detail": message }。
"""


class AppError(Exception):
    """所有業務錯誤的基底；子類別以 status_code 決定對應的 HTTP 狀態碼"""

    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class UnprocessableError(AppError):
    status_code = 422


class TooManyRequestsError(AppError):
    """請求過於頻繁；retry_after（秒）會放進回應的 Retry-After 標頭"""

    status_code = 429

    def __init__(self, message: str, retry_after: int) -> None:
        super().__init__(message)
        self.retry_after = retry_after
