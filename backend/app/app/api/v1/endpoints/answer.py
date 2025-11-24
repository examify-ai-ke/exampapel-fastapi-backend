from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from app import crud
from app.api import deps
from app.models.answer_model import Answer
from app.models.question_model import Question
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.answer_schema import (
    AnswerRead,
    AnswerCreate,
    AnswerUpdate,
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
from app.utils.exceptions import IdNotFoundException
from app.core.authz import is_authorized
from sqlmodel import select

router = APIRouter()


@router.get("", response_model=IGetResponsePaginated[AnswerRead])
async def get_answer_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[AnswerRead]:
    """
    Gets a paginated list of answers with optimized loading
    """
    # Optimized query for answer list with proper eager loading
    query = (
        select(Answer)
        .options(
            selectinload(Answer.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            selectinload(Answer.question).load_only(
                Question.id, Question.question_number, Question.text
            ),
            selectinload(Answer.children).selectinload(Answer.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            selectinload(Answer.children).selectinload(Answer.question).load_only(
                Question.id, Question.question_number, Question.text
            ),
        )
        .where(Answer.parent_id.is_(None))  # Only top-level answers
    )
    
    answers_page = await crud.answer.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    
    # Convert to safe schema format
    safe_answers = []
    for answer in answers_page.items:
        safe_answer = AnswerRead.from_orm_safe(answer)
        safe_answers.append(safe_answer)
    
    # Create new page with safe answers
    from fastapi_pagination import Page
    safe_page = Page(
        items=safe_answers,
        total=answers_page.total,
        page=answers_page.page,
        size=answers_page.size,
        pages=answers_page.pages
    )
    
    return create_response(data=safe_page)


@router.get("/question/{question_id}", response_model=IGetResponseBase[List[AnswerRead]])
async def get_answers_by_question(
    question_id: UUID,
    include_replies: bool = Query(default=True, description="Include reply threads"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[List[AnswerRead]]:
    """
    Gets all answers for a specific question
    """
    if include_replies:
        answers = await crud.answer.get_answers_by_question(
            question_id=question_id, db_session=db_session
        )
    else:
        answers = await crud.answer.get_top_level_answers_by_question(
            question_id=question_id, db_session=db_session
        )
    
    # Convert to safe schema format
    safe_answers = [AnswerRead.from_orm_safe(answer) for answer in answers]
    
    return create_response(data=safe_answers)


@router.get("/{answer_id}", response_model=IGetResponseBase[AnswerRead])
async def get_answer_by_id(
    answer_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[AnswerRead]:
    """
    Gets an answer by its id with all nested replies
    """
    answer = await crud.answer.get_answer_with_children(
        answer_id=answer_id, db_session=db_session
    )
    if not answer:
        raise IdNotFoundException(Answer, answer_id)
    
    # Convert to safe schema format
    safe_answer = AnswerRead.from_orm_safe(answer)
    
    return create_response(data=safe_answer)


@router.post("", response_model=IPostResponseBase[AnswerRead])
async def create_answer(
    answer_data: AnswerCreate,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[AnswerRead]:
    """
    Creates a new answer for a question
    
    Any authenticated user can create answers
    """
    answer = await crud.answer.create_answer_for_question(
        answer_data=answer_data,
        created_by_id=current_user.id,
        db_session=db_session
    )
    return create_response(data=answer)


@router.post("/{answer_id}/reply", response_model=IPostResponseBase[AnswerRead])
async def create_reply_to_answer(
    answer_id: UUID,
    reply_data: AnswerCreate,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[AnswerRead]:
    """
    Creates a reply to an existing answer
    
    Any authenticated user can reply to answers
    """
    reply = await crud.answer.create_reply_to_answer(
        parent_answer_id=answer_id,
        answer_data=reply_data,
        created_by_id=current_user.id,
        db_session=db_session
    )
    return create_response(data=reply)


@router.put("/{answer_id}", response_model=IPutResponseBase[AnswerRead])
async def update_answer(
    answer_id: UUID,
    answer_update: AnswerUpdate,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[AnswerRead]:
    """
    Updates an answer by its id
    
    Only the answer creator or admin/manager can update
    """
    current_answer = await crud.answer.get(id=answer_id, db_session=db_session)
    if not current_answer:
        raise IdNotFoundException(Answer, answer_id)
    
    # Check authorization - only creator or admin/manager can update
    if (current_answer.created_by_id != current_user.id and 
        current_user.role.name not in [IRoleEnum.admin, IRoleEnum.manager]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own answers"
        )

    answer_updated = await crud.answer.update(
        obj_new=answer_update, obj_current=current_answer, db_session=db_session
    )
    return create_response(data=answer_updated)


@router.post("/{answer_id}/like", response_model=IPostResponseBase[AnswerRead])
async def toggle_answer_like(
    answer_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[AnswerRead]:
    """
    Toggle like for an answer
    - If user hasn't voted: adds a like
    - If user already liked: removes the like
    - If user disliked: changes to like (removes dislike, adds like)
    """
    answer = await crud.answer.toggle_answer_like(
        answer_id=answer_id, user_id=current_user.id, db_session=db_session
    )
    return create_response(data=answer)


@router.post("/{answer_id}/dislike", response_model=IPostResponseBase[AnswerRead])
async def toggle_answer_dislike(
    answer_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPostResponseBase[AnswerRead]:
    """
    Toggle dislike for an answer
    - If user hasn't voted: adds a dislike
    - If user already disliked: removes the dislike
    - If user liked: changes to dislike (removes like, adds dislike)
    """
    answer = await crud.answer.toggle_answer_dislike(
        answer_id=answer_id, user_id=current_user.id, db_session=db_session
    )
    return create_response(data=answer)


@router.put("/{answer_id}/review", response_model=IPutResponseBase[AnswerRead])
async def mark_answer_as_reviewed(
    answer_id: UUID,
    reviewed: bool = Query(default=True, description="Mark as reviewed or unreviewed"),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[AnswerRead]:
    """
    Marks an answer as reviewed or unreviewed
    
    Required roles:
    - admin
    - manager
    """
    answer = await crud.answer.mark_answer_as_reviewed(
        answer_id=answer_id, reviewed=reviewed, db_session=db_session
    )
    return create_response(data=answer)


@router.delete("/{answer_id}", response_model=IDeleteResponseBase[AnswerRead])
async def delete_answer(
    answer_id: UUID,
    current_user: User = Depends(deps.get_current_user()),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[AnswerRead]:
    """
    Deletes an answer by its id
    
    Only the answer creator or admin/manager can delete
    """
    current_answer = await crud.answer.get(id=answer_id, db_session=db_session)
    if not current_answer:
        raise IdNotFoundException(Answer, answer_id)
    
    # Check authorization - only creator or admin/manager can delete
    if (current_answer.created_by_id != current_user.id and 
        current_user.role.name not in [IRoleEnum.admin, IRoleEnum.manager]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own answers"
        )

    answer = await crud.answer.remove(id=answer_id, db_session=db_session)
    return create_response(data=answer)


@router.get("/question/{question_id}/count", response_model=IGetResponseBase[int])
async def get_answers_count_by_question(
    question_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[int]:
    """
    Gets the count of answers for a specific question
    """
    count = await crud.answer.get_answers_count_by_question(
        question_id=question_id, db_session=db_session
    )
    return create_response(data=count)
