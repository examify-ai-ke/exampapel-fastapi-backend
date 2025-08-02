"""
Ultra-optimized queries for maximum performance
These queries load minimal data for list views
"""

from sqlalchemy.orm import selectinload, load_only, joinedload
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

class UltraOptimizedQueryBuilder:
    """
    Ultra-optimized queries that load absolute minimum data for list views
    """
    
    @staticmethod
    def build_institution_minimal_query():
        """Minimal institution query - no relationships loaded"""
        return (
            select(Institution)
            .options(
                # Only load the logo (small data)
                selectinload(Institution.logo),
                # Don't load any other relationships - use properties for counts
            )
        )
    
    @staticmethod
    def build_faculty_minimal_query():
        """Minimal faculty query"""
        return (
            select(Faculty)
            .options(
                # Use joinedload for many-to-one relationships (more efficient)
                joinedload(Faculty.created_by).load_only(
                    User.id, User.first_name, User.last_name
                ),
                selectinload(Faculty.image),
                # Don't load institutions or departments - use counts
            )
        )
    
    @staticmethod
    def build_exam_paper_minimal_query():
        """Minimal exam paper query"""
        return (
            select(ExamPaper)
            .options(
                # Use joinedload for single relationships
                joinedload(ExamPaper.course).load_only(
                    Course.id, Course.name, Course.course_acronym
                ),
                joinedload(ExamPaper.institution).load_only(
                    Institution.id, Institution.name
                ),
                joinedload(ExamPaper.created_by).load_only(
                    User.id, User.first_name, User.last_name
                ),
                # Don't load question_sets, modules, etc. - use counts
            )
        )
    
    @staticmethod
    def build_question_set_minimal_query():
        """Minimal question set query"""
        return (
            select(QuestionSet)
            .options(
                joinedload(QuestionSet.created_by).load_only(
                    User.id, User.first_name, User.last_name
                ),
                # Don't load questions - use count property
            )
        )
    
    @staticmethod
    def build_course_minimal_query():
        """Minimal course query"""
        return (
            select(Course)
            .options(
                joinedload(Course.programme).load_only(
                    Programme.id, Programme.name
                ),
                joinedload(Course.created_by).load_only(
                    User.id, User.first_name, User.last_name
                ),
                selectinload(Course.image),
                # Don't load modules - use count
            )
        )
    
    @staticmethod
    def build_department_minimal_query():
        """Minimal department query"""
        return (
            select(Department)
            .options(
                joinedload(Department.faculty).load_only(
                    Faculty.id, Faculty.name
                ),
                joinedload(Department.created_by).load_only(
                    User.id, User.first_name, User.last_name
                ),
                selectinload(Department.image),
                # Don't load programmes - use count
            )
        )

class DatabaseOptimizationTips:
    """
    Database optimization recommendations
    """
    
    @staticmethod
    def get_index_recommendations():
        """Get database index recommendations"""
        return {
            "essential_indexes": [
                "CREATE INDEX CONCURRENTLY idx_institution_created_at ON \"Institution\" (created_at);",
                "CREATE INDEX CONCURRENTLY idx_faculty_created_at ON \"Faculty\" (created_at);",
                "CREATE INDEX CONCURRENTLY idx_exam_paper_created_at ON \"ExamPaper\" (created_at);",
                "CREATE INDEX CONCURRENTLY idx_question_set_created_at ON \"QuestionSet\" (created_at);",
                "CREATE INDEX CONCURRENTLY idx_course_created_at ON \"Course\" (created_at);",
                "CREATE INDEX CONCURRENTLY idx_department_created_at ON \"Department\" (created_at);",
                "CREATE INDEX CONCURRENTLY idx_user_created_at ON \"User\" (created_at);",
            ],
            "foreign_key_indexes": [
                "CREATE INDEX CONCURRENTLY idx_institution_created_by_id ON \"Institution\" (created_by_id);",
                "CREATE INDEX CONCURRENTLY idx_faculty_created_by_id ON \"Faculty\" (created_by_id);",
                "CREATE INDEX CONCURRENTLY idx_exam_paper_created_by_id ON \"ExamPaper\" (created_by_id);",
                "CREATE INDEX CONCURRENTLY idx_question_set_created_by_id ON \"QuestionSet\" (created_by_id);",
                "CREATE INDEX CONCURRENTLY idx_course_created_by_id ON \"Course\" (created_by_id);",
                "CREATE INDEX CONCURRENTLY idx_department_created_by_id ON \"Department\" (created_by_id);",
            ],
            "search_indexes": [
                "CREATE INDEX CONCURRENTLY idx_institution_name_gin ON \"Institution\" USING gin(to_tsvector('english', name));",
                "CREATE INDEX CONCURRENTLY idx_faculty_name_gin ON \"Faculty\" USING gin(to_tsvector('english', name));",
                "CREATE INDEX CONCURRENTLY idx_course_name_gin ON \"Course\" USING gin(to_tsvector('english', name));",
            ]
        }
    
    @staticmethod
    def get_query_optimization_tips():
        """Get query optimization tips"""
        return {
            "list_views": [
                "Load only essential columns with load_only()",
                "Use joinedload for many-to-one relationships",
                "Use selectinload for one-to-many only when necessary",
                "Avoid loading relationships that can be counted",
                "Use LIMIT to restrict result sets",
                "Add proper ORDER BY clauses"
            ],
            "relationship_loading": [
                "joinedload: Best for many-to-one with few records",
                "selectinload: Best for one-to-many relationships",
                "subqueryload: For complex scenarios with many records",
                "lazy='select': Default, causes N+1 problems",
                "lazy='joined': Automatic JOIN, can cause cartesian products"
            ],
            "performance_targets": {
                "list_queries": "< 200ms (ultra-fast)",
                "search_queries": "< 500ms",
                "detail_queries": "< 1000ms"
            }
        }
