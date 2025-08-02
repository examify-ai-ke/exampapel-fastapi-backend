"""
Health check endpoints for the FastAPI application.
"""
from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_db
from app.core.startup import is_initialized, get_database_status
from app.core.config import settings
from app.db.session import SessionLocal

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "healthy",
        "message": "ExamPapel API is running",
        "environment": settings.MODE.value,
        "initialized": is_initialized()
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check that includes database connectivity.
    """
    try:
        # Test database connection
        await db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "message": "ExamPapel API detailed health check",
        "environment": settings.MODE.value,
        "initialized": is_initialized(),
        "database": db_status,
        "components": {
            "database": db_status,
            "initialization": "complete" if is_initialized() else "pending"
        }
    }


@router.get("/health/database")
async def database_status_check():
    """
    Comprehensive database status check including table data status.
    """
    db_status = await get_database_status()
    
    # Determine overall health based on database status
    is_healthy = db_status.get("connection_status") == "connected"
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "message": "Database status check",
        **db_status
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes/container orchestration.
    """
    if not is_initialized():
        return {
            "status": "not ready",
            "message": "Application is still initializing",
            "environment": settings.MODE.value
        }, 503
    
    # Check database connection
    try:
        db_status = await get_database_status()
        if db_status.get("connection_status") != "connected":
            return {
                "status": "not ready",
                "message": "Database connection failed",
                "environment": settings.MODE.value,
                "database_error": db_status.get("error")
            }, 503
    except Exception as e:
        return {
            "status": "not ready",
            "message": f"Health check failed: {str(e)}",
            "environment": settings.MODE.value
        }, 503
    
    return {
        "status": "ready",
        "message": "Application is ready to serve requests",
        "environment": settings.MODE.value
    }


@router.get("/live")
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes/container orchestration.
    """
    return {
        "status": "alive",
        "message": "Application is alive",
        "environment": settings.MODE.value
    }
