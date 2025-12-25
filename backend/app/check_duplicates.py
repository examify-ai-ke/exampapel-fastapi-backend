
import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal

async def main():
    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT title, count(*)
            FROM "QuestionSet"
            GROUP BY title
            HAVING count(*) > 1;
        """))
        duplicates = result.all()
        if duplicates:
            print("Found duplicates:", duplicates)
        else:
            print("No duplicates found.")

if __name__ == "__main__":
    asyncio.run(main())
