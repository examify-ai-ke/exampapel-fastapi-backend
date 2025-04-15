from uuid import UUID
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from app.models.faculty_model import Faculty
from app.models.exam_paper_model import ExamPaper
from app.models.question_model import QuestionSet, MainQuestion

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
from sqlmodel.ext.asyncio.session import AsyncSession
from app import crud
from app.api import deps
from app.models.institution_model import Institution
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.institution_schema import (
    InstitutionCreate,
    InstitutionRead,
    InstitutionUpdate,
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
import time
from sqlmodel import SQLModel, Session, select
from sqlalchemy.orm import selectinload
# from fastapi_sqla import Base, Page, AsyncPagination, AsyncSession

router = APIRouter()


@router.get("")
async def get_institution_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[InstitutionRead]:
    """
    Gets a paginated list of institutions
    """
    query = (
        select(Institution)
        .options(
            # Load faculties and their departments
            selectinload(Institution.faculties).selectinload(Faculty.departments),
            # Load exam papers and their related entities
            selectinload(Institution.exam_papers)
            .selectinload(ExamPaper.question_sets)
            .selectinload(QuestionSet.main_questions)
            .selectinload(MainQuestion.subquestions),
            # .selectinload(ExamPaper.instructions)  # Load instructions
            # .selectinload(ExamPaper.title)  # Load exam title
            # .selectinload(ExamPaper.description)  # Load exam description
            # .selectinload(ExamPaper.course)  # Load related course
            # .selectinload(ExamPaper.question_sets)
            # .selectinload(QuestionSet.main_questions)
            # .selectinload(MainQuestion.subquestions),  # Load question sets, main questions, and subquestions
            # Load campuses
            selectinload(Institution.campuses),
            # Load institution logo
            selectinload(Institution.logo),
            # Load creator details
            selectinload(Institution.created_by),
        )
        .offset(skip)
        .limit(limit)
    )
    institutions = await crud.institution.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=institutions)


@router.get("/get_by_created_at")
async def get_institution_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    # current_user: User =None
) -> IGetResponsePaginated[InstitutionRead]:
    """
    Gets a paginated list of institutions ordered by created at datetime
    """
    institutions = await crud.institution.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=institutions)


@router.get("/get_by_id/{institution_id}")
async def get_institution_by_id(
    institution_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
    # current_user: User = None
) -> IGetResponseBase[InstitutionRead]:
    """
    Gets a institution by its id
    """
    institution = await crud.institution.get(id=institution_id)
    if not institution:
        raise IdNotFoundException(Institution, institution_id)

    # print_hero.delay(hero.id)
    return create_response(data=institution)


@router.get("/get_by_slug/{institution_slug}")
async def get_institution_by_slug(
    institution_slug: str,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[InstitutionRead]]:
    """
    Gets a institution by slug
    """
    institution = await crud.institution.get_institution_by_slug(slug=institution_slug)
    if not institution:
        raise NameNotFoundException(Institution, institution_slug)

    return create_response(data=institution)


@router.post("")
async def create_institution(
    institution: InstitutionCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[InstitutionRead]:
    """
    Creates a new institution 

    Required roles:
    - admin
    - manager
    """
    # print("Create instituion..........")
    # print(current_user)
    inst = await crud.institution.create(
        obj_in=institution, created_by_id=current_user.id
    )
    
    return create_response(data=inst)


@router.put("/{institution_id}")
async def update_institution(
    institution_id: UUID,
    institution: InstitutionUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[InstitutionRead]:
    """
    Updates a institution by its id

    Required roles:
    - admin
    - manager
    """
    current_inst = await crud.institution.get(id=institution_id)
    if not current_inst:
        raise IdNotFoundException(Institution, institution_id)
    # if not is_authorized(current_user, "read", current_inst):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this institution because you did not created it",
    #     )

    institution_updated = await crud.institution.update(
        obj_new=institution, obj_current=current_inst
    )
    return create_response(data=institution_updated)


@router.delete("/{institution_id}")
async def remove_institution(
    institution_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[InstitutionRead]:
    """
    Deletes a institution by its id

    Required roles:
    - admin
    - manager
    """
    current_institution = await crud.institution.get(id=institution_id)
    if not current_institution:
        raise IdNotFoundException(Institution, institution_id)
    insti = await crud.institution.remove(id=institution_id)
    return create_response(data=insti)


# Associate faculty with institution
@router.post("/{institution_id}/faculties/{faculty_id}")
async def add_faculty_to_institution(
    institution_id: UUID,
    faculty_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    ) -> IDeleteResponseBase[InstitutionRead]:
    """
    Add a Faculty to an Institution by id

    Required roles:
    - admin
    - manager
    """
    institution = await crud.institution.get(id=institution_id)
    faculty = await crud.faculty.get(id=faculty_id)
    if not institution or not faculty:
        raise HTTPException(status_code=404, detail="Institution or Faculty not found")

    # Check if association already exist
    _association = await crud.institution.check_existing_association(
        institution=institution, faculty=faculty
    )  
    
    if _association is not None:
        # If an association already exists, raise an error or return a suitable response
        raise HTTPException(
            status_code=400,
            detail=f"Faculty '{faculty_id}' is already associated with Institution '{institution_id}'"
        )
    else:    

        institution.faculties.append(faculty)
        institution_with_faculty = await crud.institution.add_related(
            appended_parent_object=institution
        )
        return create_response(data=institution_with_faculty)


@router.post("/{institution_id}/logo")
async def upload_institution_logo(
    valid_institution: Institution = Depends(user_deps.is_valid_institution),
    title: str | None = Body(None),
    description: str | None = Body(None),
    institution_logo: UploadFile = File(...),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: MinioClient = Depends(deps.minio_auth),
) -> IPostResponseBase[InstitutionRead]:
    """
    Uploads a institution official logo by id

    Required roles:
    - admin
    - manager
    """
    try:
        image_modified = modify_image(BytesIO(institution_logo.file.read()))
        data_file = minio_client.put_object(
            file_name=institution_logo.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=institution_logo.content_type,
        )
        media = IMediaCreate(
            title=title, description=description, path=data_file.url
        )
        inst = await crud.institution.update_institution_logo(
            institution=valid_institution,
            media=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=inst)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)
