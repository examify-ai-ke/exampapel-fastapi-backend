from fastapi import APIRouter
from app.api.v1.endpoints import (
    natural_language,
    user,
    hero,
    team,
    login,
    logout,
    role,
    group,
    report,
    periodic_tasks,
    institution,
    faculty,
    department,
    campus,
    programme,
    course,
    module,
    exam_paper,
    instruction,
    exam_description,
    exam_title,
    question_set,
    questions,  # Unified questions endpoint
    answer,
    comment,
    detailed_statistics,
    health,  # Add health endpoints
    audit_logs,  # Add audit logs endpoints
    exam_paper_builder,
    contact,  # Add contact endpoints
)

api_router = APIRouter()

# Health check endpoints (no authentication required)
api_router.include_router(health.router, tags=["health"])

# Contact form endpoint (no authentication required)
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])

api_router.include_router(login.router, prefix="/login", tags=["login"])
api_router.include_router(logout.router, prefix="/logout", tags=["logout"])
api_router.include_router(role.router, prefix="/role", tags=["role"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(group.router, prefix="/group", tags=["group"])
api_router.include_router(team.router, prefix="/team", tags=["team"])
# api_router.include_router(hero.router, prefix="/hero", tags=["hero"])
# api_router.include_router(report.router, prefix="/report", tags=["report"])
# api_router.include_router(
#     natural_language.router, prefix="/natural_language", tags=["natural_language"]
# )
api_router.include_router(detailed_statistics.router, prefix="/report", tags=["detailed-statistics"])
# api_router.include_router(
#     periodic_tasks.router, prefix="/periodic_tasks", tags=["periodic_tasks"]
# )

api_router.include_router(
    institution.router, prefix="/institution", tags=["institution"]
)
api_router.include_router(faculty.router, prefix="/faculty", tags=["faculty"])

api_router.include_router(department.router, prefix="/department", tags=["department"])
api_router.include_router(campus.router, prefix="/campus", tags=["campus"])
api_router.include_router(programme.router, prefix="/programme", tags=["programme"])

api_router.include_router(course.router, prefix="/course", tags=["course"])

api_router.include_router(module.router, prefix="/module", tags=["modules/units"])


api_router.include_router(exam_title.router, prefix="/exam-title", tags=["exam-title"])
api_router.include_router(
    exam_description.router, prefix="/exam-description", tags=["exam-description"]
)
api_router.include_router(instruction.router, prefix="/instruction", tags=["instruction"])
api_router.include_router(exam_paper.router, prefix="/exampaper", tags=["exampaper"])
api_router.include_router(question_set.router, prefix="/question-set", tags=["question-set"])

# Unified questions endpoint
api_router.include_router(
    questions.router, prefix="/questions", tags=["questions"]
)

api_router.include_router(
    answer.router, prefix="/answer", tags=["answer"]
)
api_router.include_router(
    comment.router, prefix="/comment", tags=["comment"]
)

# Audit logs endpoints (admin only)
api_router.include_router(
    audit_logs.router, prefix="/audit-logs", tags=["audit-logs"]
)

api_router.include_router(
    exam_paper_builder.router, prefix="/exam-paper-builder", tags=["exam-paper-builder"]
)
