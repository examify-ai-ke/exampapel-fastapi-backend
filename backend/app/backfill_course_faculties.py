#!/usr/bin/env python3
"""
Backfill faculty_id for existing courses based on their programme's department's faculty
"""
import asyncio
from sqlmodel import select
from sqlalchemy.orm import selectinload
from app.db.session import SessionLocal
from app.models.course_model import Course
from app.models.programme_model import Programme
from app.models.department_model import Department


async def backfill_course_faculties():
    """Assign faculty to courses based on programme -> department -> faculty relationship"""
    async with SessionLocal() as session:
        # Get all courses without a faculty
        result = await session.execute(
            select(Course)
            .where(Course.faculty_id.is_(None))
            .options(
                selectinload(Course.programme).selectinload(Programme.departments)
            )
        )
        courses = result.scalars().all()
        
        updated_count = 0
        skipped_count = 0
        
        print(f"Found {len(courses)} courses without faculty assignment")
        
        for course in courses:
            if not course.programme:
                print(f"⚠️  Course '{course.name}' has no programme, skipping")
                skipped_count += 1
                continue
            
            # Get the first department of the programme
            if not course.programme.departments:
                print(f"⚠️  Programme '{course.programme.name}' has no departments, skipping course '{course.name}'")
                skipped_count += 1
                continue
            
            # Get the faculty from the first department
            department = course.programme.departments[0]
            
            # Load the department's faculty
            await session.refresh(department, ["faculty"])
            
            if not department.faculty:
                print(f"⚠️  Department '{department.name}' has no faculty, skipping course '{course.name}'")
                skipped_count += 1
                continue
            
            # Assign the faculty to the course
            course.faculty_id = department.faculty.id
            session.add(course)
            updated_count += 1
            print(f"✅ Assigned faculty '{department.faculty.name}' to course '{course.name}'")
        
        # Commit all changes
        await session.commit()
        
        print(f"\n📊 Summary:")
        print(f"   ✅ Updated: {updated_count} courses")
        print(f"   ⚠️  Skipped: {skipped_count} courses")
        print(f"   📝 Total processed: {len(courses)} courses")


if __name__ == "__main__":
    print("🔄 Starting course faculty backfill...\n")
    asyncio.run(backfill_course_faculties())
    print("\n✨ Backfill complete!")
