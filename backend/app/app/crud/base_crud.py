from app.models.module_model import Module
from app.models.exam_paper_model import ExamInstruction
from fastapi import HTTPException
from typing import Any, Generic, TypeVar
from uuid import UUID
from app.schemas.common_schema import IOrderEnum
from fastapi_pagination.ext.sqlmodel import paginate
from fastapi_async_sqlalchemy import db
from fastapi_pagination import Params, Page
from pydantic import BaseModel
from sqlmodel import SQLModel, select, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import Select
from sqlalchemy import exc
from sqlalchemy.orm import lazyload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload


ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
SchemaType = TypeVar("SchemaType", bound=BaseModel)
T = TypeVar("T", bound=SQLModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLModel model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model
        self.db = db

    def get_db(self) -> type(db):
        return self.db

    async def get(
        self, *, id: UUID | str, db_session: AsyncSession | None = None
    ) -> ModelType | None:
        db_session = db_session or self.db.session
        query = select(self.model).where(self.model.id == id)
        response = await db_session.execute(query)
        return response.unique().scalar_one_or_none()

    async def get_by_ids(
        self,
        *,
        list_ids: list[UUID | str],
        db_session: AsyncSession | None = None,
    ) -> list[ModelType] | None:
        db_session = db_session or self.db.session
        response = await db_session.execute(
            select(self.model).where(self.model.id.in_(list_ids))
        )
        return response.unique().scalars().all()

    async def get_count(
        self, db_session: AsyncSession | None = None
    ) -> ModelType | None:
        db_session = db_session or self.db.session
        response = await db_session.execute(
            select(func.count()).select_from(select(self.model).subquery())
        )
        return response.scalar_one()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        query: T | Select[T] | None = None,
        db_session: AsyncSession | None = None,
    ) -> list[ModelType]:
        db_session = db_session or self.db.session
        if query is None:
            query = select(self.model).offset(skip).limit(limit).order_by(self.model.id)
        response = await db_session.execute(query)
        print("get_multi()...called....")
        return response.scalars().all()

    async def get_multi_paginated(
        self,
        *,
        params: Params | None = Params(),
        query: T | Select[T] | None = None,
        db_session: AsyncSession | None = None,
    ) -> Page[ModelType]:
        db_session = db_session or self.db.session
        if query is None:
            query = select(self.model)

        output = await paginate(db_session, query, params)
        print("get_multi_paginated()....called...........")
        # print(output)
        return output

    async def get_multi_paginated_ordered(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        order_by: str | None = None,
        order: IOrderEnum | None = IOrderEnum.descendent,
        query: T | Select[T] | None = None,
        db_session: AsyncSession | None = None,
    ) -> Page[ModelType]:
        db_session = db_session or self.db.session
        params = Params(page=skip // limit + 1, size=limit)  # Convert skip/limit to page/size
        columns = self.model.__table__.columns

        if order_by is None or order_by not in columns:
            order_by = "created_at"

        if query is None:
            if order == IOrderEnum.ascendent:
                query = select(self.model).order_by(columns[order_by].asc())
            else:
                # print("get_multi_paginated_ordered() order_by created_at Desc......")
                query = select(self.model).order_by(columns[order_by].desc())

        return await paginate(db_session, query, params)

    async def get_multi_paginated_ordered_answers_with_children(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        order_by: str | None = None,
        order: IOrderEnum | None = IOrderEnum.descendent,
        query: T | Select[T] | None = None,
        db_session: AsyncSession | None = None,
    ) -> Page[ModelType]:
        db_session = db_session or self.db.session
        params = Params(page=skip // limit + 1, size=limit)  # Convert skip/limit to page/size
        columns = self.model.__table__.columns

        if order_by is None or order_by not in columns:
            order_by = "created_at"

        if query is None:
            if order == IOrderEnum.ascendent:
                # query = select(self.model).options(
                #     selectinload(self.model.children)
                # ).order_by(columns[order_by].asc())
                query = (
                    select(self.model)
                    .options(
                        selectinload(self.model.children),
                        selectinload(self.model.parent),
                    )
                    .order_by(columns[order_by].asc())
                )
            else:
                # query = select(self.model).options(
                #     selectinload(self.model.children)
                # ).order_by(columns[order_by].desc())
                query = (
                    select(self.model)
                    .options(
                        selectinload(self.model.children),
                        selectinload(self.model.parent),
                    )
                    .order_by(columns[order_by].desc())
                )
        else:
            # If a custom query is provided, add the eager loading option
            query = query.options(selectinload(self.model.children))

        return await paginate(db_session, query, params)

    async def get_multi_ordered(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        order_by: str | None = None,
        order: IOrderEnum | None = IOrderEnum.ascendent,
        db_session: AsyncSession | None = None,
    ) -> list[ModelType]:
        db_session = db_session or self.db.session

        columns = self.model.__table__.columns

        if order_by is None or order_by not in columns:
            order_by = "id"

        if order == IOrderEnum.ascendent:
            query = (
                select(self.model)
                .offset(skip)
                .limit(limit)
                .order_by(columns[order_by].asc())
            )
        else:
            query = (
                select(self.model)
                .offset(skip)
                .limit(limit)
                .order_by(columns[order_by].desc())
            )
        # print("get_multi_ordered()......called.............")
        response = await db_session.execute(query)
        # print(response)
        return response.scalars().unique().all()

    async def create(
        self,
        *,
        obj_in: CreateSchemaType | ModelType,
        created_by_id: UUID | str | None = None,
        db_session: AsyncSession | None = None,
    ) -> ModelType:
        db_session = db_session or self.db.session
        db_obj = self.model.model_validate(obj_in)  # type: ignore

        if created_by_id:
            db_obj.created_by_id = created_by_id

        try:
            db_session.add(db_obj)
            await db_session.commit()
        except exc.IntegrityError:
            db_session.rollback()
            raise HTTPException(
                status_code=409,
                detail="Resource already exists",
            )
        await db_session.refresh(db_obj)
        return db_obj

    # async def create_with_alpha_numbering(
    #     self,
    #     *,
    #     obj_in: CreateSchemaType | ModelType,
    #     created_by_id: UUID | str | None = None,
    #     db_session: AsyncSession | None = None,
    # ) -> ModelType:
    #     columns = self.model.__table__.columns
    #     db_session = db_session or self.db.session
    #     db_obj = self.model.model_validate(obj_in)  # type: ignore
    #     query = (
    #         select(self.model)
    #         .filter(
    #             self.model.exam_paper_id == obj_in.exam_paper_id,
    #             self.model.question_set_id == obj_in.question_set_id,
    #             self.model.order_within_question_set != None  # Filter out None values
    #         )
    #         .order_by(columns["order_within_question_set"].asc())
    #         )
    #     existing_main_questions = (await db_session.execute(query)).scalars().unique().all()
    #     if existing_main_questions:
    #         last_order_value = (
    #             existing_main_questions[-1].order_within_question_set
    #             if existing_main_questions
    #             else None
    #         )
    #         if last_order_value is not None:
    #             next_order_char = chr(ord(last_order_value) + 1)
    #             db_obj.order_within_question_set= next_order_char
    #         else:
    #             db_obj.order_within_question_set="a"
    #     else:
    #         db_obj.order_within_question_set = "a"
    #     if created_by_id:
    #         db_obj.created_by_id = created_by_id

    #     try:
    #         # Calculate ordering

    #         # db_obj.order_within_question_set = await self.assign_alphabetical_ordering(
    #         #     related_list_object1=related_model1
    #         # )
    #         db_session.add(db_obj)
    #         await db_session.commit()
    #     except exc.IntegrityError:
    #         db_session.rollback()
    #         raise HTTPException(
    #             status_code=409,
    #             detail="Resource already exists",
    #         )
    #     await db_session.refresh(db_obj)
    #     return db_obj

    # async def assign_alphabetical_ordering(self,*,related_list_object1: ModelType = None):
    #     if related_list_object1 is not None:
    #         existing_main_questions = related_list_object1.main_questions
    #         last_order_value = (
    #             existing_main_questions[-1].order_within_question_set
    #             if existing_main_questions
    #             else None
    #         )
    #         if last_order_value is not None:
    #             next_order_char = chr(ord(last_order_value) + 1)
    #             return next_order_char
    #         else:
    #             return "a"

    async def create_with_related_list(
        self,
        *,
        obj_in: CreateSchemaType | ModelType,
        related_list_object1: ModelType = None, #Instructions Model
        related_list_object2: ModelType = None, #Module Model
        related_object3: ModelType = None, #course Model
        items1: str = None,
        items2: str = None,
        # items3: str = None,
        created_by_id: UUID | str | None = None,
        db_session: AsyncSession | None = None,
    ) -> ModelType:
        db_session = db_session or self.db.session
        db_obj = self.model.model_validate(obj_in)  # type: ignore

        if created_by_id:
            db_obj.created_by_id = created_by_id
        if related_list_object1:
            attr1 = getattr(db_obj, items1)
            # Then, extend the list
            attr1.extend(related_list_object1)
            # db_obj.instructions.extend(related_list_object1)
        if related_list_object2:
            attr2 = getattr(db_obj, items2)
            attr2.extend(related_list_object2)
            # db_obj.modules.extend(related_list_object2)
            # getattr(db_obj.get(items2,""), "extend")(related__list_object2)
        if related_object3:
            db_obj.append(related_object3)

        try:
            # Calculate the Hash for all the Table fields: this prevents us from dublicates.
            db_obj.hash_code = db_obj.calculate_hash
            db_session.add(db_obj)
            await db_session.commit()
        except exc.IntegrityError:
            db_session.rollback()
            raise HTTPException(
                status_code=409,
                detail="Resource already exists",
            )
        await db_session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        *,
        obj_current: ModelType,
        obj_new: UpdateSchemaType | dict[str, Any] | ModelType,
        db_session: AsyncSession | None = None,
    ) -> ModelType:
        db_session = db_session or self.db.session

        if isinstance(obj_new, dict):
            update_data = obj_new

        else:
            update_data = obj_new.dict(
                exclude_unset=True
            )  # This tells Pydantic to not include the values that were not sent

        for field in update_data:
            # print(field)
            setattr(obj_current, field, update_data[field])

        db_session.add(obj_current)
        await db_session.commit()

        await db_session.refresh(obj_current)
        return obj_current

    async def add_related(
        self,
        *,
        appended_parent_object: ModelType,
        # obj_new: UpdateSchemaType | dict[str, Any] | ModelType,
        db_session: AsyncSession | None = None,
    ) -> ModelType:
        db_session = db_session or self.db.session
        appended_parent_object
        await db_session.commit()
        await db_session.refresh(appended_parent_object)
        return appended_parent_object

 

    async def remove(
        self, *, id: UUID | str, db_session: AsyncSession | None = None
    ) -> ModelType:
        db_session = db_session or self.db.session
        response = await db_session.execute(
            select(self.model).where(self.model.id == id)
        )
        obj = response.scalars().first()

        if not obj:
            raise ValueError(f"Object with id {id} not found")

        await db_session.delete(obj)
        await db_session.commit()

        return obj
