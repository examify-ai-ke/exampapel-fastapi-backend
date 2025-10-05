import gc
import logging
import os
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    FastAPI,
    HTTPException,
    Path,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi_async_sqlalchemy import SQLAlchemyMiddleware, db
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import WebSocketRateLimiter
from jwt import DecodeError, ExpiredSignatureError, MissingRequiredClaimError
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from fastapi_cache.backends.inmemory import InMemoryBackend


from app import crud
from app.api.deps import get_redis_client
from app.api.v1.api import api_router as api_router_v1


# Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy (updated to allow Swagger UI CDN resources)
        # Note: This CSP allows external resources needed for FastAPI documentation:
        # - cdn.jsdelivr.net: For Swagger UI and ReDoc assets
        # - unpkg.com: Alternative CDN for documentation assets
        # - fonts.googleapis.com & fonts.gstatic.com: For web fonts used by documentation
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https: https://fonts.gstatic.com; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (only for HTTPS in production)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
from app.core.config import ModeEnum, settings
from app.core.security import decode_token
from app.core.startup import startup_tasks, mark_initialized
from app.schemas.common_schema import IChatResponse, IUserMessage
from app.utils.fastapi_globals import GlobalsMiddleware, g
from app.utils.uuid6 import uuid7
# from transformers import pipeline
from app.health import router as health_router
# from transformers import pipeline
from fastapi_pagination import add_pagination, pagination_ctx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add these settings at the top of the file
# Configure Hugging Face to use a persistent cache directory
# os.environ["TRANSFORMERS_CACHE"] = "/code/models"
# LOAD_ML_MODELS = os.environ.get("LOAD_ML_MODELS", "true").lower() == "true"

# # Create a dummy sentiment model for when ML is disabled
# class DummySentimentModel:
#     def __call__(self, texts):
#         return [{"label": "POSITIVE", "score": 0.9} for _ in texts]


async def user_id_identifier(request: Request):
    if request.scope["type"] == "http":
        # Retrieve the Authorization header from the request
        auth_header = request.headers.get("Authorization")

        if auth_header is not None:
            # Check that the header is in the correct format
            header_parts = auth_header.split()
            if len(header_parts) == 2 and header_parts[0].lower() == "bearer":
                token = header_parts[1]
                try:
                    payload = decode_token(token)
                except ExpiredSignatureError:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Your token has expired. Please log in again.",
                    )
                except DecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Error when decoding the token. Please check your request.",
                    )
                except MissingRequiredClaimError:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="There is no required field in your token. Please contact the administrator.",
                    )

                user_id = payload["sub"]

                return user_id

    if request.scope["type"] == "websocket":
        return request.scope["path"]

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]

    client = request.client
    ip = getattr(client, "host", "0.0.0.0")
    return ip + ":" + request.scope["path"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI application...")
    
    # Initialize Redis and caching
    redis_client = await get_redis_client()
    
    # Only enable cache if ENABLE_REDIS_CACHE is True
    if settings.ENABLE_REDIS_CACHE:
        FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
        logger.info("✅ Redis cache ENABLED - responses will be cached")
    else:
        # Initialize with a dummy backend that doesn't cache
        
        # FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache", expire=0.1) # Very short expiry
        logger.info("❌ Redis cache DISABLED - no caching (development mode)")
    
    await FastAPILimiter.init(redis_client, identifier=user_id_identifier)

    # Load a pre-trained sentiment analysis model as a dictionary to an easy cleanup
    # models: dict[str, Any] = {
    #     "sentiment_model": pipeline(
    #         "sentiment-analysis",
    #         model="distilbert-base-uncased-finetuned-sst-2-english",
    #     ),
    # }
    # g.set_default("sentiment_model", models["sentiment_model"])
    
    # Initialize database and run startup tasks
    try:
        await startup_tasks()
        mark_initialized()
        logger.info(f"FastAPI startup completed successfully! Cache: {'ENABLED' if settings.ENABLE_REDIS_CACHE else 'DISABLED'}")
    except Exception as e:
        logger.error(f"FastAPI startup failed: {e}")
        # In production, you might want to prevent startup on failure
        if settings.MODE.value == "production":
            raise
        else:
            logger.warning("Continuing startup despite initialization failure (development mode)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down FastAPI application...")
    if settings.ENABLE_REDIS_CACHE:
        await FastAPICache.clear()
    await FastAPILimiter.close()
    # models.clear()
    g.cleanup()
    gc.collect()
    logger.info("FastAPI shutdown completed!")


# Core Application Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="""
## Examify API - Comprehensive PastExam Papers Management System

**Examify** is a modern, async FastAPI-based past exam papers management system designed to streamline the organization, storage, and access to historical examination materials for educational institutions.

### 🎯 **Key Features**

* **📚 Past Exam Papers Repository**: Comprehensive storage and management of historical exam papers
* **🔍 Advanced Search & Filtering**: Find past papers by institution, course, year, semester, and more
* **🏫 Multi-Institution Support**: Manage exam papers across multiple educational institutions
* **👥 Role-Based Access Control**: Secure access with Admin, Manager, and User permissions
* **📊 Analytics & Insights**: Track usage patterns and popular exam papers
* **🔐 Secure Authentication**: JWT-based authentication with refresh token support
* **⚡ High-Performance Operations**: Async database operations for optimal performance
* **📈 Real-time Features**: WebSocket support for live updates and notifications
* **🔄 Background Processing**: Automated tasks for paper processing and indexing

### 🏗️ **System Architecture**

* **Backend Framework**: FastAPI with Python 3.10+
* **Database**: PostgreSQL with async SQLModel ORM
* **Caching Layer**: Redis for high-performance data access
* **Task Queue**: Celery with Redis broker for background jobs
* **Authentication**: JWT tokens with role-based permissions
* **Documentation**: Auto-generated OpenAPI 3.0 specification

### 🚀 **Getting Started**

1. **🔐 Authentication**: Use the `/login` endpoint to obtain your access tokens
2. **📖 Explore**: Browse available endpoints in this interactive documentation
3. **🧪 Test**: Use the "Try it out" feature to test API endpoints directly
4. **📚 Access Papers**: Start exploring the vast collection of past exam papers

### 📋 **Main Endpoint Categories**

* **🔐 Authentication**: Login, logout, and token management
* **👤 User Management**: User profiles, roles, and permissions
* **🏫 Institution Management**: Educational institutions and their structure
* **📚 Past Papers**: Exam paper storage, retrieval, and management
* **🔍 Search & Discovery**: Advanced search and filtering capabilities
* **📊 Analytics**: Usage statistics and performance metrics
* **⚙️ System Health**: Monitoring and health check endpoints

### 📖 **Use Cases**

* **Students**: Access past exam papers for study and preparation
* **Educators**: Upload and manage historical exam materials
* **Administrators**: Oversee institutional exam paper repositories
* **Researchers**: Analyze examination trends and patterns over time

### 🔗 **External Resources**

* [FastAPI Documentation](https://fastapi.tiangolo.com/)
* [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
* [Pydantic V2 Documentation](https://docs.pydantic.dev/2.5/)

---
*Built with ❤️ using FastAPI, SQLModel, and modern Python async patterns for educational excellence*
    """,
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "Examify Development Team",
        "email": "support@examify.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://fastapi.localhost",
            "description": "Development server"
        },
        {
            "url": "https://api.examify.com",
            "description": "Production server"
        }
    ],
    tags_metadata=[
        {
            "name": "health",
            "description": "System health and monitoring endpoints"
        },
        {
            "name": "login",
            "description": "User authentication and login operations"
        },
        {
            "name": "logout",
            "description": "User logout and token invalidation"
        },
        {
            "name": "user",
            "description": "User management and profile operations"
        },
        {
            "name": "role",
            "description": "Role and permission management"
        },
        {
            "name": "group",
            "description": "User group management"
        },
        {
            "name": "institution",
            "description": "Educational institution management"
        },
        {
            "name": "faculty",
            "description": "Faculty and department structure management"
        },
        {
            "name": "department",
            "description": "Academic department management"
        },
        {
            "name": "programme",
            "description": "Academic programme and degree management"
        },
        {
            "name": "course",
            "description": "Course and curriculum management"
        },
        {
            "name": "modules/units",
            "description": "Course modules and unit management"
        },
        {
            "name": "exampaper",
            "description": "Past exam paper storage and management"
        },
        {
            "name": "exam-title",
            "description": "Exam paper titles and metadata management"
        },
        {
            "name": "exam-description",
            "description": "Exam paper descriptions and details"
        },
        {
            "name": "instruction",
            "description": "Exam instruction and guideline management"
        },
        {
            "name": "question-set",
            "description": "Question set organization and grouping"
        },
        {
            "name": "questions",
            "description": "Question management and categorization"
        },
        {
            "name": "detailed-statistics",
            "description": "Analytics, usage reports, and statistical insights"
        }
    ]
)


app.add_middleware(
    SQLAlchemyMiddleware,
    db_url=str(settings.ASYNC_DATABASE_URI),
    engine_args={
        "echo": False,
        "poolclass": NullPool
        if settings.MODE == ModeEnum.testing
        else AsyncAdaptedQueuePool
        # "pool_pre_ping": True,
        # "pool_size": settings.POOL_SIZE,
        # "max_overflow": 64,
    },
)
app.add_middleware(GlobalsMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add trusted host middleware (configure allowed hosts based on your deployment)
if settings.MODE.value == "production":
    # In production, specify your actual domains
    allowed_hosts = ["*.yourdomain.com", "yourdomain.com"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


# Set all CORS origins enabled
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS], 
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class CustomException(Exception):
    http_code: int
    code: str
    message: str

    def __init__(
        self,
        http_code: int = 500,
        code: str | None = None,
        message: str = "This is an error message",
    ):
        self.http_code = http_code
        self.code = code if code else str(self.http_code)
        self.message = message


from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
    )
    
    # Add custom info to the OpenAPI schema
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    
    # Add security schemes
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>"
        }
    }
    
    # Add custom extensions for Examify
    openapi_schema["info"]["x-api-id"] = "examify-api"
    openapi_schema["info"]["x-audience"] = "Educational Institutions & Students"
    openapi_schema["info"]["x-purpose"] = "Past Exam Papers Management"
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


@app.get(
    "/",
    summary="API Welcome & Information",
    description="""
    Welcome to the Examify API! This endpoint provides essential information about the API 
    and quick links to get you started with our comprehensive past exam papers management system.
    
    **Examify** is a powerful platform that helps educational institutions organize, store, 
    and provide access to their historical examination materials efficiently.
    
    ### Quick Start:
    1. 🔐 **Authenticate**: Use `/api/v1/login` to get your access token
    2. 📚 **Explore Papers**: Browse our extensive past exam papers collection
    3. 🧪 **Test API**: Try the endpoints using the Swagger UI interface
    
    ### Need Help?
    - 📖 **Documentation**: [API Docs](/api/v1/docs)
    - 📋 **ReDoc**: [Alternative Docs](/api/v1/redoc)
    - 🔧 **OpenAPI Schema**: [JSON Schema](/api/v1/openapi.json)
    """,
    response_description="Welcome message with API information and quick access links",
    tags=["welcome"]
)
async def root():
    """
    **Welcome to Examify API**
    
    This is the main entry point for the Examify past exam papers management system API.
    The API provides comprehensive functionality for managing educational institutions,
    organizing past exam papers, and facilitating access to historical examination materials.
    
    Returns basic API information and helpful links to get started.
    """
    return {
        "message": "📚 Welcome to Examify API - Comprehensive PastExam Papers Management System",
        "version": settings.API_VERSION,
        "status": "✅ Online and Ready",
        "description": "Modern async FastAPI-based past exam papers management system",
        "features": [
            "📚 Past Exam Papers Repository",
            "🔍 Advanced Search & Filtering",
            "🏫 Multi-Institution Support", 
            "👥 Role-based Access Control",
            "📊 Analytics & Usage Insights",
            "🔐 Secure JWT Authentication",
            "⚡ High-Performance Async Operations"
        ],
        "documentation": {
            "swagger_ui": f"http://fastapi.localhost{settings.API_V1_STR}/docs",
            "redoc": f"http://fastapi.localhost{settings.API_V1_STR}/redoc",
            "openapi_schema": f"http://fastapi.localhost{settings.API_V1_STR}/openapi.json"
        },
        "quick_start": {
            "1_authenticate": f"POST http://fastapi.localhost{settings.API_V1_STR}/login",
            "2_get_profile": f"GET http://fastapi.localhost{settings.API_V1_STR}/user/me",
            "3_browse_papers": f"GET http://fastapi.localhost{settings.API_V1_STR}/exampaper",
            "4_explore_docs": f"http://fastapi.localhost{settings.API_V1_STR}/docs"
        },
        "use_cases": [
            "🎓 Students: Access past papers for exam preparation",
            "👨‍🏫 Educators: Upload and manage historical exam materials",
            "🏛️ Administrators: Oversee institutional paper repositories",
            "🔬 Researchers: Analyze examination trends over time"
        ],
        "support": {
            "email": "support@examify.com",
            "documentation": f"http://fastapi.localhost{settings.API_V1_STR}/docs"
        },
        "system_info": {
            "environment": settings.MODE.value,
            "api_version": settings.API_VERSION,
            "python_version": "3.10+",
            "framework": "FastAPI with SQLModel",
            "focus": "Past Exam Papers Management"
        }
    }


@app.websocket("/chat/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: UUID):
    session_id = str(uuid4())
    key: str = f"user_id:{user_id}:session:{session_id}"
    await websocket.accept()
    redis_client = await get_redis_client()
    ws_ratelimit = WebSocketRateLimiter(times=200, hours=24)
    chat = ChatOpenAI(temperature=0, openai_api_key=settings.OPENAI_API_KEY)
    chat_history = []

    async with db():
        user = await crud.user.get_by_id_active(id=user_id)
        if user is not None:
            await redis_client.set(key, str(websocket))

    active_connection = await redis_client.get(key)
    if active_connection is None:
        await websocket.send_text(f"Error: User ID '{user_id}' not found or inactive.")
        await websocket.close()
    else:
        while True:
            try:
                # Receive and send back the client message
                data = await websocket.receive_json()
                await ws_ratelimit(websocket)
                user_message = IUserMessage.model_validate(data)
                user_message.user_id = user_id

                resp = IChatResponse(
                    sender="you",
                    message=user_message.message,
                    type="stream",
                    message_id=str(uuid7()),
                    id=str(uuid7()),
                )
                await websocket.send_json(resp.dict())

                # # Construct a response
                start_resp = IChatResponse(
                    sender="bot", message="", type="start", message_id="", id=""
                )
                await websocket.send_json(start_resp.dict())

                result = chat([HumanMessage(content=resp.message)])
                chat_history.append((user_message.message, result.content))

                end_resp = IChatResponse(
                    sender="bot",
                    message=result.content,
                    type="end",
                    message_id=str(uuid7()),
                    id=str(uuid7()),
                )
                await websocket.send_json(end_resp.dict())
            except WebSocketDisconnect:
                logging.info("websocket disconnect")
                break
            except Exception as e:
                logging.error(e)
                resp = IChatResponse(
                    message_id="",
                    id="",
                    sender="bot",
                    message="Sorry, something went wrong. Your user limit of api usages has been reached or check your API key.",
                    type="error",
                )
                await websocket.send_json(resp.dict())

        # Remove the live connection from Redis
        await redis_client.delete(key)


# Add health check router
# app.include_router(health_router)

# Add API router
app.include_router(api_router_v1, prefix=settings.API_V1_STR)
