import enum
from app.models.module_model import CourseModuleLink
from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String, JSON
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID

from typing import List, Optional
from app.models.image_media_model import ImageMedia

from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug


# Define an Enum with valid member names extended to 2025
class ExamYearsType(enum.Enum): #TODO to fix the generation o fthe year
    YEAR_2000_2001 = "2000/2001"
    YEAR_2001_2002 = "2001/2002"
    YEAR_2002_2003 = "2002/2003"
    YEAR_2003_2004 = "2003/2004"
    YEAR_2004_2005 = "2004/2005"
    YEAR_2005_2006 = "2005/2006"
    YEAR_2006_2007 = "2006/2007"
    YEAR_2007_2008 = "2007/2008"
    YEAR_2008_2009 = "2008/2009"
    YEAR_2009_2010 = "2009/2010"
    YEAR_2010_2011 = "2010/2011"
    YEAR_2011_2012 = "2011/2012"
    YEAR_2012_2013 = "2012/2013"
    YEAR_2013_2014 = "2013/2014"
    YEAR_2014_2015 = "2014/2015"
    YEAR_2015_2016 = "2015/2016"
    YEAR_2016_2017 = "2016/2017"
    YEAR_2017_2018 = "2017/2018"
    YEAR_2018_2019 = "2018/2019"
    YEAR_2019_2020 = "2019/2020"
    YEAR_2020_2021 = "2020/2021"
    YEAR_2021_2022 = "2021/2022"
    YEAR_2022_2023 = "2022/2023"
    YEAR_2023_2024 = "2023/2024"
    YEAR_2024_2025 = "2024/2025"


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


class ExamPaperBase(SQLModel):
    name: str = Field(nullable=False)  # e.g FIRST YEAR EXAMINATION
    description: Optional[str] = Field(default="University Examination")
    year_of_exam: ExamYearsType = Field(
        sa_column=Column(
            Enum(ExamYearsType), nullable=False, default=ExamYearsType.YEAR_2023_2024.value
        )
    )
    exam_duration: int = Field(default=2) #Time taken to sit the examination
    exam_date: Optional[DateTime] = Field(nullable=True)


# ExamPaper model
class ExamPaper(ExamPaperBase, BaseUUIDModel, table=True):

    tags: Optional[dict] = Field(sa_column=JSON, default=None)

    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Course.created_by_id==User.id",
        }
    )

    # Relationships
    instructions: List["ExamInstruction"] = Relationship(
        link_model=InstructionExamsLink,
        back_populates="exam_papers",
        sa_relationship_kwargs={"lazy": "joined"},
    )
    # One-to_many
    # questions: Optional["Question"] = Relationship( 
    #     back_populates="exam_paper",
    #     sa_relationship_kwargs={"lazy": "joined"},
    # )

    # Many-to_Many
    modules: List["Module"] = Relationship(
        link_model=ModuleExamsLink,
        back_populates="exam_papers",
        sa_relationship_kwargs={"lazy": "joined"},
    )

    @validator("slug", pre=True, always=True)
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)


# Instruction model
class ExamInstruction(BaseUUIDModel, table=True):
    text: str = Field(nullable=False,unique=True)
    # many-to-many relationship with ExamPaper
    exam_papers: List[ExamPaper] = Relationship(
        back_populates="instructions", link_model=InstructionExamsLink
    )
