from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession
from app.api import deps
from app.models.user_model import User
from app.schemas.exam_paper_builder_schema import CompleteExamPaperCreate
from app.schemas.exam_paper_schema import ExamPaperRead
from app.services.exam_paper_builder_service import exam_paper_builder_service

router = APIRouter()

@router.post("/", response_model=ExamPaperRead)
async def create_complete_exam_paper(
    *,
    db: AsyncSession = Depends(deps.get_db),
    exam_paper_in: CompleteExamPaperCreate,
    current_user: User = Depends(deps.get_current_user()),
) -> Any:
    """
    Create a complete exam paper with all prerequisites and questions.
    """
    try:
        exam_paper = await exam_paper_builder_service.create_complete_exam_paper(
            db=db, data=exam_paper_in, user=current_user
        )
        return exam_paper
    except Exception as e:
        # Service might raise HTTPException or others.
        import logging
        logging.error(f"Error in builder endpoint: {e}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=str(e))
