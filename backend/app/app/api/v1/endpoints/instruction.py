from uuid import UUID
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
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
from app.models.exam_paper_model import ExamInstruction
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.exam_paper_schema import (
   
    InstructionCreate,
    InstructionRead,
    InstructionUpdate
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

router = APIRouter()


@router.get("")
async def get_instruction_list(
    # params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[InstructionRead]:
    """
    Gets a paginated list of ExamPaper Instructions
    """
    instructions = await crud.instruction.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit
    )
    return create_response(data=instructions)


@router.get("/get_by_id/{instruction_id}")
async def get_instruction_by_id(
    instruction_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[InstructionRead]:
    """
    Gets a exampaper Instruction by its id
    """
    instruction = await crud.instruction.get(id=instruction_id)
    if not instruction:
        raise IdNotFoundException(ExamInstruction, instruction_id)

    return create_response(data=instruction)


@router.post("")
async def create_instruction(
    instruction: InstructionCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[InstructionRead]:
    """
    Creates a new Instruction

    Required roles:
    - admin
    - manager
    """

    inst = await crud.instruction.create(
        obj_in=instruction, created_by_id=current_user.id
    )
    return create_response(data=inst)


@router.put("/{instruction_id}")
async def update_instruction_paper(
    instruction_id: UUID,
    instruction: InstructionUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[InstructionRead]:
    """
    Updates a Instruction by its id

    Required roles:
    - admin
    - manager
    """
    current_instruction = await crud.instruction.get(id=instruction_id)
    if not current_instruction:
        raise IdNotFoundException(ExamInstruction, instruction_id)
    # if not is_authorized(current_user, "read", current_inst):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this institution because you did not created it",
    #     )

    instruction_updated = await crud.instruction.update(
        obj_new=instruction, obj_current=current_instruction
    )
    return create_response(data=instruction_updated)


@router.delete("/{instruction_id}")
async def remove_instruction_paper(
    instruction_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[InstructionRead]:
    """
    Deletes a Instruction by its id

    Required roles:
    - admin
    - manager
    """
    current_instruction = await crud.instruction.get(id=instruction_id)
    if not current_instruction:
        raise IdNotFoundException(ExamInstruction, instruction_id)
    instruction = await crud.instruction.remove(id=instruction_id)
    return create_response(data=instruction)


# # Associate faculty with institution
# @router.post("/{institution_id}/faculties/{faculty_id}")
# async def add_faculty_to_institution(
#     institution_id: UUID,
#     faculty_id: UUID,
#     current_user: User = Depends(
#         deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
#     ),
#     ) -> IDeleteResponseBase[InstitutionRead]:
#     """
#     Add a Faculty to an Institution by id

#     Required roles:
#     - admin
#     - manager
#     """
#     institution = await crud.institution.get(id=institution_id)
#     faculty = await crud.faculty.get(id=faculty_id)
#     if not institution or not faculty:
#         raise HTTPException(status_code=404, detail="Institution or Faculty not found")

#     # Check if association already exist
#     _association = await crud.institution.check_existing_association(
#         institution=institution, faculty=faculty
#     )

#     if _association is not None:
#         # If an association already exists, raise an error or return a suitable response
#         raise HTTPException(
#             status_code=400,
#             detail=f"Faculty '{faculty_id}' is already associated with Institution '{institution_id}'"
#         )
#     else:

#         institution.faculties.append(faculty)
#         institution_with_faculty = await crud.institution.add_related(
#             appended_parent_object=institution
#         )
#         return create_response(data=institution_with_faculty)


# @router.post("/{institution_id}/logo")
# async def upload_institution_logo(
#     valid_institution: Institution = Depends(user_deps.is_valid_institution),
#     title: str | None = Body(None),
#     description: str | None = Body(None),
#     institution_logo: UploadFile = File(...),
#     current_user: User = Depends(
#         deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
#     ),
#     minio_client: MinioClient = Depends(deps.minio_auth),
# ) -> IPostResponseBase[InstitutionRead]:
#     """
#     Uploads a institution official logo by id

#     Required roles:
#     - admin
#     - manager
#     """
#     try:
#         image_modified = modify_image(BytesIO(institution_logo.file.read()))
#         data_file = minio_client.put_object(
#             file_name=institution_logo.filename,
#             file_data=BytesIO(image_modified.file_data),
#             content_type=institution_logo.content_type,
#         )
#         media = IMediaCreate(
#             title=title, description=description, path=data_file.file_name
#         )
#         inst = await crud.institution.update_institution_logo(
#             institution=valid_institution,
#             image=media,
#             heigth=image_modified.height,
#             width=image_modified.width,
#             file_format=image_modified.file_format,
#         )
#         return create_response(data=inst)
#     except Exception as e:
#         print(e)
#         return Response("Internal server error", status_code=500)
