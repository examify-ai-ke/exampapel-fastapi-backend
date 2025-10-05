from uuid import UUID
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from app.models.department_model import Department
from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.minio_client import MinioClient, S3Client
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
from sqlmodel.ext.asyncio.session import AsyncSession
from app import crud
from app.api import deps
from app.models.faculty_model import Faculty
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.faculty_schema import (
    FacultyRead,
    FacultyCreate,
    FacultyUpdate,
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
from sqlalchemy.orm import selectinload, joinedload
from sqlmodel import  select
from sqlalchemy import or_, and_

router = APIRouter()


@router.get("")
async def get_faculty_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[FacultyRead]:
    """
    Gets a paginated list of faculties
    """
    query = (
        select(Faculty)
        .options(
            joinedload(Faculty.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            selectinload(Faculty.image),
        )
    )
    faculties = await crud.faculty.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=faculties)


@router.get("/search")
async def search_faculties(
    q: str = Query(default=None, description="Search query for faculties"),
    institution_id: UUID = Query(default=None, description="Filter by institution ID"),
    sort_by: str = Query(default="name", description="Sort by: name, created_at"),
    sort_order: str = Query(default="asc", description="Sort order: asc, desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[FacultyRead]:
    """
    Search faculties with filtering and sorting
    """
    from app.models.institution_model import Institution, InstitutionFacultyLink
    
    query = (
        select(Faculty)
        .options(
            joinedload(Faculty.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            selectinload(Faculty.image),
        )
    )
    
    if q:
        query = query.filter(
            or_(
                Faculty.name.ilike(f"%{q}%"),
                Faculty.description.ilike(f"%{q}%"),
                Faculty.slug.ilike(f"%{q}%"),
            )
        )
    
    if institution_id:
        query = query.join(InstitutionFacultyLink).filter(
            InstitutionFacultyLink.institution_id == institution_id
        )
    
    sort_field = Faculty.name if sort_by == "name" else Faculty.created_at
    query = query.order_by(sort_field.asc() if sort_order == "asc" else sort_field.desc())
    
    faculties = await crud.faculty.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=faculties)


@router.get("/get_by_created_at")
async def get_faculty_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[FacultyRead]:
    """
    Gets a paginated list of  faculties ordered by created at datetime
    """
    faculties = await crud.faculty.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=faculties)


@router.get("/get_by_id/{faculty_id}")
async def get_faculty_by_id(
    faculty_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[FacultyRead]:
    """
    Gets a faculty by its id
    """
    faculty = await crud.faculty.get(id=faculty_id)
    if not faculty:
        raise IdNotFoundException(Faculty, faculty_id)

    # print_hero.delay(hero.id)
    return create_response(data=faculty)


@router.get("/get_by_slug/{faculty_slug}")
async def get_faculty_by_slug(
    faculty_slug: str,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[FacultyRead]]:
    """
    Gets a faculty by slug
    """
    faculty_frm_db = await crud.faculty.get_faculty_by_slug(slug=faculty_slug)
    if not faculty_frm_db:
        raise NameNotFoundException(Faculty, faculty_slug)

    return create_response(data=faculty_frm_db)


@router.post("")
async def create_faculty(
    faculty: FacultyCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[FacultyRead]:
    """
    Creates a new faculty

    Required roles:
    - admin
    - manager
    """
     

    # Check if slug already exists
    _faculty = await crud.faculty.create(
        obj_in=faculty, created_by_id=current_user.id
    )
    return create_response(data=_faculty)


@router.put("/{faculty_id}")
async def update_faculty(
    faculty_id: UUID,
    faculty: FacultyUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[FacultyRead]:
    """
    Updates a faculty by its id

    Required roles:
    - admin
    - manager
    """
    current_faculty = await crud.faculty.get(id=faculty_id)
    if not current_faculty:
        raise IdNotFoundException(Faculty, faculty_id)
    print(current_user.role)
    # if not is_authorized(current_user, "read", current_faculty):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this faculty because you did not created it",
    #     )
    # print(faculty)
    faculty_updated = await crud.faculty.update(
        obj_new=faculty, obj_current=current_faculty
    )
    return create_response(data=faculty_updated)


@router.delete("/{faculty_id}")
async def remove_faculty(
    faculty_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[FacultyRead]:
    """
    Deletes a faculty by its id

    Required roles:
    - admin
    - manager
    """
    current_faculty = await crud.faculty.get(id=faculty_id)
    if not current_faculty:
        raise IdNotFoundException(Faculty, faculty_id)
    faculty = await crud.faculty.remove(id=faculty_id)
    return create_response(data=faculty)


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


@router.post("/{faculty_id}/image")
async def upload_faculty_image(
    valid_faculty: Faculty = Depends(user_deps.is_valid_faculty),
    title: str | None = Body(None),
    description: str | None = Body(None),
    faculty_image: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: S3Client = Depends(deps.minio_auth),
) -> IPostResponseBase[FacultyRead]:
    """
    Uploads a faculty hero image by id

    Required roles:
    - admin
    - manager
    """
    try:
        image_modified = modify_image(BytesIO(faculty_image.file.read()))
        data_file = minio_client.put_object(
            file_name=faculty_image.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=faculty_image.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.file_name
        )
        faculty_photo = await crud.faculty.update_faculty_image(
            faculty=valid_faculty,
            image=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=faculty_photo)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


# Associate department with faculty
@router.post("/{faculty_id}/departments/{department_id}")
async def add_department_to_faculty(
    faculty_id: UUID,
    department_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
)-> IPostResponseBase[FacultyRead]:
    """
    Uploads a faculty hero image by id

    Required roles:
    - admin
    - manager
    """
    faculty_db = await crud.faculty.get(id=faculty_id)
    department_db = await crud.department.get(id=department_id)
    if not faculty_db or not department_db:
        raise HTTPException(status_code=404, detail="Faculty or Department not found")

    # Check if association already exist
    _association = await crud.faculty.check_existing_faculty_department_association(
        department=department_db,faculty=faculty_db
    )

    if _association is not None:
        # If an association already exists, raise an error or return a suitable response
        raise HTTPException(
            status_code=400,
            detail=f"Faculty '{faculty_db.name}' is already associated with Department '{department_db.name}'",
        )
    else:      

        faculty_db.departments.append(department_db)
        facilty_with_department = await crud.faculty.add_related(
            appended_parent_object=faculty_db
        )
        return create_response(data=facilty_with_department)
