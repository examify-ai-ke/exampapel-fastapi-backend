from uuid import UUID
from typing import Dict, List
from sqlalchemy import or_, and_, func
from app.api.celery_task import print_hero
from app.utils.exceptions import IdNotFoundException, NameNotFoundException
from app.schemas.user_schema import IUserRead
from app.utils.resize_image import modify_image
from io import BytesIO
from app.deps import user_deps
from app.schemas.media_schema import IMediaCreate
from app.utils.slugify_string import generate_slug
from app.models.faculty_model import Faculty
from app.models.exam_paper_model import ExamPaper
from app.models.question_model import QuestionSet, Question
from app.models.institution_model import Address

from app.models.campus_model import Campus
from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.minio_client import MinioClient, S3Client
from fastapi_pagination import Params
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlmodel.ext.asyncio.session import AsyncSession
from app import crud
from app.api import deps
from app.models.institution_model import Institution, InstitutionType
from app.models.user_model import User
from app.schemas.common_schema import IOrderEnum
from app.schemas.institution_schema import (
    InstitutionCreate,
    InstitutionRead,
    InstitutionUpdate,
)
from app.schemas.address_schema import (
    AddressCreate,
    AddressRead,
    AddressUpdate,
)
from app.schemas.response_schema import (
    IDeleteResponseBase,
    IGetResponseBase,
    IGetResponsePaginated,
    IPostResponseBase,
    IPutResponseBase,
    create_response,
)
from app.schemas.role_schema import IRoleEnum
from app.core.authz import is_authorized
import time
from sqlmodel import SQLModel, Session, select
from sqlalchemy.orm import selectinload, joinedload
# from fastapi_sqla import Base, Page, AsyncPagination, AsyncSession
from app.utils.search_utils import SearchQueryBuilder, SearchResultProcessor
from typing import Dict

router = APIRouter()


@router.get("")
async def get_institution_list(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1),
    db_session: AsyncSession = Depends(deps.get_db),
    category: str = Query(default=None, description="Filter by institution category"),
    institution_type: str = Query(
        default=None, description="Filter by institution type"
    ),
    search_term: str = Query(
        default=None, description="Search term for institution name and other fields"
    ),
    location: str = Query(default=None, description="Filter by location"),
    tags: list[str] = Query(default=None, description="Filter by tags"),
    order_by: str = Query(default="created_at"),
    order: IOrderEnum = Query(default=IOrderEnum.descendent),
) -> IGetResponsePaginated[InstitutionRead]:
    """
    Gets a paginated list of institutions with ultra-optimized loading
    """
    # Ultra-optimized query - minimal data loading for maximum performance
    query = (
        select(Institution)
        .options(
            # Only load absolutely essential relationships
            selectinload(Institution.logo),  # Small image data
            selectinload(Institution.address),  # Basic address info
            # Use joinedload for many-to-one relationships (more efficient)
            joinedload(Institution.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            # Don't load faculties, campuses, exam_papers - use count properties instead
        )
    )
    # Add text search if search parameter is provided
    if search_term:
        query = query.filter(
            # Text fields
            or_(
                Institution.name.ilike(f"%{search_term}%"),
                Institution.description.ilike(f"%{search_term}%"),
                Institution.slug.ilike(f"%{search_term}%"),
                Institution.location.ilike(f"%{search_term}%"),
                Institution.full_profile.ilike(f"%{search_term}%"),
            )
        )
        # print("query:", query)
    # Filter by specific fields when provided
    if category:
        query = query.filter(Institution.category == category)

    if institution_type:
        query = query.filter(Institution.institution_type == institution_type)

    if location:
        query = query.filter(Institution.location.ilike(f"%{location}%"))

    # Filter by tags (using PostgreSQL JSONB containment)
    # More efficient tag filtering using or_
    if tags:
        # This creates a single condition checking if any tag is in the tags array
        query = query.filter(or_(*[Institution.tags.contains([tag]) for tag in tags]))
    institutions = await crud.institution.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query, order_by=order_by,
        order=order,
    )
    return create_response(data=institutions)


@router.get("/search/advanced")
async def advanced_search_institutions(
    q: str = Query(..., description="Search query for institutions"),
    institution_type: InstitutionType = Query(
        default=None, description="Filter by institution type"
    ),
    location: str = Query(default=None, description="Filter by location"),
    tags: List[str] = Query(default=None, description="Filter by tags"),
    established_year_from: int = Query(default=None, description="Filter institutions established from this year"),
    established_year_to: int = Query(default=None, description="Filter institutions established to this year"),
    has_exam_papers: bool = Query(default=None, description="Filter institutions with/without exam papers"),
    sort_by: str = Query(default="relevance", description="Sort by: relevance, name, established_year, exam_count"),
    sort_order: str = Query(default="desc", description="Sort order: asc, desc"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    highlight: bool = Query(default=False, description="Enable search term highlighting"),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponsePaginated[InstitutionRead]:
    """
    Advanced search for institutions with comprehensive filtering and sorting.
    
    Search across:
    - Institution names
    - Descriptions
    - Locations
    - Full profiles
    - Tags
    
    Features:
    - Full-text search with relevance scoring
    - Multiple filtering options
    - Advanced sorting capabilities
    - Search result highlighting
    """
    
    # Build search conditions
    search_conditions = []
    
    if q:
        q_clean = q.strip()
        
        # Multi-field search with different weights
        text_conditions = [
            # High priority fields
            Institution.name.ilike(f"%{q_clean}%"),
            Institution.slug.ilike(f"%{q_clean}%"),
            # Medium priority fields
            Institution.description.ilike(f"%{q_clean}%"),
            Institution.location.ilike(f"%{q_clean}%"),
            # Lower priority fields
            Institution.full_profile.ilike(f"%{q_clean}%"),
        ]
        
        search_conditions.append(or_(*text_conditions))
    
    # Build filter conditions
    filter_conditions = []
    
    if institution_type:
        filter_conditions.append(Institution.institution_type == institution_type)
    
    if location:
        filter_conditions.append(Institution.location.ilike(f"%{location}%"))
    
    if tags:
        # Simple tag filtering using contains (this works with JSON arrays)
        for tag in tags:
            filter_conditions.append(Institution.tags.contains([tag]))
    
    if established_year_from:
        filter_conditions.append(Institution.established_year >= established_year_from)
    
    if established_year_to:
        filter_conditions.append(Institution.established_year <= established_year_to)
    
    if has_exam_papers is not None:
        if has_exam_papers:
            # Institutions that have exam papers
            filter_conditions.append(
                func.exists(
                    select(1).select_from(ExamPaper).where(ExamPaper.institution_id == Institution.id)
                )
            )
        else:
            # Institutions without exam papers
            filter_conditions.append(
                ~func.exists(
                    select(1).select_from(ExamPaper).where(ExamPaper.institution_id == Institution.id)
                )
            )
    
    # Build the complete query with optimized loading
    query = (
        select(Institution)
        .options(
            joinedload(Institution.created_by).load_only(
                User.id, User.first_name, User.last_name, User.email
            ),
            selectinload(Institution.logo),
            # Load exam papers count for sorting
            selectinload(Institution.exam_papers).load_only(
                ExamPaper.id, ExamPaper.year_of_exam
            ),
        )
    )
    
    # Apply search conditions
    if search_conditions:
        query = query.where(and_(*search_conditions))
    
    # Apply filter conditions
    if filter_conditions:
        query = query.where(and_(*filter_conditions))
    
    # Apply sorting
    if sort_by == "name":
        sort_field = Institution.name
    elif sort_by == "established_year":
        sort_field = Institution.established_year
    elif sort_by == "exam_count":
        # This would require a subquery for accurate sorting
        sort_field = Institution.created_at  # Fallback
    else:  # relevance or default
        sort_field = Institution.created_at
    
    if sort_order.lower() == "asc":
        query = query.order_by(sort_field.asc())
    else:
        query = query.order_by(sort_field.desc())
    
    # Execute paginated query
    institutions = await crud.institution.get_multi_paginated_ordered(
        db_session=db_session, skip=skip, limit=limit, query=query
    )
    
    return create_response(data=institutions)


@router.get("/search/suggestions")
async def get_institution_search_suggestions(
    q: str = Query(..., min_length=2, description="Search query for suggestions"),
    limit: int = Query(default=10, ge=1, le=20),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IGetResponseBase[List[Dict[str, str]]]:
    """
    Get search suggestions for institutions based on partial input.
    
    Returns suggestions from:
    - Institution names
    - Locations
    - Common tags
    - Institution types
    """
    
    suggestions = []
    q_clean = q.strip().lower()
    
    # Institution name suggestions
    name_query = (
        select(Institution.name)
        .where(Institution.name.ilike(f"%{q_clean}%"))
        .limit(5)
    )
    name_result = await db_session.execute(name_query)
    for (name,) in name_result.all():
        suggestions.append({
            "type": "institution",
            "value": name,
            "display": name
        })
    
    # Location suggestions
    location_query = (
        select(Institution.location)
        .where(Institution.location.ilike(f"%{q_clean}%"))
        .distinct()
        .limit(3)
    )
    location_result = await db_session.execute(location_query)
    for (location,) in location_result.all():
        if location:
            suggestions.append({
                "type": "location",
                "value": location,
                "display": f"Location: {location}"
            })
    
    # Institution type suggestions
    for inst_type in InstitutionType:
        if q_clean in inst_type.value.lower():
            suggestions.append({
                "type": "institution_type",
                "value": inst_type.value,
                "display": f"Type: {inst_type.value}"
            })
    
    # Limit total suggestions
    suggestions = suggestions[:limit]
    
    return create_response(data=suggestions)


@router.get("/get_by_created_at")
async def get_institution_list_order_by_created_at(
    order: IOrderEnum
    | None = Query(
        default=IOrderEnum.ascendent, description="It is optional. Default is ascendent"
    ),
    params: Params = Depends(),
    # current_user: User = Depends(deps.get_current_user()),
    # current_user: User =None
) -> IGetResponsePaginated[InstitutionRead]:
    """
    Gets a paginated list of institutions ordered by created at datetime
    """
    institutions = await crud.institution.get_multi_paginated_ordered(
        params=params, order=order
    )
    return create_response(data=institutions)


@router.get("/get_by_id/{institution_id}")
async def get_institution_by_id(
    institution_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_user()),
    # current_user: User = None
) -> IGetResponseBase[InstitutionRead]:
    """
    Gets a institution by its id
    """
    # Add options to load address relationship
    institution = await crud.institution.get(
        id=institution_id,
        db_session=db_session,
        options=[
            selectinload(Institution.faculties).selectinload(Faculty.departments),
            selectinload(Institution.campuses).selectinload(Campus.address),
            selectinload(Institution.exam_papers),
            selectinload(Institution.logo),
            selectinload(Institution.created_by),
            selectinload(Institution.address),
        ],
    )
    if not institution:
        raise IdNotFoundException(Institution, institution_id)

    # print_hero.delay(hero.id)
    return create_response(data=institution)


@router.get("/get_by_slug/{institution_slug}")
async def get_institution_by_slug(
    institution_slug: str,
    db_session: AsyncSession = Depends(deps.get_db),
    # current_user: User = Depends(deps.get_current_user()),
) -> IGetResponseBase[list[InstitutionRead]]:
    """
    Gets a institution by slug
    """
    # Use db_session parameter and load address relationship
    institution = await crud.institution.get_institution_by_slug(
        slug=institution_slug, 
        db_session=db_session
    )
    if not institution:
        raise NameNotFoundException(Institution, institution_slug)

    return create_response(data=institution)


@router.post("")
async def create_institution(
    institution: InstitutionCreate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[InstitutionRead]:
    """
    Creates a new institution 

    Required roles:
    - admin
    - manager
    """
    # print("Create instituion..........")
    # print(current_user)
    inst = await crud.institution.create(
        obj_in=institution, created_by_id=current_user.id
    )    
    return create_response(data=inst)


@router.put("/{institution_id}")
async def update_institution(
    institution_id: UUID,
    institution: InstitutionUpdate,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IPutResponseBase[InstitutionRead]:
    """
    Updates a institution by its id

    Required roles:
    - admin
    - manager
    """
    current_inst = await crud.institution.get(
        id=institution_id,
        db_session=db_session,
        options=[
            selectinload(Institution.faculties).selectinload(Faculty.departments),
            selectinload(Institution.campuses).selectinload(Campus.address),
            selectinload(Institution.exam_papers),
            selectinload(Institution.logo),
            selectinload(Institution.created_by),
            selectinload(Institution.address),
        ],
    )
    if not current_inst:
        raise IdNotFoundException(Institution, institution_id)

    institution_updated = await crud.institution.update(
        obj_new=institution, obj_current=current_inst
    )
    return create_response(data=institution_updated)


@router.delete("/{institution_id}")
async def remove_institution(
    institution_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[InstitutionRead]:
    """
    Deletes a institution by its id

    Required roles:
    - admin
    - manager
    """
    current_institution = await crud.institution.get(id=institution_id)
    if not current_institution:
        raise IdNotFoundException(Institution, institution_id)
    insti = await crud.institution.remove(id=institution_id)
    return create_response(data=insti)


# Associate faculty with institution
@router.post("/{institution_id}/faculties/{faculty_id}")
async def add_faculty_to_institution(
    institution_id: UUID,
    faculty_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    ) -> IDeleteResponseBase[InstitutionRead]:
    """
    Add a Faculty to an Institution by id

    Required roles:
    - admin
    - manager
    """
    institution = await crud.institution.get(id=institution_id)
    faculty = await crud.faculty.get(id=faculty_id)
    if not institution or not faculty:
        raise HTTPException(status_code=404, detail="Institution or Faculty not found")

    # Check if association already exist
    _association = await crud.institution.check_existing_association(
        institution=institution, faculty=faculty
    )  
    
    if _association is not None:
        # If an association already exists, raise an error or return a suitable response
        raise HTTPException(
            status_code=400,
            detail=f"Faculty '{faculty_id}' is already associated with Institution '{institution_id}'"
        )
    else:    

        institution.faculties.append(faculty)
        institution_with_faculty = await crud.institution.add_related(
            appended_parent_object=institution
        )
        return create_response(data=institution_with_faculty)


@router.delete("/{institution_id}/faculties/{faculty_id}")
async def remove_faculty_from_institution(
    institution_id: UUID,
    faculty_id: UUID,
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    db_session: AsyncSession = Depends(deps.get_db),
) -> IDeleteResponseBase[InstitutionRead]:
    """
    Remove a Faculty from an Institution by id.

    Required roles:
    - admin
    - manager
    """
    # Fetch the Institution with its faculties eagerly loaded to check association
    institution = await crud.institution.get(
        id=institution_id, 
        db_session=db_session, 
        options=[selectinload(Institution.faculties)] # Eager load faculties
    )
    if not institution:
        raise IdNotFoundException(Institution, institution_id)

    # Fetch the Faculty
    faculty = await crud.faculty.get(id=faculty_id, db_session=db_session)
    if not faculty:
        raise IdNotFoundException(Faculty, faculty_id)

    # Check if the faculty is actually associated with the institution
    if faculty not in institution.faculties:
        raise HTTPException(
            status_code=400,
            detail=f"Faculty '{faculty.name}' is not associated with Institution '{institution.name}'"
        )

    # Remove the faculty from the institution's list
    # This works if the relationship is configured correctly in the models
    institution.faculties.remove(faculty)
    
    # Add the institution to the session to mark it for update and commit
    db_session.add(institution)
    await db_session.commit()
    await db_session.refresh(institution) # Refresh to get the updated state

    # Optionally, reload relationships if needed for the response model
    # This might require another query or ensure the refresh loaded them
    updated_institution = await crud.institution.get(
        id=institution_id, 
        db_session=db_session,
        options=[selectinload(Institution.faculties)] # Reload faculties for response
    )

    return create_response(data=updated_institution)


@router.post("/{institution_id}/logo")
async def upload_institution_logo(
    valid_institution: Institution = Depends(user_deps.is_valid_institution),
    title: str | None = Body(None),
    description: str | None = Body(None),
    institution_logo: UploadFile = File(...),    
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
    minio_client: S3Client = Depends(deps.minio_auth),
) -> IPostResponseBase[InstitutionRead]:
    """
    Uploads a institution official logo by id

    Required roles:
    - admin
    - manager
    """
    # print(institution_logo)
    try:
        image_modified = modify_image(BytesIO(institution_logo.file.read()))
        data_file = minio_client.put_object(
            file_name=institution_logo.filename,
            file_data=BytesIO(image_modified.file_data),
            content_type=institution_logo.content_type,
        )
        # print("data_file:", data_file)
        media = IMediaCreate(
            title=title, description=description, path=data_file.url
        )
        inst = await crud.institution.update_institution_logo(
            institution=valid_institution,
            media=media,
            heigth=image_modified.height,
            width=image_modified.width,
            file_format=image_modified.file_format,
        )
        return create_response(data=inst)
    except Exception as e:
        print(e)
        return Response("Internal server error", status_code=500)


@router.post("/{institution_id}/address")
async def create_institution_address(
    institution_id: UUID,
    address: AddressCreate,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPostResponseBase[InstitutionRead]:
    """
    Create an address for an institution

    Required roles:
    - admin
    - manager
    """
    # Verify institution exists
    institution = await crud.institution.get(
        id=institution_id, 
        db_session=db_session,
        options=[selectinload(Institution.address)]
    )
    if not institution:
        raise IdNotFoundException(Institution, institution_id)
    
    # Check if institution already has an address
    if institution.address:
        raise HTTPException(
            status_code=400,
            detail=f"Institution '{institution.name}' already has an address. Use PUT to update."
        )
    
    # Create a new address
    new_address = Address(**address.model_dump())
    new_address.institution_id = institution_id
    
    # Save address to database
    db_session.add(new_address)
    await db_session.commit()
    
    # Refresh institution to include the new address
    await db_session.refresh(institution)
    
    return create_response(data=institution)


@router.put("/{institution_id}/address")
async def update_institution_address(
    institution_id: UUID,
    address: AddressUpdate,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IPutResponseBase[InstitutionRead]:
    """
    Update an address for an institution

    Required roles:
    - admin
    - manager
    """
    # Verify institution exists
    institution = await crud.institution.get(
        id=institution_id, 
        db_session=db_session,
        options=[selectinload(Institution.address)]
    )
    if not institution:
        raise IdNotFoundException(Institution, institution_id)
    
    # Check if institution has an address
    if not institution.address:
        raise HTTPException(
            status_code=404,
            detail=f"Institution '{institution.name}' doesn't have an address. Create one first."
        )
    
    # Get address data excluding unset fields
    address_data = address.model_dump(exclude_unset=True)
    if not address_data:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )
    
    # Update existing address
    for key, value in address_data.items():
        setattr(institution.address, key, value)
    
    # Save updated address to database
    db_session.add(institution.address)
    await db_session.commit()
    
    # Refresh institution to include the updated address
    await db_session.refresh(institution)
    
    return create_response(data=institution)


@router.delete("/{institution_id}/address")
async def delete_institution_address(
    institution_id: UUID,
    db_session: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(
        deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
    ),
) -> IDeleteResponseBase[InstitutionRead]:
    """
    Delete an address from an institution

    Required roles:
    - admin
    - manager
    """
    # Verify institution exists
    institution = await crud.institution.get(
        id=institution_id, 
        db_session=db_session,
        options=[selectinload(Institution.address)]
    )
    if not institution:
        raise IdNotFoundException(Institution, institution_id)
    
    # Check if institution has an address
    if not institution.address:
        raise HTTPException(
            status_code=404,
            detail=f"Institution '{institution.name}' doesn't have an address to delete."
        )
    
    # Get the address ID for deletion
    address_id = institution.address.id
    
    # Delete the address
    delete_query = select(Address).where(Address.id == address_id)
    result = await db_session.execute(delete_query)
    address_to_delete = result.scalar_one_or_none()
    
    if address_to_delete:
        await db_session.delete(address_to_delete)
        await db_session.commit()
    
    # Refresh institution to reflect the deletion
    await db_session.refresh(institution)
    
    return create_response(data=institution)
