"""
Optimized query builders for common list endpoint patterns
"""

from sqlalchemy.orm import selectinload, load_only
from sqlmodel import select
from app.models.user_model import User
from app.models.role_model import Role
from app.models.institution_model import Institution
from app.models.faculty_model import Faculty
from app.models.department_model import Department
from app.models.course_model import Course
from app.models.module_model import Module
from app.models.programme_model import Programme
from app.models.exam_paper_model import ExamPaper
from app.models.question_model import Question, QuestionSet
from app.models.campus_model import Campus
from app.models.image_media_model import ImageMedia

class OptimizedQueryBuilder:
    """
    Builder class for creating optimized queries for list endpoints
    """
    
    @staticmethod
    def build_user_list_query():
        """Optimized query for user list"""
        return (
            select(User)
            .options(
                selectinload(User.role).load_only(
                    Role.id, Role.name, Role.description
                ),
                selectinload(User.image),  # Image is usually small
                # Don't load groups/followers in list view - too heavy
            )
        )
    
    @staticmethod
    def build_institution_list_query():
        """Optimized query for institution list"""
        return (
            select(Institution)
            .options(
                selectinload(Institution.logo),
                selectinload(Institution.address),
                selectinload(Institution.created_by).load_only(
                    User.id, User.first_name, User.last_name, User.email
                ),
                # Load minimal data for counts
                selectinload(Institution.faculties).load_only(
                    Faculty.id, Faculty.name
                ),
                selectinload(Institution.campuses).load_only(
                    Campus.id, Campus.name
                ),
                selectinload(Institution.exam_papers).load_only(
                    ExamPaper.id, ExamPaper.year_of_exam
                ),
            )
        )
    
    @staticmethod
    def build_faculty_list_query():
        """Optimized query for faculty list"""
        return (
            select(Faculty)
            .options(
                selectinload(Faculty.institutions).load_only(
                    Institution.id, Institution.name, Institution.slug
                ),
                selectinload(Faculty.departments).load_only(
                    Department.id, Department.name, Department.slug
                ),
                selectinload(Faculty.image),
                selectinload(Faculty.created_by).load_only(
                    User.id, User.first_name, User.last_name, User.email
                ),
            )
        )
    
    @staticmethod
    def build_exam_paper_list_query():
        """Optimized query for exam paper list"""
        return (
            select(ExamPaper)
            .options(
                selectinload(ExamPaper.course).load_only(
                    Course.id, Course.name, Course.course_acronym
                ),
                selectinload(ExamPaper.institution).load_only(
                    Institution.id, Institution.name, Institution.slug
                ),
                selectinload(ExamPaper.created_by).load_only(
                    User.id, User.first_name, User.last_name, User.email
                ),
                # Load minimal data for related entities
                selectinload(ExamPaper.question_sets).load_only(
                    QuestionSet.id, QuestionSet.title
                ),
                selectinload(ExamPaper.modules).load_only(
                    Module.id, Module.name, Module.unit_code
                ),
            )
        )
    
    @staticmethod
    def build_question_set_list_query():
        """Optimized query for question set list"""
        return (
            select(QuestionSet)
            .options(
                selectinload(QuestionSet.created_by).load_only(
                    User.id, User.first_name, User.last_name, User.email
                ),
                # Load questions with minimal data for counts
                selectinload(QuestionSet.questions).load_only(
                    Question.id, Question.question_number, Question.marks
                ),
            )
        )
    
    @staticmethod
    def build_course_list_query():
        """Optimized query for course list"""
        return (
            select(Course)
            .options(
                selectinload(Course.programme).load_only(
                    Programme.id, Programme.name, Programme.slug
                ),
                selectinload(Course.created_by).load_only(
                    User.id, User.first_name, User.last_name, User.email
                ),
                selectinload(Course.image),
                # Load modules with minimal data
                selectinload(Course.modules).load_only(
                    Module.id, Module.name, Module.unit_code
                ),
            )
        )
    
    @staticmethod
    def build_department_list_query():
        """Optimized query for department list"""
        return (
            select(Department)
            .options(
                selectinload(Department.faculty).load_only(
                    Faculty.id, Faculty.name, Faculty.slug
                ),
                selectinload(Department.created_by).load_only(
                    User.id, User.first_name, User.last_name, User.email
                ),
                selectinload(Department.image),
                # Load programmes with minimal data
                selectinload(Department.programmes).load_only(
                    Programme.id, Programme.name, Programme.slug
                ),
            )
        )

class QueryOptimizationTips:
    """
    Tips and best practices for query optimization
    """
    
    TIPS = {
        "list_views": [
            "Use load_only() to limit columns",
            "Avoid loading full relationship data",
            "Load only essential fields for related entities",
            "Don't load deep nested relationships",
            "Use properties for counts instead of loading full data"
        ],
        "detail_views": [
            "Load all necessary relationships upfront",
            "Use selectinload for one-to-many relationships",
            "Use joinedload for many-to-one with few records",
            "Consider using subqueryload for complex scenarios"
        ],
        "search_queries": [
            "Add proper database indexes",
            "Use ILIKE for case-insensitive search",
            "Consider full-text search for complex searches",
            "Limit search results appropriately"
        ],
        "performance_targets": {
            "list_queries": "< 500ms",
            "detail_queries": "< 1000ms", 
            "search_queries": "< 2000ms"
        }
    }
    
    @classmethod
    def get_optimization_checklist(cls) -> dict:
        """Get a checklist for query optimization"""
        return {
            "before_optimization": [
                "Identify slow queries (> 1s)",
                "Check current selectinload usage",
                "Analyze relationship depth",
                "Review schema requirements"
            ],
            "optimization_steps": [
                "Replace full relationship loads with load_only()",
                "Remove unnecessary deep nesting",
                "Use appropriate loading strategies",
                "Add database indexes where needed",
                "Test query performance"
            ],
            "after_optimization": [
                "Measure query execution time",
                "Verify data completeness",
                "Check for N+1 query issues",
                "Monitor production performance"
            ]
        }
