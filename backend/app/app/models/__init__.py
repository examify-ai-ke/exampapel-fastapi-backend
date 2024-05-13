from .user_model import User
from .role_model import Role
from .hero_model import Hero
from .team_model import Team
from .group_model import Group
from .media_model import Media
from .image_media_model import ImageMedia
from .user_follow_model import UserFollow

# Custome Models
from .institution_model import Institution
from .faculty_model import (
    Faculty,
    InstitutionFacultyLink,
)
from .department_model import Department
from .programme_model import Programme
from .campus_model import Campus
from .course_model import Course
from .module_model import Module
from .exam_paper_model import (
    ExamPaper,
    ExamInstruction,
    ModuleExamsLink,
    InstructionExamsLink,
    ExamDescription,
    ExamTitle,
    ExamPaperQuestionLink,
)

from .question_model import (
    QuestionSet,
    MainQuestion,
    SubQuestion,
    QuestionBase
)
from .answer_model import AnswerBase, Answer