#!/usr/bin/env python3
"""
Test script to verify the questions endpoint works correctly after fixing the ResponseValidationError.
"""

import asyncio
import sys
import os

# Add the backend/app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from app.db.session import SessionLocal
from app.models.question_model import Question
from app.schemas.question_schema import QuestionRead
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import ValidationError


async def test_question_serialization():
    """Test that Question model can be serialized to QuestionRead schema"""
    
    print("🧪 Testing Question model serialization...")
    
    async with SessionLocal() as session:
        # Get a few questions from the database
        query = (
            select(Question)
            .options(
                selectinload(Question.question_set),
                selectinload(Question.exam_paper),
                selectinload(Question.parent),
                selectinload(Question.children).selectinload(Question.answers),
                selectinload(Question.answers),
                selectinload(Question.created_by),
            )
            .limit(3)
        )
        
        result = await session.execute(query)
        questions = result.unique().scalars().all()
        
        if not questions:
            print("   ⚠️  No questions found in database. Run initialization first.")
            return False
        
        print(f"   📊 Found {len(questions)} questions to test")
        
        # Test serialization of each question
        for i, question in enumerate(questions, 1):
            try:
                print(f"\n   🔍 Testing Question {i}:")
                print(f"      - ID: {question.id}")
                print(f"      - Type: {'Main' if question.is_main_question else 'Sub' if question.is_sub_question else 'Unknown'}")
                print(f"      - Question Number: {question.question_number}")
                print(f"      - Marks: {question.marks}")
                print(f"      - Children Count: {len(question.children) if question.children else 0}")
                
                # Try to serialize to QuestionRead schema
                question_read = QuestionRead.model_validate(question)
                
                print(f"      ✅ Serialization successful")
                print(f"         - Schema ID: {question_read.id}")
                print(f"         - Schema is_main_question: {question_read.is_main_question}")
                print(f"         - Schema is_sub_question: {question_read.is_sub_question}")
                
            except ValidationError as e:
                print(f"      ❌ Validation error: {e}")
                return False
            except Exception as e:
                print(f"      ❌ Unexpected error: {e}")
                return False
        
        print("\n   ✅ All questions serialized successfully!")
        return True


async def test_question_properties():
    """Test that question properties work correctly"""
    
    print("\n🔧 Testing Question model properties...")
    
    async with SessionLocal() as session:
        # Get questions with different types
        query = select(Question).limit(5)
        result = await session.execute(query)
        questions = result.scalars().all()
        
        if not questions:
            print("   ⚠️  No questions found in database.")
            return False
        
        main_questions = []
        sub_questions = []
        
        for question in questions:
            if question.is_main_question:
                main_questions.append(question)
            elif question.is_sub_question:
                sub_questions.append(question)
        
        print(f"   📊 Found {len(main_questions)} main questions and {len(sub_questions)} sub-questions")
        
        # Test main question properties
        if main_questions:
            main_q = main_questions[0]
            print(f"\n   🔍 Testing Main Question:")
            print(f"      - question_set_id: {main_q.question_set_id}")
            print(f"      - exam_paper_id: {main_q.exam_paper_id}")
            print(f"      - parent_id: {main_q.parent_id}")
            print(f"      - is_main_question: {main_q.is_main_question}")
            print(f"      - is_sub_question: {main_q.is_sub_question}")
            
            if main_q.is_main_question and not main_q.is_sub_question:
                print("      ✅ Main question properties correct")
            else:
                print("      ❌ Main question properties incorrect")
                return False
        
        # Test sub-question properties
        if sub_questions:
            sub_q = sub_questions[0]
            print(f"\n   🔍 Testing Sub-Question:")
            print(f"      - question_set_id: {sub_q.question_set_id}")
            print(f"      - exam_paper_id: {sub_q.exam_paper_id}")
            print(f"      - parent_id: {sub_q.parent_id}")
            print(f"      - is_main_question: {sub_q.is_main_question}")
            print(f"      - is_sub_question: {sub_q.is_sub_question}")
            
            if sub_q.is_sub_question and not sub_q.is_main_question:
                print("      ✅ Sub-question properties correct")
            else:
                print("      ❌ Sub-question properties incorrect")
                return False
        
        return True


async def main():
    """Main test function"""
    print("🧪 Questions Endpoint Validation Test")
    print("=" * 40)
    
    try:
        # Test question serialization
        serialization_ok = await test_question_serialization()
        
        # Test question properties
        properties_ok = await test_question_properties()
        
        # Summary
        print("\n" + "=" * 40)
        print("📊 TEST SUMMARY")
        print("=" * 40)
        
        if serialization_ok and properties_ok:
            print("✅ All tests passed!")
            print("   The questions endpoint should work correctly now.")
            print("   Try accessing: GET /questions")
            return 0
        else:
            print("❌ Some tests failed!")
            print("   There may still be issues with the questions endpoint.")
            return 1
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
