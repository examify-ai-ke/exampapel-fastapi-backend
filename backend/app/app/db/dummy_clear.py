# This file only clears all dummy data from the tables,
# It does NOT work in Production Environments.
import os
from app.core.config import settings
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import MetaData, inspect,text
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine


ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


# async def clear_all_tables(session: AsyncSession):
#     if ENVIRONMENT.lower() != "development":
#         print("This function is only available in the development environment.")
#         return

#     metadata = MetaData()

#     # async with SessionLocal() as session:

#     conn = await session.connection()
#     async with session.connection() as conn:
#         await conn.run_sync(metadata.reflect)
#         inspector = await conn.run_sync(inspect)

#         try:
#             # Disable foreign key checks (for PostgreSQL)
#             await session.execute(text("SET session_replication_role = 'replica';"))

#             # Get all table names
#             table_names = await conn.run_sync(inspector.get_table_names)

#             # Delete all records from each table, excluding 'alembic_version'
#             for table_name in table_names:
#                 if table_name != "alembic_version":
#                     await session.execute(
#                         text(f"TRUNCATE TABLE {table_name} CASCADE;")
#                     )
#                     print(f"Cleared all records from {table_name}")
#                 else:
#                     print(f"Skipped clearing {table_name}")

#             # Re-enable foreign key checks (for PostgreSQL)
#             await session.execute(text("SET session_replication_role = 'origin';"))


#             # Commit the changes
#             await session.commit()
#             print(
#                 "All tables (except alembic_version) have been cleared successfully."
#             )
#         except Exception as e:
#             await session.rollback()
#             print(f"An error occurred: {e}")
async def clear_all_tables(session: AsyncSession):
    if ENVIRONMENT.lower() != "development":
        print("This function is only available in the development environment.")
        return

    try:
        # Disable foreign key checks (for PostgreSQL)
        await session.execute(text("SET session_replication_role = 'replica';"))
        
        # Get all table names
        result = await session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public';")
        )
        table_names = [row[0] for row in result]
        
        # Delete all records from each table, excluding 'alembic_version'
        for table_name in table_names:
            if table_name.lower() != "alembic_version":
                await session.execute(
                    text(f'TRUNCATE TABLE "{table_name}" CASCADE;')
                )
                print(f"Cleared all records from {table_name}")
            else:
                print(f"Skipped clearing {table_name}")
        
        # Re-enable foreign key checks (for PostgreSQL)
        await session.execute(text("SET session_replication_role = 'origin';"))
        
        # Commit the changes
        await session.commit()
        print("All tables (except alembic_version) have been cleared successfully.")
    
    except Exception as e:
        await session.rollback()
        print(f"An error occurred: {e}")
        raise  # Re-raise the exception for proper error handling
