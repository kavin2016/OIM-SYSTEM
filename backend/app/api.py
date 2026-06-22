from fastapi import APIRouter

from .controllers.attendance_controller import router as attendance_router
from .controllers.auth_controller import router as auth_router
from .controllers.department_controller import router as department_router
from .controllers.domain_controller import router as domain_router
from .controllers.health_controller import router as health_router
from .controllers.login_log_controller import router as login_log_router
from .controllers.permission_controller import router as permission_router
from .controllers.position_controller import router as position_router
from .controllers.openvpn_controller import router as openvpn_router
from .controllers.operation_log_controller import router as operation_log_router
from .controllers.role_controller import router as role_router
from .controllers.user_controller import router as user_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(attendance_router)
api_router.include_router(user_router)
api_router.include_router(department_router)
api_router.include_router(role_router)
api_router.include_router(position_router)
api_router.include_router(domain_router)
api_router.include_router(openvpn_router)
api_router.include_router(operation_log_router)
api_router.include_router(login_log_router)
api_router.include_router(permission_router)
