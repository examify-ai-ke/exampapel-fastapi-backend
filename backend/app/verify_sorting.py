from sqlalchemy import func, select, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Institution(Base):
    __tablename__ = 'institution'
    id = Column(Integer, primary_key=True)
    exam_papers = relationship("ExamPaper", backref='institution')
    created_at = Column(Integer)

class ExamPaper(Base):
    __tablename__ = 'exampaper'
    id = Column(Integer, primary_key=True)
    questions = relationship("Question", back_populates="exam_paper")
    institution_id = Column(Integer, ForeignKey('institution.id'))

class Question(Base):
    __tablename__ = 'question'
    id = Column(Integer, primary_key=True)
    exam_paper_id = Column(Integer, ForeignKey('exampaper.id'))
    exam_paper = relationship("ExamPaper", back_populates="questions")

class Course(Base):
    __tablename__ = 'course'
    id = Column(Integer, primary_key=True)
    exam_papers = relationship("ExamPaper", backref='course')


async def test_sorting():
    print("Testing sorting logic...")
    
    # 1. Verify Exam Paper Sorting by Question Count
    print("\n--- Testing Exam Paper Query Construction ---")
    try:
        query = select(ExamPaper)
        query = query.outerjoin(ExamPaper.questions).group_by(ExamPaper.id)
        sort_field = func.count(Question.id)
        query = query.order_by(sort_field.desc())
        print("Exam Paper SQL:")
        print(query)
        print(" [OK] Exam Paper Q Construction successful")
    except Exception as e:
         print(f" [FAIL] Exam Paper Q Construction failed: {e}")

    # 2. Verify Course Sorting by Exam Paper Count
    print("\n--- Testing Course Query Construction ---")
    try:
        query = select(Course)
        query = query.outerjoin(Course.exam_papers).group_by(Course.id)
        sort_field = func.count(ExamPaper.id)
        query = query.order_by(sort_field.desc())
        print("Course SQL:")
        print(query)
        print(" [OK] Course Q Construction successful")
    except Exception as e:
        print(f" [FAIL] Course Q Construction failed: {e}")

    # 3. Verify Institution Sorting
    print("\n--- Testing Institution Query Construction ---")
    try:
        # Test sort_by="exam_count"
        query_exam = select(Institution)
        query_exam = query_exam.outerjoin(Institution.exam_papers).group_by(Institution.id)
        sort_field = func.count(ExamPaper.id)
        query_exam = query_exam.order_by(sort_field.desc())
        
        print("Institution (Exam Count) SQL:")
        print(query_exam)
        print(" [OK] Institution (Exam Count) Q Construction successful")

        # Test sort_by="question_count"
        query_q = select(Institution)
        query_q = query_q.outerjoin(Institution.exam_papers).outerjoin(ExamPaper.questions).group_by(Institution.id)
        sort_field = func.count(Question.id)
        query_q = query_q.order_by(sort_field.desc())
        
        print("Institution (Question Count) SQL:")
        print(query_q)
        print(" [OK] Institution (Question Count) Q Construction successful")

    except Exception as e:
        print(f" [FAIL] Institution Q Construction failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_sorting())
