from sqlmodel import Field, Relationship, SQLModel, Enum, Column, DateTime, String
from app.models.base_uuid_model import BaseUUIDModel
from uuid import UUID
import enum
from typing import List, Optional
from app.models.image_media_model import ImageMedia
from pydantic import EmailStr, field_validator, validator
from app.utils.slugify_string import generate_slug

# from starlette_admin import TagsField
from starlette_admin.contrib.sqla import  ModelView
from starlette_admin import fields, TagsField

# Define an enumeration for institution types
class InstitutionTypes(enum.Enum):
    UNIVERSITY = "University"
    COLLEGE = "College"
    TVET = "TVET"
    OTHER = "Other"


# Define the link model for the many-to-many relationship between Institution and  Faculty
class InstitutionFacultyLink(BaseUUIDModel, SQLModel, table=True):
    institution_id: UUID | None = Field(
        foreign_key="Institution.id",
        primary_key=True,
        default=None,

    )
    faculty_id: UUID | None = Field(
        foreign_key="Faculty.id",
        primary_key=True,
        default=None,
  
    )


# Define the base Institution model
class InstitutionBase(SQLModel):
    name: str = Field(nullable=False, unique=True)
    description: Optional[str] = Field(nullable=True, default="An Institution of choice")
    institution_type: InstitutionTypes = Field(
        sa_column=Column(Enum(InstitutionTypes), nullable=False))
    email: EmailStr = Field(sa_column=Column(String, index=True, unique=True))
    phone_number: Optional[str] = Field(nullable=False)
    # Slug with a validator to generate it from the name
    slug: Optional[str] = Field(default=None, unique=True)


class Institution(BaseUUIDModel, InstitutionBase, table=True): 

    image_id: UUID | None = Field(default=None, foreign_key="ImageMedia.id")
    logo: ImageMedia = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Institution.image_id==ImageMedia.id",
        }
    )
    created_by_id: UUID | None = Field(default=None, foreign_key="User.id")
    created_by: "User" = Relationship(  # noqa: F821
        sa_relationship_kwargs={
            "lazy": "joined",
            "primaryjoin": "Institution.created_by_id==User.id",
        }
    )

    # Relationships
    campuses: List["Campus"] = Relationship(
        back_populates="institution", sa_relationship_kwargs={"lazy": "joined"}
    )

    # # Many-to-many relationship with Faculty via a linktable
    faculties: List["Faculty"] = Relationship(
        link_model=InstitutionFacultyLink,
        back_populates="institutions",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    exam_papers: List["ExamPaper"] = Relationship(
        back_populates="institution", sa_relationship_kwargs={"lazy": "selectin"}
    )

    @validator("slug")
    def set_slug(cls, value, values):
        name = values.get("name", "")
        return generate_slug(name)

    @property
    def exams_count(self):
        count=len(self.exam_papers)
        return count
    @property
    def campuses_count(self):
        count_campuses = len(self.campuses)
        return count_campuses

    @property
    def faculties_count(self):
        count_faculties = len(self.faculties)
        return count_faculties


# class CustomModelView(ModelView):
#     def get_list(self, request, *args, **kwargs):
#         """
#         Overrides the default get_list method to transform the response.
#         """
#         response = super().get_list(request, *args, **kwargs)

#         # Transform the response to extract the 'items' field
#         if isinstance(response, dict):
#             response = response.get("data", {}).get("items", [])
#         print(response)
#         return response


class InstitutionView(ModelView):
    page_size = 50
    page_size_options = [-1]
    name = "Institution"
    responsive_table = True
    pk_attr = "id"

    list_fields = ["name", "institution_type", "email"]
    search_fields = ["name", "email", "description", "slug"]
    fields = [
        fields.StringField("id"),
        fields.StringField("name"),
        fields.StringField("description"),
        fields.StringField("institution_type"),
        fields.StringField("email"),
        fields.StringField("phone_number"),
        fields.StringField("slug"),
        fields.IntegerField("exams_count"),
        fields.IntegerField("campuses_count", label="Campuses"),
        fields.IntegerField("faculties_count", label="Faculties"),
    ]

    async def serialize_list(self, objects, request):
        """
        Override serialize_list to handle the nested response structure
        """
        print("serialize_list called...................")
        if isinstance(objects, dict):
            if "data" in objects and "items" in objects["data"]:
                objects = objects["data"]["items"]
        return await super().serialize_list(objects, request)

    async def serialize_item(self, obj, request):
        """
        Override serialize_item to handle the nested response structure
        """
        print("serialize_item called...................")
        if isinstance(obj, dict) and "data" in obj:
            obj = obj["data"]
        return await super().serialize_item(obj, request)

    async def serialize_value(self, value, field_name, request):
        """
        Override serialize_value to handle specific field transformations if needed
        """
        print(f"serialize_value called for {field_name}...................")
        return await super().serialize_value(value, field_name, request)

     