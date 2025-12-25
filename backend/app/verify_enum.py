
import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal

async def main():
    async with SessionLocal() as session:
        # Check for old values
        result_old = await session.execute(text("""
            SELECT numbering_style, count(*)
            FROM "Question"
            WHERE numbering_style IN ('alpha', 'numerical')
            GROUP BY numbering_style;
        """))
        old_counts = result_old.all()
        
        # Check for new values
        result_total = await session.execute(text("""
            SELECT count(*) FROM "Question";
        """))
        total_count = result_total.scalar()
        print(f"Total Questions: {total_count}")
        
        result_new = await session.execute(text("""
            SELECT numbering_style, count(*)
            FROM "Question"
            WHERE numbering_style IN ('alphabetic', 'numeric')
            GROUP BY numbering_style;
        """))
        new_counts = result_new.all()
        
        result_all = await session.execute(text("""
            SELECT numbering_style, count(*)
            FROM "Question"
            GROUP BY numbering_style;
        """))
        all_counts = result_all.all()
        print("All Values:", all_counts)

if __name__ == "__main__":
    asyncio.run(main())
