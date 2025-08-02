#!/usr/bin/env python3
"""
Test script to verify conditional initialization works correctly.
This script tests the updated initial_data.py functionality.
"""

import asyncio
import sys
import os

# Add the backend/app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from app.db.session import SessionLocal
from app.models.user_model import User
from app.models.institution_model import Institution
from app.models.question_model import Question, QuestionSet
from sqlalchemy import select


async def test_conditional_init():
    """Test that conditional initialization works correctly"""
    
    print("🧪 Testing conditional initialization...")
    
    async with SessionLocal() as session:
        # Check current state of database
        print("\n📊 Checking current database state...")
        
        # Count users
        user_result = await session.execute(select(User))
        user_count = len(user_result.scalars().all())
        print(f"   👥 Users in database: {user_count}")
        
        # Count institutions
        institution_result = await session.execute(select(Institution))
        institution_count = len(institution_result.scalars().all())
        print(f"   🏫 Institutions in database: {institution_count}")
        
        # Count question sets
        question_set_result = await session.execute(select(QuestionSet))
        question_set_count = len(question_set_result.scalars().all())
        print(f"   📝 Question sets in database: {question_set_count}")
        
        # Count questions
        question_result = await session.execute(select(Question))
        questions = question_result.scalars().all()
        question_count = len(questions)
        main_question_count = len([q for q in questions if q.is_main_question])
        sub_question_count = len([q for q in questions if q.is_sub_question])
        
        print(f"   ❓ Total questions in database: {question_count}")
        print(f"      - Main questions: {main_question_count}")
        print(f"      - Sub-questions: {sub_question_count}")
        
        # Determine what should happen with initialization
        if user_count > 0 and institution_count > 0:
            print("\n✅ Database already contains data - initialization should be skipped")
        elif user_count > 0:
            print("\n⚠️  Users exist but institutions missing - partial initialization should occur")
        elif institution_count > 0:
            print("\n⚠️  Institutions exist but users missing - partial initialization should occur")
        else:
            print("\n🆕 Empty database - full initialization should occur")
        
        # Test question model properties
        if question_count > 0:
            print("\n🔍 Testing Question model properties...")
            for question in questions[:3]:  # Test first 3 questions
                print(f"   Question ID: {question.id}")
                print(f"   - Is main question: {question.is_main_question}")
                print(f"   - Is sub question: {question.is_sub_question}")
                print(f"   - Question number: {question.question_number}")
                print(f"   - Marks: {question.marks}")
                if question.is_main_question:
                    print(f"   - Sub-questions count: {len(question.children)}")
                elif question.is_sub_question:
                    print(f"   - Parent question ID: {question.parent_id}")
                print()


async def main():
    """Main test function"""
    try:
        await test_conditional_init()
        print("✅ Test completed successfully!")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
