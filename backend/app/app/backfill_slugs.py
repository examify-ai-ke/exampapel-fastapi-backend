"""
Script to backfill missing slugs for existing records in the database.
Run this once to fix all existing records with NULL slugs.

Usage:
    docker compose -f docker-compose-dev.yml exec fastapi_server python app/backfill_slugs.py
"""

import asyncio
from sqlmodel import select, or_
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import engine
from app.models.institution_model import Institution
from app.models.faculty_model import Faculty
from app.models.department_model import Department
from app.models.course_model import Course
from app.models.programme_model import Programme
from app.models.module_model import Module
from app.models.campus_model import Campus
from app.models.exam_paper_model import ExamPaper
from app.utils.slugify_string import generate_slug


async def backfill_slugs():
    """Backfill missing slugs for all models"""
    
    async with AsyncSession(engine) as session:
        models_to_fix = [
            (Institution, "name"),
            (Faculty, "name"),
            (Department, "name"),
            (Course, "name"),
            (Programme, "name"),
            (Module, "name"),
            (Campus, "name"),
            (ExamPaper, "identifying_name"),
        ]
        
        total_fixed = 0
        
        for model, name_field in models_to_fix:
            print(f"\n🔍 Checking {model.__name__}...")
            
            # Get all records with NULL slug or empty slug
            query = select(model).where(
                or_(model.slug.is_(None), model.slug == "")
            )
            
            # Special handling for ExamPaper - need to load relationships
            if model == ExamPaper:
                query = query.options(
                    selectinload(ExamPaper.title),
                    selectinload(ExamPaper.course),
                    selectinload(ExamPaper.institution),
                )
            
            result = await session.execute(query)
            records = result.scalars().all()
            
            if not records:
                print(f"   ✅ All {model.__name__} records have slugs")
                continue
            
            print(f"   📝 Found {len(records)} records without slugs")
            
            for record in records:
                # Special handling for ExamPaper (uses method)
                if model == ExamPaper:
                    # Generate and save identifying_name
                    record.identifying_name = record.generate_identifying_name()
                    # Use the method which includes hash + date
                    name = record.generate_identifying_name_with_hash()
                    slug = generate_slug(name)
                else:
                    name = getattr(record, name_field)
                    # Special handling for Programme (name is an Enum)
                    if model == Programme and hasattr(name, 'value'):
                        name = name.value
                    slug = generate_slug(name)
                
                record.slug = slug
                session.add(record)
                total_fixed += 1
                
                # Truncate long names for display
                display_name = name[:60] + "..." if len(name) > 60 else name
                display_slug = slug[:60] + "..." if len(slug) > 60 else slug
                print(f"   ✓ Fixed: {display_name} -> {display_slug}")
            
            # Commit after each model
            await session.commit()
            print(f"   ✅ Committed {len(records)} {model.__name__} records")
        
        print(f"\n🎉 Done! Fixed {total_fixed} records in total")


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting slug backfill script...")
    print("=" * 60)
    asyncio.run(backfill_slugs())
    print("=" * 60)
    print("✅ Script completed successfully!")
    print("=" * 60)
