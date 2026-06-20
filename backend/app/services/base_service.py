from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class ConflictError(Exception):
    pass


class NotFoundError(Exception):
    pass


class BaseService(Generic[ModelT]):
    model: Type[ModelT]
    resource_name: str

    def __init__(self, db: Session):
        self.db = db

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_disabled: bool = False,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        query = self.db.query(self.model)
        if hasattr(self.model, "is_active") and not include_disabled:
            query = query.filter(self.model.is_active.is_(True))
        if hasattr(self.model, "is_deleted") and not include_deleted:
            query = query.filter(self.model.is_deleted.is_(False))
        return query.offset(skip).limit(limit).all()

    def get(self, item_id: int, include_deleted: bool = False) -> Optional[ModelT]:
        query = self.db.query(self.model).filter(self.model.id == item_id)
        if hasattr(self.model, "is_deleted") and not include_deleted:
            query = query.filter(self.model.is_deleted.is_(False))
        return query.first()

    def get_required(self, item_id: int, include_deleted: bool = False) -> ModelT:
        item = self.get(item_id, include_deleted=include_deleted)
        if item is None:
            raise NotFoundError(f"{self.resource_name}不存在")
        return item

    def commit(self, item: ModelT, conflict_message: str) -> ModelT:
        self.db.add(item)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictError(conflict_message) from exc
        self.db.refresh(item)
        return item
