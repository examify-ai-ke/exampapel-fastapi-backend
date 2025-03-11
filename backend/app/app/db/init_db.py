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
from app.models.module_model import CourseModuleLink, Module
from app.models.programme_model import Programme, ProgrammeDepartmentLink, ProgrammeTypes
from app.models.exam_paper_model import ExamDescription, ExamInstruction, ExamPaper, ExamTitle
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


async def init_db(db_session: AsyncSession) -> None:
    for role in roles:
        role_current = await crud.role.get_role_by_name(
            name=role.name, db_session=db_session
        )
        if not role_current:
            await crud.role.create(obj_in=role, db_session=db_session)

    for user in users:
        current_user = await crud.user.get_by_email(
            email=user["data"].email, db_session=db_session
        )
        role = await crud.role.get_role_by_name(
            name=user["role"], db_session=db_session
        )
        if not current_user:
            user["data"].role_id = role.id
            await crud.user.create_with_role(obj_in=user["data"], db_session=db_session)

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


async def init_db_institution(db: AsyncSession) -> None:
    # ADMIN_USER_ID = uuid.UUID("019074fa-2036-79f1-bf01-d7d7a2b07a3b")
    current_admin = await crud.user.get_by_email(
        email=settings.FIRST_SUPERUSER_EMAIL, db_session=db
    )

    ADMIN_USER_ID=current_admin.id

    try:
        # Check if there are any records in the Institution table
        institution_count = await crud.institution.get_count_of_institutions(
            db_session=db
        )

        print("Institution Count:", institution_count)
        if not institution_count:
            print("No institutions found. Initializing database with dummy data...")

            # Create ImageMedia
            # image = ImageMedia(
            #     id=uuid.uuid4(),
            #     file_format="jpg",
            #     width=800,
            #     height=600,
            #     created_at=datetime.utcnow(),
            #     updated_at=datetime.utcnow(),
            #     created_by_id=ADMIN_USER_ID,
            # )

            # await db.add(image)
            # await db.flush()

            # Create Institution
            institution_create = Institution(
                # id=uuid.uuid4(),
                name="Sample University",
                description="A leading institution of higher education",
                institution_type=InstitutionTypes.UNIVERSITY,
                email="info@sampleuniversity.edu",
                phone_number="+1234567890",
                slug="sample-university",
                image_id=None,
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            # Create Faculty
            faculty_create = Faculty(
                # id=uuid.uuid4(),
                name="Faculty of Science",
                description="Exploring the wonders of science",
                slug="faculty-of-science",
                # image_id=image.id,
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            # Create Department
            department = Department(
                # id=uuid.uuid4(),
                name="Department of Computer Science",
                description="Advancing computer science education and research",
                slug="computer-science",
                # image_id=image.id,
                # faculty_id=faculty_create.id,
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )
            # Create Programme
            programme = Programme(
                # id=uuid.uuid4(),
                name=ProgrammeTypes.UNDERGRADUATE,
                description="A comprehensive program in computer science",
                slug="bsc-computer-science",
                # image_id=image.id,
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            # Create Course
            course = Course(
                # id=uuid.uuid4(),
                name="Introduction to Programming",
                description="Fundamentals of programming and problem-solving",
                slug="intro-to-programming",
                # programme_id=programme.id,
                # image_id=image.id,
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            # Create Module
            module = Module(
                id=uuid.uuid4(),
                name="Python Basics",
                slug="python-basics",
                unit_code="PY101",
                description="Introduction to Python programming language",
                # image_id=image.id,
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            # Create ExamTitle
            exam_title = ExamTitle(
                # id=uuid.uuid4(),
                name="Python Basics Final Exam",
                description="Final examination for the Python Basics module",
                slug="python-basics-final-exam",
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            # Create ExamDescription
            exam_description = ExamDescription(
                # id=uuid.uuid4(),
                name="Python Basics Final Exam Description",
                slug="python-basics-final-exam-description",
                description="This exam covers all topics taught in the Python Basics module, including variables, data types, control structures, functions, and basic object-oriented programming concepts.",
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID
            )

            # Create ExamInstruction
            exam_instruction = ExamInstruction(
                id=uuid.uuid4(),
                name="Python Basics Exam Instructions",
                slug="python-basics-exam-instructions",
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            hash_object = (
                hashlib.sha256(
                    "python-basics-exam-instructions+Python Basics Final Exam Description".encode()
                )
            ).hexdigest()

            # Create ExamPaper
            exam_paper = ExamPaper(
                # id=uuid.uuid4(),
                year_of_exam="2024",
                exam_duration=120,  # 2 hours
                exam_date=date(2024, 6, 15),  # Example date
                tags=["python", "programming", "basics"],
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
                # description_id=exam_description.id,
                # title_id=exam_title.id,
                # course_id=course.id,
                # institution_id=institution.id,
                hash_code=str(hash_object),  # Generate a unique hash code
            )

            # Exams Questions now....................................
            # Create QuestionSet
            question_set = QuestionSet(
                # id=uuid.uuid4(),
                title=QuestionSetTitleEnum.QUESTION_ONE,  # Assuming this is one of the enum values
                slug="python-basics-main-questions",
                # created_at=datetime.utcnow(),
                # updated_at=datetime.utcnow(),
                created_by_id=ADMIN_USER_ID,
            )

            # Create MainQuestions
            main_questions = [
                MainQuestion(
                    # id=uuid.uuid4(),
                    text="Explain the concept of variables in Python and provide examples of different data types.",
                    marks=5,
                    numbering_style="ROMAN",
                    question_number="i",
                    slug="python-variables-and-data-types",
                    question_set_id=question_set.id,
                    # exam_paper_id=exam_paper.id,
                    # created_at=datetime.utcnow(),
                    # updated_at=datetime.utcnow(),
                    created_by_id=ADMIN_USER_ID,
                ),
                MainQuestion(
                    # id=uuid.uuid4(),
                    text="Write a Python function that calculates the factorial of a given number. Explain your code.",
                    marks=15,
                    order_within_question_set="2",
                    slug="python-factorial-function",
                    numbering_style="ROMAN",
                    question_number="ii",
                    question_set_id=question_set.id,
                    # exam_paper_id=exam_paper.id,
                    # created_at=datetime.utcnow(),
                    # updated_at=datetime.utcnow(),
                    created_by_id=ADMIN_USER_ID,
                ),
            ]

            # Create SubQuestions for the second MainQuestion
            sub_questions = [
                SubQuestion(
                    # id=uuid.uuid4(),
                    text="What is recursion and how can it be used to calculate factorial?",
                    marks=5,
                    main_question_id=main_questions[1].id,
                    # created_at=datetime.utcnow(),
                    # updated_at=datetime.utcnow(),
                    created_by_id=ADMIN_USER_ID,
                ),
                SubQuestion(
                    # id=uuid.uuid4(),
                    text="Provide an iterative solution for calculating factorial. Compare it with the recursive approach.",
                    marks=10,
                    main_question_id=main_questions[1].id,
                    # created_at=datetime.utcnow(),
                    # updated_at=datetime.utcnow(),
                    created_by_id=ADMIN_USER_ID,
                ),
            ]

            # --------------------------------------------------------
            # exam_paper.modules.append(module)
            exam_title.exam_papers.append(exam_paper)
            exam_description.exam_papers.append(exam_paper)
            exam_paper.instructions.append(exam_instruction)
            exam_paper.question_sets.append(question_set)
            exam_paper.modules.append(module)

            # Append examPaper to the Course
            course.exam_papers.append(exam_paper)

            # ---------------------------------------------------------
            # Institutions
            institution_create.exam_papers.append(exam_paper)

            department.faculty_id=faculty_create.id
            faculty_create.departments.append(department)

            course.programme_id = programme.id
            programme.courses.append(course)
            department.programmes.append(programme)
            course.modules.append(module)
            institution_create.faculties.append(faculty_create)

            # # Add ExamPaper Id in each MainQuestion---Its required
            # for main_question in main_questions:
            #     main_question.exam_paper_id = exam_paper.id

            # # Add the All Sub Questions to MainQuestion 1.
            # for sub_question in sub_questions:
            #     main_questions[0].subquestions.append(sub_question)

            # # Append the MainQuestions to the QuestionSet
            # for main_question in main_questions:
            #     question_set.main_questions.append(main_question)
            # # TODO
            # # ExamPaper should have a list of all MainQuestions that belong to it

            # ---------------------------------------------------------
            # Questions now

            # ----------------------------------------------------------

            # for main_question in main_questions:
            #     main_question.exam_paper_id = exam_paper.id

            for sub_question in sub_questions:
                main_questions[0].subquestions.append(sub_question)

            for main_question in main_questions:
                question_set.main_questions.append(main_question)

            db.add(institution_create)
            # Commit the MainQuestions and SubQuestions
            await db.commit()
            await db.flush()

            print("Institution & Faculty created.")
            print("Instritution ID:", institution_create.id)
            print("Faculty ID: ", faculty_create.id)
            print("Department ID:", department.id)

            print("Database initialized with dummy data and relationships.")
        else:
            print("Institutions already exist. Skipping database initialization.")
    except Exception as e:
        print(f"An error occurred: {e}")
        await db.rollback()
    finally:
        await db.close()
