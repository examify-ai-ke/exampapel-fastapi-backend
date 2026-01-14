from typing import Any, Dict, List, Optional
from datetime import datetime
from app.utils.partial import optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class BlockData(BaseModel):
    text: str


class Block(BaseModel):
    id: str
    data: Dict[str, Any]
    type: str


class AnswerTextSchema(BaseModel):
    time: int
    blocks: list[Block]

    class Config:
        json_schema_extra = {
            "example": {
                "time": 1742156891260,
                "blocks": [
                    {
                        "id": "dCcbQeoht12",
                        "data": {
                            "text": "Write a Python function that calculates the factorial of a given number. Explain your code."
                        },
                        "type": "paragraph",
                    }
                ],
            }
        }


class AnswerBase(BaseModel):
    text: Optional[AnswerTextSchema] = None
    question_id: UUID  # Updated to use unified Question model

    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump()
        return v

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


@optional()
class AnswerUpdate(AnswerBase):
    question_id: Optional[UUID] = None  # Make optional for updates


class AnswerCreate(AnswerBase):
    pass


# Minimal schemas for nested relationships to avoid circular imports and recursion
class UserMinimal(BaseModel):
    """Minimal user schema for use in answer responses"""
    id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    
    class Config:
        from_attributes = True


class QuestionMinimal(BaseModel):
    """Minimal question schema for use in answer responses"""
    id: UUID
    question_number: Optional[str] = None
    text: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class AnswerReadMinimal(BaseModel):
    """Minimal answer schema for nested relationships"""
    id: UUID
    text: Optional[Dict[str, Any]] = None
    question_id: Optional[UUID] = None
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: bool = False
    auto_answer: bool = False
    created_at: datetime
    created_by_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    
    # Only include basic user and question info
    created_by: Optional[UserMinimal] = None
    question: Optional[QuestionMinimal] = None
    
    class Config:
        from_attributes = True


class AnswerRead(BaseModel):
    """Full answer schema for API responses"""
    id: UUID
    text: Optional[Dict[str, Any]] = None
    question_id: Optional[UUID] = None
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: bool = False
    auto_answer: bool = False
    created_at: datetime
    created_by_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    
    # Relationships with proper nesting control
    created_by: Optional[UserMinimal] = None
    question: Optional[QuestionMinimal] = None
    
    # Only include children, not parent to avoid recursion
    children: Optional[List[AnswerReadMinimal]] = []
    
    @classmethod
    def from_orm_safe(cls, answer):
        """Safely convert SQLModel Answer to Pydantic schema"""
        # Extract basic fields
        data = {
            "id": answer.id,
            "text": answer.text,
            "question_id": answer.question_id,
            "likes": answer.likes,
            "dislikes": answer.dislikes,
            "reviewed": answer.reviewed,
            "auto_answer": answer.auto_answer,
            "created_at": answer.created_at,
            "created_by_id": answer.created_by_id,
            "parent_id": answer.parent_id,
        }
        
        # Safely extract created_by relationship
        if hasattr(answer, 'created_by') and answer.created_by:
            try:
                data["created_by"] = UserMinimal.model_validate(answer.created_by)
            except Exception:
                data["created_by"] = None
        
        # Safely extract question relationship
        if hasattr(answer, 'question') and answer.question:
            try:
                data["question"] = QuestionMinimal.model_validate(answer.question)
            except Exception:
                data["question"] = None
        
        # Safely extract children relationships (no recursion)
        if hasattr(answer, 'children') and answer.children:
            try:
                children = []
                for child in answer.children:
                    child_data = {
                        "id": child.id,
                        "text": child.text,
                        "question_id": child.question_id,
                        "likes": child.likes,
                        "dislikes": child.dislikes,
                        "reviewed": child.reviewed,
                        "auto_answer": child.auto_answer,
                        "created_at": child.created_at,
                        "created_by_id": child.created_by_id,
                        "parent_id": child.parent_id,
                    }
                    
                    # Add child relationships safely
                    if hasattr(child, 'created_by') and child.created_by:
                        try:
                            child_data["created_by"] = UserMinimal.model_validate(child.created_by)
                        except Exception:
                            child_data["created_by"] = None
                    
                    if hasattr(child, 'question') and child.question:
                        try:
                            child_data["question"] = QuestionMinimal.model_validate(child.question)
                        except Exception:
                            child_data["question"] = None
                    
                    children.append(AnswerReadMinimal(**child_data))
                
                data["children"] = children
            except Exception:
                data["children"] = []
        
        return cls(**data)
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class AnswerReadForQuestion(BaseModel):
    """Answer schema for use in Question responses - simplified to avoid deep nesting"""
    id: UUID
    text: Optional[Dict[str, Any]] = None
    likes: Optional[int] = 0
    dislikes: Optional[int] = 0
    reviewed: bool = False
    auto_answer: bool = False
    created_at: datetime
    created_by_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    
    # Only basic user info to avoid circular imports
    created_by: Optional[UserMinimal] = None
    
    class Config:
        from_attributes = True
