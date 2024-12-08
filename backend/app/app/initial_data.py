import asyncio
from app.db.init_db import init_db, init_db_institution
from app.db.session import SessionLocal


async def create_init_data() -> None:
    async with SessionLocal() as session:
        await init_db(session)
        # async with SessionLocal() as db_session:
        await init_db_institution(session)


async def main() -> None:
    await create_init_data()


if __name__ == "__main__":
    asyncio.run(main())
