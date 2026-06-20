from __future__ import annotations

from datetime import datetime
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..models.department import Department
from ..models.openvpn import OpenVpnAccount, OpenVpnConnectionLog, OpenVpnSession
from ..models.position import Position
from ..models.role import Role
from ..models.user import User
from ..models.user_department import UserDepartment
from ..models.user_position import UserPosition
from ..models.user_role import UserRole
from ..schemas.user import UserAdminCreate, UserAdminUpdate, UserCreate, UserUpdate
from .base_service import BaseService, ConflictError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService(BaseService[User]):
    model = User
    resource_name = "用户"
    protected_username = "admin"

    def __init__(self, db: Session):
        super().__init__(db)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return pwd_context.verify(password, hashed_password)

    @staticmethod
    def normalize_contacts(contacts: Optional[list[str]]) -> list[str]:
        if not contacts:
            return []
        return [contact.strip() for contact in contacts if contact and contact.strip()]

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
        include_deleted: bool = False,
        username: Optional[str] = None,
        nickname: Optional[str] = None,
        is_active: Optional[bool] = None,
        department_id: Optional[int] = None,
        role_id: Optional[int] = None,
        created_at_start: Optional[datetime] = None,
        created_at_end: Optional[datetime] = None,
    ) -> list[User]:
        query = self.db.query(User)
        if not include_deleted:
            query = query.filter(User.is_deleted.is_(False))
        if is_active is not None:
            query = query.filter(User.is_active.is_(is_active))
        elif not include_disabled:
            query = query.filter(User.is_active.is_(True))
        if username:
            query = query.filter(User.username.like(f"%{username.strip()}%"))
        if nickname:
            query = query.filter(User.nickname.like(f"%{nickname.strip()}%"))
        if department_id:
            query = query.join(UserDepartment, UserDepartment.user_id == User.id).filter(
                UserDepartment.department_id == department_id,
            )
        if role_id:
            query = query.join(UserRole, UserRole.user_id == User.id).filter(UserRole.role_id == role_id)
        if created_at_start:
            query = query.filter(User.created_at >= created_at_start)
        if created_at_end:
            query = query.filter(User.created_at <= created_at_end)
        return query.order_by(User.id.desc()).offset(skip).limit(limit).all()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username, User.is_deleted.is_(False)).first()

    def get_by_email(self, email: str) -> Optional[User]:
        if not email:
            return None
        return self.db.query(User).filter(User.email == email, User.is_deleted.is_(False)).first()

    def get_by_nickname(self, nickname: str) -> Optional[User]:
        return self.db.query(User).filter(User.nickname == nickname, User.is_deleted.is_(False)).first()

    def create_user(self, user_create: UserCreate, is_admin: bool = False, actor_id: int = None) -> User:
        if self.get_by_username(user_create.username):
            raise ConflictError("用户名已存在")
        if user_create.nickname and self.get_by_nickname(user_create.nickname):
            raise ConflictError("用户昵称已存在")
        if user_create.email and self.get_by_email(user_create.email):
            raise ConflictError("邮箱已存在")

        user = User(
            username=user_create.username,
            email=user_create.email or None,
            nickname=user_create.nickname,
            gender=user_create.gender,
            phone=user_create.phone,
            position=user_create.position,
            remark=user_create.remark,
            contacts=self.normalize_contacts(user_create.contacts),
            hashed_password=self.hash_password(user_create.password),
            is_admin=is_admin,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self.commit(user, "用户名或邮箱已存在")

    def create_admin_user(self, user_create: UserAdminCreate, actor_id: int) -> User:
        user = self.create_user(user_create, is_admin=user_create.is_admin, actor_id=actor_id)
        user.is_active = user_create.is_active
        self.commit(user, "用户名或邮箱已存在")
        self.replace_departments(user.id, user_create.department_ids)
        self.replace_roles(user.id, user_create.role_ids)
        self.replace_positions(user.id, user_create.position_ids)
        self.db.refresh(user)
        return user

    def update_user(self, user: User, user_update: UserUpdate, actor_id: int = None) -> User:
        if user_update.username is not None:
            if user_update.username != user.username:
                raise ConflictError("用户名不能修改")
            existing = self.get_by_username(user_update.username)
            if existing and existing.id != user.id:
                raise ConflictError("用户名已存在")
            user.username = user_update.username
        if "email" in user_update.model_fields_set:
            if user_update.email:
                existing = self.get_by_email(user_update.email)
                if existing and existing.id != user.id:
                    raise ConflictError("邮箱已存在")
            user.email = user_update.email or None
        if "nickname" in user_update.model_fields_set:
            if user_update.nickname:
                existing = self.get_by_nickname(user_update.nickname)
                if existing and existing.id != user.id:
                    raise ConflictError("用户昵称已存在")
            user.nickname = user_update.nickname
        if "gender" in user_update.model_fields_set:
            user.gender = user_update.gender
        if "phone" in user_update.model_fields_set:
            user.phone = user_update.phone
        if "position" in user_update.model_fields_set:
            user.position = user_update.position
        if "remark" in user_update.model_fields_set:
            user.remark = user_update.remark
        if "contacts" in user_update.model_fields_set:
            user.contacts = self.normalize_contacts(user_update.contacts)
        if user_update.password is not None:
            user.hashed_password = self.hash_password(user_update.password)
        user.updated_by = actor_id

        return self.commit(user, "用户名或邮箱已存在")

    def update_admin_user(self, user_id: int, user_update: UserAdminUpdate, actor_id: int) -> User:
        user = self.get_required(user_id)
        if user.username == self.protected_username:
            raise ConflictError("admin 用户不能修改")
        self.update_user(user, user_update, actor_id=actor_id)
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
            if user_update.is_active is False:
                self.disable_user_openvpn(user.id, actor_id)
        if user_update.is_admin is not None:
            user.is_admin = user_update.is_admin
        if user_update.is_deleted is not None:
            user.is_deleted = user_update.is_deleted
        user.updated_by = actor_id
        self.commit(user, "用户名或邮箱已存在")
        if "department_ids" in user_update.model_fields_set:
            self.replace_departments(user.id, user_update.department_ids)
        if "role_ids" in user_update.model_fields_set:
            self.replace_roles(user.id, user_update.role_ids)
        if "position_ids" in user_update.model_fields_set:
            self.replace_positions(user.id, user_update.position_ids)
        self.db.refresh(user)
        return user

    def delete_user(self, user_id: int, actor_id: int) -> User:
        user = self.get_required(user_id)
        if user.username == self.protected_username:
            raise ConflictError("内置 admin 用户不能删除")
        user.is_deleted = True
        user.is_active = False
        user.updated_by = actor_id
        self.disable_user_openvpn(user.id, actor_id)
        return self.commit(user, "用户删除失败")

    def delete_users(self, user_ids: list[int], actor_id: int) -> list[User]:
        ids = self.unique_ids(user_ids)
        if not ids:
            return []

        users = (
            self.db.query(User)
            .filter(
                User.id.in_(ids),
                User.is_deleted.is_(False),
            )
            .all()
        )
        if any(user.username == self.protected_username for user in users):
            raise ConflictError("内置 admin 用户不能删除")
        for user in users:
            user.is_deleted = True
            user.is_active = False
            user.updated_by = actor_id
            self.disable_user_openvpn(user.id, actor_id)
        self.db.commit()
        for user in users:
            self.db.refresh(user)
        return users

    def disable_user_openvpn(self, user_id: int, actor_id: int) -> None:
        account = self.db.query(OpenVpnAccount).filter(OpenVpnAccount.user_id == user_id).first()
        if not account:
            return
        account.status = "disabled"
        account.updated_by = actor_id
        sessions = (
            self.db.query(OpenVpnSession)
            .filter(OpenVpnSession.account_id == account.id, OpenVpnSession.status == "online")
            .all()
        )
        for session in sessions:
            session.status = "offline"
            session.disconnected_at = datetime.utcnow()
            self.db.add(
                OpenVpnConnectionLog(
                    server_id=session.server_id,
                    account_id=session.account_id,
                    user_id=session.user_id,
                    action="kicked",
                    real_ip=session.real_ip,
                    virtual_ip=session.virtual_ip,
                    result="success",
                    message="用户已禁用或删除",
                )
            )
        self.db.add(account)

    def reset_password(self, user_id: int, password: str, actor_id: int) -> User:
        user = self.get_required(user_id)
        if user.username == self.protected_username:
            raise ConflictError("admin 用户不能重置密码")
        user.hashed_password = self.hash_password(password)
        user.updated_by = actor_id
        return self.commit(user, "重置密码失败")

    def replace_departments(self, user_id: int, department_ids: Optional[list[int]]) -> None:
        self.db.query(UserDepartment).filter(UserDepartment.user_id == user_id).delete()
        valid_ids = self.get_valid_department_ids(department_ids)
        for index, department_id in enumerate(valid_ids):
            self.db.add(
                UserDepartment(
                    user_id=user_id,
                    department_id=department_id,
                    is_primary=index == 0,
                )
            )
        self.db.commit()

    def replace_roles(self, user_id: int, role_ids: Optional[list[int]]) -> None:
        self.db.query(UserRole).filter(UserRole.user_id == user_id).delete()
        for role_id in self.get_valid_role_ids(role_ids):
            self.db.add(UserRole(user_id=user_id, role_id=role_id))
        self.db.commit()

    def replace_positions(self, user_id: int, position_ids: Optional[list[int]]) -> None:
        self.db.query(UserPosition).filter(UserPosition.user_id == user_id).delete()
        for position_id in self.get_valid_position_ids(position_ids):
            self.db.add(UserPosition(user_id=user_id, position_id=position_id))
        self.db.commit()

    def assign_roles(self, user_id: int, role_ids: Optional[list[int]], actor_id: int) -> User:
        user = self.get_required(user_id)
        if user.username == self.protected_username:
            raise ConflictError("admin 用户不能分配角色")
        self.replace_roles(user.id, role_ids)
        user.updated_by = actor_id
        return self.commit(user, "分配角色失败")

    def get_valid_department_ids(self, department_ids: Optional[list[int]]) -> list[int]:
        ids = self.unique_ids(department_ids)
        if not ids:
            return []
        rows = (
            self.db.query(Department.id)
            .filter(
                Department.id.in_(ids),
                Department.is_active.is_(True),
                Department.is_deleted.is_(False),
            )
            .all()
        )
        valid_id_set = {row.id for row in rows}
        return [department_id for department_id in ids if department_id in valid_id_set]

    def get_valid_role_ids(self, role_ids: Optional[list[int]]) -> list[int]:
        ids = self.unique_ids(role_ids)
        if not ids:
            return []
        rows = (
            self.db.query(Role.id)
            .filter(
                Role.id.in_(ids),
                Role.is_active.is_(True),
                Role.is_deleted.is_(False),
            )
            .all()
        )
        valid_id_set = {row.id for row in rows}
        return [role_id for role_id in ids if role_id in valid_id_set]

    def get_valid_position_ids(self, position_ids: Optional[list[int]]) -> list[int]:
        ids = self.unique_ids(position_ids)
        if not ids:
            return []
        rows = (
            self.db.query(Position.id)
            .filter(
                Position.id.in_(ids),
                Position.status == 0,
                Position.is_deleted.is_(False),
            )
            .all()
        )
        valid_id_set = {row.id for row in rows}
        return [position_id for position_id in ids if position_id in valid_id_set]

    @staticmethod
    def unique_ids(values: Optional[list[int]]) -> list[int]:
        ids = []
        for value in values or []:
            if value and value not in ids:
                ids.append(value)
        return ids

    def list_departments(self, user_id: int) -> list[Department]:
        self.get_required(user_id)
        return (
            self.db.query(Department)
            .join(UserDepartment, UserDepartment.department_id == Department.id)
            .filter(
                UserDepartment.user_id == user_id,
                Department.is_active.is_(True),
                Department.is_deleted.is_(False),
            )
            .order_by(UserDepartment.is_primary.desc(), Department.id.asc())
            .all()
        )

    def list_roles(self, user_id: int) -> list[Role]:
        self.get_required(user_id)
        return (
            self.db.query(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(
                UserRole.user_id == user_id,
                Role.is_active.is_(True),
                Role.is_deleted.is_(False),
            )
            .order_by(Role.id.asc())
            .all()
        )

    def list_positions(self, user_id: int) -> list[Position]:
        self.get_required(user_id)
        return (
            self.db.query(Position)
            .join(UserPosition, UserPosition.position_id == Position.id)
            .filter(
                UserPosition.user_id == user_id,
                Position.status == 0,
                Position.is_deleted.is_(False),
            )
            .order_by(Position.sort_order.asc(), Position.id.asc())
            .all()
        )

    def authenticate(self, username: str, password: str) -> Optional[User]:
        user = self.get_by_username(username)
        if user and self.verify_password(password, user.hashed_password):
            return user
        return None
