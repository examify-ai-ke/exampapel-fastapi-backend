"""
Script to fix Media paths that contain full URLs instead of just object keys
"""
import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import SessionLocal
from app.models.media_model import Media
import re


async def fix_media_paths():
    """Fix media paths that contain full presigned URLs"""
    async with SessionLocal() as session:
        # Get all media records
        result = await session.execute(select(Media))
        media_records = result.scalars().all()
        
        fixed_count = 0
        for media in media_records:
            if media.path and "https://" in media.path:
                # Extract just the object key from the URL
                # Pattern: https://bucket.s3.amazonaws.com/OBJECT_KEY?params
                match = re.search(r'amazonaws\.com/([^?]+)', media.path)
                if match:
                    object_key = match.group(1)
                    # Decode URL encoding if present
                    import urllib.parse
                    object_key = urllib.parse.unquote(object_key)
                    
                    print(f"Fixing media {media.id}")
                    print(f"  Old path: {media.path[:100]}...")
                    print(f"  New path: {object_key}")
                    
                    media.path = object_key
                    session.add(media)
                    fixed_count += 1
        
        if fixed_count > 0:
            await session.commit()
            print(f"\n✅ Fixed {fixed_count} media records")
        else:
            print("✅ No media records need fixing")


if __name__ == "__main__":
    asyncio.run(fix_media_paths())
