import logging

from fastapi import APIRouter, Depends, Form, HTTPException, status

from ..captcha import CaptchaProvider
from ..dependencies import MenuServiceDep, UserServiceDep
from ..schemas.captcha import CaptchaResponse
from ..schemas.menu import MenuItem
from ..schemas.token import AuthSession, Token
from ..schemas.user import UserCreate, UserRead
from ..security import create_access_token, get_current_active_user

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha():
    return CaptchaProvider.generate()


@router.post("/token", response_model=Token)
def login_for_access_token(
    user_service: UserServiceDep,
    username: str = Form(...),
    password: str = Form(...),
    captcha: str = Form(...),
    captcha_token: str = Form(...),
):
    if not CaptchaProvider.validate(captcha_token, captcha):
        raise HTTPException(status_code=400, detail="验证码不正确或已过期")

    try:
        user = user_service.authenticate(username, password)
    except Exception as exc:
        logger.exception("Login authentication failed unexpectedly for username=%s", username)
        raise HTTPException(status_code=500, detail="登录认证服务异常，请稍后重试") from exc
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")

    return {
        "access_token": create_access_token({"sub": user.username, "is_admin": user.is_admin}),
        "token_type": "bearer",
    }


@router.post("/register", response_model=UserRead)
def register(user_create: UserCreate, user_service: UserServiceDep):
    return user_service.create_user(user_create)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user=Depends(get_current_active_user)):
    return current_user


@router.get("/session", response_model=AuthSession)
def read_current_session(
    menu_service: MenuServiceDep,
    current_user=Depends(get_current_active_user),
):
    access = menu_service.list_user_access(current_user)
    return {
        "user": current_user,
        "menus": access["menus"],
        "permissions": access["permissions"],
    }


@router.get("/menus", response_model=list[MenuItem])
def read_current_user_menus(
    menu_service: MenuServiceDep,
    current_user=Depends(get_current_active_user),
):
    return menu_service.list_user_menus(current_user)


@router.get("/permissions", response_model=list[str])
def read_current_user_permissions(
    menu_service: MenuServiceDep,
    current_user=Depends(get_current_active_user),
):
    return menu_service.list_user_permission_codes(current_user)
