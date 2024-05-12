import hashlib
from sqlalchemy import String, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel, Column, JSON
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional
# from app.models.image_media_model import ImageMedia

from pydantic import  field_validator, validator 
from app.utils.slugify_string import generate_slug
from datetime import date


# Define an Enum with valid member names extended to 2025
#  to fix the generation o fthe year
# class ExamYearsType(enum.Enum):
#     YEAR_2000_2001 = "2000/2001"
#     YEAR_2001_2002 = "2001/2002"
#     YEAR_2002_2003 = "2002/2003"
#     YEAR_2003_2004 = "2003/2004"
#     YEAR_2004_2005 = "2004/2005"
#     YEAR_2005_2006 = "2005/2006"
#     YEAR_2006_2007 = "2006/2007"
#     YEAR_2007_2008 = "2007/2008"
#     YEAR_2008_2009 = "2008/2009"
#     YEAR_2009_2010 = "2009/2010"
#     YEAR_2010_2011 = "2010/2011"
#     YEAR_2011_2012 = "2011/2012"
#     YEAR_2012_2013 = "2012/2013"
#     YEAR_2013_2014 = "2013/2014"
#     YEAR_2014_2015 = "2014/2015"
#     YEAR_2015_2016 = "2015/2016"
#     YEAR_2016_2017 = "2016/2017"
#     YEAR_2017_2018 = "2017/2018"
#     YEAR_2018_2019 = "2018/2019"
#     YEAR_2019_2020 = "2019/2020"
#     YEAR_2020_2021 = "2020/2021"
#     YEAR_2021_2022 = "2021/2022"
#     YEAR_2022_2023 = "2022/2023"
#     YEAR_2023_2024 = "2023/2024"
#     YEAR_2024_2025 = "2024/2025"


# Association table for many-to-many relationship between Unit and ExamPaper
class ModuleExamsLink(BaseUUIDModel, SQLModel, table=True):
    module_id: UUID | None = Field(
        foreign_key="Module.id",
        primary_key=True,
        default=None,
    )
    exam_id: UUID | None = Field(
        foreign_key="ExamPaper.id",
        primary_key=True,
        default=None,
    )


class InstructionExamsLink(BaseUUIDModel, SQLModel, table=True):
    instruction_id: UUID | None = Field(
        foreign_key="ExamInstruction.id",
        primary_key=True,
        default=None,
    )
    exam_id: UUID | None = Field(
        foreign_key="ExamPaper.id",
        primary_key=True,
        default=None,
    )


class ExamPaperQuestionLink(BaseUUIDModel, SQLModel, table=True):
    question_set_id: UUID | None = Field(
        foreign_key="QuestionSet.id",
        primary_key=True,
        default=None,
    )
    exam_id: UUID | None = Field(
        foreign_key="ExamPaper.id",
        primary_key=True,
        default=None,
    )
    # Define unique constraint
    __table_args__ = (
        UniqueConstraint(
            "exam_id", "question_set_id", name="_exam_paper_question_set_uc"
        ),
    )


class ExamPaperBase(SQLModel):
    # name: str = Field(nullable=False, unique=True)
    # description: Optional[str] = Field(default="University Examination", unique=False)
    year_of_exam: Optional[str] = Field(
        default="2024/2025",
        unique=False,
        nullable=True,
    )
    exam_duration: int = Field(
        default=2,
        nullable=True,
    )  # Time taken to sit the examination, in Hours
    exam_date: Optional[date] = Field(nullable=True, unique=False)


# ExamPaper model
class ExamPaper(BaseUUIDModel,ExamPaperBase, table=True):    
    tags: Optional[List] = Field(sa_column=Column(JSON, nullable=True, default=None))
    # tags: Optional[List] = Field(nullable=True, sa_type=JSONB, default_factory=dict)

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamPaper.created_by_id==User.id",
        }
    )

    # Relationships
    instructions: List["ExamInstruction"] = Relationship(
        link_model=InstructionExamsLink,
        back_populates="exam_papers",
        sa_relationship_kwargs={"lazy": "joined"},
    )
    # Relationship
    description_id: UUID | None = Field(default=None, foreign_key="ExamDescription.id")
    description: "ExamDescription" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamPaper.description_id==ExamDescription.id",
        },
    )

    title_id: UUID | None = Field(default=None, foreign_key="ExamTitle.id")
    title: "ExamTitle" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamPaper.title_id==ExamTitle.id",
        },
    )
    course_id: UUID | None = Field(default=None, foreign_key="Course.id")
    course: "Course" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamPaper.course_id==Course.id",
        },
    )

    institution_id: UUID | None = Field(default=None, foreign_key="Institution.id")
    institution: "Institution" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamPaper.institution_id==Institution.id",
        },
    )
    # One-to_many
    question_sets: List["QuestionSet"] = Relationship(
        back_populates="exam_papers",
        link_model=ExamPaperQuestionLink,
        sa_relationship_kwargs={"lazy": "joined"},
    )
    
    # Many-to_Many
    modules: List["Module"] = Relationship(
        link_model=ModuleExamsLink,
        back_populates="exam_papers",
        sa_relationship_kwargs={"lazy": "joined"},
    )

    # Hash value field
    hash_code: Optional[str] = Field(nullable=False, unique=True,default=None)

    @property
    def calculate_hash(self):
        input_string = input_string = (
            f"{self.title_id}-{self.year_of_exam}-{self.institution_id}-{self.description_id}-{str(self.exam_date.strftime('%Y-%m-%d'))}-{str(self.exam_duration)}-{''.join(str(m.name) for m in self.modules)}-{''.join(str(i.name) for i in self.instructions)}"
        )
        # Add more fields as needed
        # Compute SHA-256 hash
        hash_object = hashlib.sha256(input_string.encode())
        hash_value = hash_object.hexdigest()
        print(hash_value)
        return hash_value


# -----------------------------------------------------------------------
# Instruction model
class ExamInstruction(BaseUUIDModel,SQLModel, table=True):
    name: str = Field(nullable=False,unique=True)
    slug: Optional[str] = Field(nullable=False, unique=True)
    # many-to-many relationship with ExamPaper
    exam_papers: List[ExamPaper] = Relationship(
        back_populates="instructions", link_model=InstructionExamsLink
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamInstruction.created_by_id==User.id",
        }
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)


# ------------------------------------------------------------------------
class ExamTitleBase(SQLModel):
    name: str = Field(nullable=False, unique=True)  # e.g UNIVERSITY EXAMINATIONS
    
    description: Optional[str] = Field(
        nullable=True,
        default='''The title or name typically refers to the overarching categorization or identity of the exam. e.g "UNIVERSITY EXAMINATIONS:"''',
    )

class ExamTitle(BaseUUIDModel, ExamTitleBase,  table=True):
    """
    Model for exam titles.
    """
    slug: Optional[str] = Field(default=None, unique=True)
    exam_papers: List["ExamPaper"] = Relationship(
        back_populates="title",
        sa_relationship_kwargs={"lazy": "joined"},
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamTitle.created_by_id==User.id",
        }
    )

    @validator("name", pre=True, always=True)
    def capitalize_name(cls, value):
        if value:
            # Capitalize the first letter of each word
            # return re.sub(r"(\w)(\w*)", lambda m: m.group(1).upper() + m.group(2).lower(), value)
            return value.title()
        return value

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)

# -----------------------------------------------------
class ExamDescription(BaseUUIDModel, SQLModel, table=True):
    """
    Model for exam descriptions.
    """

    name: str = Field(nullable=False, unique=True)  # e.g SECOND YEAR STAGE EXAMINATION For ........
    slug: Optional[str] = Field(default=None, unique=True)
    description: Optional[str] = Field(
        nullable=True,
        default="The description usually provides additional information about the exam, such as its level, degree program, or specific course details. e.g SECOND YEAR STAGE EXAMINATION For....",
    )

    exam_papers: List["ExamPaper"] = Relationship(
        back_populates="description",
        sa_relationship_kwargs={"lazy": "joined"},
    )

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "ExamDescription.created_by_id==User.id",
        }
    )

    @validator("name", pre=True, always=True)
    def capitalize_name(cls, value):
        if value:
            # Capitalize the first letter of each word
            # return re.sub(r"(\w)(\w*)", lambda m: m.group(1).upper() + m.group(2).lower(), value)
            return value.title()
        return value

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)
