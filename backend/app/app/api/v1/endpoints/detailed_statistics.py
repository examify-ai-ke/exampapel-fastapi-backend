# from app.schemas.institution_schema import InstitutionDetailedStatistics
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
from app.schemas.institution_schema import InstitutionDetailedStatistics
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

from app.schemas.response_schema import (
    IDeleteResponseBase,
    IGetResponseBase,
    IGetResponsePaginated,
    IPostResponseBase,
    IPutResponseBase,
    create_response,
)
from app import crud
from app.api import deps
from app.models.course_model import Course
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from sqlmodel.ext.asyncio.session import AsyncSession
from app.schemas.role_schema import IRoleEnum


router = APIRouter()

@router.get("/detailed-statistics")
async def get_detailed_statistics(
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[InstitutionDetailedStatistics]:
    """
    Get detailed dashboard statistics for institutions and its related entities.
    """
    total_institutions = await crud.institution.get_count(db_session=db_session)
    # if not institution:
    #     raise HTTPException(status_code=404, detail="Institution not found")

    total_courses = await crud.course.get_count(
        db_session=db_session
    )
    total_departments = await crud.department.get_count(
        db_session=db_session
    )
    total_modules = await crud.module.get_count(    
        db_session=db_session
    )
    total_faculties = await crud.faculty.get_count(
        db_session=db_session
    )
    total_questions = await crud.question.get_count(
        db_session=db_session
    )
    total_users = await crud.user.get_count(
        db_session=db_session
    )
    total_exam_papers = await crud.exam_paper.get_count(
        db_session=db_session
    )
    total_answers = await crud.answer.get_count(
        db_session=db_session
    )
    total_campuses = await crud.campus.get_count(
        db_session=db_session
    )

    statsData = InstitutionDetailedStatistics(
        total_institutions=total_institutions,
        total_courses=total_courses,
        total_departments=total_departments,
        total_modules=total_modules,
        total_faculties=total_faculties,
        total_main_questions=total_questions,
        total_users=total_users,
        total_exam_papers=total_exam_papers,
        total_answers=total_answers,
        total_campuses=total_campuses,
    )
    return create_response(data=statsData)
