"""
Startup initialization functions for FastAPI application.
This module handles database initialization and other startup tasks.
"""
import asyncio
import logging
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import select, text

from app.core.config import settings, ModeEnum
from app.core.db_restore import initialize_from_backup
from app.db.init_db import run_init_db
from app.db.session import SessionLocal
from app.models.user_model import User
from app.models.institution_model import Institution
from app.models.question_model import Question, QuestionSet
from app.models.role_model import Role

logger = logging.getLogger(__name__)


async def check_database_has_data(session: AsyncSession) -> dict[str, bool]:
    """
    Check if the database has any data in key tables.
    
    Returns:
        dict: Dictionary with table names as keys and boolean values indicating if data exists
    """
    tables_to_check = {
        "users": User,
        "roles": Role,
        "institutions": Institution,
        "questions": Question,
        "question_sets": QuestionSet,
    }
    
    data_status = {}
    
    for table_name, model in tables_to_check.items():
        try:
            result = await session.execute(select(model).limit(1))
            has_data = result.scalars().first() is not None
            data_status[table_name] = has_data
            logger.debug(f"Table '{table_name}': {'has data' if has_data else 'empty'}")
        except Exception as e:
            logger.warning(f"Could not check table '{table_name}': {e}")
            data_status[table_name] = False
    
    return data_status


async def should_initialize_database() -> bool:
    """
    Determine if database initialization should run based on:
    1. Current environment mode
    2. Database state (empty or has data)
    
    Returns:
        bool: True if initialization should run, False otherwise
    """
    # Check if we're in development mode
    is_development = settings.MODE == ModeEnum.development
    
    if not is_development:
        logger.info(f"Skipping database initialization - not in development mode (current: {settings.MODE.value})")
        return False
    
    logger.info("Development mode detected - checking database state...")
    
    try:
        async with SessionLocal() as session:
            # Check if database has data
            data_status = await check_database_has_data(session)
            
            # Log current database state
            total_tables = len(data_status)
            tables_with_data = sum(1 for has_data in data_status.values() if has_data)
            
            logger.info(f"Database state: {tables_with_data}/{total_tables} tables have data")
            for table_name, has_data in data_status.items():
                status = "✅ HAS DATA" if has_data else "❌ EMPTY"
                logger.info(f"  - {table_name}: {status}")
            
            # Only initialize if ALL key tables are empty
            should_init = not any(data_status.values())
            
            if should_init:
                logger.info("🆕 Database is empty - initialization will proceed")
            else:
                logger.info("📊 Database has data - skipping initialization to prevent duplicates")
                logger.info("💡 To force re-initialization, clear the database first")
            
            return should_init
            
    except Exception as e:
        logger.error(f"Error checking database state: {e}")
        logger.warning("Assuming database needs initialization due to check failure")
        return True


async def initialize_database() -> None:
    """
    Initialize the database with initial data if needed.
    This function is called during FastAPI startup.
    
    Initialization process:
    1. First, attempt to restore from backup file if database is completely empty
    2. If backup restore succeeds, initialization is complete
    3. If no backup or restore fails, fall back to normal initialization (if configured)
    
    Only runs if:
    - We're in development mode
    - The database is empty (no tables or no data in key tables)
    """
    try:
        logger.info("🚀 Starting database initialization check...")
        
        # STEP 1: Try to initialize from backup file first
        # This only runs if database is completely empty (no tables)
        logger.info("📦 Step 1: Checking for database backup file...")
        backup_restored = await initialize_from_backup()
        
        if backup_restored:
            logger.info("✅ Database initialized successfully from backup file!")
            logger.info("⏭️  Skipping normal initialization since backup was restored")
            return
        
        # STEP 2: If no backup or backup failed, check if we should run normal initialization
        logger.info("📝 Step 2: Checking if normal initialization is needed...")
        
        # Check if we should initialize
        if not await should_initialize_database():
            logger.info("⏭️  Database initialization skipped")
            return
        
        logger.info("🔧 Proceeding with normal database initialization...")
        
        # We no longer need to initialize the db with data here
        # You can enable this if you have a run_init_db function
        # async with SessionLocal() as session:
        #     await run_init_db(session)
            
        logger.info("✅ Database initialization completed successfully!")
        
        # Log final state
        async with SessionLocal() as session:
            data_status = await check_database_has_data(session)
            tables_with_data = sum(1 for has_data in data_status.values() if has_data)
            logger.info(f"📊 Final state: {tables_with_data}/{len(data_status)} tables now have data")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # In production, you might want to raise the exception to prevent startup
        # For development, we'll log the error and continue
        if settings.MODE == ModeEnum.production:
            raise
        else:
            logger.warning("⚠️  Continuing startup despite database initialization failure (development mode)")


async def check_database_connection() -> bool:
    """
    Check if the database connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        async with SessionLocal() as session:
            # Simple query to test connection
            await session.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


async def startup_tasks() -> None:
    """
    Run all startup tasks for the FastAPI application.
    Add any additional startup tasks here.
    """
    try:
        logger.info("🚀 Starting FastAPI application startup tasks...")
        logger.info(f"🔧 Environment: {settings.MODE.value}")
        
        # Check database connection first
        if not await check_database_connection():
            raise Exception("Database connection failed")
        
        # Initialize database (with smart checks)
        await initialize_database()
        
        # Add other startup tasks here as needed
        # await initialize_cache()
        # await setup_background_tasks()
        
        logger.info("🎉 All startup tasks completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Startup tasks failed: {e}")
        raise


def run_startup_sync() -> None:
    """
    Synchronous wrapper for startup tasks.
    Use this if you need to run startup tasks from a synchronous context.
    """
    asyncio.run(startup_tasks())


# Optional: Create a flag to track if initialization has been completed
_initialization_complete = False


async def ensure_initialized() -> None:
    """
    Ensure that initialization has been completed.
    This can be called from endpoints that require the database to be initialized.
    """
    global _initialization_complete
    
    if not _initialization_complete:
        await startup_tasks()
        _initialization_complete = True


def is_initialized() -> bool:
    """
    Check if the application has been initialized.
    """
    return _initialization_complete


def mark_initialized() -> None:
    """
    Mark the application as initialized.
    """
    global _initialization_complete
    _initialization_complete = True


async def get_database_status() -> dict:
    """
    Get detailed database status information.
    Useful for health checks and debugging.
    
    Returns:
        dict: Database status information
    """
    try:
        async with SessionLocal() as session:
            data_status = await check_database_has_data(session)
            
            # Count total records in each table
            record_counts = {}
            for table_name, model in {
                "users": User,
                "roles": Role,
                "institutions": Institution,
                "questions": Question,
                "question_sets": QuestionSet,
            }.items():
                try:
                    result = await session.execute(select(model))
                    count = len(result.scalars().all())
                    record_counts[table_name] = count
                except Exception as e:
                    logger.warning(f"Could not count records in '{table_name}': {e}")
                    record_counts[table_name] = 0
            
            return {
                "connection_status": "connected",
                "environment": settings.MODE.value,
                "tables_with_data": data_status,
                "record_counts": record_counts,
                "total_tables_checked": len(data_status),
                "tables_with_data_count": sum(1 for has_data in data_status.values() if has_data),
                "initialization_complete": _initialization_complete,
            }
            
    except Exception as e:
        return {
            "connection_status": "failed",
            "error": str(e),
            "environment": settings.MODE.value,
            "initialization_complete": _initialization_complete,
        }
