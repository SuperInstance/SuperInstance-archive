"""
Base repository class providing common CRUD operations and async database session management.

This module implements the repository pattern with async support, providing a clean
abstraction layer over SQLAlchemy operations.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.base_class import Base
from app.core.logging import get_logger

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base repository with common CRUD operations.

    Provides async database operations with proper session management,
    error handling, and logging.
    """

    def __init__(self, model: Type[ModelType], db_session: AsyncSession):
        """
        Initialize repository with model and database session.

        Args:
            model: SQLAlchemy model class
            db_session: Async database session
        """
        self.model = model
        self.db_session = db_session
        self.logger = get_logger(f"{__name__}.{model.__name__}")

    async def create(
        self,
        *,
        obj_in: CreateSchemaType,
        **kwargs
    ) -> ModelType:
        """
        Create a new record.

        Args:
            obj_in: Pydantic model with creation data
            **kwargs: Additional fields to set

        Returns:
            Created model instance
        """
        try:
            obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
            obj_data.update(kwargs)

            db_obj = self.model(**obj_data)
            self.db_session.add(db_obj)
            await self.db_session.flush()
            await self.db_session.refresh(db_obj)

            self.logger.info(f"Created {self.model.__name__} with id: {getattr(db_obj, 'id', 'unknown')}")
            return db_obj

        except Exception as e:
            self.logger.error(f"Failed to create {self.model.__name__}: {str(e)}")
            await self.db_session.rollback()
            raise

    async def get(
        self,
        id: Union[UUID, str, int],
        *,
        options: Optional[List] = None
    ) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            id: Primary key value
            options: SQLAlchemy options for eager loading

        Returns:
            Model instance or None if not found
        """
        try:
            query = select(self.model).where(self.model.id == id)
            if options:
                query = query.options(*options)

            result = await self.db_session.execute(query)
            db_obj = result.scalar_one_or_none()

            if db_obj:
                self.logger.debug(f"Retrieved {self.model.__name__} with id: {id}")
            else:
                self.logger.warning(f"{self.model.__name__} with id: {id} not found")

            return db_obj

        except Exception as e:
            self.logger.error(f"Failed to get {self.model.__name__} with id {id}: {str(e)}")
            raise

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        options: Optional[List] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        Get multiple records with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            options: SQLAlchemy options for eager loading
            filters: Dictionary of field filters
            order_by: Field name to order by

        Returns:
            List of model instances
        """
        try:
            query = select(self.model)

            # Apply filters
            if filters:
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        query = query.where(getattr(self.model, field) == value)

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by))

            # Apply options for eager loading
            if options:
                query = query.options(*options)

            # Apply pagination
            query = query.offset(skip).limit(limit)

            result = await self.db_session.execute(query)
            objects = result.scalars().all()

            self.logger.debug(f"Retrieved {len(objects)} {self.model.__name__} records")
            return list(objects)

        except Exception as e:
            self.logger.error(f"Failed to get multiple {self.model.__name__}: {str(e)}")
            raise

    async def update(
        self,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.

        Args:
            db_obj: Existing model instance
            obj_in: Pydantic model or dict with update data

        Returns:
            Updated model instance
        """
        try:
            if isinstance(obj_in, BaseModel):
                update_data = obj_in.model_dump(exclude_unset=True)
            else:
                update_data = obj_in

            for field, value in update_data.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)

            self.db_session.add(db_obj)
            await self.db_session.flush()
            await self.db_session.refresh(db_obj)

            self.logger.info(f"Updated {self.model.__name__} with id: {getattr(db_obj, 'id', 'unknown')}")
            return db_obj

        except Exception as e:
            self.logger.error(f"Failed to update {self.model.__name__}: {str(e)}")
            await self.db_session.rollback()
            raise

    async def delete(self, *, id: Union[UUID, str, int]) -> Optional[ModelType]:
        """
        Delete a record by ID.

        Args:
            id: Primary key value

        Returns:
            Deleted model instance or None if not found
        """
        try:
            obj = await self.get(id=id)
            if obj:
                await self.db_session.delete(obj)
                await self.db_session.flush()

                self.logger.info(f"Deleted {self.model.__name__} with id: {id}")
                return obj
            else:
                self.logger.warning(f"Cannot delete {self.model.__name__} with id {id}: not found")
                return None

        except Exception as e:
            self.logger.error(f"Failed to delete {self.model.__name__} with id {id}: {str(e)}")
            await self.db_session.rollback()
            raise

    async def count(
        self,
        *,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count records with optional filtering.

        Args:
            filters: Dictionary of field filters

        Returns:
            Number of matching records
        """
        try:
            query = select(func.count(self.model.id))

            # Apply filters
            if filters:
                conditions = []
                for field, value in filters.items():
                    if hasattr(self.model, field):
                        conditions.append(getattr(self.model, field) == value)
                if conditions:
                    query = query.where(and_(*conditions))

            result = await self.db_session.execute(query)
            count = result.scalar()

            self.logger.debug(f"Counted {count} {self.model.__name__} records")
            return count

        except Exception as e:
            self.logger.error(f"Failed to count {self.model.__name__}: {str(e)}")
            raise

    async def exists(self, *, id: Union[UUID, str, int]) -> bool:
        """
        Check if a record exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if record exists, False otherwise
        """
        try:
            query = select(func.count(self.model.id)).where(self.model.id == id)
            result = await self.db_session.execute(query)
            count = result.scalar()
            return count > 0

        except Exception as e:
            self.logger.error(f"Failed to check existence of {self.model.__name__} with id {id}: {str(e)}")
            raise

    async def get_by_field(
        self,
        *,
        field_name: str,
        field_value: Any,
        options: Optional[List] = None
    ) -> Optional[ModelType]:
        """
        Get a record by a specific field value.

        Args:
            field_name: Name of the field to search by
            field_value: Value to search for
            options: SQLAlchemy options for eager loading

        Returns:
            Model instance or None if not found
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(f"Model {self.model.__name__} does not have field {field_name}")

            query = select(self.model).where(getattr(self.model, field_name) == field_value)
            if options:
                query = query.options(*options)

            result = await self.db_session.execute(query)
            db_obj = result.scalar_one_or_none()

            if db_obj:
                self.logger.debug(f"Retrieved {self.model.__name__} by {field_name}: {field_value}")

            return db_obj

        except Exception as e:
            self.logger.error(f"Failed to get {self.model.__name__} by {field_name}: {str(e)}")
            raise

    async def bulk_create(
        self,
        *,
        objects_in: List[CreateSchemaType]
    ) -> List[ModelType]:
        """
        Create multiple records in a single transaction.

        Args:
            objects_in: List of Pydantic models with creation data

        Returns:
            List of created model instances
        """
        try:
            db_objects = []
            for obj_in in objects_in:
                obj_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
                db_objects.append(self.model(**obj_data))

            self.db_session.add_all(db_objects)
            await self.db_session.flush()

            # Refresh all objects to get their IDs
            for obj in db_objects:
                await self.db_session.refresh(obj)

            self.logger.info(f"Bulk created {len(db_objects)} {self.model.__name__} records")
            return db_objects

        except Exception as e:
            self.logger.error(f"Failed to bulk create {self.model.__name__}: {str(e)}")
            await self.db_session.rollback()
            raise