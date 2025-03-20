from app.models.module_model import CourseModuleLink
from app.models.exam_paper_model import ExamPaperQuestionLink
from sqlmodel import Field, Relationship, SQLModel, Enum, Column,  String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
from sqlalchemy.dialects.postgresql import TEXT
from typing import Any, ClassVar, Dict, List, Optional
# from app.models.image_media_model import ImageMedia
from sqlalchemy_utils import ChoiceType
from pydantic import  field_validator, validator, model_validator
from app.utils.slugify_string import   generate_slug, generate_slug_for_question_text
import enum
from sqlalchemy import UniqueConstraint, event
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
        sa_column=Column(Enum(QuestionSetTitleEnum, impl=String()), unique=True)
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
class NumberingStyleEnum(enum.Enum):
    ROMAN = "roman"
    ALPHA = "alpha"


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


class MainQuestion(BaseUUIDModel, QuestionBase, table=True): 
    """
    
    Args:
        BaseUUIDModel (_type_): _description_
        QuestionBase (_type_): _description_
        table (bool, optional): _description_. Defaults to True.
      This is the parent Questions under the "QuestionSet" e.g (1), (I) e.t.c
    """
    # order_within_question_set: Optional[str] = Field(nullable=False, default=None)
    # Changed to String for alphabetical ordering
    slug: Optional[str] = Field(default=None, unique=False)
    question_set_id: UUID | None = Field(default=None, foreign_key="QuestionSet.id")    
    question_set: QuestionSet = Relationship(
        back_populates="main_questions",
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "MainQuestion.question_set_id==QuestionSet.id",
        },
    )

    # This is added for integrigy checks and Constraints for Numbering purposes
    exam_paper_id: UUID | None = Field(default=None, foreign_key="ExamPaper.id")
    # exam_paper: "ExamPaper" = Relationship(
    #     back_populates="main_questions",
    #     sa_relationship_kwargs={
    #         "lazy": "joined",
    #         "primaryjoin": "MainQuestion.exam_paper_id==ExamPaper.id",
    #     },
    # )

    subquestions: List["SubQuestion"] = Relationship(
        back_populates="main_question",
        sa_relationship_kwargs={
            "lazy": "joined",
            "cascade": "all, delete-orphan",
            "single_parent": True,  # Ensures orphan removal
        },
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
    answers: List["Answer"] | None = Relationship(
        back_populates="main_question",
        sa_relationship_kwargs={"lazy": "joined"}
    )
    # Define unique constraint
    __table_args__ = (
        UniqueConstraint(
            "exam_paper_id",
            "question_number",
            "question_set_id",
            name="_questions_order_per_question_set_uc",
        ),
    )


class SubQuestion(BaseUUIDModel,SQLModel, table=True):
    """_summary_

    Args:
        BaseUUIDModel (_type_): _description_
        SQLModel (_type_): _description_
        table (bool, optional): _description_. Defaults to True.
        
        This is the smallest/child question under the MainQuestion above. e.g (a), (b), (i) e.t.c
    """
    text: Optional[Dict[str, Any]] = Field(
        default_factory={}, sa_column=Column(JSONB, nullable=True)
    )
    marks: Optional[int] = None

    main_question_id: UUID | None = Field(default=None, foreign_key="MainQuestion.id")
    main_question: "MainQuestion" = Relationship(
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
    answers: List["Answer"] | None = Relationship(
        back_populates="sub_question", 
        sa_relationship_kwargs={"lazy": "joined"}
    )


# Define event listener to call the method before insertion
# @event.listens_for(MainQuestion, "before_insert")
# def before_insert_listener(mapper, connection, target):
#     target.assign_alphabetical_ordering()
