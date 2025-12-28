import asyncio
import os
import sys
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

# Add app to path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.question_model import Question
from app.utils.slugify_string import generate_slug

async def deduplicate_slugs():
    async with SessionLocal() as session:
        print("Checking for duplicate slugs...")
        
        # Find duplicates
        # Group by slug and having count > 1
        query = (
            select(Question.slug, func.count(Question.id))
            .group_by(Question.slug)
            .having(func.count(Question.id) > 1)
        )
        
        duplicates = await session.execute(query)
        duplicate_slugs = [row[0] for row in duplicates.all()]
        
        if not duplicate_slugs:
            print("No duplicates found!")
            return

        print(f"Found {len(duplicate_slugs)} duplicate slugs. Fixing...")
        
        for slug in duplicate_slugs:
            # Get all questions with this slug
            q_query = select(Question).where(Question.slug == slug)
            questions_result = await session.execute(q_query)
            questions = questions_result.scalars().all()
            
            print(f"Fixing slug '{slug}' for {len(questions)} records...")
            
            # Skip the first one (keep it as is), update the rest
            for i, question in enumerate(questions[1:], 1):
                # Update slug using the new logic (append exam_paper_id/parent_id short hash)
                # Or just random/unique suffix if context is missing or to be safe
                
                suffix = str(question.id)[:6]
                if question.exam_paper_id:
                     suffix = str(question.exam_paper_id)[:6]
                elif question.parent_id:
                     suffix = str(question.parent_id)[:6]
                     
                new_slug = f"{slug}-{suffix}"
                
                # Check if this new slug is also taken (unlikely but possible)
                # But to be safe lets use the question ID itself as suffix if we are fixing data
                # Actually previously I said use exam_paper_id... but if multiple questions within same exam have same text...
                # Then they would still collide if I use exam_paper_id suffix.
                # The user's goal is to control duplicates during creation. 
                # For EXISTING duplicates, they are probably distinct questions.
                # Safest unique suffix is the question ID itself.
                
                new_slug = f"{slug}-{str(question.id)[:8]}"
                
                print(f"  Renaming {question.id} -> {new_slug}")
                question.slug = new_slug
                session.add(question)
                
        await session.commit()
        print("Deduplication complete.")

if __name__ == "__main__":
    asyncio.run(deduplicate_slugs())
