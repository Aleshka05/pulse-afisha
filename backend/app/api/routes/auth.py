from datetime import timedelta

from jose import JWTError, jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.loader import APP_LOGGER
from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
    create_password_reset_token,
)
from app.db.session import get_session
from app.models.user import User, UserRole
from app.schemas.auth import Token, PasswordResetApply, ForgotPasswordRequest
from app.schemas.user import UserCreate, UserRead
from app.services.email import send_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    # Нормализуем email один раз
    normalized_email = payload.email.strip().lower()

    # Проверяем, есть ли уже такой пользователь
    query = select(User).where(User.email == normalized_email)
    result = await session.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    user = User(
        email=normalized_email,  # <-- сохраняем уже в нижнем регистре
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.user,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> Token:
    # OAuth2PasswordRequestForm кладёт email в поле username
    normalized_email = form_data.username.strip().lower()

    query = select(User).where(User.email == normalized_email)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный email или пароль",
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token)


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Запрос на восстановление пароля.

    Даже если email не найден – отвечаем одинаково,
    чтобы нельзя было по этому методу угадывать существующие аккаунты.
    """
    normalized_email = payload.email.strip().lower()

    stmt = select(User).where(User.email == normalized_email)
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    # Одинаковый ответ для найденного/ненайденного пользователя
    public_detail = (
        "Если такой email зарегистрирован в системе, "
        "мы отправили ссылку для восстановления пароля."
    )

    if user is None:
        APP_LOGGER.info("[forgot_password] email not found %s", normalized_email)
        return {"detail": public_detail}

    # Генерируем токен и ссылку
    token = create_password_reset_token(user.id)
    reset_link = f"https://pulse.of.by/auth/reset-password?token={token}"

    body = (
        "Вы запросили восстановление пароля на сайте Pulse Afisha.\n\n"
        f"Для смены пароля перейдите по ссылке:\n{reset_link}\n\n"
        "Ссылка действительна ограниченное время. "
        "Если вы не запрашивали восстановление пароля, просто игнорируйте это письмо."
    )

    try:
        send_email(
            to=user.email,
            subject="Восстановление пароля на Pulse Afisha",
            text=body,
        )
        APP_LOGGER.info(
            "[forgot_password] reset email sent user_id=%s email=%s",
            user.id,
            user.email,
        )
    except Exception:
        APP_LOGGER.exception(
            "[forgot_password] failed to send email user_id=%s email=%s",
            user.id,
            user.email,
        )

    return {"detail": public_detail}


@router.post("/reset-password")
async def reset_password(
    payload: PasswordResetApply,
    session: AsyncSession = Depends(get_session),
):
    try:
        data = jwt.decode(
            payload.token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ссылка для восстановления недействительна или устарела.",
        )

    if data.get("scope") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный тип токена восстановления.",
        )

    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректный токен.",
        )

    stmt = select(User).where(User.id == int(user_id))
    res = await session.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден.",
        )

    user.hashed_password = hash_password(payload.new_password)
    session.add(user)
    await session.commit()

    APP_LOGGER.info("[auth.reset_password] password changed user_id=%s", user.id)

    return {"detail": "Пароль успешно изменён. Теперь вы можете войти с новым паролем."}
