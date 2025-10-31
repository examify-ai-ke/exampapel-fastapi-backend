"""
Complete Exam Paper Creation Flow
================================

This file demonstrates the complete workflow for adding an exam paper to the FastAPI application.
It includes all necessary schemas, validation, and step-by-step functions.

Flow Steps:
1. Create/Validate Prerequisites (Institution, Course, Title, Description, Instructions, Modules)
2. Create Exam Paper
3. Add Question Sets (optional)
4. Add Questions to Exam Paper (optional)

Author: Amazon Q Developer
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, validator
from sqlmodel import SQLModel
import asyncio

# ============================================================================
# SCHEMAS FOR EXAM PAPER CREATION FLOW
# ============================================================================

class InstitutionCreateSchema(BaseModel):
    """Schema for creating an institution"""
    name: str = Field(..., min_length=2, max_length=200)
    slug: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class CourseCreateSchema(BaseModel):
    """Schema for creating a course"""
    name: str = Field(..., min_length=2, max_length=200)
    course_acronym: Optional[str] = Field(None, max_length=10)
    slug: Optional[str] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class ExamTitleCreateSchema(BaseModel):
    """Schema for creating exam title"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(
        default="The title or name typically refers to the overarching categorization or identity of the exam.",
        max_length=500
    )
    
    class Config:
        from_attributes = True

class ExamDescriptionCreateSchema(BaseModel):
    """Schema for creating exam description"""
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(
        default="The description usually provides additional information about the exam, such as its level, degree program, or specific course details.",
        max_length=500
    )
    
    class Config:
        from_attributes = True

class ExamInstructionCreateSchema(BaseModel):
    """Schema for creating exam instructions"""
    name: str = Field(..., min_length=2, max_length=500)
    
    class Config:
        from_attributes = True

class ModuleCreateSchema(BaseModel):
    """Schema for creating a module"""
    name: str = Field(..., min_length=2, max_length=200)
    unit_code: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = None
    
    class Config:
        from_attributes = True

class ExamPaperCreateSchema(BaseModel):
    """Complete schema for creating an exam paper"""
    # Basic exam paper fields
    year_of_exam: str = Field(default="2024/2025", description="Academic year")
    exam_duration: int = Field(default=120, ge=30, le=480, description="Duration in minutes")
    exam_date: Optional[date] = Field(None, description="Date of the exam")
    tags: Optional[List[str]] = Field(default=[], description="Tags for categorization")
    
    # Required relationships (IDs)
    title_id: UUID = Field(..., description="Exam title ID")
    description_id: UUID = Field(..., description="Exam description ID")
    course_id: UUID = Field(..., description="Course ID")
    institution_id: UUID = Field(..., description="Institution ID")
    
    # Many-to-many relationships
    instruction_ids: List[UUID] = Field(default=[], description="List of instruction IDs")
    module_ids: List[UUID] = Field(default=[], description="List of module IDs")
    
    @validator('year_of_exam')
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
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError('Year parts must be valid integers')
            raise e
        return v
    
    class Config:
        from_attributes = True

class QuestionSetCreateSchema(BaseModel):
    """Schema for creating a question set"""
    title: str = Field(..., min_length=2, max_length=200)
    # description: Optional[str] = None
    # instructions: Optional[str] = None
    
    class Config:
        from_attributes = True

# ============================================================================
# EDITOR.JS BLOCK SCHEMAS
# ============================================================================

class ParagraphBlockData(BaseModel):
    """Data for paragraph block"""
    text: str

class HeaderBlockData(BaseModel):
    """Data for header block"""
    text: str
    level: int = Field(ge=1, le=6, default=1)

class ListBlockData(BaseModel):
    """Data for list block"""
    style: str = Field(default="unordered")  # "ordered" or "unordered"
    items: List[str]

class ImageFileData(BaseModel):
    """File data for image block"""
    url: str
    name: Optional[str] = None
    size: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None

class ImageBlockData(BaseModel):
    """Data for image block"""
    file: ImageFileData
    caption: Optional[str] = None
    stretched: bool = False
    withBorder: bool = False
    withBackground: bool = False

class QuoteBlockData(BaseModel):
    """Data for quote block"""
    text: str
    caption: Optional[str] = None
    alignment: str = Field(default="left")  # "left" or "center"

class CodeBlockData(BaseModel):
    """Data for code block"""
    code: str
    language: Optional[str] = None

class DelimiterBlockData(BaseModel):
    """Data for delimiter block (usually empty)"""
    pass

class TableBlockData(BaseModel):
    """Data for table block"""
    withHeadings: bool = False
    content: List[List[str]]  # 2D array of cell contents

class ChecklistItem(BaseModel):
    """Individual checklist item"""
    text: str
    checked: bool = False

class ChecklistBlockData(BaseModel):
    """Data for checklist block"""
    items: List[ChecklistItem]

class EmbedBlockData(BaseModel):
    """Data for embed block (videos, etc.)"""
    service: str  # "youtube", "vimeo", etc.
    source: str   # URL
    embed: str    # Embed code
    width: Optional[int] = None
    height: Optional[int] = None
    caption: Optional[str] = None

class LinkToolBlockData(BaseModel):
    """Data for link tool block"""
    link: str
    meta: Optional[Dict[str, Any]] = None

class WarningBlockData(BaseModel):
    """Data for warning block"""
    title: str
    message: str

class RawBlockData(BaseModel):
    """Data for raw HTML block"""
    html: str

class MathBlockData(BaseModel):
    """Data for mathematical formula block"""
    formula: str
    display: str = Field(default="block")  # "block" or "inline"

class EditorJSBlock(BaseModel):
    """Generic Editor.js block schema"""
    id: str
    type: str
    data: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "id": "pp0wt2psxQ",
                    "type": "paragraph",
                    "data": {"text": "This is a sample paragraph."}
                },
                {
                    "id": "8z7KYTOioJ",
                    "type": "header",
                    "data": {"text": "Sample Header", "level": 2}
                },
                {
                    "id": "xyz123abc",
                    "type": "image",
                    "data": {
                        "file": {
                            "url": "https://example.com/image.png",
                            "name": "sample.png",
                            "size": 104763,
                            "width": 265,
                            "height": 262,
                            "format": "PNG"
                        },
                        "caption": "Sample image",
                        "stretched": False,
                        "withBorder": False,
                        "withBackground": False
                    }
                }
            ]
        }

class QuestionTextSchema(BaseModel):
    """Schema for question text using Editor.js format"""
    time: int
    blocks: List[EditorJSBlock]
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "time": 1761416444650,
                "blocks": [
                    {
                        "id": "8z7KYTOioJ",
                        "data": {
                            "file": {
                                "url": "https://exampapel-images-bucket2025.s3.amazonaws.com/019a1c1c-a20e-77fc-b3c8-dfd5587162b0favicon-exam.png",
                                "name": "favicon-exam.png",
                                "size": 104763,
                                "width": 265,
                                "format": "PNG",
                                "height": 262,
                            },
                            "caption": "logo-sample",
                            "stretched": False,
                            "withBorder": False,
                            "withBackground": False,
                        },
                        "type": "image",
                    },
                    {
                        "id": "pp0wt2psxQ",
                        "data": {"text": "What is the derivative of x^2 + 3x + 2?"},
                        "type": "paragraph",
                    },
                    {
                        "id": "header123",
                        "data": {"text": "Part A: Multiple Choice", "level": 2},
                        "type": "header"
                    },
                    {
                        "id": "list456",
                        "data": {
                            "style": "ordered",
                            "items": ["Option A: 2x + 3", "Option B: x^2 + 3", "Option C: 2x + 2"]
                        },
                        "type": "list"
                    }
                ],
            },
        }

class MainQuestionCreateSchema(BaseModel):
    """Schema for creating main questions"""
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = Field(None, ge=1, le=100)
    numbering_style: str = Field(default="numeric")
    question_number: str = Field(..., min_length=1)
    question_set_id: UUID = Field(..., description="Question set this question belongs to")
    exam_paper_id: UUID = Field(..., description="Exam paper this question belongs to")
    
    class Config:
        from_attributes = True

class SubQuestionCreateSchema(BaseModel):
    """Schema for creating sub-questions (children of main questions)"""
    text: Optional[QuestionTextSchema] = None
    marks: Optional[int] = Field(None, ge=1, le=100)
    numbering_style: str = Field(default="alphabetic")
    question_number: str = Field(default="a")
    parent_id: UUID = Field(..., description="Parent main question ID")
    
    class Config:
        from_attributes = True

# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ExamPaperResponseSchema(BaseModel):
    """Response schema for exam paper"""
    id: UUID
    year_of_exam: str
    exam_duration: int
    exam_date: Optional[date]
    tags: Optional[List[str]]
    slug: Optional[str]
    identifying_name: Optional[str]
    created_at: datetime
    
    # Relationships
    title: Optional[Dict[str, Any]] = None
    description: Optional[Dict[str, Any]] = None
    course: Optional[Dict[str, Any]] = None
    institution: Optional[Dict[str, Any]] = None
    instructions: Optional[List[Dict[str, Any]]] = []
    modules: Optional[List[Dict[str, Any]]] = []
    question_sets: Optional[List[Dict[str, Any]]] = []
    
    class Config:
        from_attributes = True

class FlowStepResult(BaseModel):
    """Result of each step in the flow"""
    step_name: str
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

class CompleteFlowResult(BaseModel):
    """Complete flow execution result"""
    success: bool
    exam_paper_id: Optional[UUID] = None
    steps: List[FlowStepResult]
    total_steps: int
    completed_steps: int

# ============================================================================
# EXAM PAPER CREATION FLOW CLASS
# ============================================================================

class ExamPaperCreationFlow:
    """
    Complete workflow for creating an exam paper with all prerequisites.
    
    This class handles the entire process of creating an exam paper including:
    1. Validating and creating prerequisites
    2. Creating the exam paper
    3. Adding question sets and questions
    4. Error handling and rollback
    """
    
    def __init__(self, db_session=None, current_user_id: UUID = None):
        self.db_session = db_session
        self.current_user_id = current_user_id or uuid4()
        self.results: List[FlowStepResult] = []
        self.created_entities: Dict[str, UUID] = {}
        
    async def execute_complete_flow(
        self,
        exam_paper_data: ExamPaperCreateSchema,
        prerequisites: Dict[str, Any] = None,
        question_sets_data: List[QuestionSetCreateSchema] = None,
        main_questions_data: List[MainQuestionCreateSchema] = None,
        sub_questions_data: List[SubQuestionCreateSchema] = None
    ) -> CompleteFlowResult:
        """
        Execute the complete exam paper creation flow.
        
        Args:
            exam_paper_data: The exam paper creation schema
            prerequisites: Optional dict containing prerequisite data
            question_sets_data: Optional list of question sets to create
            questions_data: Optional list of questions to create
            
        Returns:
            CompleteFlowResult with success status and details
        """
        try:
            # Step 1: Validate Prerequisites
            await self._step_validate_prerequisites(exam_paper_data, prerequisites)
            
            # Step 2: Create/Validate Institution
            await self._step_handle_institution(exam_paper_data, prerequisites)
            
            # Step 3: Create/Validate Course
            await self._step_handle_course(exam_paper_data, prerequisites)
            
            # Step 4: Create/Validate Exam Title
            await self._step_handle_exam_title(exam_paper_data, prerequisites)
            
            # Step 5: Create/Validate Exam Description
            await self._step_handle_exam_description(exam_paper_data, prerequisites)
            
            # Step 6: Create/Validate Instructions
            await self._step_handle_instructions(exam_paper_data, prerequisites)
            
            # Step 7: Create/Validate Modules
            await self._step_handle_modules(exam_paper_data, prerequisites)
            
            # Step 8: Create Exam Paper
            exam_paper_id = await self._step_create_exam_paper(exam_paper_data)
            
            # Step 9: Add Question Sets (if provided)
            if question_sets_data:
                await self._step_add_question_sets(exam_paper_id, question_sets_data)
            
            # Step 10: Add Questions (if provided)
            if main_questions_data or sub_questions_data:
                await self._step_add_questions(exam_paper_id, main_questions_data, sub_questions_data)
            
            return CompleteFlowResult(
                success=True,
                exam_paper_id=exam_paper_id,
                steps=self.results,
                total_steps=len(self.results),
                completed_steps=len([r for r in self.results if r.success])
            )
            
        except Exception as e:
            # Add error step
            self.results.append(FlowStepResult(
                step_name="Flow Execution",
                success=False,
                message=f"Flow failed: {str(e)}",
                errors=[str(e)]
            ))
            
            # Attempt rollback
            await self._rollback_created_entities()
            
            return CompleteFlowResult(
                success=False,
                steps=self.results,
                total_steps=len(self.results),
                completed_steps=len([r for r in self.results if r.success])
            )
    
    async def _step_validate_prerequisites(
        self, 
        exam_paper_data: ExamPaperCreateSchema, 
        prerequisites: Dict[str, Any] = None
    ):
        """Step 1: Validate all prerequisites and data"""
        try:
            errors = []
            
            # Validate exam paper data
            if not exam_paper_data.title_id and not (prerequisites and prerequisites.get('title')):
                errors.append("Title ID or title data is required")
            
            if not exam_paper_data.description_id and not (prerequisites and prerequisites.get('description')):
                errors.append("Description ID or description data is required")
            
            if not exam_paper_data.course_id and not (prerequisites and prerequisites.get('course')):
                errors.append("Course ID or course data is required")
            
            if not exam_paper_data.institution_id and not (prerequisites and prerequisites.get('institution')):
                errors.append("Institution ID or institution data is required")
            
            # Validate date is not in the future (if provided)
            if exam_paper_data.exam_date and exam_paper_data.exam_date > date.today():
                # This might be acceptable, so just a warning
                pass
            
            if errors:
                raise ValueError(f"Validation errors: {', '.join(errors)}")
            
            self.results.append(FlowStepResult(
                step_name="Validate Prerequisites",
                success=True,
                message="All prerequisites validated successfully",
                data={"validated_fields": ["title", "description", "course", "institution"]}
            ))
            
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Validate Prerequisites",
                success=False,
                message=f"Validation failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_handle_institution(
        self, 
        exam_paper_data: ExamPaperCreateSchema, 
        prerequisites: Dict[str, Any] = None
    ):
        """Step 2: Handle institution creation or validation"""
        try:
            if exam_paper_data.institution_id:
                # Validate existing institution
                # In real implementation: institution = await crud.institution.get(id=exam_paper_data.institution_id)
                # if not institution: raise ValueError("Institution not found")
                
                self.results.append(FlowStepResult(
                    step_name="Handle Institution",
                    success=True,
                    message=f"Using existing institution: {exam_paper_data.institution_id}",
                    data={"institution_id": str(exam_paper_data.institution_id), "action": "validated"}
                ))
            else:
                # Create new institution
                institution_data = prerequisites.get('institution', {})
                institution_schema = InstitutionCreateSchema(**institution_data)
                
                # In real implementation:
                # institution = await crud.institution.create(obj_in=institution_schema, created_by_id=self.current_user_id)
                # exam_paper_data.institution_id = institution.id
                
                # Simulate creation
                new_institution_id = uuid4()
                exam_paper_data.institution_id = new_institution_id
                self.created_entities['institution'] = new_institution_id
                
                self.results.append(FlowStepResult(
                    step_name="Handle Institution",
                    success=True,
                    message=f"Created new institution: {institution_schema.name}",
                    data={"institution_id": str(new_institution_id), "action": "created", "name": institution_schema.name}
                ))
                
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Handle Institution",
                success=False,
                message=f"Institution handling failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_handle_course(
        self, 
        exam_paper_data: ExamPaperCreateSchema, 
        prerequisites: Dict[str, Any] = None
    ):
        """Step 3: Handle course creation or validation"""
        try:
            if exam_paper_data.course_id:
                # Validate existing course
                self.results.append(FlowStepResult(
                    step_name="Handle Course",
                    success=True,
                    message=f"Using existing course: {exam_paper_data.course_id}",
                    data={"course_id": str(exam_paper_data.course_id), "action": "validated"}
                ))
            else:
                # Create new course
                course_data = prerequisites.get('course', {})
                course_schema = CourseCreateSchema(**course_data)
                
                # Simulate creation
                new_course_id = uuid4()
                exam_paper_data.course_id = new_course_id
                self.created_entities['course'] = new_course_id
                
                self.results.append(FlowStepResult(
                    step_name="Handle Course",
                    success=True,
                    message=f"Created new course: {course_schema.name}",
                    data={"course_id": str(new_course_id), "action": "created", "name": course_schema.name}
                ))
                
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Handle Course",
                success=False,
                message=f"Course handling failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_handle_exam_title(
        self, 
        exam_paper_data: ExamPaperCreateSchema, 
        prerequisites: Dict[str, Any] = None
    ):
        """Step 4: Handle exam title creation or validation"""
        try:
            if exam_paper_data.title_id:
                # Validate existing title
                self.results.append(FlowStepResult(
                    step_name="Handle Exam Title",
                    success=True,
                    message=f"Using existing exam title: {exam_paper_data.title_id}",
                    data={"title_id": str(exam_paper_data.title_id), "action": "validated"}
                ))
            else:
                # Create new title
                title_data = prerequisites.get('title', {})
                title_schema = ExamTitleCreateSchema(**title_data)
                
                # Simulate creation
                new_title_id = uuid4()
                exam_paper_data.title_id = new_title_id
                self.created_entities['title'] = new_title_id
                
                self.results.append(FlowStepResult(
                    step_name="Handle Exam Title",
                    success=True,
                    message=f"Created new exam title: {title_schema.name}",
                    data={"title_id": str(new_title_id), "action": "created", "name": title_schema.name}
                ))
                
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Handle Exam Title",
                success=False,
                message=f"Exam title handling failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_handle_exam_description(
        self, 
        exam_paper_data: ExamPaperCreateSchema, 
        prerequisites: Dict[str, Any] = None
    ):
        """Step 5: Handle exam description creation or validation"""
        try:
            if exam_paper_data.description_id:
                # Validate existing description
                self.results.append(FlowStepResult(
                    step_name="Handle Exam Description",
                    success=True,
                    message=f"Using existing exam description: {exam_paper_data.description_id}",
                    data={"description_id": str(exam_paper_data.description_id), "action": "validated"}
                ))
            else:
                # Create new description
                description_data = prerequisites.get('description', {})
                description_schema = ExamDescriptionCreateSchema(**description_data)
                
                # Simulate creation
                new_description_id = uuid4()
                exam_paper_data.description_id = new_description_id
                self.created_entities['description'] = new_description_id
                
                self.results.append(FlowStepResult(
                    step_name="Handle Exam Description",
                    success=True,
                    message=f"Created new exam description: {description_schema.name}",
                    data={"description_id": str(new_description_id), "action": "created", "name": description_schema.name}
                ))
                
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Handle Exam Description",
                success=False,
                message=f"Exam description handling failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_handle_instructions(
        self, 
        exam_paper_data: ExamPaperCreateSchema, 
        prerequisites: Dict[str, Any] = None
    ):
        """Step 6: Handle instructions creation or validation"""
        try:
            validated_ids = []
            created_ids = []
            
            # Handle existing instruction IDs
            for instruction_id in exam_paper_data.instruction_ids:
                # In real implementation: validate instruction exists
                validated_ids.append(instruction_id)
            
            # Handle new instructions from prerequisites
            if prerequisites and prerequisites.get('instructions'):
                for instruction_data in prerequisites['instructions']:
                    instruction_schema = ExamInstructionCreateSchema(**instruction_data)
                    
                    # Simulate creation
                    new_instruction_id = uuid4()
                    exam_paper_data.instruction_ids.append(new_instruction_id)
                    created_ids.append(new_instruction_id)
                    self.created_entities[f'instruction_{new_instruction_id}'] = new_instruction_id
            
            self.results.append(FlowStepResult(
                step_name="Handle Instructions",
                success=True,
                message=f"Processed {len(validated_ids)} existing and created {len(created_ids)} new instructions",
                data={
                    "validated_ids": [str(id) for id in validated_ids],
                    "created_ids": [str(id) for id in created_ids],
                    "total_instructions": len(exam_paper_data.instruction_ids)
                }
            ))
            
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Handle Instructions",
                success=False,
                message=f"Instructions handling failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_handle_modules(
        self, 
        exam_paper_data: ExamPaperCreateSchema, 
        prerequisites: Dict[str, Any] = None
    ):
        """Step 7: Handle modules creation or validation"""
        try:
            validated_ids = []
            created_ids = []
            
            # Handle existing module IDs
            for module_id in exam_paper_data.module_ids:
                # In real implementation: validate module exists
                validated_ids.append(module_id)
            
            # Handle new modules from prerequisites
            if prerequisites and prerequisites.get('modules'):
                for module_data in prerequisites['modules']:
                    module_schema = ModuleCreateSchema(**module_data)
                    
                    # Simulate creation
                    new_module_id = uuid4()
                    exam_paper_data.module_ids.append(new_module_id)
                    created_ids.append(new_module_id)
                    self.created_entities[f'module_{new_module_id}'] = new_module_id
            
            self.results.append(FlowStepResult(
                step_name="Handle Modules",
                success=True,
                message=f"Processed {len(validated_ids)} existing and created {len(created_ids)} new modules",
                data={
                    "validated_ids": [str(id) for id in validated_ids],
                    "created_ids": [str(id) for id in created_ids],
                    "total_modules": len(exam_paper_data.module_ids)
                }
            ))
            
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Handle Modules",
                success=False,
                message=f"Modules handling failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_create_exam_paper(self, exam_paper_data: ExamPaperCreateSchema) -> UUID:
        """Step 8: Create the exam paper"""
        try:
            # In real implementation:
            # exam_paper = await crud.exam_paper.create_with_related_list(
            #     obj_in=exam_paper_data,
            #     related_list_object1=instructions,
            #     related_list_object2=modules,
            #     items1="instructions",
            #     items2="modules",
            #     created_by_id=self.current_user_id,
            # )
            
            # Simulate creation
            exam_paper_id = uuid4()
            self.created_entities['exam_paper'] = exam_paper_id
            
            self.results.append(FlowStepResult(
                step_name="Create Exam Paper",
                success=True,
                message=f"Successfully created exam paper for {exam_paper_data.year_of_exam}",
                data={
                    "exam_paper_id": str(exam_paper_id),
                    "year": exam_paper_data.year_of_exam,
                    "duration": exam_paper_data.exam_duration,
                    "exam_date": str(exam_paper_data.exam_date) if exam_paper_data.exam_date else None,
                    "tags": exam_paper_data.tags
                }
            ))
            
            return exam_paper_id
            
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Create Exam Paper",
                success=False,
                message=f"Exam paper creation failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_add_question_sets(
        self, 
        exam_paper_id: UUID, 
        question_sets_data: List[QuestionSetCreateSchema]
    ):
        """Step 9: Add question sets to exam paper"""
        try:
            created_question_sets = []
            
            for qs_data in question_sets_data:
                # In real implementation:
                # question_set = await crud.question_set.create(obj_in=qs_data, created_by_id=self.current_user_id)
                # await crud.exam_paper.add_question_set_to_exam_paper(exam_paper_id, question_set.id)
                
                # Simulate creation
                question_set_id = uuid4()
                created_question_sets.append({
                    "id": str(question_set_id),
                    "title": qs_data.title,
                    "description": qs_data.description
                })
                self.created_entities[f'question_set_{question_set_id}'] = question_set_id
            
            self.results.append(FlowStepResult(
                step_name="Add Question Sets",
                success=True,
                message=f"Successfully added {len(created_question_sets)} question sets",
                data={
                    "exam_paper_id": str(exam_paper_id),
                    "question_sets": created_question_sets
                }
            ))
            
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Add Question Sets",
                success=False,
                message=f"Question sets addition failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _step_add_questions(
        self, 
        exam_paper_id: UUID, 
        main_questions_data: List[MainQuestionCreateSchema] = None,
        sub_questions_data: List[SubQuestionCreateSchema] = None
    ):
        """Step 10: Add main questions and sub-questions to exam paper"""
        try:
            created_main_questions = []
            created_sub_questions = []
            
            # Create main questions first
            if main_questions_data:
                for q_data in main_questions_data:
                    # In real implementation:
                    # question = await crud.question.create(obj_in=q_data, created_by_id=self.current_user_id)
                    
                    # Simulate creation
                    question_id = uuid4()
                    question_text = "Sample question text" if not q_data.text else "Rich text question"
                    created_main_questions.append({
                        "id": str(question_id),
                        "question_number": q_data.question_number,
                        "question_text": question_text,
                        "marks": q_data.marks,
                        "numbering_style": q_data.numbering_style,
                        "type": "main_question"
                    })
                    self.created_entities[f'main_question_{question_id}'] = question_id
            
            # Create sub-questions
            if sub_questions_data:
                for sq_data in sub_questions_data:
                    # In real implementation:
                    # sub_question = await crud.question.create(obj_in=sq_data, created_by_id=self.current_user_id)
                    
                    # Simulate creation
                    sub_question_id = uuid4()
                    question_text = "Sample sub-question text" if not sq_data.text else "Rich text sub-question"
                    created_sub_questions.append({
                        "id": str(sub_question_id),
                        "question_number": sq_data.question_number,
                        "question_text": question_text,
                        "marks": sq_data.marks,
                        "numbering_style": sq_data.numbering_style,
                        "parent_id": str(sq_data.parent_id),
                        "type": "sub_question"
                    })
                    self.created_entities[f'sub_question_{sub_question_id}'] = sub_question_id
            
            total_questions = len(created_main_questions) + len(created_sub_questions)
            
            self.results.append(FlowStepResult(
                step_name="Add Questions",
                success=True,
                message=f"Successfully added {len(created_main_questions)} main questions and {len(created_sub_questions)} sub-questions",
                data={
                    "exam_paper_id": str(exam_paper_id),
                    "main_questions": created_main_questions,
                    "sub_questions": created_sub_questions,
                    "total_questions": total_questions
                }
            ))
            
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Add Questions",
                success=False,
                message=f"Questions addition failed: {str(e)}",
                errors=[str(e)]
            ))
            raise
    
    async def _rollback_created_entities(self):
        """Rollback all created entities in case of failure"""
        try:
            rollback_results = []
            
            for entity_key, entity_id in reversed(list(self.created_entities.items())):
                try:
                    # In real implementation: delete the created entity
                    # await crud.{entity_type}.remove(id=entity_id)
                    rollback_results.append(f"Rolled back {entity_key}: {entity_id}")
                except Exception as e:
                    rollback_results.append(f"Failed to rollback {entity_key}: {str(e)}")
            
            self.results.append(FlowStepResult(
                step_name="Rollback",
                success=True,
                message=f"Rollback completed for {len(rollback_results)} entities",
                data={"rollback_results": rollback_results}
            ))
            
        except Exception as e:
            self.results.append(FlowStepResult(
                step_name="Rollback",
                success=False,
                message=f"Rollback failed: {str(e)}",
                errors=[str(e)]
            ))

# ============================================================================
# COMPLETE REALISTIC EXAMPLE FROM ACTUAL EXAM PAPER
# ============================================================================

async def create_realistic_exam_paper_example():
    """Create a complete realistic exam paper based on BIT 1103 Basic Electricity exam"""
    
    flow = ExamPaperCreationFlow(current_user_id=uuid4())
    
    # Exam paper metadata
    exam_paper_data = ExamPaperCreateSchema(
        year_of_exam="2010/2011",
        exam_duration=120,  # 2 hours
        exam_date=date(2011, 8, 1),
        tags=["basic_electricity", "first_year", "bit_1103"],
        title_id=None,
        description_id=None,
        course_id=None,
        institution_id=None,
        instruction_ids=[],
        module_ids=[]
    )
    
    # Prerequisites
    prerequisites = {
        "institution": {
            "name": "University of Technology",
            "description": "Leading technology university"
        },
        "course": {
            "name": "Bachelor of Science in Information Technology",
            "course_acronym": "BIT",
            "description": "Undergraduate IT program"
        },
        "title": {
            "name": "UNIVERSITY EXAMINATIONS"
        },
        "description": {
            "name": "FIRST YEAR STAGE EXAMINATION FOR THE DEGREE OF BACHELOR OF SCIENCE IN INFORMATION TECHNOLOGY"
        },
        "instructions": [
            {"name": "Answer question ONE and any other TWO questions"}
        ],
        "modules": [
            {
                "name": "Basic Electricity",
                "unit_code": "BIT 1103",
                "description": "Fundamental concepts of electricity"
            }
        ]
    }
    
    # Question Set
    question_sets = [
        QuestionSetCreateSchema(
            title="Main Examination Questions"
        )
    ]
    
    # Get IDs for relationships (in real implementation, these would come from created entities)
    question_set_id = uuid4()
    exam_paper_id = uuid4()
    
    # QUESTION ONE - Compulsory with multiple sub-questions
    question_one_id = uuid4()
    main_questions = [
        MainQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q1_header",
                        type="header",
                        data={"text": "Question One", "level": 2}
                    )
                ]
            ),
            marks=30,
            numbering_style="numeric",
            question_number="1",
            question_set_id=question_set_id,
            exam_paper_id=exam_paper_id
        )
    ]
    
    # Sub-questions for Question One
    sub_questions_q1 = [
        # Part a
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q1a_text",
                        type="paragraph",
                        data={"text": "Define Kirchhoff's current law and Kirchhoff's voltage law."}
                    )
                ]
            ),
            marks=4,
            numbering_style="alphabetic",
            question_number="a",
            parent_id=question_one_id
        ),
        # Part b
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q1b_text",
                        type="paragraph",
                        data={"text": "By drawing the two circuits which depict Kirchhoff's laws, show how effective resistance of each circuit may be derived."}
                    )
                ]
            ),
            marks=6,
            numbering_style="alphabetic",
            question_number="b",
            parent_id=question_one_id
        ),
        # Part c
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q1c_text",
                        type="paragraph",
                        data={"text": "Determine the standard values of the following resistors; giving minimum and maximum values of each resistor."}
                    ),
                    EditorJSBlock(
                        id="q1c_list",
                        type="list",
                        data={
                            "style": "ordered",
                            "items": [
                                "Brown-Green-Brown-Silver",
                                "Orange-Blue-Silver-Gold"
                            ]
                        }
                    )
                ]
            ),
            marks=4,
            numbering_style="alphabetic",
            question_number="c",
            parent_id=question_one_id
        ),
        # Part d
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q1d_text",
                        type="paragraph",
                        data={"text": "Give the correct band-colours of the following standard resistors."}
                    ),
                    EditorJSBlock(
                        id="q1d_list",
                        type="list",
                        data={
                            "style": "ordered",
                            "items": [
                                "3.6K ± 5%",
                                "180R ± 10%"
                            ]
                        }
                    )
                ]
            ),
            marks=4,
            numbering_style="alphabetic",
            question_number="d",
            parent_id=question_one_id
        ),
        # Part e
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q1e_text1",
                        type="paragraph",
                        data={"text": "(i) Name the factors which affect the resistance of a conductor."}
                    ),
                    EditorJSBlock(
                        id="q1e_text2",
                        type="paragraph",
                        data={"text": "(ii) Show clearly the relationship between the resistance and each of those factors stated in part (i)"}
                    )
                ]
            ),
            marks=6,
            numbering_style="alphabetic",
            question_number="e",
            parent_id=question_one_id
        ),
        # Part f
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q1f_text",
                        type="paragraph",
                        data={"text": "Two resistors R1, R2 are connected in parallel across the dc source of voltage, E. If an ammeter A is connected to measure the total current and voltmeter V is connected to measure the p.d. across the resistor R2, draw a neat labeled circuit diagram of the circuit."}
                    )
                ]
            ),
            marks=6,
            numbering_style="alphabetic",
            question_number="f",
            parent_id=question_one_id
        )
    ]
    
    # QUESTION TWO with image
    question_two_id = uuid4()
    main_questions.append(
        MainQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q2_header",
                        type="header",
                        data={"text": "Question Two", "level": 2}
                    )
                ]
            ),
            marks=20,
            numbering_style="numeric",
            question_number="2",
            question_set_id=question_set_id,
            exam_paper_id=exam_paper_id
        )
    )
    
    sub_questions_q2 = [
        # Part a
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q2a_text",
                        type="paragraph",
                        data={"text": "Two resistors R1 = 560 R ± 10% and R2 = 430 R ± 5% are connected in a circuit to a 12V-dc source. Determine the minimum and maximum values of currents flowing from the 12V-dc source if; (answers expressed in mA corrected to 2 dec. places)"}
                    ),
                    EditorJSBlock(
                        id="q2a_list",
                        type="list",
                        data={
                            "style": "ordered",
                            "items": [
                                "R1 and R2 are in series.",
                                "R1 and R2 are in parallel"
                            ]
                        }
                    )
                ]
            ),
            marks=10,
            numbering_style="alphabetic",
            question_number="a",
            parent_id=question_two_id
        ),
        # Part b with image
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q2b_text",
                        type="paragraph",
                        data={"text": "For the circuit shown in fig.Q2, determine an expression for the voltage V3 across R3, in terms of E, R1, and R3 only."}
                    ),
                    EditorJSBlock(
                        id="q2b_image",
                        type="image",
                        data={
                            "file": {
                                "url": "bit-1103-august-2011-basic-electricity-2010-2011-with-image-refs_artifacts/image_000001_71734f12f6e8b1d655a61cab82c24a883cb7016b63f9c16e0fcd95d11c63d152.png",
                                "name": "circuit_diagram_q2.png",
                                "size": 125000,
                                "width": 600,
                                "height": 400,
                                "format": "PNG"
                            },
                            "caption": "Fig. Q2 - Circuit diagram",
                            "stretched": False,
                            "withBorder": True,
                            "withBackground": False
                        }
                    )
                ]
            ),
            marks=4,
            numbering_style="alphabetic",
            question_number="b",
            parent_id=question_two_id
        ),
        # Part c
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q2c_text",
                        type="paragraph",
                        data={"text": "If in the circuit of fig. Q2, R1 = 15 Ω, R2 = 30 Ω, R3 = 45 Ω and E = 33 V, calculate;"}
                    ),
                    EditorJSBlock(
                        id="q2c_list",
                        type="list",
                        data={
                            "style": "ordered",
                            "items": [
                                "the value of V3,",
                                "the values of currents I2, I3 through R2, R3 respectively."
                            ]
                        }
                    )
                ]
            ),
            marks=6,
            numbering_style="alphabetic",
            question_number="c",
            parent_id=question_two_id
        )
    ]
    
    # QUESTION THREE with table
    question_three_id = uuid4()
    main_questions.append(
        MainQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q3_header",
                        type="header",
                        data={"text": "Question Three", "level": 2}
                    )
                ]
            ),
            marks=20,
            numbering_style="numeric",
            question_number="3",
            question_set_id=question_set_id,
            exam_paper_id=exam_paper_id
        )
    )
    
    sub_questions_q3 = [
        # Part a
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q3a_text",
                        type="paragraph",
                        data={"text": "Define the term resistivity of a resistor and show its unit of measurement."}
                    )
                ]
            ),
            marks=3,
            numbering_style="alphabetic",
            question_number="a",
            parent_id=question_three_id
        ),
        # Part b with table
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q3b_text",
                        type="paragraph",
                        data={"text": "Three resistors (R1, R2, and R3) made from the same materials, have the dimension as shown in Table Q3."}
                    ),
                    EditorJSBlock(
                        id="q3b_table",
                        type="table",
                        data={
                            "withHeadings": True,
                            "content": [
                                ["Resistor", "R1", "R2", "R3"],
                                ["Cross-sectional area", "A", "2A", "1.5A"],
                                ["Length", "L", "1.5L", "2L"]
                            ]
                        }
                    ),
                    EditorJSBlock(
                        id="q3b_text2",
                        type="paragraph",
                        data={"text": "The current, I1 through resistor R1 is 20 A for a given voltage V. For the same voltage, applied separately across R2 and R3, determine the values of currents I2 and I3."}
                    )
                ]
            ),
            marks=7,
            numbering_style="alphabetic",
            question_number="b",
            parent_id=question_three_id
        ),
        # Part c with image
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=int(datetime.now().timestamp() * 1000),
                blocks=[
                    EditorJSBlock(
                        id="q3c_text",
                        type="paragraph",
                        data={"text": "Fig. Q3 (c) shows a simple electrical circuit."}
                    ),
                    EditorJSBlock(
                        id="q3c_image",
                        type="image",
                        data={
                            "file": {
                                "url": "bit-1103-august-2011-basic-electricity-2010-2011-with-image-refs_artifacts/image_000002_6b60fcd207d327d297b38c6258b8f3a236aca5303e3af05f97e9c46de96aa1c7.png",
                                "name": "circuit_diagram_q3c.png",
                                "size": 110000,
                                "width": 550,
                                "height": 380,
                                "format": "PNG"
                            },
                            "caption": "Fig. Q3(c) - Electrical circuit",
                            "stretched": False,
                            "withBorder": True,
                            "withBackground": False
                        }
                    ),
                    EditorJSBlock(
                        id="q3c_text2",
                        type="paragraph",
                        data={"text": "By applying the Kirchhoff's laws, determine the values all the currents I1, I2 and I3, flowing through R1, R2 and R3."}
                    )
                ]
            ),
            marks=10,
            numbering_style="alphabetic",
            question_number="c",
            parent_id=question_three_id
        )
    ]
    
    # Combine all sub-questions
    all_sub_questions = sub_questions_q1 + sub_questions_q2 + sub_questions_q3
    
    # Execute the flow
    result = await flow.execute_complete_flow(
        exam_paper_data,
        prerequisites=prerequisites,
        question_sets_data=question_sets,
        main_questions_data=main_questions,
        sub_questions_data=all_sub_questions
    )
    
    return result

# ============================================================================
# USAGE EXAMPLES AND DEMO FUNCTIONS
# ============================================================================

async def demo_complete_flow():
    """Demonstrate the complete exam paper creation flow"""
    
    print("🚀 Starting Complete Exam Paper Creation Flow Demo")
    print("=" * 60)
    
    # Initialize the flow
    flow = ExamPaperCreationFlow(current_user_id=uuid4())
    
    # Example 1: Create exam paper with existing entities (using IDs)
    print("\n📋 Example 1: Using Existing Entities")
    print("-" * 40)
    
    exam_paper_data_1 = ExamPaperCreateSchema(
        year_of_exam="2024/2025",
        exam_duration=180,
        exam_date=date(2024, 12, 15),
        tags=["final", "computer_science", "algorithms"],
        title_id=uuid4(),
        description_id=uuid4(),
        course_id=uuid4(),
        institution_id=uuid4(),
        instruction_ids=[uuid4(), uuid4()],
        module_ids=[uuid4()]
    )
    
    result_1 = await flow.execute_complete_flow(exam_paper_data_1)
    print_flow_result(result_1, "Example 1")
    
    # Example 2: Create exam paper with new entities (creating prerequisites)
    print("\n📋 Example 2: Creating New Entities")
    print("-" * 40)
    
    flow_2 = ExamPaperCreationFlow(current_user_id=uuid4())
    
    exam_paper_data_2 = ExamPaperCreateSchema(
        year_of_exam="2024/2025",
        exam_duration=120,
        exam_date=date(2024, 11, 20),
        tags=["midterm", "mathematics", "calculus"],
        title_id=uuid4(),  # Will be ignored since we provide prerequisites
        description_id=uuid4(),  # Will be ignored
        course_id=uuid4(),  # Will be ignored
        institution_id=uuid4(),  # Will be ignored
        instruction_ids=[],  # Will be populated from prerequisites
        module_ids=[]  # Will be populated from prerequisites
    )
    
    # Reset IDs to None to force creation from prerequisites
    exam_paper_data_2.title_id = None
    exam_paper_data_2.description_id = None
    exam_paper_data_2.course_id = None
    exam_paper_data_2.institution_id = None
    
    prerequisites = {
        "institution": {
            "name": "University of Technology",
            "description": "Leading technology university"
        },
        "course": {
            "name": "Advanced Mathematics",
            "course_acronym": "MATH301",
            "description": "Advanced calculus and linear algebra"
        },
        "title": {
            "name": "UNIVERSITY EXAMINATIONS",
            "description": "Official university examination"
        },
        "description": {
            "name": "SECOND YEAR MATHEMATICS EXAMINATION",
            "description": "Comprehensive mathematics examination for second year students"
        },
        "instructions": [
            {"name": "Answer ALL questions"},
            {"name": "Show all working clearly"},
            {"name": "Use of calculators is permitted"}
        ],
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
        ]
    }
    
    # Question sets to add
    question_sets = [
        QuestionSetCreateSchema(
            title="Section A: Multiple Choice",
            description="Choose the best answer for each question",
            instructions="Select only one answer per question"
        ),
        QuestionSetCreateSchema(
            title="Section B: Problem Solving",
            description="Solve the following problems showing all work",
            instructions="Partial credit will be given for correct methodology"
        )
    ]
    
    # Main questions to add (will be created first to get IDs for sub-questions)
    main_questions = [
        MainQuestionCreateSchema(
            text=QuestionTextSchema(
                time=1761416444650,
                blocks=[
                    EditorJSBlock(
                        id="header001",
                        type="header",
                        data={"text": "Question 1: Calculus", "level": 3}
                    ),
                    EditorJSBlock(
                        id="pp0wt2psxQ",
                        type="paragraph",
                        data={"text": "What is the derivative of x^2 + 3x + 2?"}
                    ),
                    EditorJSBlock(
                        id="list001",
                        type="list",
                        data={
                            "style": "ordered",
                            "items": ["A) 2x + 3", "B) x^2 + 3", "C) 2x + 2", "D) x + 3"]
                        }
                    )
                ]
            ),
            marks=5,
            numbering_style="numeric",
            question_number="1",
            question_set_id=uuid4(),  # This would be from created question sets
            exam_paper_id=uuid4()     # This would be the actual exam paper ID
        ),
        MainQuestionCreateSchema(
            text=QuestionTextSchema(
                time=1761416444651,
                blocks=[
                    EditorJSBlock(
                        id="header002",
                        type="header",
                        data={"text": "Question 2: Advanced Problems", "level": 3}
                    ),
                    EditorJSBlock(
                        id="pp0wt2psxR",
                        type="paragraph",
                        data={"text": "Solve the following calculus problems:"}
                    ),
                    EditorJSBlock(
                        id="image001",
                        type="image",
                        data={
                            "file": {
                                "url": "https://example.com/calculus-diagram.png",
                                "name": "calculus-diagram.png",
                                "size": 85432,
                                "width": 400,
                                "height": 300,
                                "format": "PNG"
                            },
                            "caption": "Reference diagram for calculus problems",
                            "stretched": False,
                            "withBorder": True,
                            "withBackground": False
                        }
                    )
                ]
            ),
            marks=15,
            numbering_style="numeric", 
            question_number="2",
            question_set_id=uuid4(),
            exam_paper_id=uuid4()
        )
    ]
    
    # Sub-questions (children of main questions)
    sub_questions = [
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=1761416444652,
                blocks=[
                    EditorJSBlock(
                        id="pp0wt2psxS",
                        type="paragraph",
                        data={"text": "Find the integral of sin(x)cos(x)dx from 0 to π/2"}
                    ),
                    EditorJSBlock(
                        id="math001",
                        type="math",
                        data={
                            "formula": "\\int_0^{\\pi/2} \\sin(x)\\cos(x) dx",
                            "display": "block"
                        }
                    ),
                    EditorJSBlock(
                        id="warning001",
                        type="warning",
                        data={
                            "title": "Note",
                            "message": "Show all steps in your calculation"
                        }
                    )
                ]
            ),
            marks=8,
            numbering_style="alphabetic",
            question_number="a",
            parent_id=uuid4()  # This would be ID of main question 2
        ),
        SubQuestionCreateSchema(
            text=QuestionTextSchema(
                time=1761416444653,
                blocks=[
                    EditorJSBlock(
                        id="pp0wt2psxT",
                        type="paragraph",
                        data={"text": "Find the eigenvalues of the matrix:"}
                    ),
                    EditorJSBlock(
                        id="table001",
                        type="table",
                        data={
                            "withHeadings": False,
                            "content": [["2", "1"], ["1", "2"]]
                        }
                    ),
                    EditorJSBlock(
                        id="code001",
                        type="code",
                        data={
                            "code": "# You may use this Python code structure:\nimport numpy as np\nA = np.array([[2, 1], [1, 2]])\neigenvalues = np.linalg.eigvals(A)",
                            "language": "python"
                        }
                    )
                ]
            ),
            marks=7,
            numbering_style="alphabetic",
            question_number="b",
            parent_id=uuid4()  # This would be ID of main question 2
        )
    ]
    
    result_2 = await flow_2.execute_complete_flow(
        exam_paper_data_2,
        prerequisites=prerequisites,
        question_sets_data=question_sets,
        main_questions_data=main_questions,
        sub_questions_data=sub_questions
    )
    print_flow_result(result_2, "Example 2")
    
    # Example 4: Realistic exam paper from actual exam
    print("\n📋 Example 4: Realistic Exam Paper (BIT 1103 Basic Electricity)")
    print("-" * 40)
    
    result_4 = await create_realistic_exam_paper_example()
    print_flow_result(result_4, "Example 4 (Realistic Exam)")
    
    # Example 3: Demonstrate error handling
    print("\n📋 Example 3: Error Handling Demo")
    print("-" * 40)
    
    flow_3 = ExamPaperCreationFlow(current_user_id=uuid4())
    
    # Invalid exam paper data (invalid year format)
    try:
        invalid_exam_data = ExamPaperCreateSchema(
            year_of_exam="2024-2025",  # Invalid format
            exam_duration=120,
            title_id=uuid4(),
            description_id=uuid4(),
            course_id=uuid4(),
            institution_id=uuid4()
        )
    except Exception as e:
        print(f"❌ Validation Error Caught: {e}")
        
        # Create valid data for error flow demo
        invalid_exam_data = ExamPaperCreateSchema(
            year_of_exam="2024/2025",
            exam_duration=120,
            title_id=None,  # Missing required data
            description_id=None,
            course_id=None,
            institution_id=None
        )
        
        result_3 = await flow_3.execute_complete_flow(invalid_exam_data)
        print_flow_result(result_3, "Example 3 (Error Demo)")

def print_flow_result(result: CompleteFlowResult, example_name: str):
    """Print formatted flow result"""
    print(f"\n📊 {example_name} Results:")
    print(f"Success: {'✅' if result.success else '❌'}")
    print(f"Completed Steps: {result.completed_steps}/{result.total_steps}")
    
    if result.exam_paper_id:
        print(f"Exam Paper ID: {result.exam_paper_id}")
    
    print("\nStep Details:")
    for i, step in enumerate(result.steps, 1):
        status = "✅" if step.success else "❌"
        print(f"  {i}. {status} {step.step_name}: {step.message}")
        
        if step.data and step.success:
            print(f"     📄 Data: {step.data}")
        
        if step.errors:
            print(f"     ❌ Errors: {step.errors}")

# ============================================================================
# INTEGRATION WITH EXISTING FASTAPI ENDPOINTS
# ============================================================================

def create_fastapi_endpoint_example():
    """
    Example of how to integrate this flow with FastAPI endpoints.
    This would go in your actual endpoint file.
    """
    
    from fastapi import APIRouter, Depends, HTTPException
    from app.api import deps
    from app.models.user_model import User
    from app.schemas.role_schema import IRoleEnum
    
    router = APIRouter()
    
    @router.post("/exam-papers/complete-flow")
    async def create_exam_paper_complete_flow(
        exam_paper_data: ExamPaperCreateSchema,
        prerequisites: Optional[Dict[str, Any]] = None,
        question_sets_data: Optional[List[QuestionSetCreateSchema]] = None,
        main_questions_data: Optional[List[MainQuestionCreateSchema]] = None,
        sub_questions_data: Optional[List[SubQuestionCreateSchema]] = None,
        current_user: User = Depends(
            deps.get_current_user(required_roles=[IRoleEnum.admin, IRoleEnum.manager])
        ),
        db_session = Depends(deps.get_db),
    ):
        """
        Create an exam paper using the complete flow with all prerequisites.
        
        This endpoint handles:
        - Creating or validating all prerequisite entities
        - Creating the exam paper with relationships
        - Adding question sets and questions
        - Comprehensive error handling and rollback
        
        Required roles: admin, manager
        """
        
        # Initialize the flow with real database session
        flow = ExamPaperCreationFlow(
            db_session=db_session,
            current_user_id=current_user.id
        )
        
        # Execute the complete flow
        result = await flow.execute_complete_flow(
            exam_paper_data=exam_paper_data,
            prerequisites=prerequisites,
            question_sets_data=question_sets_data,
            main_questions_data=main_questions_data,
            sub_questions_data=sub_questions_data
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Exam paper creation flow failed",
                    "steps": [step.dict() for step in result.steps],
                    "completed_steps": result.completed_steps,
                    "total_steps": result.total_steps
                }
            )
        
        return {
            "message": "Exam paper created successfully",
            "exam_paper_id": result.exam_paper_id,
            "flow_summary": {
                "total_steps": result.total_steps,
                "completed_steps": result.completed_steps,
                "steps": [
                    {
                        "step_name": step.step_name,
                        "success": step.success,
                        "message": step.message
                    }
                    for step in result.steps
                ]
            }
        }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """Run the demo when script is executed directly"""
    print("🎓 Exam Paper Creation Flow - Complete Implementation")
    print("=" * 60)
    print("This file demonstrates a complete workflow for creating exam papers")
    print("with all necessary prerequisites, validation, and error handling.")
    print("\nFeatures:")
    print("- Complete question hierarchy (QuestionSet → MainQuestion → SubQuestion)")
    print("- Rich text with Editor.js blocks (paragraphs, headers, lists, images, tables)")
    print("- Realistic example from actual BIT 1103 Basic Electricity exam")
    print("- Proper marks allocation and numbering styles")
    print("\nRunning demo...")

    # Run the demo
    asyncio.run(demo_complete_flow())

    print("\n" + "=" * 60)
    print("✅ Demo completed!")
    print("\n📚 Complete Schema Hierarchy Demonstrated:")
    print("   ExamPaper")
    print("   └── QuestionSet (Section/Part)")
    print("       └── MainQuestion (Question 1, 2, 3...)")
    print("           └── SubQuestion (a, b, c...)")
    print("               └── Editor.js Blocks (text, images, tables, lists, etc.)")
    print("\n🔧 To integrate with your FastAPI application:")
    print("1. Import the necessary classes and schemas")
    print("2. Use ExamPaperCreationFlow in your endpoints")
    print("3. Replace simulation code with actual CRUD operations")
    print("4. Add proper database session management")
    print("5. Implement proper error handling and logging")
    print("\n💡 The realistic example (Example 4) shows:")
    print("- Complete exam with 3 main questions")
    print("- 15 sub-questions with proper hierarchy")
    print("- Images, tables, lists in question text")
    print("- Proper marks allocation (total 70 marks)")
    print("- Realistic academic year and metadata")

# ExamPaper (BIT 1103 - Basic Electricity 2010/2011)
# └── QuestionSet (Main Examination Questions)
#     ├── MainQuestion 1 (30 marks) - Compulsory
#     │   ├── SubQuestion a (4 marks) - Kirchhoff's laws definition
#     │   ├── SubQuestion b (6 marks) - Circuit diagrams
#     │   ├── SubQuestion c (4 marks) - Resistor color codes (with list)
#     │   ├── SubQuestion d (4 marks) - Band colors (with list)
#     │   ├── SubQuestion e (6 marks) - Resistance factors
#     │   └── SubQuestion f (6 marks) - Circuit diagram drawing
#     ├── MainQuestion 2 (20 marks)
#     │   ├── SubQuestion a (10 marks) - Current calculations (with list)
#     │   ├── SubQuestion b (4 marks) - Voltage expression (with image)
#     │   └── SubQuestion c (6 marks) - Circuit calculations (with list)
#     └── MainQuestion 3 (20 marks)
#         ├── SubQuestion a (3 marks) - Resistivity definition
#         ├── SubQuestion b (7 marks) - Resistor dimensions (with table)
#         └── SubQuestion c (10 marks) - Kirchhoff's laws application (with image)
"Question One":{
    "main_question": "a",
    "text": " Distinguish between the following geographic concepts;",
    "sub_questions": [
        {"numbering_style": "alphabetic",
            "question_number": "a",
            "text":"Digitizing and cartography "  , 
            "marks": 4},
        {"numbering_style": "alphabetic",
            "question_number": "b",
            "text":"Geographic information systems (GIS) "  , 
            "marks": 6},
        
    ]
}
