from datetime import datetime, timedelta
from time import monotonic
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models.permission import Permission
from .models.role import Role
from .models.role_permission import RolePermission
from .models.user import User
from .models.user_role import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

USER_CACHE_TTL_SECONDS = 30
_current_user_cache = {}


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    cache_key = username
    cached = _current_user_cache.get(cache_key)
    now = monotonic()
    if cached and cached["expires_at"] > now:
        user = db.query(User).filter(User.id == cached["user_id"], User.is_deleted.is_(False)).first()
        if user is not None:
            return user

    user = db.query(User).filter(User.username == username, User.is_deleted.is_(False)).first()
    if user is None:
        raise credentials_exception
    _current_user_cache[cache_key] = {
        "user_id": user.id,
        "expires_at": now + USER_CACHE_TTL_SECONDS,
    }
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有管理员权限")
    return current_user


def require_permission(permission_code: str):
    def permission_dependency(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.is_admin:
            return current_user

        has_permission = (
            db.query(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == current_user.id,
                Permission.code == permission_code,
                Permission.is_active.is_(True),
                Permission.is_deleted.is_(False),
                Role.is_active.is_(True),
                Role.is_deleted.is_(False),
            )
            .first()
        )
        if not has_permission:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有操作权限")
        return current_user

    return permission_dependency
