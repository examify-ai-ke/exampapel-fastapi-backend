"""
Exam Paper Inserter - Complete API Client
======================================

This module provides a complete Python client for inserting exam papers and questions
into the FastAPI backend. It includes:

1. User authentication with bearer token management
2. Institution detail retrieval and validation
3. Complete exam paper creation workflow
4. Question and sub-question insertion
5. Error handling and validation

Author: Kilo Code
"""

import asyncio
import json
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field, validator, field_validator, ConfigDict, EmailStr


# ============================================================================
# CONFIGURATION AND LOGGING
# ============================================================================

class APIConfig(BaseModel):
    """Configuration for API connection"""
    base_url: str = "http://fastapi.localhost/api/v1"
    timeout: int = 30
    max_retries: int = 3
    
    model_config = ConfigDict(from_attributes=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION SCHEMAS AND CLIENT
# ============================================================================

class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str
    provider: str = Field(default="email")
    
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    """Token response schema - matches backend Token schema"""
    access_token: str
    token_type: str
    refresh_token: str
    user: Dict[str, Any]  # Backend returns IUserRead object, but we accept as dict for flexibility
    
    model_config = ConfigDict(from_attributes=True)

class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refresh_token: str
    
    model_config = ConfigDict(from_attributes=True)

class AuthClient:
    """
    Client for handling authentication with the FastAPI backend.
    
    Provides login, token refresh, and automatic token management.
    """
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.client = httpx.AsyncClient(timeout=config.timeout)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.user_info: Optional[Dict[str, Any]] = None
        
    async def login(self, email: str, password: str) -> bool:
        """
        Authenticate user and store tokens
        
        Args:
            email: User email
            password: User password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            login_data = LoginRequest(email=email, password=password)
            response = await self.client.post(
                f"{self.config.base_url}/login",
                json=login_data.model_dump(mode='json')
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # Backend returns data wrapped in response format: {data: {...}, message: "...", meta: {...}}
                token_data = TokenResponse(**response_data["data"])
                self.access_token = token_data.access_token
                self.refresh_token = token_data.refresh_token
                self.user_info = token_data.user
                
                # Set token expiration (default 30 minutes from backend)
                self.token_expires_at = datetime.now() + timedelta(minutes=25)  # Conservative
                
                logger.info(f"Successfully logged in as {email}")
                return True
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    async def refresh_access_token(self) -> bool:
        """
        Refresh the access token using refresh token
        
        Returns:
            True if refresh successful, False otherwise
        """
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
            
        try:
            refresh_data = RefreshTokenRequest(refresh_token=self.refresh_token)
            response = await self.client.post(
                f"{self.config.base_url}/login/new_access_token",
                json=refresh_data.model_dump(mode='json')
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # Backend returns data wrapped in response format: {data: {...}, message: "...", meta: {...}}
                token_data = response_data["data"]
                self.access_token = token_data["access_token"]
                self.token_expires_at = datetime.now() + timedelta(minutes=25)
                
                logger.info("Access token refreshed successfully")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return False
    
    async def get_headers(self) -> Dict[str, str]:
        """
        Get authorization headers for API requests
        
        Returns:
            Dictionary with authorization headers
        """
        # Check if token needs refresh
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            await self.refresh_access_token()
            
        if not self.access_token:
            raise ValueError("No access token available - please login first")
            
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def logout(self) -> bool:
        """
        Logout user and clear tokens
        
        Returns:
            True if logout successful, False otherwise
        """
        try:
            headers = await self.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/logout",
                headers=headers
            )
            
            if response.status_code == 200:
                self.access_token = None
                self.refresh_token = None
                self.token_expires_at = None
                self.user_info = None
                
                logger.info("Successfully logged out")
                return True
            else:
                logger.error(f"Logout failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return False
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# ============================================================================
# PROGRAMME SCHEMAS AND CLIENT
# ============================================================================

class ProgrammeCreate(BaseModel):
    """Schema for creating a programme"""
    name: str = Field(default="Bachelors/Undergraduate")
    description: Optional[str] = Field("A specific type of university/College program (e.g., Bachelors, Masters. etc)", max_length=500)
    
    model_config = ConfigDict(from_attributes=True)

class ProgrammeRead(BaseModel):
    """Schema for programme response"""
    id: UUID
    name: str
    slug: Optional[str]
    description: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)

class ProgrammeClient:
    """
    Client for handling programme operations.
    """
    
    def __init__(self, config: APIConfig, auth_client: AuthClient):
        self.config = config
        self.auth_client = auth_client
        self.client = httpx.AsyncClient(timeout=config.timeout)
    
    async def create_programme(self, programme_data: ProgrammeCreate) -> Optional[ProgrammeRead]:
        """Create a new programme"""
        try:
            headers = await self.auth_client.get_headers()
            # First try to get all programmes and check if it exists (since we don't have search by name yet maybe)
            # But the backend might return 400 if duplicate. Let's try to create and handle error or success.
            # Actually, standard flow: try create.
            
            response = await self.client.post(
                f"{self.config.base_url}/programme",
                headers=headers,
                json=programme_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created programme: {data['name']}")
                return ProgrammeRead(**data)
            elif response.status_code == 400 or response.status_code == 409:
                 # Ensure we handle existing programmes if API returns error for duplicates
                 logger.warning(f"Programme might already exist: {response.status_code}")
                 # You might need a way to fetch the existing programme here if create fails
                 # For now, let's assume valid flow or look at search if available.
                 # Let's try to fetch all and find it (inefficient but works for script)
                 return await self.get_programme_by_name(programme_data.name)
            else:
                logger.error(f"Failed to create programme: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating programme: {str(e)}")
            return None

    async def get_programme_by_name(self, name: str) -> Optional[ProgrammeRead]:
        """Helper to find programme by name from list"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.get(
                f"{self.config.base_url}/programme",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                # data is likely list of items or paginated {items: []}
                items = data.get("items", []) if isinstance(data, dict) else data
                
                for item in items:
                    if item.get("name") == name:
                         return ProgrammeRead(**item)
                return None
            else:
                return None
        except Exception:
            return None

    async def close(self):
        await self.client.aclose()


# ============================================================================
# INSTITUTION SCHEMAS AND CLIENT
# ============================================================================

class InstitutionCreate(BaseModel):
    """Schema for creating an institution"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field("An Institution of choice", max_length=500)
    category: str = Field(default="University")
    institution_type: str = Field(default="Public")
    location: Optional[str] = Field(None, max_length=200)
    key: Optional[str] = None
    kuccps_institution_url: Optional[str] = None
    full_profile: Optional[str] = None
    parent_ministry: Optional[str] = None
    tags: Optional[List[str]] = None
    
    model_config = ConfigDict(from_attributes=True)

class InstitutionRead(BaseModel):
    """Schema for institution response"""
    id: UUID
    name: str
    slug: Optional[str]
    description: Optional[str]
    category: Optional[str]
    institution_type: Optional[str]
    location: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InstitutionClient:
    """
    Client for handling institution operations.
    
    Provides methods to retrieve, create, and validate institutions.
    """
    
    def __init__(self, config: APIConfig, auth_client: AuthClient):
        self.config = config
        self.auth_client = auth_client
        self.client = httpx.AsyncClient(timeout=config.timeout)
    
    async def get_institution_by_id(self, institution_id: UUID) -> Optional[InstitutionRead]:
        """
        Get institution by ID
        
        Args:
            institution_id: UUID of the institution
            
        Returns:
            Institution data if found, None otherwise
        """
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.get(
                f"{self.config.base_url}/institution/get_by_id/{institution_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                return InstitutionRead(**data)
            else:
                logger.error(f"Failed to get institution: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting institution: {str(e)}")
            return None
    
    async def get_institution_by_slug(self, slug: str) -> Optional[InstitutionRead]:
        """
        Get institution by slug
        
        Args:
            slug: Slug of the institution
            
        Returns:
            Institution data if found, None otherwise
        """
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.get(
                f"{self.config.base_url}/institution/get_by_slug/{slug}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                return InstitutionRead(**data)
            else:
                logger.error(f"Failed to get institution by slug: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting institution by slug: {str(e)}")
            return None
    
    async def search_institutions(
        self, 
        search_term: Optional[str] = None,
        limit: int = 50,
        sort_by: str = "relevance",
        sort_order: str = "desc",
        skip: int = 0,
        highlight: bool = False
    ) -> List[InstitutionRead]:
        """
        Search institutions using advanced search
        
        Args:
            search_term: Search query (q)
            limit: Maximum number of results
            sort_by: Sort field (relevance, name, created_at)
            sort_order: Sort order (asc, desc)
            skip: Pagination skip
            highlight: Enable highlighting
            
        Returns:
            List of institutions matching criteria
        """
        try:
            headers = await self.auth_client.get_headers()
            params = {
                "limit": limit,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "skip": skip,
                "highlight": str(highlight).lower()
            }
            
            if search_term:
                params["q"] = search_term
                
            response = await self.client.get(
                f"{self.config.base_url}/institution/search/advanced",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()["data"]
                institutions = []
                # Advanced search likely returns list directly or inside items
                items = data.get("items", []) if isinstance(data, dict) else data
                for item in items:
                    institutions.append(InstitutionRead(**item))
                return institutions
            else:
                logger.error(f"Failed to search institutions: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error searching institutions: {str(e)}")
            return []
    
    async def create_institution(self, institution_data: InstitutionCreate) -> Optional[InstitutionRead]:
        """
        Create a new institution
        
        Args:
            institution_data: Institution creation data
            
        Returns:
            Created institution data if successful, None otherwise
        """
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/institution",
                headers=headers,
                json=institution_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created institution: {data['name']}")
                return InstitutionRead(**data)
            else:
                logger.error(f"Failed to create institution: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating institution: {str(e)}")
            return None
    
    async def validate_institution_exists(self, institution_id: UUID) -> bool:
        """
        Validate that an institution exists
        
        Args:
            institution_id: UUID of the institution to validate
            
        Returns:
            True if institution exists, False otherwise
        """
        institution = await self.get_institution_by_id(institution_id)
        return institution is not None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# ============================================================================
# EXAM PAPER SCHEMAS
# ============================================================================

class ExamPaperCreate(BaseModel):
    """Schema for creating an exam paper"""
    year_of_exam: str = Field(default="2024/2025")
    exam_duration: int = Field(default=120, ge=30, le=480)
    exam_date: Optional[date] = Field(None)
    tags: Optional[List[str]] = Field(default=None)
    
    # Required relationships
    title_id: UUID
    description_id: UUID
    course_id: UUID
    institution_id: UUID
    
    # Many-to-many relationships
    instruction_ids: List[UUID] = Field(default=[])
    module_ids: List[UUID] = Field(default=[])
    
    @field_validator('year_of_exam')
    @classmethod
    def validate_year_format(cls, v):
        """Validate academic year format (YYYY/YYYY)"""
        if not v or '/' not in v:
            raise ValueError('Year must be in format YYYY/YYYY')
        parts = v.split('/')
        if len(parts) != 2:
            raise ValueError('Year must be in format YYYY/YYYY')
        try:
            year1, year2 = int(parts[0]), int(parts[1])
            if year2 != year1 + 1:
                raise ValueError('Second year must be consecutive to first year')
            if year1 < 1990 or year1 > 2030:
                raise ValueError('Year must be between 1990 and 2030')
        except ValueError:
            raise ValueError('Year parts must be valid integers')
        return v
    
    model_config = ConfigDict(from_attributes=True)

class ExamTitleCreate(BaseModel):
    """Schema for creating exam title"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    
    model_config = ConfigDict(from_attributes=True)

class ExamDescriptionCreate(BaseModel):
    """Schema for creating exam description"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field("The description usually provides additional information about the exam, such as its level, degree program, or specific course details. e.g SECOND YEAR STAGE EXAMINATION For....", max_length=500)
    
    model_config = ConfigDict(from_attributes=True)

class ExamInstructionCreate(BaseModel):
    """Schema for creating exam instruction"""
    name: str = Field(..., min_length=2, max_length=500)
    slug: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ModuleCreate(BaseModel):
    """Schema for creating a module"""
    name: str = Field(..., min_length=2, max_length=200)
    unit_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=500)
    
    model_config = ConfigDict(from_attributes=True)

class CourseCreate(BaseModel):
    """Schema for creating a course"""
    name: str = Field(..., min_length=2, max_length=200)
    course_acronym: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = Field(None, max_length=500)
    programme_id: UUID
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# QUESTION SCHEMAS (Editor.js Compatible)
# ============================================================================

class EditorJSBlock(BaseModel):
    """Generic Editor.js block schema"""
    id: str
    type: str
    data: Dict[str, Any]
    
    model_config = ConfigDict(from_attributes=True)

class QuestionTextSchema(BaseModel):
    """Schema for question text using Editor.js format"""
    time: int
    blocks: List[EditorJSBlock]
    
    model_config = ConfigDict(from_attributes=True)

class QuestionSetCreate(BaseModel):
    """Schema for creating a question set"""
    title: str = Field(..., min_length=2, max_length=200)
    
    model_config = ConfigDict(from_attributes=True)

class MainQuestionCreate(BaseModel):
    """Schema for creating main questions"""
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = Field(None, ge=1, le=100)
    numbering_style: str = Field(default="numeric")
    question_number: str = Field(..., min_length=1)
    question_set_id: Optional[UUID] = None
    exam_paper_id: Optional[UUID] = None
    
    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump(mode='json')
        return v
    
    model_config = ConfigDict(from_attributes=True)

class SubQuestionCreate(BaseModel):
    """Schema for creating sub-questions"""
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = Field(None, ge=1, le=100)
    numbering_style: str = Field(default="alphabetic")
    question_number: str = Field(default="a")
    parent_id: Optional[UUID] = None
    
    @field_validator("text", mode="before")
    @classmethod
    def text_to_dict(cls, v):
        if v is None:
            return v
        if isinstance(v, dict):
            return v
        if hasattr(v, "model_dump"):
            return v.model_dump(mode='json')
        return v
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# EXAM PAPER CLIENT
# ============================================================================

class ExamPaperClient:
    """
    Client for handling exam paper operations.
    
    Provides methods to create exam papers with all related entities.
    """
    
    def __init__(self, config: APIConfig, auth_client: AuthClient):
        self.config = config
        self.auth_client = auth_client
        self.client = httpx.AsyncClient(timeout=config.timeout)

    async def _get_all_pages(self, endpoint: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Helper to fetch all pages of a paginated resource"""
        all_items = []
        skip = 0
        limit = 100
        
        while True:
            response = await self.client.get(
                f"{self.config.base_url}/{endpoint}",
                headers=headers,
                params={"skip": skip, "limit": limit}
            )
            
            if response.status_code != 200:
                break
                
            data = response.json().get("data", {})
            items = data.get("items", []) if isinstance(data, dict) else data
            
            if not items:
                break
                
            all_items.extend(items)
            
            # If we got fewer items than limit, we're done
            if len(items) < limit:
                break
                
            skip += limit
            
        return all_items

    async def _find_entity_by_name(self, endpoint: str, name: str) -> Optional[Dict[str, Any]]:
        """Helper to find an entity by name from all results"""
        try:
            headers = await self.auth_client.get_headers()
            
            # Use search endpoint for supported entities
            if endpoint in ["exam-title", "exam-description", "instruction", "module", "course"]:
                try:
                   response = await self.client.get(
                        f"{self.config.base_url}/{endpoint}/search",
                        headers=headers,
                        params={"q": name, "limit": 1}
                   )
                   if response.status_code == 200:
                       data = response.json().get("data", {})
                       items = data.get("items", []) if isinstance(data, dict) else data
                       if items:
                           return items[0]
                       return None
                except Exception as e:
                    logger.warning(f"Search failed for {endpoint}, falling back to list: {e}")

            # Fallback to listing all pages (legacy or if search fails)
            items = await self._get_all_pages(endpoint, headers)
            
            for item in items:
                # Some entities might use 'title' instead of 'name' if mismatched, but schema says 'name' for all these
                if item.get("name") == name:
                    return item
            
            return None
        except Exception as e:
            logger.error(f"Error finding entity in {endpoint}: {str(e)}")
            return None    
    async def create_exam_title(self, title_data: ExamTitleCreate) -> Optional[Dict[str, Any]]:
        """Create an exam title"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/exam-title",
                headers=headers,
                json=title_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created exam title: {data['name']}")
                return data
            elif response.status_code == 409:
                logger.warning(f"Exam title '{title_data.name}' already exists, fetching existing...")
                return await self._find_entity_by_name("exam-title", title_data.name)
            else:
                logger.error(f"Failed to create exam title: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating exam title: {str(e)}")
            return None
    
    async def create_exam_description(self, description_data: ExamDescriptionCreate) -> Optional[Dict[str, Any]]:
        """Create an exam description"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/exam-description",
                headers=headers,
                json=description_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created exam description: {data['name']}")
                return data
            elif response.status_code == 409:
                logger.warning(f"Exam description '{description_data.name}' already exists, fetching existing...")
                return await self._find_entity_by_name("exam-description", description_data.name)
            else:
                logger.error(f"Failed to create exam description: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating exam description: {str(e)}")
            return None
    
    async def create_exam_instruction(self, instruction_data: ExamInstructionCreate) -> Optional[Dict[str, Any]]:
        """Create an exam instruction"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/instruction",
                headers=headers,
                json=instruction_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created exam instruction: {data['name']}")
                return data
            elif response.status_code == 409:
                logger.warning(f"Exam instruction '{instruction_data.name}' already exists, fetching existing...")
                return await self._find_entity_by_name("instruction", instruction_data.name)
            else:
                logger.error(f"Failed to create exam instruction: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating exam instruction: {str(e)}")
            return None
    
    async def create_module(self, module_data: ModuleCreate) -> Optional[Dict[str, Any]]:
        """Create a module"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/module",
                headers=headers,
                json=module_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created module: {data['name']}")
                return data
            elif response.status_code == 409:
                logger.warning(f"Module '{module_data.name}' already exists, fetching existing...")
                return await self._find_entity_by_name("module", module_data.name)
            else:
                logger.error(f"Failed to create module: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating module: {str(e)}")
            return None
    
    async def create_course(self, course_data: CourseCreate) -> Optional[Dict[str, Any]]:
        """Create a course"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/course",
                headers=headers,
                json=course_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created course: {data['name']}")
                return data
            elif response.status_code == 409:
                logger.warning(f"Course '{course_data.name}' already exists, fetching existing...")
                return await self._find_entity_by_name("course", course_data.name)
            else:
                logger.error(f"Failed to create course: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating course: {str(e)}")
            return None
    
    async def create_exam_paper(self, exam_paper_data: ExamPaperCreate) -> Optional[Dict[str, Any]]:
        """Create an exam paper"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/exampaper",
                headers=headers,
                json=exam_paper_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created exam paper: {data['id']}")
                return data
            elif response.status_code == 409:
                logger.warning("Exam paper already exists, fetching existing...")
                # Fetch all exam papers and find the match
                # Matching criteria: course_id and year_of_exam
                items = await self._get_all_pages("exampaper", headers)
                target_course_id = str(exam_paper_data.course_id)
                target_year = exam_paper_data.year_of_exam
                
                for item in items:
                    # Check course_id (might be in 'course' object or direct field)
                    # Based on typical API response structure
                    item_course_id = item.get("course_id")
                    if not item_course_id and "course" in item:
                        item_course_id = item["course"].get("id")
                    
                    if str(item_course_id) == target_course_id and item.get("year_of_exam") == target_year:
                        logger.info(f"Found existing exam paper: {item['id']}")
                        return item
                
                logger.error("Could not find the existing exam paper despite 409 error")
                return None
            else:
                logger.error(f"Failed to create exam paper: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating exam paper: {str(e)}")
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# ============================================================================
# QUESTION CLIENT
# ============================================================================

class QuestionClient:
    """
    Client for handling question operations.
    
    Provides methods to create question sets, main questions, and sub-questions.
    """
    
    def __init__(self, config: APIConfig, auth_client: AuthClient):
        self.config = config
        self.auth_client = auth_client
        self.client = httpx.AsyncClient(timeout=config.timeout)
    
    async def create_question_set(self, question_set_data: QuestionSetCreate) -> Optional[Dict[str, Any]]:
        """Create a question set"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/question-set",
                headers=headers,
                json=question_set_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created question set: {data['title']}")
                return data
            elif response.status_code == 409:
                logger.warning(f"Question set '{question_set_data.title}' already exists, fetching existing...")
                get_response = await self.client.get(
                    f"{self.config.base_url}/question-set",
                    headers=headers,
                    params={"limit": 100}
                )
                if get_response.status_code == 200:
                    items_data = get_response.json().get("data", {})
                    items = items_data.get("items", []) if isinstance(items_data, dict) else items_data
                    for item in items:
                        if item.get("title") == question_set_data.title:
                             return item
                return None
            else:
                logger.error(f"Failed to create question set: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating question set: {str(e)}")
            return None
    
    async def create_main_question(self, question_data: MainQuestionCreate) -> Optional[Dict[str, Any]]:
        """Create a main question"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/questions/main",
                headers=headers,
                json=question_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created main question: {question_data.question_number}")
                return data
            else:
                logger.error(f"Failed to create main question: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating main question: {str(e)}")
            return None
    
    async def create_sub_question(self, question_data: SubQuestionCreate) -> Optional[Dict[str, Any]]:
        """Create a sub-question"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/questions/sub",
                headers=headers,
                json=question_data.model_dump(mode='json')
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created sub-question: {question_data.question_number}")
                return data
            else:
                logger.error(f"Failed to create sub-question: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating sub-question: {str(e)}")
            return None
    
    async def add_question_set_to_exam_paper(
        self, 
        exam_paper_id: UUID, 
        question_set_id: UUID
    ) -> bool:
        """Add a question set to an exam paper"""
        try:
            headers = await self.auth_client.get_headers()
            response = await self.client.post(
                f"{self.config.base_url}/exampaper/{exam_paper_id}/question-sets/{question_set_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info(f"Added question set to exam paper")
                return True
            else:
                logger.error(f"Failed to add question set: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding question set: {str(e)}")
            return False
    
    async def create_multiple_sub_questions(
        self, 
        main_question_id: UUID, 
        sub_questions: List[SubQuestionCreate]
    ) -> Optional[List[Dict[str, Any]]]:
        """Create multiple sub-questions for a main question"""
        try:
            headers = await self.auth_client.get_headers()
            sub_questions_data = [sq.model_dump(mode='json') for sq in sub_questions]
            
            response = await self.client.post(
                f"{self.config.base_url}/questions/{main_question_id}/sub-questions/bulk",
                headers=headers,
                json=sub_questions_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()["data"]
                logger.info(f"Created {len(data)} sub-questions")
                return data
            else:
                logger.error(f"Failed to create sub-questions: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating sub-questions: {str(e)}")
            return None
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# ============================================================================
# MAIN EXAM PAPER INSERTER CLASS
# ============================================================================

class ExamPaperInserter:
    """
    Main class for inserting complete exam papers with all related entities.
    
    This class orchestrates the entire process:
    1. Authentication
    2. Institution validation/creation
    3. Prerequisite creation (titles, descriptions, courses, modules)
    4. Exam paper creation
    5. Question set and question creation
    """
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.auth_client = AuthClient(config)
        self.institution_client = InstitutionClient(config, self.auth_client)
        self.programme_client = ProgrammeClient(config, self.auth_client)
        self.exam_paper_client = ExamPaperClient(config, self.auth_client)
        self.question_client = QuestionClient(config, self.auth_client)
        self.created_entities: Dict[str, Any] = {}
    
    async def authenticate(self, email: str, password: str) -> bool:
        """
        Authenticate with the API
        
        Args:
            email: User email
            password: User password
            
        Returns:
            True if authentication successful, False otherwise
        """
        return await self.auth_client.login(email, password)
    
    async def get_or_create_institution(
        self, 
        institution_name: Optional[str] = None,
        institution_id: Optional[UUID] = None,
        create_if_missing: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get institution by ID/name or create if missing
        
        Args:
            institution_name: Name of institution to search for
            institution_id: ID of existing institution
            create_if_missing: Whether to create institution if not found
            
        Returns:
            Institution data or None
        """
        # If ID provided, validate it exists
        if institution_id:
            institution = await self.institution_client.get_institution_by_id(institution_id)
            if institution:
                self.created_entities['institution'] = institution.dict()
                return institution.dict()
            else:
                logger.error(f"Institution with ID {institution_id} not found")
                return None
        
        # If name provided, search for it
        if institution_name:
            institutions = await self.institution_client.search_institutions(
                search_term=institution_name,
                limit=10
            )
            
            # Look for exact match
            for inst in institutions:
                if inst.name.lower() == institution_name.lower():
                    self.created_entities['institution'] = inst.dict()
                    return inst.dict()
            
            # Create if not found and requested
            if create_if_missing:
                institution_data = InstitutionCreate(name=institution_name)
                created = await self.institution_client.create_institution(institution_data)
                if created:
                    self.created_entities['institution'] = created
                    return created
                else:
                    logger.error(f"Failed to create institution: {institution_name}")
                    return None
        
        logger.error("No institution name or ID provided")
        return None
    
    async def create_prerequisites(
        self,
        exam_title_data: Optional[ExamTitleCreate] = None,
        exam_description_data: Optional[ExamDescriptionCreate] = None,
        programme_data: Optional[ProgrammeCreate] = None,
        course_data: Optional[CourseCreate] = None,
        module_data_list: Optional[List[ModuleCreate]] = None,
        instruction_data_list: Optional[List[ExamInstructionCreate]] = None
    ) -> Dict[str, Any]:
        """
        Create all prerequisite entities for exam paper
        
        Args:
            exam_title_data: Exam title creation data
            exam_description_data: Exam description creation data
            course_data: Course creation data
            module_data_list: List of module creation data
            instruction_data_list: List of instruction creation data
            
        Returns:
            Dictionary with IDs of created entities
        """
        prerequisites_ids = {}
        
        # Create exam title
        if exam_title_data:
            title = await self.exam_paper_client.create_exam_title(exam_title_data)
            if title:
                prerequisites_ids['title_id'] = title['id']
                self.created_entities['title'] = title
            else:
                raise Exception("Failed to create exam title")
        
        # Create exam description
        if exam_description_data:
            description = await self.exam_paper_client.create_exam_description(exam_description_data)
            if description:
                prerequisites_ids['description_id'] = description['id']
                self.created_entities['description'] = description
            else:
                raise Exception("Failed to create exam description")
        
        # Create programme
        programme_id = None
        if programme_data:
             programme = await self.programme_client.create_programme(programme_data)
             if programme:
                 programme_id = programme.id
                 self.created_entities['programme'] = programme.model_dump(mode='json')
             else:
                 # Try to continue if course doesn't strictly need it here (but schema says it does)
                 logger.warning("Failed to create/retrieve programme, course creation might fail")

        # Create course
        if course_data:
            if programme_id:
                course_data.programme_id = programme_id
            
            course = await self.exam_paper_client.create_course(course_data)
            if course:
                prerequisites_ids['course_id'] = course['id']
                self.created_entities['course'] = course
            else:
                raise Exception("Failed to create course")
        
        # Create modules
        if module_data_list:
            module_ids = []
            for module_data in module_data_list:
                module = await self.exam_paper_client.create_module(module_data)
                if module:
                    module_ids.append(module['id'])
                    self.created_entities[f'module_{module["id"]}'] = module
                else:
                    raise Exception(f"Failed to create module: {module_data.name}")
            prerequisites_ids['module_ids'] = module_ids
        
        # Create instructions
        if instruction_data_list:
            instruction_ids = []
            for instruction_data in instruction_data_list:
                instruction = await self.exam_paper_client.create_exam_instruction(instruction_data)
                if instruction:
                    instruction_ids.append(instruction['id'])
                    self.created_entities[f'instruction_{instruction["id"]}'] = instruction
                else:
                    raise Exception(f"Failed to create instruction: {instruction_data.name}")
            prerequisites_ids['instruction_ids'] = instruction_ids
        
        return prerequisites_ids
    
    async def create_exam_paper_with_questions(
        self,
        exam_paper_data: ExamPaperCreate,
        question_set_data: Optional[QuestionSetCreate] = None,
        main_questions_data: Optional[List[MainQuestionCreate]] = None,
        main_questions_sub_qs: Optional[Dict[int, List[SubQuestionCreate]]] = None
    ) -> Dict[str, Any]:
        """
        Create complete exam paper with questions
        
        Args:
            exam_paper_data: Exam paper creation data
            question_set_data: Question set creation data
            main_questions_data: List of main question creation data
            sub_questions_data: List of sub-question creation data
            
        Returns:
            Dictionary with created exam paper and questions data
        """
        result = {
            'exam_paper': None,
            'question_sets': [],
            'main_questions': [],
            'sub_questions': [],
            'success': False,
            'errors': []
        }
        
        try:
            # Create exam paper
            exam_paper = await self.exam_paper_client.create_exam_paper(exam_paper_data)
            if not exam_paper:
                result['errors'].append("Failed to create exam paper")
                return result
            
            result['exam_paper'] = exam_paper
            self.created_entities['exam_paper'] = exam_paper
            exam_paper_id = exam_paper['id']
            
            # Create question set if provided
            question_set_id = None
            if question_set_data:
                question_set = await self.question_client.create_question_set(question_set_data)
                if question_set:
                    question_set_id = question_set['id']
                    result['question_sets'].append(question_set)
                    self.created_entities['question_set'] = question_set
                    
                    # Add question set to exam paper
                    added = await self.question_client.add_question_set_to_exam_paper(
                        exam_paper_id, question_set_id
                    )
                    if not added:
                        result['errors'].append("Failed to add question set to exam paper")
                        return result
                else:
                    result['errors'].append("Failed to create question set")
                    return result
            
            # Create main questions
            created_main_questions = []
            if main_questions_data:
                for main_q_data in main_questions_data:
                    # Set exam paper ID and question set ID
                    main_q_data.exam_paper_id = exam_paper_id
                    if question_set_id:
                        main_q_data.question_set_id = question_set_id
                    
                    main_question = await self.question_client.create_main_question(main_q_data)
                    if main_question:
                        result['main_questions'].append(main_question)
                        created_main_questions.append(main_question)
                        self.created_entities[f'main_question_{main_question["id"]}'] = main_question
                    else:
                        result['errors'].append(f"Failed to create main question: {main_q_data.question_number}")
            
            # Create sub-questions
            if main_questions_sub_qs and created_main_questions:
                # Map sub-questions to their parent main questions
                sub_q_index = 0
                for i, main_question in enumerate(created_main_questions):
                    parent_sub_questions = []
                    
                    # Get sub-questions for this main question from the mapping
                    if i in main_questions_sub_qs:
                        parent_sub_questions = main_questions_sub_qs[i]
                        # Set the parent ID for each sub-question
                        for sub_q in parent_sub_questions:
                            sub_q.parent_id = main_question['id']
                    
                    # Create sub-questions for this main question
                    if parent_sub_questions:
                        created = await self.question_client.create_multiple_sub_questions(
                            main_question['id'], parent_sub_questions
                        )
                        if created:
                            result['sub_questions'].extend(created)
                            for sq in created:
                                self.created_entities[f'sub_question_{sq["id"]}'] = sq
                        else:
                            result['errors'].append(f"Failed to create sub-questions for parent: {main_question['id']}")
            
            result['success'] = len(result['errors']) == 0
            return result
            
        except Exception as e:
            result['errors'].append(f"Unexpected error: {str(e)}")
            logger.error(f"Error creating exam paper with questions: {str(e)}")
            return result
    
    async def close(self):
        """Close all clients"""
        await self.auth_client.close()
        await self.institution_client.close()
        await self.exam_paper_client.close()
        await self.programme_client.close()
        await self.question_client.close()


# ============================================================================
# HELPER FUNCTIONS AND EXAMPLES
# ============================================================================

def create_sample_exam_paper() -> Dict[str, Any]:
    """
    Create a sample exam paper data structure
    
    Returns:
        Dictionary with sample exam paper data
    """
    return {
        "exam_paper": {
            "year_of_exam": "2024/2025",
            "exam_duration": 180,
            "exam_date": date(2024, 12, 15),
            "tags": ["sample", "mathematics", "calculus"]
        },
        "prerequisites": {
            "exam_title": {
                "name": "UNIVERSITY EXAMINATIONS",
                "description": "Official university examination"
            },
            "exam_description": {
                "name": "SECOND YEAR MATHEMATICS EXAMINATION",
                "description": "Comprehensive mathematics examination"
            },
            "course": {
                "name": "Advanced Mathematics",
                "course_acronym": "MATH301",
                "description": "Advanced calculus and linear algebra"
            },
            "institution": {
                "name": "University of Technology",
                "description": "Leading technology university",
                "category": "University",
                "institution_type": "Public",
                "location": "Nairobi"
            },
            "programme": {
                "name": "Bachelors/Undergraduate",
                "description": "Bachelor of Science in Information Technology"
            },
            "modules": [
                {
                    "name": "Calculus II",
                    "unit_code": "CALC201",
                    "description": "Advanced calculus concepts"
                },
                {
                    "name": "Linear Algebra",
                    "unit_code": "LINALG201",
                    "description": "Matrix operations and vector spaces"
                }
            ],
            "instructions": [
                {"name": "Answer ALL questions"},
                {"name": "Show all working clearly"},
                {"name": "Calculators permitted"}
            ]
        },
       
        "questions": {
         "question_sets": [
            {
            "title": "Question One",
            "main_questions": [
                {
                    "text": {
                        "time": 1700000000000,
                        "blocks": [
                            {
                                "id": "q1a_stem",
                                "type": "paragraph",
                                "data": {
                                    "text": "Define Kirchhoff's current law and Kirchhoff's voltage law."
                                }
                            }
                        ]
                    },
                    "marks": 4,
                    "numbering_style": "alphabetic",
                    "question_number": "a",
                    "sub_questions": []
                },
                {
                    "text": {
                        "time": 1700000000001,
                        "blocks": [
                            {
                                "id": "q1b_stem",
                                "type": "paragraph",
                                "data": {
                                    "text": "By drawing the two circuits which depict Kirchhoff's laws, show how effective resistance of each circuit may be derived."
                                }
                            }
                        ]
                    },
                    "marks": 6,
                    "numbering_style": "alphabetic",
                    "question_number": "b",
                    "sub_questions": []
                },
                {
                    "text": {
                        "time": 1700000000002,
                        "blocks": [
                            {
                                "id": "q1c_stem",
                                "type": "paragraph",
                                "data": {
                                    "text": "Determine the standard values of the following resistors; giving minimum and maximum values of each resistor."
                                }
                            }
                        ]
                    },
                    "marks": 4,
                    "numbering_style": "alphabetic",
                    "question_number": "c",
                    "sub_questions": [
                        {
                            "text": {
                                "time": 1700000000003,
                                "blocks": [
                                    {
                                        "id": "q1c_i",
                                        "type": "paragraph",
                                        "data": {
                                            "text": "Brown-Green -Brown-Silver"
                                        }
                                    }
                                ]
                            },
                            "marks": 2,
                            "numbering_style": "roman",
                            "question_number": "i"
                        },
                        {
                            "text": {
                                "time": 1700000000004,
                                "blocks": [
                                    {
                                        "id": "q1c_ii",
                                        "type": "paragraph",
                                        "data": {
                                            "text": "Orange-Blue-Silver-Gold"
                                        }
                                    }
                                ]
                            },
                            "marks": 2,
                            "numbering_style": "roman",
                            "question_number": "ii"
                        }
                    ]
                },
                {
                    "text": {
                        "time": 1700000000005,
                        "blocks": [
                            {
                                "id": "q1d_stem",
                                "type": "paragraph",
                                "data": {
                                    "text": "Give the correct band-colours of the following standard resistors."
                                }
                            }
                        ]
                    },
                    "marks": 4,
                    "numbering_style": "alphabetic",
                    "question_number": "d",
                    "sub_questions": [
                        {
                            "text": {
                                "time": 1700000000006,
                                "blocks": [
                                    {
                                        "id": "q1d_i",
                                        "type": "paragraph",
                                        "data": {
                                            "text": "3.6K \u00b1 5%"
                                        }
                                    }
                                ]
                            },
                            "marks": 2,
                            "numbering_style": "roman",
                            "question_number": "i"
                        },
                        {
                            "text": {
                                "time": 1700000000007,
                                "blocks": [
                                    {
                                        "id": "q1d_ii",
                                        "type": "paragraph",
                                        "data": {
                                            "text": "180R \u00b1 10%"
                                        }
                                    }
                                ]
                            },
                            "marks": 2,
                            "numbering_style": "roman",
                            "question_number": "ii"
                        }
                    ]
                },
                {
                    "text": {
                        "time": 1700000000008,
                        "blocks": [
                            {
                                "id": "q1e_stem",
                                "type": "paragraph",
                                "data": {
                                    "text": "Name the factors which affect the resistance of a conductor and show clearly the relationship between the resistance and each of those factors stated in part (i)"
                                }
                            }
                        ]
                    },
                    "marks": 6,
                    "numbering_style": "alphabetic",
                    "question_number": "e",
                    "sub_questions": [
                        {
                            "text": {
                                "time": 1700000000009,
                                "blocks": [
                                    {
                                        "id": "q1e_i",
                                        "type": "paragraph",
                                        "data": {
                                            "text": "Name the factors which affect the resistance of a conductor."
                                        }
                                    }
                                ]
                            },
                            "marks": None,
                            "numbering_style": "roman",
                            "question_number": "i"
                        },
                        {
                            "text": {
                                "time": 1700000000010,
                                "blocks": [
                                    {
                                        "id": "q1e_ii",
                                        "type": "paragraph",
                                        "data": {
                                            "text": "Show clearly the relationship between the resistance and each of those factors stated in part (i)"
                                        }
                                    }
                                ]
                            },
                            "marks": None,
                            "numbering_style": "roman",
                            "question_number": "ii"
                        }
                    ]
                },
                {
                    "text": {
                        "time": 1700000000011,
                        "blocks": [
                            {
                                "id": "q1f_stem",
                                "type": "paragraph",
                                "data": {
                                    "text": "Two resistors R_1, R_2 are connected in parallel across the dc source of voltage, E. If an ammeter A is connected to measure the total current and voltmeter V is connected to measure the p.d. across the resistor R_2, draw a neat labeled circuit diagram of the circuit."
                                }
                            }
                        ]
                    },
                    "marks": 6,
                    "numbering_style": "alphabetic",
                    "question_number": "f",
                    "sub_questions": []
                }
            ]
            }
            ]
       },
       
    }


async def main():
    """
    Main function demonstrating the exam paper inserter
    """
    print("🚀 Exam Paper Inserter - Complete API Client")
    print("=" * 60)
    
    # Configuration
    config = APIConfig(
        base_url="http://fastapi.localhost/api/v1",
        timeout=30
    )
    
    # Initialize inserter
    inserter = ExamPaperInserter(config)
    
    try:
        # Step 1: Authenticate
        print("\n📝 Step 1: Authentication")
        print("-" * 30)
        
        # Get credentials (in real use, get from secure source)
        # email = input("Enter email: ")
        # password = input("Enter password: ")
        email = "david@techgrids.com"
        password = "##Jipanoran2020"
        
        auth_success = await inserter.authenticate(email, password)
        if not auth_success:
            print("❌ Authentication failed!")
            return
        
        print("✅ Authentication successful!")
        
        # Step 2: Get or create institution
        print("\n🏛️ Step 2: Institution Handling")
        print("-" * 30)
        
        # Option 1: Use existing institution by ID
        # institution = await inserter.get_or_create_institution(
        #     institution_id=UUID("your-institution-id-here")
        # )
        
        # Option 2: Search and create institution
        institution = await inserter.get_or_create_institution(
            institution_name="University of Technology",
            create_if_missing=True
        )
        
        if not institution:
            print("❌ Failed to get or create institution!")
            return
        
        print(f"✅ Institution: {institution['name']}")
        
        # Step 3: Create prerequisites
        print("\n📋 Step 3: Creating Prerequisites")
        print("-" * 30)
        
        sample_data = create_sample_exam_paper()
        prerequisites = sample_data["prerequisites"]
        
        # Convert to schema objects
        exam_title_data = ExamTitleCreate(**prerequisites["exam_title"])
        exam_description_data = ExamDescriptionCreate(**prerequisites["exam_description"])
        
        # We need a dummy UUID for initial schema validation of CourseCreate, 
        # but it will be overwritten in create_prerequisites with actual ID
        course_dict = prerequisites["course"].copy()
        course_dict["programme_id"] = uuid4() 
        course_data = CourseCreate(**course_dict)
        
        programme_data = ProgrammeCreate(**prerequisites["programme"])
        
        module_data_list = [ModuleCreate(**m) for m in prerequisites["modules"]]
        instruction_data_list = [ExamInstructionCreate(**i) for i in prerequisites["instructions"]]
        
        prerequisites_ids = await inserter.create_prerequisites(
            exam_title_data=exam_title_data,
            exam_description_data=exam_description_data,
            programme_data=programme_data,
            course_data=course_data,
            module_data_list=module_data_list,
            instruction_data_list=instruction_data_list
        )
        
        print(f"✅ Created {len(prerequisites_ids)} prerequisite entities")
        
        # Step 4: Create exam paper
        print("\n📄 Step 4: Creating Exam Paper")
        print("-" * 30)
        
        exam_paper_data = ExamPaperCreate(
            **sample_data["exam_paper"],
            institution_id=institution["id"],
            **prerequisites_ids
        )
        
        # Extract question set data from the new format
        question_set_info = sample_data["questions"]["question_sets"][0]
        question_set_data = QuestionSetCreate(title=question_set_info["title"])
        
        # Prepare main questions and track their sub-questions
        main_questions_data = []
        main_questions_sub_qs = {}  # Track sub-questions for each main question
        
        for i, main_q in enumerate(question_set_info["main_questions"]):
            # Create main question without sub-questions initially
            main_q_data = {
                "text": main_q["text"],
                "marks": main_q["marks"],
                "numbering_style": main_q["numbering_style"],
                "question_number": main_q["question_number"],
                "exam_paper_id": None,  # Will be set in create_exam_paper_with_questions
                "question_set_id": None  # Will be set in create_exam_paper_with_questions
            }
            main_question_create = MainQuestionCreate(**main_q_data)
            main_questions_data.append(main_question_create)
            
            # Track sub-questions for this main question
            sub_questions_for_main = []
            for j, sub_q in enumerate(main_q.get("sub_questions", [])):
                sub_q_data = {
                    "text": sub_q["text"],
                    "marks": sub_q["marks"],
                    "numbering_style": sub_q["numbering_style"],
                    "question_number": sub_q["question_number"],
                    "parent_id": None  # Will be set after main question is created
                }
                sub_questions_for_main.append(SubQuestionCreate(**sub_q_data))
            
            if sub_questions_for_main:
                main_questions_sub_qs[i] = sub_questions_for_main
        
        result = await inserter.create_exam_paper_with_questions(
            exam_paper_data=exam_paper_data,
            question_set_data=question_set_data,
            main_questions_data=main_questions_data,
            main_questions_sub_qs=main_questions_sub_qs
        )
        
        if result['success']:
            print("✅ Exam paper created successfully!")
            print(f"   Exam Paper ID: {result['exam_paper']['id']}")
            print(f"   Question Sets: {len(result['question_sets'])}")
            print(f"   Main Questions: {len(result['main_questions'])}")
            print(f"   Sub-Questions: {len(result['sub_questions'])}")
        else:
            print("❌ Failed to create exam paper!")
            for error in result['errors']:
                print(f"   Error: {error}")
        
        # Step 5: Summary
        print("\n📊 Summary")
        print("-" * 30)
        print(f"Total entities created: {len(inserter.created_entities)}")
        for entity_type, entity_data in inserter.created_entities.items():
            if isinstance(entity_data, dict) and 'id' in entity_data:
                print(f"  {entity_type}: {entity_data['id']}")
        
    except Exception as e:
        logger.error(f"Main execution error: {str(e)}")
        print(f"❌ Error: {str(e)}")
    
    finally:
        # Clean up
        await inserter.close()
        print("\n👋 Cleanup completed")


if __name__ == "__main__":
    """
    Run the exam paper inserter demo
    """
    print("🎓 Exam Paper Inserter - Complete Implementation")
    print("=" * 60)
    print("This script provides a complete client for inserting exam papers")
    print("with all necessary prerequisites and questions.")
    print("\nFeatures:")
    print("- User authentication with bearer token management")
    print("- Institution retrieval and creation")
    print("- Complete exam paper creation workflow")
    print("- Question and sub-question insertion")
    print("- Editor.js compatible rich text support")
    print("- Comprehensive error handling")
    print("\nStarting demo...")
    
    # Run the main function
    asyncio.run(main())
    
    print("\n" + "=" * 60)
    print("✅ Demo completed!")
    print("\n💡 Usage Tips:")
    print("1. Modify the APIConfig to match your server URL")
    print("2. Replace sample data with your actual exam paper data")
    print("3. Use proper authentication credentials")
    print("4. Handle errors appropriately in your application")
    print("5. Consider batch processing for multiple exam papers")
