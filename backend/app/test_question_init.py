#!/usr/bin/env python3
"""
Test script to verify Question model initialization.
Run this to test the question creation functionality.
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

from app.db.session import SessionLocal
from app.core.startup import startup_tasks
from sqlmodel import select
from app.models.question_model import Question, QuestionSet
from app.models.user_model import User


async def test_question_initialization():
    """Test the question initialization process."""
    try:
        print("🚀 Starting question initialization test...")
        print("=" * 60)
        
        # Run startup tasks (which includes database initialization)
        await startup_tasks()
        
        print("\n🔍 Testing database connection and querying data...")
        print("-" * 60)
        
        # Test database connection and query questions
        async with SessionLocal() as session:
            # Check users first
            users_result = await session.execute(select(User))
            users = users_result.scalars().all()
            print(f"👥 Found {len(users)} users:")
            for user in users:
                print(f"   - {user.email} ({user.first_name} {user.last_name})")
            
            # Check question sets
            question_sets_result = await session.execute(select(QuestionSet))
            question_sets = question_sets_result.scalars().all()
            print(f"\n📊 Found {len(question_sets)} question sets:")
            
            for qs in question_sets:
                print(f"   - {qs.title.value} (ID: {qs.id})")
            
            # Check questions
            questions_result = await session.execute(select(Question))
            questions = questions_result.scalars().all()
            print(f"\n❓ Found {len(questions)} total questions")
            
            # Separate main questions and sub-questions
            main_questions = [q for q in questions if q.is_main_question]
            sub_questions = [q for q in questions if q.is_sub_question]
            
            print(f"   - Main questions: {len(main_questions)}")
            print(f"   - Sub-questions: {len(sub_questions)}")
            
            # Display question structure
            print(f"\n📝 Question Structure:")
            print("-" * 40)
            
            total_marks = 0
            for main_q in main_questions:
                print(f"\n🔹 Main Question {main_q.question_number}:")
                print(f"   📊 Marks: {main_q.marks}")
                print(f"   🔢 Numbering Style: {main_q.numbering_style.value}")
                print(f"   👥 Created by: {main_q.created_by.email if main_q.created_by else 'Unknown'}")
                print(f"   📋 Sub-questions: {len(main_q.children)}")
                
                total_marks += main_q.marks or 0
                
                for sub_q in main_q.children:
                    print(f"      ↳ Sub-question {sub_q.question_number}: {sub_q.marks} marks")
            
            print(f"\n📊 Summary Statistics:")
            print("-" * 30)
            print(f"   Total Main Questions: {len(main_questions)}")
            print(f"   Total Sub-questions: {len(sub_questions)}")
            print(f"   Total Questions: {len(questions)}")
            print(f"   Total Marks: {total_marks}")
            print(f"   Question Sets: {len(question_sets)}")
        
        print("\n" + "=" * 60)
        print("✅ Question initialization test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_question_initialization())
    sys.exit(0 if success else 1)
