"""
Script to manually update the AnswerVote foreign key constraint to include CASCADE delete
"""
import asyncio
from sqlalchemy import text
from app.db.session import async_session

async def update_constraint():
    async with async_session() as session:
        # Drop the existing constraint
        await session.execute(text(
            'ALTER TABLE "AnswerVote" DROP CONSTRAINT IF EXISTS "AnswerVote_answer_id_fkey"'
        ))
        
        # Add the constraint with CASCADE delete
        await session.execute(text(
            'ALTER TABLE "AnswerVote" ADD CONSTRAINT "AnswerVote_answer_id_fkey" '
            'FOREIGN KEY (answer_id) REFERENCES "Answer"(id) ON DELETE CASCADE'
        ))
        
        await session.commit()
        print("✅ Successfully updated AnswerVote foreign key constraint with CASCADE delete")

if __name__ == "__main__":
    asyncio.run(update_constraint())
