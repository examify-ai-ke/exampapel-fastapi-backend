from app.models.module_model import CourseModuleLink
from app.models.exam_paper_model import ExamPaperQuestionLink
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
from sqlalchemy.dialects.postgresql import TEXT
from typing import List, Optional
# from app.models.image_media_model import ImageMedia
from sqlalchemy_utils import ChoiceType
from pydantic import  field_validator, validator
from app.utils.slugify_string import   generate_slug, generate_slug_for_question_text
import enum

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
        sa_column=Column(Enum(QuestionSetTitleEnum, impl=String())),
    )

class QuestionSet(BaseUUIDModel,QuestionSetBase, table=True):

    slug: Optional[str] = Field(default=None, unique=True)
    main_questions: List["MainQuestion"] = Relationship(
        back_populates="question_set",
        sa_relationship_kwargs={"lazy": "joined"}
    )

    exam_papers: List["ExamPaper"] = Relationship(
        back_populates="question_sets",
        link_model=ExamPaperQuestionLink,
        sa_relationship_kwargs={"lazy": "joined"},
    )
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "QuestionSet.created_by_id==User.id",
        }
    )
    @property
    def count_questions(self):
        total = len(self.main_questions)
        return total

    main_questions_count = count_questions

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        text = values.get("title", "")
        return generate_slug(text.value)

# Define the Question model
class QuestionBase(SQLModel):  
    # Use ENUM for the name field
    text: str = Field(sa_column=Column(TEXT,nullable=False, unique=False))
    marks: Optional[int] =None # marks given to a Question

class MainQuestion(BaseUUIDModel, QuestionBase, table=True): 

    slug: Optional[str] = Field(default=None, unique=False)
    question_set_id: UUID | None = Field(default=None, foreign_key="QuestionSet.id")    
    question_set: QuestionSet = Relationship(
        back_populates="main_questions",
        sa_relationship_kwargs={"lazy": "joined"}
    )

    subquestions: List["SubQuestion"] = Relationship(
        back_populates="main_question",
        sa_relationship_kwargs={"lazy": "joined"}
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        text = values.get("text", "")
        return generate_slug_for_question_text(text)

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": " MainQuestion.created_by_id==User.id",
        }
    )


class SubQuestion(BaseUUIDModel,SQLModel, table=True):
    text: str
    marks: Optional[int] = None

    main_question_id: UUID | None = Field(default=None, foreign_key="MainQuestion.id")
    main_question: MainQuestion = Relationship(
        back_populates="subquestions",
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "SubQuestion.main_question_id==MainQuestion.id",
        },
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "SubQuestion.created_by_id==User.id",
        }
    )
