from datetime import date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.models.exam_paper_model import ExamPaperBase

class QuestionSetSimpleRead(BaseModel):
    id: UUID
    title: str
    slug: Optional[str] = None
    questions_count: Optional[int] = 0
    
    class Config:
        from_attributes = True

class ExamPaperSimpleRead(ExamPaperBase):
    id: UUID
    tags: Optional[list[str]] = Field(default_factory=list)
    created_by_id: UUID
    identifying_name: Optional[str]
    question_sets: Optional[List[QuestionSetSimpleRead]] = Field(default_factory=list)
    
    # Basic relationship info without nested data
    title_name: Optional[str] = None
    description_name: Optional[str] = None
    course_name: Optional[str] = None
    institution_name: Optional[str] = None
    
    class Config:
        from_attributes = True
        
    @classmethod
    def from_exam_paper(cls, exam_paper):
        """Create a simple read schema from an ExamPaper instance"""
        return cls(
            id=exam_paper.id,
            year_of_exam=exam_paper.year_of_exam,
            exam_duration=exam_paper.exam_duration,
            exam_date=exam_paper.exam_date,
            tags=exam_paper.tags or [],
            created_by_id=exam_paper.created_by_id,
            identifying_name=exam_paper.identifying_name,
            title_name=exam_paper.title.name if exam_paper.title else None,
            description_name=exam_paper.description.name if exam_paper.description else None,
            course_name=exam_paper.course.name if exam_paper.course else None,
            institution_name=exam_paper.institution.name if exam_paper.institution else None,
            question_sets=[
                QuestionSetSimpleRead(
                    id=qs.id,
                    title=qs.title.value if hasattr(qs.title, 'value') else str(qs.title),
                    slug=qs.slug,
                    questions_count=len(qs.questions) if hasattr(qs, 'questions') and qs.questions else 0
                )
                for qs in (exam_paper.question_sets or [])
            ]
        )