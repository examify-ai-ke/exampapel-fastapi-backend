from app import crud
from app.models.role_model import Role
from app.models.user_model import User
from app.schemas.user_schema import IUserCreate
from app.schemas.user_schema import IUserRead
from app.utils.exceptions.common_exception import IdNotFoundException
from uuid import UUID
from app.schemas.institution_schema import InstitutionRead
from app.models.institution_model import Institution
from app.schemas.faculty_schema import FacultyRead
from app.models.department_model import Department
from app.schemas.department_schema import DepartmentRead
from fastapi import HTTPException, Path, status
from typing_extensions import Annotated


async def user_exists(new_user: IUserCreate) -> IUserCreate:
    user = await crud.user.get_by_email(email=new_user.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="There is already a user with same email",
        )
    role = await crud.role.get(id=new_user.role_id)
    if not role:
        raise IdNotFoundException(Role, id=new_user.role_id)

    return new_user


async def is_valid_user(
    user_id: Annotated[UUID, Path(title="The UUID id of the user")]
) -> IUserRead:
    user = await crud.user.get(id=user_id)
    if not user:
        raise IdNotFoundException(User, id=user_id)

    return user

async def is_valid_institution(
    institution_id: Annotated[UUID, Path(title="The UUID id of the institution")]
)-> InstitutionRead:
    inst= await crud.institution.get(id=institution_id)
    if not inst:
        raise IdNotFoundException(Institution, id=institution_id)
    return inst


async def is_valid_faculty(
    faculty_id: Annotated[UUID, Path(title="The UUID id of the faculty")]
) -> FacultyRead:
    faculty = await crud.faculty.get(id=faculty_id)
    if not faculty:
        raise IdNotFoundException(faculty, id=faculty_id)
    return faculty


async def is_valid_department(
    department_id: Annotated[UUID, Path(title="The UUID id of the department")]
) -> DepartmentRead:
    department = await crud.faculty.get(id=department_id)
    if not department:
        raise IdNotFoundException(Department, id=department_id)
    return department


async def is_valid_user_id(
    user_id: Annotated[UUID, Path(title="The UUID id of the user")]
) -> IUserRead:
    user = await crud.user.get(id=user_id)
    if not user:
        raise IdNotFoundException(User, id=user_id)

    return user_id
