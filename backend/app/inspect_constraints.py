
import asyncio
from sqlalchemy import text
from app.db.session import SessionLocal

async def main():
    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT tablename FROM pg_tables WHERE schemaname = 'public';
        """))
        tables = result.scalars().all()
        print("Tables:", tables)

if __name__ == "__main__":
    asyncio.run(main())
