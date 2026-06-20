from typing import Optional

from ..models.department import Department
from ..models.user import User
from ..models.user_department import UserDepartment
from .base_service import ConflictError
from .named_code_service import NamedCodeService


class DepartmentService(NamedCodeService):
    model = Department
    resource_name = "部门"
    name_label = "部门名称"
    code_label = "部门编码"

    def validate_parent(self, parent_id: Optional[int], current_id: Optional[int] = None) -> Optional[int]:
        if parent_id is None:
            return None
        if current_id is not None and parent_id == current_id:
            raise ConflictError("上级部门不能选择当前部门")
        parent = self.get(parent_id)
        if parent is None:
            raise ConflictError("上级部门不存在或已删除")
        if current_id is not None and parent_id in self.collect_descendant_ids(current_id):
            raise ConflictError("上级部门不能选择当前部门的子部门")
        return parent_id

    def create_item(self, item_create, actor_id: int):
        self.ensure_unique(item_create.name, item_create.code)
        item = self.model(
            parent_id=self.validate_parent(item_create.parent_id),
            name=item_create.name,
            code=item_create.code,
            description=item_create.description,
            is_active=item_create.is_active,
            created_by=actor_id,
            updated_by=actor_id,
        )
        return self.commit(item, f"{self.name_label}或{self.code_label}已存在")

    def update_item(self, item_id: int, item_update, actor_id: int):
        item = self.get_required(item_id, include_deleted=True)
        self.ensure_unique(item_update.name, item_update.code, current_id=item.id)

        update_data = item_update.model_dump(exclude_unset=True)
        if "parent_id" in update_data:
            update_data["parent_id"] = self.validate_parent(update_data["parent_id"], current_id=item.id)
        if update_data.get("is_deleted") is True:
            if not item.is_deleted:
                self.ensure_department_tree_has_no_users(item.id)
            update_data["is_active"] = False
            descendant_ids = self.collect_descendant_ids(item.id)
            if descendant_ids:
                descendants = self.db.query(Department).filter(Department.id.in_(descendant_ids)).all()
                for descendant in descendants:
                    descendant.is_deleted = True
                    descendant.is_active = False
                    descendant.updated_by = actor_id
        for field_name, value in update_data.items():
            setattr(item, field_name, value)
        item.updated_by = actor_id
        return self.commit(item, f"{self.name_label}或{self.code_label}已存在")

    def collect_descendant_ids(self, department_id: int) -> set[int]:
        descendant_ids: set[int] = set()
        pending_ids = [department_id]
        while pending_ids:
            child_ids = [
                item.id
                for item in self.db.query(Department.id)
                .filter(
                    Department.parent_id.in_(pending_ids),
                    Department.is_deleted.is_(False),
                )
                .all()
            ]
            child_ids = [child_id for child_id in child_ids if child_id not in descendant_ids]
            descendant_ids.update(child_ids)
            pending_ids = child_ids
        return descendant_ids

    def get_department_tree_ids(self, department_id: int) -> set[int]:
        return {department_id, *self.collect_descendant_ids(department_id)}

    def ensure_department_tree_has_no_users(self, department_id: int) -> None:
        department_ids = self.get_department_tree_ids(department_id)
        user_count = (
            self.db.query(UserDepartment)
            .join(User, User.id == UserDepartment.user_id)
            .filter(
                UserDepartment.department_id.in_(department_ids),
                User.is_deleted.is_(False),
            )
            .count()
        )
        if user_count > 0:
            raise ConflictError("当前部门或子部门下存在人员，不能删除")

    def delete_item(self, item_id: int, actor_id: int):
        item = self.get_required(item_id)
        self.ensure_department_tree_has_no_users(item.id)

        department_ids = self.get_department_tree_ids(item.id)
        departments = self.db.query(Department).filter(Department.id.in_(department_ids)).all()
        for department in departments:
            department.is_deleted = True
            department.is_active = False
            department.updated_by = actor_id
        try:
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            raise ConflictError("部门删除失败") from exc
        self.db.refresh(item)
        return item
