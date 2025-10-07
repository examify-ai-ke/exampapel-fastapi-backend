from uuid import UUID
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from app.models.programme_model import Programme
from app.schemas.programme_schema import ProgrammeCreate
from app.models.user_model import User
from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.minio_client import MinioClient
from fastapi_pagination import Params
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Query,
    Response,
    UploadFile,
    status,
)
from app import crud
from app.api import deps
from app.models.department_model import Department
from app.models.faculty_model import Faculty
from app.schemas.common_schema import IOrderEnum
from app.schemas.department_schema import (
    DepartmentRead,
    DepartmentCreate,
    DepartmentUpdate,
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
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlalchemy import or_
from fastapi_cache.decorator import cache

router = APIRouter()


@router.get("")
# @cache(expire=300)
async def get_department_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[DepartmentRead]:
    """
    Gets a paginated list of departments
    """
    query = (
        select(Department)
        .options(
            selectinload(Department.faculty).load_only(
                Faculty.id, Faculty.name, Faculty.slug
            ),
            selectinload(Department.programmes).load_only(
                Programme.id, Programme.name, Programme.slug
            ),
            selectinload(Department.image),
            selectinload(Department.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
        )
    )
    departments = await crud.department.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=departments)


@router.get("/search")
# @cache(expire=180)
async def search_departments(
    q: str = Query(default=None, description="Search query for departments"),
    faculty_id: UUID = Query(default=None, description="Filter by faculty ID"),
    institution_id: UUID = Query(default=None, description="Filter by institution ID (via faculty)"),
    sort_by: str = Query(default="name", description="Sort by: name, created_at"),
    sort_order: str = Query(default="asc", description="Sort order: asc, desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[DepartmentRead]:
    """
    Search departments with filtering and sorting
    """
    from app.models.institution_model import InstitutionFacultyLink
    
    query = (
        select(Department)
        .options(
            selectinload(Department.faculty).load_only(
                Faculty.id, Faculty.name, Faculty.slug
            ),
            selectinload(Department.programmes).load_only(
                Programme.id, Programme.name, Programme.slug
            ),
            selectinload(Department.image),
            selectinload(Department.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
        )
    )
    
    if q:
        query = query.filter(
            or_(
                Department.name.ilike(f"%{q}%"),
                Department.description.ilike(f"%{q}%"),
                Department.slug.ilike(f"%{q}%"),
            )
        )
    
    if faculty_id:
        query = query.filter(Department.faculty_id == faculty_id)
    
    if institution_id:
        query = query.join(Faculty).join(InstitutionFacultyLink).filter(
            InstitutionFacultyLink.institution_id == institution_id
        )
    
    sort_field = Department.name if sort_by == "name" else Department.created_at
    query = query.order_by(sort_field.asc() if sort_order == "asc" else sort_field.desc())
    
    departments = await crud.department.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=departments)


@router.get("/get_by_created_at")
async def get_departments_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[DepartmentRead]:
    """
    Gets a paginated list of  departments ordered by created at datetime
    """
    departments = await crud.department.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=departments)


@router.get("/get_by_id/{department_id}")
# @cache(expire=600)
async def get_department_by_id(
    department_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[DepartmentRead]:
    """
    Gets a department by its id
    """
    department = await crud.department.get(
        id=department_id,
        db_session=db_session,
        options=[
            selectinload(Department.faculty),
            selectinload(Department.programmes),
            selectinload(Department.image),
            selectinload(Department.created_by),
        ],
    )
    if not department:
        raise IdNotFoundException(Department, department_id)

    # print_hero.delay(hero.id)
    return create_response(data=department)


@router.get("/get_by_slug/{department_slug}")
@cache(expire=600)
async def get_department_by_slug(
    department_slug: str,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[list[DepartmentRead]]:
    """
    Gets a department by slug
    """
    department_frm_db = await crud.department.get_department_by_slug(
        slug=department_slug,
        db_session=db_session,
    )
    if not department_frm_db:
        raise NameNotFoundException(Department, department_slug)

    return create_response(data=department_frm_db)


@router.post("")
async def create_department(
    department: DepartmentCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[DepartmentRead]:
    """
    Creates a new department

    Required roles:
    - admin
    - manager
    """
    # print(department)
    _department = await crud.department.create(
        obj_in=department, created_by_id=current_user.id
    )
    return create_response(data=_department)


@router.put("/{department_id}")
async def update_department(
    department_id: UUID,
    department: DepartmentUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[DepartmentRead]:
    """
    Updates a department by its id

    Required roles:
    - admin
    - manager
    """
    current_dept = await crud.department.get(id=department_id)
    if not current_dept:
        raise IdNotFoundException(Department, department_id)
    # if not is_authorized(current_user, "read", current_dept):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this Department because you did not created it",
    #     )

    department_updated = await crud.department.update(
        obj_new=department, obj_current=current_dept
    )
    return create_response(data=department_updated)


@router.delete("/{department_id}")
async def remove_department(
    department_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[DepartmentRead]:
    """
    Deletes a department by its id

    Required roles:
    - admin
    - manager
    """
    current_depart = await crud.department.get(id=department_id)
    if not current_depart:
        raise IdNotFoundException(Department, department_id)
    department = await crud.department.remove(id=department_id)
    return create_response(data=department)


# @router.post("/logo")
# async def upload_institution_logo(
#     title: str | None = Body("Institution Logo"),
#     description: str | None = Body("The Institution official Logo"),
#     institution_logo: UploadFile = File(...),
#     current_user: User = Depends(deps.get_current_user()),
#     minio_client: MinioClient = Depends(deps.minio_auth),
# ) -> IPostResponseBase[InstitutionRead]:
#     """
#     Uploads a institution official logo/image
#     """
#     try:
#         image_modified = modify_image(BytesIO(institution_logo.file.read()))
#         data_file = minio_client.put_object(
#             file_name=institution_logo.filename,
#             file_data=BytesIO(image_modified.file_data),
#             content_type=institution_logo.content_type,
#         )
#         print("data_file", data_file)
#         media = IMediaCreate(
#             title=title, description=description, path=data_file.file_name
#         )
#         user = await crud.institution.update_institution_logo(
#             user=current_user,
#             institution_logo=media,
#             heigth=image_modified.height,
#             width=image_modified.width,
#             file_format=image_modified.file_format,
#         )
#         return create_response(data=user)
#     except Exception as e:
#         print(e)
#         return Response("Internal server error", status_code=500)


@router.post("/{department_id}/image")
async def upload_department_image(
    valid_department: Department= Depends(user_deps.is_valid_department),
    title: str | None = Body(None),
    description: str | None = Body(None),
    department_image: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[DepartmentRead]:
    """
    Uploads a department hero image by id

    Required roles:
    - admin
    - manager
    """
    try:
        image_modified = modify_image(BytesIO(department_image.file.read()))
        data_file = minio_client.put_object(
            file_name=department_image.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=department_image.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        department_photo = await crud.department.update_department_image(
            department=valid_department,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=department_photo)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


# Associate  programme with departmenmt
@router.post("/{department_id}/programmes/{programme_id}")
async def add_programme_to_department(
    department_id: UUID,
    programme_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[DepartmentRead]:
    """
    Add a Programme to a Department by IDs

    Required roles:
    - admin
    - manager
    """
    department_db = await crud.department.get(id=department_id)
    programme_db = await crud.programme.get(id=programme_id)
    if not department_db or not programme_db:
        raise HTTPException(status_code=404, detail="Department  or Programme not found")
 
    # Check if association already exist
    _association = await crud.department.check_existing_association_with_programme(
        department=department_db, programme=programme_db
    )

    if _association is not None:
        # If an association already exists, raise an error or return a suitable response
        raise HTTPException(
            status_code=400,
            detail=f"Department '{department_db.name}' is already associated with  Programme '{programme_db.name}'",
        )
    else:
        # Add the programme to the department's list of programmes
        department_db.programmes.append(programme_db)

        department_with_programme = await crud.department.add_related(
            appended_parent_object=department_db
        )
        return create_response(data=department_with_programme)


@router.delete("/{department_id}/programmes/{programme_id}")
async def remove_programme_from_department(
    department_id: UUID,
    programme_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[DepartmentRead]:
    """
    Remove a Programme from a Department (unlink only, does not delete the programme)

    Required roles:
    - admin
    - manager
    """
    department_db = await crud.department.get(
        id=department_id,
        db_session=db_session,
        options=[selectinload(Department.programmes)],
    )
    programme_db = await crud.programme.get(id=programme_id, db_session=db_session)
    
    if not department_db or not programme_db:
        raise HTTPException(status_code=404, detail="Department or Programme not found")

    if programme_db not in department_db.programmes:
        raise HTTPException(
            status_code=404,
            detail=f"Programme '{programme_db.name.value}' is not associated with Department '{department_db.name}'",
        )

    department_db.programmes.remove(programme_db)
    db_session.add(department_db)
    await db_session.commit()
    await db_session.refresh(department_db)

    return create_response(data=department_db, message="Programme removed from department successfully")
