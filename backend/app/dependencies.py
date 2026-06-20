from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from .database import get_db
from .services.department_service import DepartmentService
from .services.attendance_service import AttendanceService
from .services.domain_service import DomainService
from .services.menu_service import MenuService
from .services.openvpn_service import OpenVpnService
from .services.permission_service import PermissionService
from .services.position_service import PositionService
from .services.role_service import RoleService
from .services.user_service import UserService

DbSession = Annotated[Session, Depends(get_db)]


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


def get_department_service(db: DbSession) -> DepartmentService:
    return DepartmentService(db)


def get_attendance_service(db: DbSession) -> AttendanceService:
    return AttendanceService(db)


def get_role_service(db: DbSession) -> RoleService:
    return RoleService(db)


def get_permission_service(db: DbSession) -> PermissionService:
    return PermissionService(db)


def get_position_service(db: DbSession) -> PositionService:
    return PositionService(db)


def get_domain_service(db: DbSession) -> DomainService:
    return DomainService(db)


def get_menu_service(db: DbSession) -> MenuService:
    return MenuService(db)


def get_openvpn_service(db: DbSession) -> OpenVpnService:
    return OpenVpnService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
AttendanceServiceDep = Annotated[AttendanceService, Depends(get_attendance_service)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
PositionServiceDep = Annotated[PositionService, Depends(get_position_service)]
DomainServiceDep = Annotated[DomainService, Depends(get_domain_service)]
MenuServiceDep = Annotated[MenuService, Depends(get_menu_service)]
OpenVpnServiceDep = Annotated[OpenVpnService, Depends(get_openvpn_service)]
