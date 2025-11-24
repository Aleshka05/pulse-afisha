from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    role: UserRole
    


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    avatar_url: str | None
    role: UserRole
    is_blocked: bool
    created_at: datetime
    phone: str | None = None
    telegram: str | None = None
    about: str | None = None
    preferences: str | None = None

    class Config:
        from_attributes = True


class UserUpdateProfile(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)
    phone: str | None = Field(default=None, max_length=50)
    telegram: str | None = Field(default=None, max_length=64)
    about: str | None = Field(default=None, max_length=2000)
    preferences: str | None = Field(
        default=None,
        max_length=2000,
        description="Предпочтения по мероприятиям, свободный текст.",
    )

class UserRoleUpdate(BaseModel):
    role: UserRole = Field(
        ...,
        description="Новая роль пользователя: admin / organizer / user",
    )


class UserBlockUpdate(BaseModel):
    is_blocked: bool = Field(
        ...,
        description="Заблокировать (true) или разблокировать (false) пользователя",
    )