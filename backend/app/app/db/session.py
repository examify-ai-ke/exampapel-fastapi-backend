# https://stackoverflow.com/questions/75252097/fastapi-testing-runtimeerror-task-attached-to-a-different-loop/75444607#75444607
from sqlalchemy.orm import sessionmaker
from app.core.config import ModeEnum, settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
 
 
DB_POOL_SIZE =100
WEB_CONCURRENCY = 10
POOL_SIZE = max(DB_POOL_SIZE // WEB_CONCURRENCY, 5)

connect_args = {"check_same_thread": False}

# Create engine with proper URL - add default for SQLALCHEMY_ECHO
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=getattr(settings, 'SQLALCHEMY_ECHO', False),  # Use False as default if not defined
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"server_settings": {"application_name": "fastapi_app"}}
)

# Create session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# For backward compatibility - used in deps.py
SessionLocal = async_session

# Database dependency
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

engine_celery = create_async_engine(
    str(settings.DATABASE_URL),  # Use the same database URL for Celery
    echo=False,
    poolclass=NullPool
    if settings.MODE == ModeEnum.testing
    else AsyncAdaptedQueuePool,  # Asincio pytest works with NullPool
    # pool_size=POOL_SIZE,
    # max_overflow=64,
)

SessionLocalCelery = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_celery,
    class_=AsyncSession,
    expire_on_commit=False,
)



 
