import asyncio
from app.db.init_db import run_init_db 
from app.db.session import SessionLocal
from sqlalchemy import select
from app.models.user_model import User
from app.models.institution_model import Institution


async def create_init_data() -> None:
    """
    Initialize database with sample data only if tables are empty.
    This prevents duplicate data creation on subsequent runs.
    """
    async with SessionLocal() as session:
        # Check if users already exist
        existing_users = await session.execute(select(User))
        users_exist = existing_users.scalars().first() is not None
        
        # Check if institutions already exist
        existing_institutions = await session.execute(select(Institution))
        institutions_exist = existing_institutions.scalars().first() is not None
        
        if users_exist and institutions_exist:
            print("🔍 Database already contains data. Skipping initialization...")
            print("   ✅ Users found in database")
            print("   ✅ Institutions found in database")
            print("   💡 To reinitialize, clear the database first")
            return
        
        if users_exist:
            print("🔍 Users already exist, but institutions missing. Running partial initialization...")
        elif institutions_exist:
            print("🔍 Institutions already exist, but users missing. Running partial initialization...")
        else:
            print("🔍 Empty database detected. Running full initialization...")
        
        await run_init_db(session)

async def main() -> None:
    await create_init_data()


if __name__ == "__main__":
    asyncio.run(main())
