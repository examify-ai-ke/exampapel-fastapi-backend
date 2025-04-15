import hashlib
from sqlalchemy import String, UniqueConstraint, ARRAY
from sqlmodel import Field, Relationship, SQLModel, Column, JSON
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional
# from app.models.image_media_model import ImageMedia
from app.models.module_model import ModuleExamsLink
from pydantic import  field_validator, validator 
from app.utils.slugify_string import generate_slug
# from datetime import date
from datetime import datetime, date

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


def generate_academic_years(start_year: int = 1990) -> list:
    """Generate academic years in the format 'YYYY/YYYY+1' from start_year to the current academic year."""
    current_year = datetime.now().year
    return [f"{y}/{y+1}" for y in range(start_year, current_year + 1)]


# Generate the academic years list
# academic_years = generate_academic_years()


# Create a static Enum from 1990/1991 to the current year
# class AcademicYearEnum(str, enum.Enum):
#     """Enum for academic years from 1990/1991 to current year."""

#     for year in academic_years:
#         locals()[year.replace("/", "_")] = year  # Convert "YYYY/YYYY" to "YYYY_YYYY"


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
    # year_of_exam: Optional[str] = Field(
    #     default=academic_years[-1], nullable=True  # Default to the latest academic year
    # )
    exam_duration: int = Field(
        default=120,
        nullable=True,
    )  # Time taken to sit the examination, in minutes
    exam_date: Optional[date] = Field(nullable=True, unique=False)


# ExamPaper model
class ExamPaper(BaseUUIDModel,ExamPaperBase, table=True):    
    """_summary_

    Args:
        BaseUUIDModel (_type_): _description_
        ExamPaperBase (_type_): _description_
        table (bool, optional): _description_. Defaults to True.

    Returns:
        Unique ExamPaper with Questions and SubQuestions And All Its Description.
    """
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
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    # Relationship
    description_id: UUID | None = Field(default=None, foreign_key="ExamDescription.id")
    description: "ExamDescription" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "ExamPaper.description_id==ExamDescription.id",
        },
    )

    title_id: UUID | None = Field(default=None, foreign_key="ExamTitle.id")
    title: "ExamTitle" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "ExamPaper.title_id==ExamTitle.id",
        },
    )
    course_id: UUID | None = Field(default=None, foreign_key="Course.id")
    course: "Course" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "ExamPaper.course_id==Course.id",
        },
    )

    institution_id: UUID | None = Field(default=None, foreign_key="Institution.id")
    institution: "Institution" = Relationship(
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "primaryjoin": "ExamPaper.institution_id==Institution.id",
        },
    )
    # One-to_many
    question_sets: List["QuestionSet"] = Relationship(
        back_populates="exam_papers",
        link_model=ExamPaperQuestionLink,
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "single_parent": True,  # This allows delete-orphan to work
            "order_by": "QuestionSet.title.asc()",  # Sort question_sets by slug in ascending order
        },
    )

    # One-to-many relationship with MainQuestion
    main_questions: List["MainQuestion"] = Relationship(
        back_populates="exam_paper",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "single_parent": True,  # Ensures orphan removal
        },
    )

    # Many-to_Many
    modules: List["Module"] = Relationship(
        link_model=ModuleExamsLink,
        back_populates="exam_papers",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "cascade": "all, delete-orphan",
            "single_parent": True,
        },
    )

    # Hash value field
    hash_code: Optional[str] = Field(nullable=False, unique=True, default=None)

    # identifying_name: Optional[str] = Field(
    #     default="University Examination",
    #     nullable=True,
    # )  # e.g UNIVERSITY EXAMINATIONS

    @property
    def identifying_name(self) -> str:
        """
        Generate a unique identifying name for the exam paper based on its attributes.
        """
        title_name = self.title.name if self.title else "Unnamed Exam"
        year = self.year_of_exam if self.year_of_exam else "Unknown Year"
        exam_date = self.exam_date.strftime("%Y-%m-%d") if self.exam_date else "No Date"
        course_name = self.course.name if self.course else "No Course"
        institution_name = (
            self.institution.name if self.institution else "No Institution"
        )

        # Combine attributes to create a unique identifying name
        return (
            f"{title_name}-{year}-{course_name}-{institution_name}"
        )

    @property
    def calculate_hash(self):
        input_string = (
            f"{self.title_id}-{self.year_of_exam}-{self.institution_id}-{self.description_id}-{str(self.exam_date.strftime('%Y-%m-%d'))}-{str(self.exam_duration)}-{''.join(str(m.name) for m in self.modules)}-{''.join(str(i.name) for i in self.instructions)}-{self.identifying_name}"
        ) 

        # Add more fields as needed
        # Compute SHA-256 hash
        hash_object = hashlib.sha256(input_string.encode())
        hash_value = hash_object.hexdigest()
        # print(hash_value)
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
            "lazy": "selectin",
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
        # sa_relationship_kwargs={"lazy": "joined"},
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
        # sa_relationship_kwargs={"lazy": "joined"},
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
