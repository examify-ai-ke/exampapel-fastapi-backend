
import asyncio
from app.db.session import SessionLocal
from app.models.programme_model import Programme
from sqlmodel import select

async def main():
    async with SessionLocal() as session:
        result = await session.execute(select(Programme))
        programmes = result.scalars().all()
        print(f"Found {len(programmes)} programmes:")
        for p in programmes:
            print(f"ID: {p.id}, Name: {p.name} (Type: {type(p.name)}), Slug: {p.slug}")

if __name__ == "__main__":
    asyncio.run(main())
