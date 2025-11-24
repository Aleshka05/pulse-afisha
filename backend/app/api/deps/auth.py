from typing import Annotated, Callable
from collections.abc import Callable
from typing import Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import User, UserRole
from app.schemas.auth import TokenPayload
from app.loader import APP_LOGGER

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Возвращает текущего пользователя по access-токену."""
    payload_data = decode_token(token)
    if payload_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )

    payload = TokenPayload(**payload_data)
    if payload.sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен",
        )

    query = select(User).where(User.id == int(payload.sub))
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован",
        )

    return user


def role_required(*roles: UserRole | str) -> Callable[..., Any]:
    """
    Проверка роли пользователя.
    Принимает и Enum, и строки ('admin', 'organizer').
    """

    allowed_roles = {
        r.value if isinstance(r, UserRole) else r
        for r in roles
    }

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
      raw_role = current_user.role
      current_role = raw_role.value if isinstance(raw_role, UserRole) else raw_role

      APP_LOGGER.info(
          f"[role_required] user_id={current_user.id} role={current_role} "
          f"allowed={sorted(allowed_roles)}"
      )

      if current_role not in allowed_roles:
          APP_LOGGER.warning(
              f"[role_required] access denied user_id={current_user.id} "
              f"role={current_role} allowed={sorted(allowed_roles)}"
          )
          raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail="Недостаточно прав",
          )
      return current_user

    return dependency