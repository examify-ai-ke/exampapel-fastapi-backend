from datetime import date, datetime
import hashlib
from app.models.course_model import Course
from app.models.department_model import Department
from app.models.faculty_model import Faculty
from app.models.image_media_model import ImageMedia
from app.models.institution_model import (
    Institution,
    InstitutionFacultyLink,
    InstitutionCategory,
    InstitutionType,
    Address
)
from app.models.campus_model import Campus
from app.models.media_model import Media
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

from app.schemas.media_schema import IMediaCreate
from app.utils.resize_image import modify_image
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
import json
from pathlib import Path
from uuid import uuid4

from io import BytesIO
from app.utils.minio_client import MinioClient, S3Client
from app.core.config import settings
import requests

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
        # if skip_institutions:
        #     return

        # Check if institutions already exist
        existing_institutions = await db_session.execute(select(Institution))
        if existing_institutions.scalars().first():
            print("Institutions already exist. Skipping institution initialization....")
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

            # Create institution with new fields
            institution = Institution(
                name="University of Technology",
                description="A leading institution in technology education",
                category=InstitutionCategory.UNIVERSITY,
                institution_type=InstitutionType.PUBLIC,

                created_by_id=ADMIN_USER_ID,
                slug="university-of-technology",
                key="UOT001",
                location="Nairobi County",
                kuccps_institution_url="https://kuccps.ac.ke/uot",
                full_profile="The University of Technology is a premier institution dedicated to advancing knowledge in technology fields. Established in 1980, it has grown to become one of the leading institutions in engineering, computer science, and applied technology research. The university is known for its innovative approach to education, combining theoretical learning with practical applications.",
                parent_ministry="Ministry of Education"
            )
            db_session.add(institution)
            await db_session.flush()

            # Create an address for the institution
            institution_address = Address(
                address_line1="123 Education Avenue",
                address_line2="Technology Park",
                county="Nairobi",
                constituency="Central",
                zip_code="00100",
                telephone="+254-20-123456",
                telephone2="+254-20-789012",
                email="address@utech.edu",
                website="https://www.utech.edu",
                country="Kenya",
                institution_id=institution.id
            )
            db_session.add(institution_address)
            await db_session.flush()

            # Create a second institution with different category and type
            institution2 = Institution(
                name="Nairobi Technical College",
                description="A technical college focusing on practical skills",
                category=InstitutionCategory.COLLEGE,
                institution_type=InstitutionType.PRIVATE,
                created_by_id=ADMIN_USER_ID,
                slug="nairobi-technical-college",
                key="NTC001",
                location="Nairobi County",
                kuccps_institution_url="https://kuccps.ac.ke/ntc",
                full_profile="Nairobi Technical College is dedicated to providing hands-on technical training for various industries. The college emphasizes practical skills development alongside theoretical knowledge, ensuring graduates are ready for the workforce.",
                parent_ministry="Ministry of Technical Education"
            )
            db_session.add(institution2)
            await db_session.flush()

            # Create an address for the second institution
            institution2_address = Address(
                address_line1="456 Technical Road",
                address_line2="Industrial Area",
                county="Nairobi",
                constituency="Eastern",
                zip_code="00200",
                telephone="+254-20-345678",
                telephone2="+254-20-890123",
                email="address@ntc.edu",
                website="https://www.ntc.edu",
                country="Kenya",
                institution_id=institution2.id
            )
            db_session.add(institution2_address)
            await db_session.flush()

            # Create a campus for the main institution
            campus = Campus(
                name="Main Campus",
                description="The main campus of University of Technology",
                slug="main-campus",
                institution_id=institution.id,
                created_by_id=ADMIN_USER_ID
            )
            db_session.add(campus)
            await db_session.flush()

            # Create an address for the campus
            campus_address = Address(
                address_line1="789 Education Drive",
                address_line2="University Heights",
                county="Nairobi",
                constituency="Western",
                zip_code="00300",
                telephone="+254-20-567890",
                telephone2="+254-20-901234",
                email="campus@utech.edu",
                website="https://campus.utech.edu",
                country="Kenya",
                campus_id=campus.id
            )
            db_session.add(campus_address)
            await db_session.flush()

            # Create a second campus for the main institution
            campus2 = Campus(
                name="Downtown Campus",
                description="The city center campus of University of Technology",
                slug="downtown-campus",
                institution_id=institution.id,
                created_by_id=ADMIN_USER_ID
            )
            db_session.add(campus2)
            await db_session.flush()

            # Create an address for the second campus
            campus2_address = Address(
                address_line1="100 Central Avenue",
                address_line2="City Center",
                county="Nairobi",
                constituency="Central",
                zip_code="00400",
                telephone="+254-20-678901",
                telephone2="+254-20-012345",
                email="downtown@utech.edu",
                website="https://downtown.utech.edu",
                country="Kenya",
                campus_id=campus2.id
            )
            db_session.add(campus2_address)
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
                slug="bachelors-or-undergraduate", db_session=db_session
            )
            if not programme:
                programme = Programme(
                    name=ProgrammeTypes.BACHELORS,
                    slug="bachelors-or-undergraduate",
                    description="A specific type of undergraduate program, typically lasting 3–4 years (e.g., Bachelor of Arts, Bachelor of Science)",
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

async def import_institutions_from_json(db_session: AsyncSession, json_path: str = "kuccps_institutions_2025-04-26-master-UPDATED.json"):
    """
    Import institutions from a JSON file into the database.
    """
    try:
        with open(json_path, 'r') as f:
            institutions_data = json.load(f)

        current_admin = await crud.user.get_by_email(
            email=settings.FIRST_SUPERUSER_EMAIL, db_session=db_session
        )
        ADMIN_USER_ID = current_admin.id

        insitutions =institutions_data["institutions"]
        print(f"Importing {len(insitutions)} institutions...")

        for idx, inst_data in enumerate(insitutions, 1):
            existing_institution = await db_session.execute(select(Institution).where(Institution.name == inst_data.get("name")))
            if existing_institution.scalars().first():
                print(f"Institution {inst_data.get('name')} already exists. Skipping import.....")
                continue
            # Process logo if available
            # Create an S3Client instance
            s3_client = S3Client(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
                bucket_name=settings.S3_BUCKET_NAME,
            )
            # Process and upload logo
            image_id = None
            if logo_url := inst_data.get("logo"):
                try:
                    # Download image from URL
                    response = requests.get(logo_url, stream=True, verify=False)
                    if response.status_code == 200:
                        image_modified = modify_image(
                            BytesIO(response.content)
                        )
                        # print(image_modified.file_format)
                        # print(image_modified.file_data)
                        # Prepare image data
                        # file_data = BytesIO(response.content)

                        file_name = f"{uuid4()}.png"
                        content_type = response.headers.get('Content-Type', 'image/png')
                        data_file = s3_client.put_object(
                            file_name=file_name,
                            file_data=image_modified.file_data,
                            content_type=content_type,
                        )
                        media = Media(
                            title=f"Logo for {inst_data.get('name', 'Institution')}",
                            description=f"Official logo for {inst_data.get('name', 'Institution')}",
                            path=data_file.url,
                        )
                        # print(media)
                        db_session.add(media)
                        await db_session.flush()
                        # Create ImageMedia record with S3 URL
                        image_media = ImageMedia(
                            media_id=media.id,
                            file_format=image_modified.file_format,
                            width=image_modified.width,
                            height=image_modified.height,
                            # media=media
                        )
                        db_session.add(image_media)
                        await db_session.flush()  
                        image_id = image_media.id
                except Exception as e:
                    print(f"Error uploading logo for {inst_data.get('name')}: {e}")
            # Create institution
            # inst_data=json.loads(_data)
            institution = Institution(
                name=inst_data.get("name", "Unnamed Institution"),
                key=inst_data.get("key", ""),
                description=inst_data.get("short_description", ""),
                category=InstitutionCategory(inst_data.get("category", "OTHER")),
                location=inst_data.get("county", ""),
                kuccps_institution_url=inst_data.get("kuccps_institution_url", ""),
                full_profile=inst_data.get("profile", ""),
                parent_ministry=inst_data.get("parent_ministry", ""),
                tags=inst_data.get("tags", []),
                institution_type=InstitutionType(
                    inst_data.get("institution_type", "OTHER")
                ),
                created_by_id=ADMIN_USER_ID,  # Use admin user
                image_id=image_id,  # Link to logo image
            )

            # Create address from other_info
            other_info = inst_data.get("other_info", {})

            address = Address(
                address_line1=other_info.get("address", ""),
                address_line2=other_info.get("location", ""),
                county=inst_data.get("county", ""),
                constituency=inst_data.get("constituency", ""),
                zip_code=other_info.get("postal_code", ""),
                telephone=other_info.get("telephone", ""),
                telephone2=other_info.get("telephone2", ""),
                email=other_info.get("email", ""),
                website=inst_data.get("website", ""),
                country="Kenya",  # Default to Kenya
                institution=institution,
            )

            db_session.add(institution)
            db_session.add(address)

            if idx % 100 == 0:  # Commit in batches
                await db_session.flush()
                print(f"Processed {idx} institutions...")

        await db_session.commit()
        print("Successfully imported all institutions!")

    except Exception as e:
        await db_session.rollback()
        print(f"Error importing institutions: {e}")
        raise


# This function helps run the init_db function in an async context
async def run_init_db(db_session: AsyncSession):
    """Main async entry point for database initialization"""
    try:
        # Initialize core data
        await init_db(db_session)

        # Import institutions from JSON
        # Get the project root directory
        project_root = Path(__file__).resolve().parent.parent.parent
        # print(project_root)
        json_path = project_root/"kuccps_institutions_2025-04-26-master-UPDATED.json"
        # json_path = Path(
        #     "kuccps_institutions_2025-04-26-master-UPDATED.json"
        # )
        if json_path.exists():
            await import_institutions_from_json(db_session, str(json_path))
        else:
            print(f"JSON file not found at {json_path}, skipping institution import")

    except Exception as e:
        print(f"Initialization failed: {e}")
        raise


# If this script is run directly, initialize the database
# if __name__ == "__main__":
#     run_init_db()
