import asyncio
import os
from app.db.dummy_clear import clear_all_tables
from app.db.session import SessionLocal
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

async def main():
    if ENVIRONMENT.lower() == "development":
        confirm = input(
            "Are you sure you want to clear all tables (except alembic_version)? This action cannot be undone. (y/n): "
        )
        if confirm.lower() == "y":
            async with SessionLocal() as session:
                await clear_all_tables(session)
        else:
            print("Operation cancelled.")
    else:
        print("This script is only available in the development environment.")


if __name__ == "__main__":
    asyncio.run(main())
