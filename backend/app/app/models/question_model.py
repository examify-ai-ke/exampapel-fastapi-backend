from app.models.module_model import CourseModuleLink
from app.models.exam_paper_model import ExamPaperQuestionLink
from sqlmodel import Field, Relationship, SQLModel, Enum, Column,  String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
from sqlalchemy.dialects.postgresql import TEXT
from typing import Any, ClassVar, Dict, List, Optional
# from app.models.image_media_model import ImageMedia
from sqlalchemy_utils import ChoiceType
from pydantic import validator, model_validator
from app.utils.slugify_string import   generate_slug, generate_slug_for_question_text
import enum
from sqlalchemy import UniqueConstraint
# from sqlmodel import Field, SQLModel
# from sqlalchemy import  JSON
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy as sqla

class QuestionSetTitleEnum(enum.Enum):
    QUESTION_ONE = "Question One"
    QUESTION_TWO = "Question Two"
    QUESTION_THREE = "Question Three"
    QUESTION_FOUR = "Question Four"
    QUESTION_FIVE = "Question Five"
    QUESTION_SIX = "Question Six"
    QUESTION_SEVEN = "Question Seven"
    QUESTION_EIGHT = "Question Eight"
    QUESTION_NINE = "Question Nine"
    QUESTION_TEN = "Question Ten"

class QuestionSetBase(SQLModel):
    title: QuestionSetTitleEnum | None = Field(
        default=QuestionSetTitleEnum.QUESTION_ONE,
        sa_column=Column(Enum(QuestionSetTitleEnum, impl=String()),unique=True,
            nullable=False)
    )

class QuestionSet(BaseUUIDModel,QuestionSetBase, table=True):
    """_summary_

    Args:
        BaseUUIDModel (_type_): _description_
        QuestionSetBase (_type_): _description_
        table (bool, optional): _description_. Defaults to True.

        This is the Main Question Section of the question Paper. e.g "QUESTION ONE" section
    """
    slug: Optional[str] = Field(default=None, unique=True)
    questions: List["Question"] = Relationship(
        back_populates="question_set",
        sa_relationship_kwargs={"lazy": "noload"}
    )

    exam_papers: List["ExamPaper"] = Relationship(
        back_populates="question_sets",
        link_model=ExamPaperQuestionLink,
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "QuestionSet.created_by_id==User.id",
        }
    )
    @property
    def count_questions(self):
        total = len(self.questions)
        return total
    
    @property
    def exam_papers_count(self):
        try:
            return len(self.exam_papers) if self.exam_papers else 0
        except:
            # If exam_papers relationship is not loaded, return 0
            return 0
    
    questions_count = count_questions

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        # If slug is already provided and not None, use it
        if value:
            return value
            
        title = values.get("title")
        if title:
            return generate_slug(title.value)
        
        # Fallback if no title
        import uuid
        return generate_slug(f"question-set-{str(uuid.uuid4())[:8]}")


# Define the Question model
class NumberingStyleEnum(enum.Enum):
    ROMAN = "roman"
    ALPHA = "alphabetic"
    NUMERICAL = "numeric"
    # LOWERCASE_ALPHA = "lowercase_alpha"
    # LOWERCASE_ROMAN = "lowercase_roman"


class QuestionBase(SQLModel):
    # text: str = Field(sa_column=Column(TEXT, nullable=True, unique=False))
    # text: Optional[Dict[str, Any]] = Field(
    #     default=None, sa_column=Column(JSON, nullable=True)
    # )
    
    text: Optional[Dict[str, Any]] = Field(
        default_factory={}, sa_column=Column(JSONB, nullable=False)
    )
    marks: Optional[int] = None  # Marks given to a Question
    numbering_style: NumberingStyleEnum = Field(
        sa_column=Column(Enum(NumberingStyleEnum, native_enum=False), nullable=False)
    )
    question_number: str


class Question(BaseUUIDModel, QuestionBase, table=True):
    """
    Unified Question model that can represent both main questions and sub-questions.
    Main questions have question_set_id and exam_paper_id.
    Sub-questions have parent_id pointing to their main question.
    """
    slug: Optional[str] = Field(default=None, unique=True)
    
    # For main questions - link to question set and exam paper
    question_set_id: UUID | None = Field(default=None, foreign_key="QuestionSet.id")
    exam_paper_id: UUID | None = Field(default=None, foreign_key="ExamPaper.id")
    
    # For sub-questions - link to parent question
    parent_id: UUID | None = Field(default=None, foreign_key="Question.id")
    
    # Relationships
    question_set: Optional["QuestionSet"] = Relationship(
        back_populates="questions",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Question.question_set_id==QuestionSet.id",
        },
    )
    
    exam_paper: Optional["ExamPaper"] = Relationship(
        back_populates="questions",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Question.exam_paper_id==ExamPaper.id",
        },
    )
    
    # Self-referential relationship
    parent: Optional["Question"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "Question.id", 
            "lazy": "selectin",
            "join_depth": 3  # Limit join depth to prevent infinite recursion
        },
    )
    
    children: List["Question"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "join_depth": 3  # Limit join depth to prevent infinite recursion
        },
    )
    
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "Question.created_by_id==User.id",
        }
    )
    
    answers: List["Answer"] | None = Relationship(
        back_populates="question",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
        }
    )
    
    @model_validator(mode="before")
    @classmethod
    def set_slug(cls, data: Any) -> Any:
        # If not a dict, return as is (could be validation from ORM object)
        if not isinstance(data, dict):
            return data
            
        # If slug is already provided and not None, return data
        if data.get("slug"):
            return data
            
        base_slug = ""
        text = data.get("text", {})
        
        # 1. Try to get slug from text content
        if isinstance(text, dict):
            for block in text.get("blocks", []):
                if "text" in block.get("data", {}):
                    base_slug = block["data"]["text"]
                    break
        
        # 2. If we have text, slugify it
        generated_slug = ""
        if base_slug:
            generated_slug = generate_slug_for_question_text(base_slug)
        else:
            # 3. Fallback to question number
            question_number = data.get("question_number", "")
            if question_number:
                generated_slug = generate_slug(f"question-{question_number}")
            else:
                # 4. Final fallback - generate a random slug
                import uuid
                generated_slug = generate_slug(f"question-{str(uuid.uuid4())[:8]}")
        
        # Append context prefix/suffix for uniqueness
        exam_paper_id = data.get("exam_paper_id")
        parent_id = data.get("parent_id")
        
        if exam_paper_id:
            # Main questions: use exam_paper_id
            generated_slug = f"{generated_slug}-{str(exam_paper_id)[:6]}"
        elif parent_id:
            # Sub-questions: use parent_id (since they don't have exam_paper_id directly)
            generated_slug = f"{generated_slug}-{str(parent_id)[:6]}"
            
        data["slug"] = generated_slug
        return data
    
    @property
    def is_main_question(self) -> bool:
        """Check if this is a main question (has question_set_id)"""
        return self.question_set_id is not None
    
    @property
    def is_sub_question(self) -> bool:
        """Check if this is a sub-question (has parent_id)"""
        return self.parent_id is not None
    
    @property
    def children_count(self) -> int:
        """Count of sub-questions"""
        return len(self.children)
    
    @property
    def answers_count(self) -> int:
        """Count of answers for this question"""
        return len(self.answers) if self.answers else 0
    
    @property
    def total_marks(self) -> int:
        """Total marks including all children"""
        base_marks = self.marks or 0
        children_marks = sum(child.marks or 0 for child in self.children)
        return base_marks + children_marks
    
    @property
    def institution(self):
        """Get institution via exam_paper"""
        return self.exam_paper.institution if self.exam_paper else None
    
    @property
    def course(self):
        """Get course via exam_paper"""
        return self.exam_paper.course if self.exam_paper else None
    
    @property
    def modules(self):
        """Get modules via exam_paper"""
        return self.exam_paper.modules if self.exam_paper else []
    
    @property
    def programme(self):
        """Get programme via exam_paper.course"""
        if self.exam_paper and self.exam_paper.course:
            return self.exam_paper.course.programme
        return None
    
    __table_args__ = (
        UniqueConstraint(
            "exam_paper_id",
            "question_number",
            "question_set_id",
            name="_questions_order_per_question_set_uc",
        ),
    )

# Ensure exam_paper relationships are loaded for computed properties
from sqlalchemy import event

@event.listens_for(Question, "load")
def receive_load(target, context):
    """Ensure exam_paper is loaded when Question is loaded"""
    pass  # Relationships are handled by selectinload in queries
