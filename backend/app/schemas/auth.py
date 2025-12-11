from pydantic import BaseModel, EmailStr, constr

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    email: EmailStr | None = None
    role: str | None = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class PasswordResetApply(BaseModel):
    token: str
    new_password: constr(min_length=6)