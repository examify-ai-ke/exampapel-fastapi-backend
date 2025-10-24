from typing import Optional
from uuid import UUID
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
# from app.deps import user_deps, deps
from app.api import deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from app.utils.minio_client import MinioClient
from fastapi_pagination import Params
from fastapi import (
    APIRouter,
    File,
    Response,
    UploadFile,
    status,
)
from app import crud
from app.api import deps
from app.models.module_model import Module
from app.models.user_model import User
from app.models.course_model import Course
from app.schemas.common_schema import IOrderEnum
from app.schemas.module_schema import (
    ModuleCreate,
    ModuleRead,
    ModuleUpdate,
    ModuleAddCourses,
    
)
from app.schemas.response_schema import (
    IDeleteResponseBase,
    IGetResponseBase,
    IGetResponsePaginated,
    IPostResponseBase,
    IPutResponseBase,
    create_response,
)
from app.schemas.role_schema import IRoleEnum
from app.core.authz import is_authorized
from app.crud import module as crud_module, course as crud_course
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlalchemy import or_
from fastapi_cache.decorator import cache

router = APIRouter()


@router.get("")
# @cache(expire=300)
async def get_module_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ModuleRead]:
    """
    Gets a paginated list of modules
    """
    from app.models.exam_paper_model import ExamPaper, ExamTitle
    
    query = (
        select(Module)
        .options(
            selectinload(Module.courses),
            selectinload(Module.exam_papers).selectinload(ExamPaper.title),
            selectinload(Module.image),
            selectinload(Module.created_by),
        )
    )
    modules = await crud.module.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=modules)


@router.get("/search")
# @cache(expire=180)
async def search_modules(
    q: str = Query(default=None, description="Search query for modules"),
    course_id: UUID = Query(default=None, description="Filter by course ID"),
    unit_code: str = Query(default=None, description="Filter by unit code"),
    sort_by: str = Query(default="name", description="Sort by: name, unit_code, created_at"),
    sort_order: str = Query(default="asc", description="Sort order: asc, desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ModuleRead]:
    """
    Search modules with filtering and sorting
    """
    from app.models.module_model import CourseModuleLink
    from app.models.exam_paper_model import ExamPaper
    
    query = (
        select(Module)
        .options(
            selectinload(Module.courses),
            selectinload(Module.exam_papers).selectinload(ExamPaper.title),
            selectinload(Module.image),
            selectinload(Module.created_by),
        )
    )
    
    if q:
        query = query.filter(
            or_(
                Module.name.ilike(f"%{q}%"),
                Module.unit_code.ilike(f"%{q}%"),
                Module.description.ilike(f"%{q}%"),
                Module.slug.ilike(f"%{q}%"),
            )
        )
    
    if course_id:
        query = query.join(CourseModuleLink).filter(
            CourseModuleLink.course_id == course_id
        )
    
    if unit_code:
        query = query.filter(Module.unit_code.ilike(f"%{unit_code}%"))
    
    if sort_by == "unit_code":
        sort_field = Module.unit_code
    elif sort_by == "created_at":
        sort_field = Module.created_at
    else:
        sort_field = Module.name
    
    query = query.order_by(sort_field.asc() if sort_order == "asc" else sort_field.desc())
    
    modules = await crud.module.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=modules)


@router.get("/get_by_created_at")
async def get_module_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
) -> IGetResponsePaginated[ModuleRead]:
    """
    Gets a paginated list of modules ordered by created at datetime
    """
    modules = await crud.module.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=modules)


@router.get("/get_by_id/{module_id}")
@cache(expire=600)
async def get_module_by_id(
    module_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[ModuleRead]:
    """
    Gets a course module by its id
    """
    from app.models.exam_paper_model import ExamPaper
    
    module = await crud.module.get(
        id=module_id,
        db_session=db_session,
        options=[
            selectinload(Module.courses),
            selectinload(Module.exam_papers).selectinload(ExamPaper.title),
            selectinload(Module.image),
            selectinload(Module.created_by),
        ],
    )
    if not module:
        raise IdNotFoundException(Module, module_id)

    return create_response(data=module)


@router.get("/get_by_slug/{module_slug}")
@cache(expire=600)
async def get_module_by_slug(
    module_slug: str,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[list[ModuleRead]]:
    """
    Gets a module by slug
    """
    module = await crud.module.get_module_by_slug(
        slug=module_slug,
        db_session=db_session,
    )
    if not module:
        raise NameNotFoundException(Module, module_slug)

    return create_response(data=module)


@router.post("")
async def create_module(
    module: ModuleCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[ModuleRead]:
    """
    Creates a new Course Module

    Required roles:
    - admin
    - manager
    """

    module = await crud.module.create(
        obj_in=module, created_by_id=current_user.id
    )
    return create_response(data=module)


@router.put("/{module_id}")
async def update_module(
    module_id: UUID,
    module: ModuleUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[ModuleRead]:
    """
    Updates a module by its id

    Required roles:
    - admin
    - manager
    """
    current_module = await crud.module.get(id=module_id)
    if not current_module:
        raise IdNotFoundException(Module, module_id)

    module_updated = await crud.module.update(
        obj_new=module, obj_current=current_module
    )
    return create_response(data=module_updated)


@router.delete("/{module_id}")
async def remove_course_module(
    module_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[ModuleRead]:
    """
    Deletes a module by its id

    Required roles:
    - admin
    - manager
    """
    current_module = await crud.module.get(id=module_id)
    if not current_module:
        raise IdNotFoundException(Module, module_id)
    module = await crud.module.remove(id=module_id)
    return create_response(data=module)


@router.post("/{module_id}/courses", response_model=IPostResponseBase[ModuleRead])
async def add_courses_to_module(
    module_id: UUID,
    payload: ModuleAddCourses = Body(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[ModuleRead]:
    """
    Associate multiple Courses with a Module by their IDs.

    Required roles:
    - admin
    - manager
    """
    module = await crud.module.get(
        id=module_id,
        db_session=db_session,
        options=[selectinload(Module.courses)]
    )
    if not module:
        raise IdNotFoundException(Module, module_id)

    courses_to_add = []
    not_found_course_ids = []
    already_linked_course_ids = []
    current_linked_ids = {course.id for course in module.courses}

    for course_id in payload.course_ids:
        if course_id in current_linked_ids:
            already_linked_course_ids.append(str(course_id))
            continue

        course = await crud_course.course.get(id=course_id, db_session=db_session)
        if not course:
            not_found_course_ids.append(str(course_id))
        else:
            courses_to_add.append(course)

    if not_found_course_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Courses not found with IDs: {', '.join(not_found_course_ids)}"
        )

    if already_linked_course_ids:
        print(f"Courses already linked and skipped: {', '.join(already_linked_course_ids)}")

    if courses_to_add:
        module.courses.extend(courses_to_add)
        db_session.add(module)
        await db_session.commit()
        await db_session.refresh(module)

        updated_module = await crud_module.module.get(
            id=module_id,
            db_session=db_session,
            options=[selectinload(Module.courses)]
        )
        return create_response(data=updated_module)
    else:
        return create_response(data=module)
