from uuid import UUID
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from app.models.question_model import QuestionSet, Question
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
from app.models.exam_paper_model import ExamPaper, ExamInstruction, ExamPaperQuestionLink
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.models.answer_model import Answer
from app.schemas.exam_paper_schema import (
    ExamPaperCreate,
    ExamPaperRead,
    ExamPaperUpdate,
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
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlalchemy import delete

router = APIRouter()


@router.get("")
async def get_exam_paper_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[ExamPaperRead]:
    """
    Gets a paginated list of exam papers
    """
    query = (
        select(ExamPaper).options(
            selectinload(ExamPaper.course),  # Load related course
            selectinload(ExamPaper.description),  # Load related exam description
            selectinload(ExamPaper.institution),  # Load related institution
            selectinload(ExamPaper.question_sets)
            .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
            .selectinload(Question.children),  # Load question sets, main questions, and sub-questions
            selectinload(ExamPaper.question_sets)
            .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
            .selectinload(Question.answers),  # Load answers for main questions
            selectinload(ExamPaper.questions.and_(Question.exam_paper_id.is_not(None))),  # Load related main questions
            selectinload(ExamPaper.created_by),  # Load creator details
            selectinload(ExamPaper.instructions),  # Load related instructions
            selectinload(ExamPaper.modules),  # Load related modules
            selectinload(ExamPaper.title),  # Load related exam title
        )
    )
    exam_papers = await crud.exam_paper.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    return create_response(data=exam_papers)


@router.get("/get_exam_paper_properties")
async def get_exam_paper_properties(
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
    ):
    exam_headers= await crud.exam_paper.get_all_exam_properties(db_session=db_session)
    return exam_headers


@router.get("/get_by_created_at")
async def get_exams_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    current_user: User = Depends(deps.get_current_user()),
) -> IGetResponsePaginated[ExamPaperRead]:
    """
    Gets a paginated list of ExamPapers ordered by created at datetime
    """
    exampapers = await crud.exam_paper.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=exampapers)


@router.get("/get_by_id/{exampaper_id}")
async def get_exam_paper_by_id(
    exampaper_id: UUID,
    # current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[ExamPaperRead]:
    """
    Get an ExamPaper by ID with all related modules and nested relationships.
    """
    options = [
        selectinload(ExamPaper.course),  # Load related course
        selectinload(ExamPaper.description),  # Load related exam description
        selectinload(ExamPaper.institution),  # Load related institution
        selectinload(ExamPaper.question_sets)
        .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
        .selectinload(
            Question.children  # Load main questions and their sub-questions
        ),
        selectinload(ExamPaper.question_sets)
        .selectinload(QuestionSet.questions.and_(Question.question_set_id.is_not(None)))
        .selectinload(Question.answers),  # Load answers for main questions
        selectinload(ExamPaper.created_by),  # Load creator details
        selectinload(ExamPaper.instructions),  # Load related instructions
        selectinload(ExamPaper.modules),  # Load related modules
        selectinload(ExamPaper.title),  # Load related exam title
    ]

    exampaper = await crud.exam_paper.get(
        id=exampaper_id, db_session=db_session
    )
    # exampaper = await crud.exam_paper.get(id=exampaper_id)
    if not exampaper:
        raise IdNotFoundException(ExamPaper, exampaper_id)

    # print_hero.delay(hero.id)
    return create_response(data=exampaper)


@router.get("/get_by_slug/{exampaper_slug}")
async def get_exam_paper_by_slug(
    exampaper_slug: str,
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[ExamPaperRead]]:
    """
    Gets a ExamPaper by slug
    """
    exampaper = await crud.exam_paper.get_exam_paper_by_slug(slug=exampaper_slug)
    if not exampaper:
        raise NameNotFoundException(ExamPaper, exampaper_slug)

    return create_response(data=exampaper)


@router.post("")
async def create_exam_paper(
    exampaper: ExamPaperCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[ExamPaperRead]:
    """
    Creates a new ExamPaper

    Required roles:
    - admin
    - manager
    """

    instructions = await crud.instruction.get_by_ids(list_ids=exampaper.instruction_ids)
    modules = await crud.module.get_by_ids(list_ids=exampaper.module_ids)
    # course = await crud.course.get(id=exampaper.course_id)
    if len(instructions) != len(exampaper.instruction_ids):
        raise HTTPException(
            status_code=404, detail="Some instructions not found"
        )
    if len(modules) != len(exampaper.module_ids):
        raise HTTPException(status_code=404, detail="Some modules not found")
    # if not course:
    #     raise HTTPException(status_code=404, detail="The Selected Course was not found")
    # Add modules to the examPaper
    # exampaper..modules.extend(modules_list)  # Add the list of modules
    
    exampaper = await crud.exam_paper.create_with_related_list(
        obj_in=exampaper,
        related_list_object1=instructions,
        related_list_object2=modules,
        # related_object3=course,
        items1="instructions",
        items2="modules",
        created_by_id=current_user.id,
    )
    return create_response(data=exampaper)


@router.put("/{exampaper_id}")
async def update_exam_paper(
    exampaper_id: UUID,
    exampaper_new: ExamPaperUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[ExamPaperRead]:
    """
    Updates a ExamPaper by its id

    Required roles:
    - admin
    - manager
    """
    # current_exam = await crud.exam_paper.get(id=exampaper_id)

    # if not current_exam:
    #     raise IdNotFoundException(ExamPaper, exampaper_id)
    # if not is_authorized(current_user, "read", exampaper):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="You are not Authorized to update this institution because you did not created it",
    #     )

    exam_updated = await crud.exam_paper.update_examPaper(
        exam_paper_id=exampaper_id, obj_new=exampaper_new
    )

    return create_response(data=exam_updated)


@router.delete("/{exampaper_id}")
async def remove_exam_paper(
    exampaper_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[ExamPaperRead]:
    """
    Deletes a ExamPaper by its id

    Required roles:
    - admin
    - manager
    """
    current_exam = await crud.exam_paper.get(id=exampaper_id)
    if not current_exam:
        raise IdNotFoundException(ExamPaper, exampaper_id)
    exam = await crud.exam_paper.remove(id=exampaper_id)
    return create_response(data=exam)


# # Associate ExamPaper with A QuestionSet
@router.post("/{exampaper_id}/question-sets/{question_set_id}")
async def add_question_set_to_exam_paper(
    exampaper_id: UUID,
    question_set_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[ExamPaperRead]:
    """
    Add a QuestionSet to an ExamPaper by IDs.

    Required roles:
    - admin
    - manager
    """
    # Fetch the ExamPaper
    exam_paper = await crud.exam_paper.get(id=exampaper_id, db_session=db_session)
    if not exam_paper:
        raise HTTPException(status_code=404, detail="ExamPaper not found")

    # Fetch the QuestionSet
    question_set = await crud.question_set.get(id=question_set_id, db_session=db_session)
    if not question_set:
        raise HTTPException(status_code=404, detail="QuestionSet not found")

    # Check if the QuestionSet is already associated with the ExamPaper
    if question_set.id in [qs.id for qs in exam_paper.question_sets]:
        raise HTTPException(
            status_code=400,
            detail=f"ExamPaper '{exam_paper.year_of_exam}-{exam_paper.title.name}-{exam_paper.description.name}' is already associated with QuestionSet '{question_set.title}'",
        )

    # Add the QuestionSet to the ExamPaper
    exam_paper.question_sets.append(question_set)

    # Save the updated ExamPaper
    updated_exam_paper = await crud.exam_paper.update(
        obj_current=exam_paper, obj_new=exam_paper, db_session=db_session
    )

    return create_response(data=updated_exam_paper)


@router.delete("/{exampaper_id}/question-sets/{question_set_id}")
async def remove_question_set_from_exam_paper(
    exampaper_id: UUID,
    question_set_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[ExamPaperRead]:
    """
    Remove a QuestionSet from an ExamPaper by IDs without deleting the QuestionSet.

    Required roles:
    - admin
    - manager
    """
    # Fetch the ExamPaper
    exam_paper = await crud.exam_paper.get(id=exampaper_id, db_session=db_session)
    if not exam_paper:
        raise HTTPException(status_code=404, detail="ExamPaper not found")

    # Fetch the QuestionSet
    question_set = await crud.question_set.get(id=question_set_id, db_session=db_session)
    if not question_set:
        raise HTTPException(status_code=404, detail="QuestionSet not found")

    # Check if the QuestionSet is associated with the ExamPaper
    if question_set.id not in [qs.id for qs in exam_paper.question_sets]:
        raise HTTPException(
            status_code=400,
            detail=f"QuestionSet '{question_set.title}' is not associated with ExamPaper '{exam_paper.year_of_exam}-{exam_paper.title.name}-{exam_paper.description.name}'",
        )

    # Unlink the QuestionSet from the ExamPaper by deleting the association in the linking table
    await db_session.execute(
        delete(ExamPaperQuestionLink).where(
            ExamPaperQuestionLink.exam_id == exampaper_id,
            ExamPaperQuestionLink.question_set_id == question_set_id,
        )
    )
    await db_session.commit()

    # Fetch the updated ExamPaper to return in the response
    updated_exam_paper = await crud.exam_paper.get(id=exampaper_id, db_session=db_session)

    return create_response(data=updated_exam_paper)
