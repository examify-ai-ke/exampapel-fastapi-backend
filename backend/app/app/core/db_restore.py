"""
Database restore utilities for initializing database from backup files.
This module handles automatic database restoration from backup dumps on first run.
"""
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


async def is_database_empty(session: AsyncSession) -> bool:
    """
    Check if the database is completely empty (no tables at all).
    
    Returns:
        bool: True if database has no tables, False if tables exist
    """
    try:
        # Check if any user tables exist in the public schema
        query = text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            AND table_name NOT LIKE 'pg_%';
        """)
        
        result = await session.execute(query)
        table_count = result.scalar()
        
        logger.info(f"Database table count: {table_count}")
        return table_count == 0
        
    except Exception as e:
        logger.error(f"Error checking if database is empty: {e}")
        # If we can't check, assume it's not empty to be safe
        return False


async def get_table_counts(session: AsyncSession) -> dict[str, int]:
    """
    Get row counts for all tables in the database.
    
    Returns:
        dict: Dictionary with table names as keys and row counts as values
    """
    try:
        # Get all table names
        query = text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename NOT LIKE 'pg_%';
        """)
        
        result = await session.execute(query)
        tables = [row[0] for row in result.fetchall()]
        
        table_counts = {}
        for table in tables:
            count_query = text(f'SELECT COUNT(*) FROM "{table}"')
            count_result = await session.execute(count_query)
            table_counts[table] = count_result.scalar()
        
        return table_counts
        
    except Exception as e:
        logger.error(f"Error getting table counts: {e}")
        return {}


def find_backup_file() -> Optional[Path]:
    """
    Find the database backup file to use for initialization.
    Looks in the project root directory and /code for the clean backup file.
    
    Returns:
        Optional[Path]: Path to the backup file, or None if not found
    """
    # Get project root (4 levels up from this file)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent.parent
    
    # For Docker deployments, also check /code directory
    code_dir = Path("/code")
    
    # Look for the clean backup file (custom format preferred)
    backup_candidates = [
        # Docker deployment locations (checked first)
        code_dir / "exams_fastapi_db_clean_backup.dump",
        code_dir / "exams_fastapi_db_clean_backup.sql",
        # Local development locations
        project_root / "exams_fastapi_db_clean_backup.dump",
        project_root / "exams_fastapi_db_clean_backup.sql",
        project_root / "backups" / "latest.dump",
        project_root / "backups" / "latest.sql",
    ]
    
    for backup_path in backup_candidates:
        if backup_path.exists():
            logger.info(f"Found backup file: {backup_path}")
            return backup_path
    
    logger.warning("No backup file found in project root or /code directory")
    return None


def restore_from_backup(backup_file: Path) -> bool:
    """
    Restore database from backup file using pg_restore or psql.
    
    Args:
        backup_file: Path to the backup file
        
    Returns:
        bool: True if restore was successful, False otherwise
    """
    try:
        # Determine which tool to use based on file extension
        is_custom_format = backup_file.suffix == ".dump"
        
        # Connection parameters from settings
        db_host = os.getenv("DATABASE_HOST", "localhost")
        db_port = os.getenv("DATABASE_PORT", "5432")
        db_user = os.getenv("DATABASE_USER", "postgres")
        db_password = os.getenv("DATABASE_PASSWORD", "")
        db_name = os.getenv("DATABASE_NAME", "exams_fastapi_db")
        
        # Set PGPASSWORD environment variable for authentication
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        logger.info(f"Restoring database from: {backup_file}")
        logger.info(f"Database: {db_name} at {db_host}:{db_port}")
        
        if is_custom_format:
            # Use pg_restore for custom format (.dump)
            cmd = [
                "pg_restore",
                "-h", db_host,
                "-p", db_port,
                "-U", db_user,
                "-d", db_name,
                "-v",  # Verbose
                str(backup_file)
            ]
        else:
            # Use psql for SQL format (.sql)
            cmd = [
                "psql",
                "-h", db_host,
                "-p", db_port,
                "-U", db_user,
                "-d", db_name,
                "-f", str(backup_file)
            ]
        
        logger.info(f"Executing: {' '.join(cmd)}")
        
        # Run the restore command
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✅ Database restore completed successfully!")
            return True
        else:
            logger.error(f"❌ Database restore failed with return code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
            return False
            
    except FileNotFoundError:
        logger.error("pg_restore or psql command not found. Make sure PostgreSQL client tools are installed.")
        return False
    except Exception as e:
        logger.error(f"Error restoring database from backup: {e}")
        return False


async def initialize_from_backup() -> bool:
    """
    Initialize the database from a backup file if the database is empty.
    This is the main function called during application startup.
    
    Returns:
        bool: True if initialization was performed and successful, False otherwise
    """
    try:
        logger.info("🔍 Checking if database needs initialization from backup...")
        
        async with SessionLocal() as session:
            # Check if database is empty
            if not await is_database_empty(session):
                logger.info("📊 Database already has tables - skipping backup restore")
                
                # Log current state for debugging
                table_counts = await get_table_counts(session)
                total_records = sum(table_counts.values())
                logger.info(f"Database contains {len(table_counts)} tables with {total_records} total records")
                
                return False
        
        logger.info("🆕 Database is empty - will attempt to restore from backup")
        
        # Find backup file
        backup_file = find_backup_file()
        if not backup_file:
            logger.warning("⚠️  No backup file found - database will remain empty")
            logger.info("💡 To initialize with data, place backup file in project root:")
            logger.info("   - exams_fastapi_db_clean_backup.dump (preferred)")
            logger.info("   - exams_fastapi_db_clean_backup.sql")
            return False
        
        # Restore from backup
        logger.info(f"📦 Restoring database from: {backup_file.name}")
        success = restore_from_backup(backup_file)
        
        if success:
            # Verify restoration
            async with SessionLocal() as session:
                table_counts = await get_table_counts(session)
                total_records = sum(table_counts.values())
                
                logger.info("✅ Database initialization completed successfully!")
                logger.info(f"📊 Restored {len(table_counts)} tables with {total_records} total records")
                
                # Log top tables by record count
                sorted_tables = sorted(table_counts.items(), key=lambda x: x[1], reverse=True)
                logger.info("Top tables by record count:")
                for table, count in sorted_tables[:10]:
                    if count > 0:
                        logger.info(f"  - {table}: {count} records")
        else:
            logger.error("❌ Database initialization from backup failed")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error during database initialization from backup: {e}")
        return False
