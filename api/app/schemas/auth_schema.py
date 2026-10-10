"""登入與密碼規則"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

# bcrypt 只處理前 72 bytes；bcrypt 5.x 對超過長度的輸入直接拋出 ValueError
PASSWORD_MAX_BYTES = 72


def _password_bytes(value: str) -> str:
    """檢查密碼的 UTF-8 編碼長度不超過 bcrypt 上限"""
    # 中文一字佔 3 bytes，因此以 bytes 而非字元數限制
    if len(value.encode()) > PASSWORD_MAX_BYTES:
        raise ValueError(f"密碼過長（上限 {PASSWORD_MAX_BYTES} bytes）")
    return value


# 設定密碼（建立帳號、重設密碼）時的規則：至少 8 字元，且不超過 72 bytes
Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_password_bytes)]
# 建立帳號時的帳號名稱規則
Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30)]


class LoginIn(BaseModel):
    """POST /api/auth/login 的請求內容"""

    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    # 登入時不套用 Password 的規則：超長密碼一律視為「帳號或密碼錯誤」，不透露規則
    password: str = Field(min_length=1, max_length=100)
