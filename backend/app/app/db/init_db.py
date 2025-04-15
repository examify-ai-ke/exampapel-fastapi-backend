from datetime import date, datetime
import hashlib
from app.models.course_model import Course
from app.models.department_model import Department
from app.models.faculty_model import Faculty
from app.models.image_media_model import ImageMedia
from app.models.institution_model import (
    Institution,
    InstitutionFacultyLink,
    InstitutionTypes,
)
from app.models.module_model import CourseModuleLink, Module, ModuleExamsLink
from app.models.programme_model import Programme, ProgrammeDepartmentLink, ProgrammeTypes
from app.models.exam_paper_model import (
    ExamDescription,
    ExamInstruction,
    ExamPaper,
    ExamTitle,
    ExamPaperQuestionLink,
    InstructionExamsLink,
)
from app.models.question_model import MainQuestion, QuestionSet, QuestionSetTitleEnum, SubQuestion
from sqlmodel.ext.asyncio.session import AsyncSession
from app import crud
from app.schemas.role_schema import IRoleCreate
from app.core.config import settings
from app.schemas.user_schema import IUserCreate
from app.schemas.team_schema import ITeamCreate
from app.schemas.hero_schema import IHeroCreate
from app.schemas.group_schema import IGroupCreate
import uuid
import asyncio
from sqlalchemy import select


roles: list[IRoleCreate] = [
    IRoleCreate(name="admin", description="This the Admin role"),
    IRoleCreate(name="manager", description="Manager role"),
    IRoleCreate(name="user", description="User role"),
]

groups: list[IGroupCreate] = [
    IGroupCreate(name="GR1", description="This is the first group")
]

users: list[dict[str, str | IUserCreate]] = [
    {
        "data": IUserCreate(
            first_name="Admin",
            last_name="FastAPI",
            password=settings.FIRST_SUPERUSER_PASSWORD,
            email=settings.FIRST_SUPERUSER_EMAIL,
            is_superuser=True,
        ),
        "role": "admin",
    },
    {
        "data": IUserCreate(
            first_name="Manager",
            last_name="FastAPI",
            password=settings.FIRST_SUPERUSER_PASSWORD,
            email="manager@example.com",
            is_superuser=False,
        ),
        "role": "manager",
    },
    {
        "data": IUserCreate(
            first_name="User",
            last_name="FastAPI",
            password=settings.FIRST_SUPERUSER_PASSWORD,
            email="user@example.com",
            is_superuser=False,
        ),
        "role": "user",
    },
]

teams: list[ITeamCreate] = [
    ITeamCreate(name="Preventers", headquarters="Sharp Tower"),
    ITeamCreate(name="Z-Force", headquarters="Sister Margaret's Bar"),
]

heroes: list[dict[str, str | IHeroCreate]] = [
    {
        "data": IHeroCreate(name="Deadpond", secret_name="Dive Wilson", age=21),
        "team": "Z-Force",
    },
    {
        "data": IHeroCreate(name="Rusty-Man", secret_name="Tommy Sharp", age=48),
        "team": "Preventers",
    },
]


async def init_db(db_session: AsyncSession, skip_institutions=False) -> None:
    """
    Initialize database with core data and optionally institutions.
    
    Args:
        db_session: The database session
        skip_institutions: If True, skip institution initialization
    """
    try:
        # Create roles first
        for role in roles:
            role_current = await crud.role.get_role_by_name(
                name=role.name, db_session=db_session
            )
            if not role_current:
                await crud.role.create(obj_in=role, db_session=db_session)

        # Then create users (including admin)
        for user in users:
            current_user = await crud.user.get_by_email(
                email=user["data"].email, db_session=db_session
            )
            if not current_user:
                role = await crud.role.get_role_by_name(
                    name=user["role"], db_session=db_session
                )
                user["data"].role_id = role.id
                await crud.user.create_with_role(obj_in=user["data"], db_session=db_session)

        # Get admin user ID for creating other entities
        current_admin = await crud.user.get_by_email(
            email=settings.FIRST_SUPERUSER_EMAIL, db_session=db_session
        )
        ADMIN_USER_ID = current_admin.id

        # Create groups, teams, heroes
        for group in groups:
            current_group = await crud.group.get_group_by_name(
                name=group.name, db_session=db_session
            )
            if not current_group:
                current_user = await crud.user.get_by_email(
                    email=users[0]["data"].email, db_session=db_session
                )
                new_group = await crud.group.create(
                    obj_in=group, created_by_id=current_user.id, db_session=db_session
                )
                current_users = []
                for user in users:
                    current_users.append(
                        await crud.user.get_by_email(
                            email=user["data"].email, db_session=db_session
                        )
                    )
                await crud.group.add_users_to_group(
                    users=current_users, group_id=new_group.id, db_session=db_session
                )

        for team in teams:
            current_team = await crud.team.get_team_by_name(
                name=team.name, db_session=db_session
            )
            if not current_team:
                current_user = await crud.user.get_by_email(
                    email=users[0]["data"].email, db_session=db_session
                )
                await crud.team.create(
                    obj_in=team, created_by_id=current_user.id, db_session=db_session
                )

        for heroe in heroes:
            current_heroe = await crud.hero.get_heroe_by_name(
                name=heroe["data"].name, db_session=db_session
            )
            team = await crud.team.get_team_by_name(
                name=heroe["team"], db_session=db_session
            )
            if not current_heroe:
                current_user = await crud.user.get_by_email(
                    email=users[0]["data"].email, db_session=db_session
                )
                new_heroe = heroe["data"]
                new_heroe.team_id = team.id
                await crud.hero.create(
                    obj_in=new_heroe, created_by_id=current_user.id, db_session=db_session
                )

        # Check if we should skip institution initialization
        if skip_institutions:
            return

        # Check if institutions already exist
        existing_institutions = await db_session.execute(select(Institution))
        if existing_institutions.scalars().first():
            print("Institutions already exist. Skipping institution initialization.")
            return

        # Initialize institutions and related entities
        try:
            # Create exam title
            exam_title = ExamTitle(
                name="Introduction to Programming",
                slug="introduction-to-programming",
                created_by_id=ADMIN_USER_ID,
            )
            db_session.add(exam_title)
            await db_session.flush()

            # Create an exam description
            exam_description = ExamDescription(
                name="Final Examination",
                slug="final-examination",
                created_by_id=ADMIN_USER_ID,
            )
            db_session.add(exam_description)
            await db_session.flush()

            # Create institution
            institution = Institution(
                name="University of Technology",
                description="A leading institution in technology education",
                institution_type=InstitutionTypes.UNIVERSITY,
                email="info@utech.edu",
                phone_number="+1234567890",
                created_by_id=ADMIN_USER_ID,
                slug="university-of-technology",
            )
            db_session.add(institution)
            await db_session.flush()

            # Create a module
            module = Module(
                name="Python Programming",
                unit_code="CS101",
                description="Introduction to programming with Python",
                slug="python-programming",
                created_by_id=ADMIN_USER_ID,
            )
            db_session.add(module)
            await db_session.flush()

            # Create an exam paper (this must exist before creating MainQuestions)
            hash_object = hashlib.sha256(
                f"{exam_title.name}+{exam_description.name}".encode()
            ).hexdigest()

            exam_paper = ExamPaper(
                title_id=exam_title.id,
                description_id=exam_description.id,
                institution_id=institution.id,
                year_of_exam="2023",
                exam_date=datetime.utcnow(),
                exam_duration=180,  # 3 hours in minutes
                created_by_id=ADMIN_USER_ID,
                hash_code=hash_object,  # Ensure hash_code is set
            )
            db_session.add(exam_paper)
            await db_session.flush()

            # Create exam instruction
            exam_instruction = ExamInstruction(
                name="Python Basics Exam Instructions",
                slug="python-basics-exam-instructions",
                created_by_id=ADMIN_USER_ID,
            )
            db_session.add(exam_instruction)
            await db_session.flush()

            # Link module to exam paper
            module_exam_link = ModuleExamsLink(
                module_id=module.id,
                exam_id=exam_paper.id
            )
            db_session.add(module_exam_link)
            await db_session.flush()

            # Create all question sets from the QuestionSetTitleEnum
            question_sets = []
            for question_set_title in QuestionSetTitleEnum:
                question_set = QuestionSet(
                    title=question_set_title,
                    slug=question_set_title.value.lower().replace(" ", "-"),  # Generate slug from title
                    created_by_id=ADMIN_USER_ID,
                )
                db_session.add(question_set)
                question_sets.append(question_set)  # Keep track of all question sets
            await db_session.flush()

            # Link only QUESTION_ONE to the ExamPaper
            question_one_set = next(
                (qs for qs in question_sets if qs.title == QuestionSetTitleEnum.QUESTION_ONE), None
            )
            if question_one_set:
                # Link QUESTION_ONE to the ExamPaper
                exam_paper_question_link = ExamPaperQuestionLink(
                    exam_id=exam_paper.id,
                    question_set_id=question_one_set.id,
                )
                db_session.add(exam_paper_question_link)
                await db_session.flush()

                # Create main questions linked to QUESTION_ONE and the ExamPaper
                main_questions = [
                    MainQuestion(
                        text={
                            "time": 1742156891249,
                            "blocks": [
                                {
                                    "id": "dCcbQeoht6",
                                    "type": "paragraph",
                                    "data": {
                                        "text": "Explain the concept of variables in Python and provide examples of different data types.",
                                    },
                                }
                            ],
                        },
                        marks=5,
                        numbering_style="ROMAN",
                        question_number="i",
                        slug="python-variables-and-data-types",
                        question_set_id=question_one_set.id,  # Link to QUESTION_ONE
                        exam_paper_id=exam_paper.id,  # Link to the ExamPaper
                        created_by_id=ADMIN_USER_ID,
                    ),
                    MainQuestion(
                        text={
                            "time": 1742156891260,
                            "blocks": [
                                {
                                    "id": "dCcbQeoht12",
                                    "type": "paragraph",
                                    "data": {
                                        "text": "Write a Python function that calculates the factorial of a given number. Explain your code.",
                                    },
                                }
                            ],
                        },
                        marks=15,
                        numbering_style="ROMAN",
                        question_number="ii",
                        slug="python-factorial-function",
                        question_set_id=question_one_set.id,  # Link to QUESTION_ONE
                        exam_paper_id=exam_paper.id,  # Link to the ExamPaper
                        created_by_id=ADMIN_USER_ID,
                    ),
                ]

                # Add the main questions to the session
                for question in main_questions:
                    db_session.add(question)
                await db_session.flush()

            # Link exam instruction to exam paper
            instruction_link = InstructionExamsLink(
                exam_id=exam_paper.id, instruction_id=exam_instruction.id
            )
            db_session.add(instruction_link)

            # Create faculty first
            faculty = await crud.faculty.get_faculty_by_slug(
                slug="faculty-of-computer-science", db_session=db_session
            )
            if not faculty:
                faculty = Faculty(
                    name="Faculty of Computer Science",
                    slug="faculty-of-computer-science",
                    description="Computer Science and Technology Faculty",
                    created_by_id=ADMIN_USER_ID,
                )
                db_session.add(faculty)
                await db_session.flush()

            # Create faculty-institution link
            institution_faculty_link = InstitutionFacultyLink(
                institution_id=institution.id,
                faculty_id=faculty.id
            )
            db_session.add(institution_faculty_link)
            await db_session.flush()

            # Now create department WITH faculty_id
            department = await crud.department.get_department_by_slug(
                slug="software-engineering-department", db_session=db_session
            )
            if not department:
                department = Department(
                    name="Software Engineering Department",
                    slug="software-engineering-department",
                    description="Department offering software engineering courses",
                    faculty_id=faculty.id,  # Set faculty_id at creation time
                    created_by_id=ADMIN_USER_ID,
                )
                db_session.add(department)
                await db_session.flush()

            # Create programme first
            programme = await crud.programme.get_programme_by_slug(
                slug="undergraduate", db_session=db_session
            )
            if not programme:
                programme = Programme(
                    name=ProgrammeTypes.UNDERGRADUATE,
                    slug="undergraduate",
                    description="Undergraduate programmes",
                    created_by_id=ADMIN_USER_ID,
                )
                db_session.add(programme)
                await db_session.flush()

            # Create course with programme_id set
            course = await crud.course.get_course_by_slug(
                slug="computer-science", db_session=db_session
            )
            if not course:
                course = Course(
                    name="Computer Science",
                    slug="computer-science",
                    course_acronym="CS", 
                    description="Degree in Computer Science",
                    programme_id=programme.id,  # Set programme_id at creation time
                    created_by_id=ADMIN_USER_ID,
                )
                db_session.add(course)
                await db_session.flush()

            # Set the exam paper's course ID
            exam_paper.course_id = course.id
            await db_session.flush()

            # Create programme-department link
            programme_department_link = ProgrammeDepartmentLink(
                programme_id=programme.id,
                department_id=department.id
            )
            db_session.add(programme_department_link)

            # Create course-module link
            course_module_link = CourseModuleLink(
                course_id=course.id,
                module_id=module.id
            )
            db_session.add(course_module_link)

            await db_session.commit()
            print("Database initialized with dummy data and relationships.")
        except Exception as e:
            print(f"An error occurred during institution initialization: {e}")
            await db_session.rollback()
            raise

    except Exception as e:
        print(f"Error during database initialization: {e}")
        await db_session.rollback()
        raise

# This function helps run the init_db function in an async context
def run_init_db():
    """Run the init_db function in a proper async context."""
    from app.db.session import async_engine, get_async_session
    import contextlib
    
    async def init_db_wrapper():
        # Create a new session
        async with async_engine.begin() as conn:
            # Drop and create tables
            # await conn.run_sync(SQLModel.metadata.drop_all)
            # await conn.run_sync(SQLModel.metadata.create_all)
            pass
        
        # Create a session context manager
        async_session_maker = get_async_session()
        async with async_session_maker() as session:
            await init_db(session)
    
    # Run the async function in the event loop
    asyncio.run(init_db_wrapper())

# If this script is run directly, initialize the database
if __name__ == "__main__":
    run_init_db()
