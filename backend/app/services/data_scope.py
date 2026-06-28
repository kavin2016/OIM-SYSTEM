from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..models.department import Department
from ..models.user import User
from ..models.user_data_scope_department import UserDataScopeDepartment
from ..models.user_department import UserDepartment


def _descendant_department_ids(db: Session, department_ids: list[int]) -> set[int]:
    scoped_ids = {department_id for department_id in department_ids if department_id}
    pending_ids = list(scoped_ids)
    while pending_ids:
        children = (
            db.query(Department.id)
            .filter(
                Department.parent_id.in_(pending_ids),
                Department.is_deleted.is_(False),
            )
            .all()
        )
        pending_ids = []
        for row in children:
            child_id = row[0]
            if child_id not in scoped_ids:
                scoped_ids.add(child_id)
                pending_ids.append(child_id)
    return scoped_ids


def user_department_scope_ids(db: Session, user: User) -> Optional[list[int]]:
    if user.is_admin:
        return None
    configured_ids = [
        row[0]
        for row in db.query(UserDataScopeDepartment.department_id)
        .filter(UserDataScopeDepartment.user_id == user.id)
        .all()
    ]
    if configured_ids:
        return sorted(_descendant_department_ids(db, configured_ids))
    return []


def scoped_user_ids(
    db: Session,
    user: User,
    *,
    user_id: Optional[int] = None,
    department_id: Optional[int] = None,
) -> Optional[list[int]]:
    requested_department_ids = (
        _descendant_department_ids(db, [department_id])
        if department_id
        else None
    )

    if user.is_admin:
        if user_id:
            return [user_id]
        if requested_department_ids is None:
            return None
        return _user_ids_in_departments(db, requested_department_ids)

    scope_department_ids = set(user_department_scope_ids(db, user) or [])
    if requested_department_ids is not None:
        scope_department_ids = scope_department_ids.intersection(requested_department_ids)

    allowed_user_ids = set(_user_ids_in_departments(db, scope_department_ids)) if scope_department_ids else set()
    allowed_user_ids.add(user.id)

    if user_id:
        return [user_id] if user_id in allowed_user_ids else []
    return sorted(allowed_user_ids)


def scoped_department_ids(
    db: Session,
    user: User,
    *,
    department_id: Optional[int] = None,
) -> Optional[list[int]]:
    requested_ids = _descendant_department_ids(db, [department_id]) if department_id else None
    if user.is_admin:
        return sorted(requested_ids) if requested_ids is not None else None

    allowed_ids = set(user_department_scope_ids(db, user) or [])
    if requested_ids is not None:
        allowed_ids = allowed_ids.intersection(requested_ids)
    return sorted(allowed_ids)


def ensure_user_in_scope(
    db: Session,
    user: User,
    target_user_id: Optional[int],
    *,
    detail: str = "无权访问该用户数据",
) -> None:
    if user.is_admin:
        return
    if not target_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    if target_user_id not in set(scoped_user_ids(db, user) or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def ensure_departments_in_scope(
    db: Session,
    user: User,
    department_ids: list[int],
    *,
    detail: str = "无权访问该部门数据",
) -> None:
    if user.is_admin or not department_ids:
        return
    allowed_ids = set(user_department_scope_ids(db, user) or [])
    if any(department_id not in allowed_ids for department_id in department_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def _user_ids_in_departments(db: Session, department_ids: set[int]) -> list[int]:
    if not department_ids:
        return []
    return [
        row[0]
        for row in db.query(UserDepartment.user_id)
        .join(User, User.id == UserDepartment.user_id)
        .filter(
            UserDepartment.department_id.in_(department_ids),
            User.is_deleted.is_(False),
        )
        .distinct()
        .all()
    ]
