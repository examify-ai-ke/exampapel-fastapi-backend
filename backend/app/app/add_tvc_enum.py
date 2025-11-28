from sqlalchemy import text
from app.db.session import engine
import asyncio

async def add_tvc_to_enum():
    async with engine.begin() as conn:
        # Add TVC to the enum if it doesn't exist
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'TVC' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'institutioncategory')
                ) THEN
                    ALTER TYPE institutioncategory ADD VALUE 'TVC';
                END IF;
            END$$;
        """))
        print("Successfully added TVC to institutioncategory enum")

if __name__ == "__main__":
    asyncio.run(add_tvc_to_enum())
