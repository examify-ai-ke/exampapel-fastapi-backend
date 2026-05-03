import sys
import os
import uuid
from typing import Dict, Any

# Add the backend app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

try:
    from app.models.question_model import Question, NumberingStyleEnum
    from app.utils.slugify_string import generate_slug_for_question_text

    def test_slug_generation():
        exam_paper_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        
        # Test Main Question
        print("Testing Main Question Slug Generation...")
        q1 = Question(
            text={'blocks': [{'data': {'text': 'What is Python?'}}]},
            marks=10,
            numbering_style=NumberingStyleEnum.ROMAN,
            question_number='1',
            exam_paper_id=exam_paper_id
        )
        
        print(f"Slug: {q1.slug}")
        expected_suffix = str(exam_paper_id)[:6]
        if expected_suffix in q1.slug:
            print("✅ SUCCESS: Main Question Slug has exam_paper_id suffix")
        else:
            print(f"❌ FAILURE: Main Question Slug missing suffix. Expected '{expected_suffix}' in '{q1.slug}'")

        # Test Sub Question
        print("\nTesting Sub Question Slug Generation...")
        q2 = Question(
            text={'blocks': [{'data': {'text': 'Explain syntax'}}]},
            marks=5,
            numbering_style=NumberingStyleEnum.ALPHA,
            question_number='a',
            parent_id=parent_id
        )
        
        print(f"Slug: {q2.slug}")
        expected_suffix = str(parent_id)[:6]
        if expected_suffix in q2.slug:
            print("✅ SUCCESS: Sub Question Slug has parent_id suffix")
        else:
            print(f"❌ FAILURE: Sub Question Slug missing suffix. Expected '{expected_suffix}' in '{q2.slug}'")

    if __name__ == "__main__":
        test_slug_generation()
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
