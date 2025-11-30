"""
Activity Logging Middleware

FastAPI middleware that automatically logs all API requests to ActivityLog.
This middleware runs for every request and captures:
- HTTP method and endpoint
- Response time
- Status code
- User context
- Request metadata
"""

import logging
import time
import uuid
from typing import Callable
from uuid import UUID

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.crud.audit_log_crud import activity_log
from app.core.config import settings
from app.models.audit_log_model import AuditActionType


logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging API requests and responses.
    
    This middleware automatically logs all API requests to the ActivityLog table,
    capturing request and response details for analytics and monitoring.
    """

    def __init__(self, app: FastAPI, exclude_paths: list[str] = None):
        """
        Initialize the middleware.
        
        Args:
            app: FastAPI application instance
            exclude_paths: List of paths to exclude from logging
        """
        super().__init__(app)
        # Paths to exclude from logging (health checks, static files, etc.)
        self.exclude_paths = set(exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
            "/static/",
        ])
        
        # Also exclude paths that match these patterns
        self.exclude_patterns = [
            "/docs",
            "/redoc", 
            "/openapi",
            "/static"
        ]

    def should_exclude_path(self, path: str) -> bool:
        """
        Check if a path should be excluded from logging.
        
        Args:
            path: Request path to check
            
        Returns:
            True if path should be excluded, False otherwise
        """
        # Check exact matches
        if path in self.exclude_paths:
            return True
            
        # Check pattern matches
        for pattern in self.exclude_patterns:
            if pattern in path:
                return True
                
        return False

    def get_client_info(self, request: Request) -> tuple[str | None, str | None]:
        """
        Extract client information from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tuple of (ip_address, user_agent)
        """
        # Get client IP address
        client_ip = None
        if "x-forwarded-for" in request.headers:
            # Get first IP from X-Forwarded-For header
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
            
        # Get user agent
        user_agent = request.headers.get("user-agent")
        
        return client_ip, user_agent

    def extract_user_id(self, request: Request) -> UUID | None:
        """
        Extract user ID from request if authenticated.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User ID if authenticated, None otherwise
        """
        try:
            # Check if user is authenticated by looking for authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.lower().startswith("bearer"):
                # The actual user validation is done by the dependency injection
                # Here we just check if there's a user in request state
                # This is set by the get_current_user dependency
                if hasattr(request.state, "user_id"):
                    return request.state.user_id
        except Exception as e:
            logger.debug(f"Failed to extract user ID: {str(e)}")
            
        return None

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and log the activity.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response object
        """
        # Skip logging for excluded paths
        if self.should_exclude_path(request.url.path):
            return await call_next(request)
            
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        
        # Get client information
        client_ip, user_agent = self.get_client_info(request)
        
        # Record start time for response time calculation
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Extract user ID if available
            user_id = self.extract_user_id(request)
            
            # Log the activity (non-blocking)
            try:
                await activity_log.log_request(
                    method=request.method,
                    endpoint=request.url.path,
                    path=str(request.url),
                    user_id=user_id,
                    status_code=response.status_code,
                    response_time_ms=round(response_time_ms, 2),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    request_id=request_id,
                    query_params=dict(request.query_params) if request.query_params else None
                )
            except Exception as e:
                # Log the error but don't break the request
                logger.error(f"Failed to log activity: {str(e)}")
                
        except Exception as e:
            # Log failed requests with error status
            response_time_ms = (time.time() - start_time) * 1000
            user_id = self.extract_user_id(request)
            
            try:
                await activity_log.log_request(
                    method=request.method,
                    endpoint=request.url.path,
                    path=str(request.url),
                    user_id=user_id,
                    status_code=500,  # Internal server error
                    response_time_ms=round(response_time_ms, 2),
                    ip_address=client_ip,
                    user_agent=user_agent,
                    request_id=request_id,
                    query_params=dict(request.query_params) if request.query_params else None,
                    details={"error": str(e)}
                )
            except Exception as log_error:
                logger.error(f"Failed to log error activity: {str(log_error)}")
                
            # Re-raise the original exception
            raise
            
        return response


def setup_activity_logging(app: FastAPI) -> None:
    """
    Setup activity logging middleware for the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    if not settings.ENABLE_ACTIVITY_LOGGING:
        logger.info("Activity logging is disabled")
        return
        
    # Add the middleware
    app.add_middleware(ActivityLoggingMiddleware)
    
    logger.info("Activity logging middleware configured")
