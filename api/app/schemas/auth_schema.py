"""登入與密碼規則"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, StringConstraints

# bcrypt 只處理前 72 bytes；bcrypt 5.x 對超過長度的輸入直接拋出 ValueError
PASSWORD_MAX_BYTES = 72


def _password_bytes(value: str) -> str:
    # 中文一字佔 3 bytes，因此以 bytes 而非字元數限制
    if len(value.encode()) > PASSWORD_MAX_BYTES:
        raise ValueError(f"密碼過長（上限 {PASSWORD_MAX_BYTES} bytes）")
    return value


Password = Annotated[str, Field(min_length=8, max_length=72), AfterValidator(_password_bytes)]
Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=30)]


class LoginIn(BaseModel):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    # 登入時不套用 Password 的規則：超長密碼一律視為「帳號或密碼錯誤」，不透露規則
    password: str = Field(min_length=1, max_length=100)
