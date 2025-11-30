"""
Audit Logs API Endpoints

Provides endpoints for querying and viewing audit logs and activity logs.
These endpoints are typically restricted to administrators and security personnel.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_async_sqlalchemy import db

from app import crud
from app.api.deps import get_current_user
from app.crud.audit_log_crud import audit_log, activity_log
from app.models.audit_log_model import AuditActionType
from app.models.user_model import User
from app.schemas.audit_log_schema import (
    AuditLogRead,
    ActivityLogRead,
    AuditLogFilter,
    ActivityLogFilter,
    AuditLogStats,
    ActivityLogStats,
    AuditLogListResponse,
    ActivityLogListResponse
)
from app.schemas.response_schema import create_response, IGetResponseBase

router = APIRouter()


@router.get("/audit", response_model=AuditLogListResponse)
async def get_audit_logs(
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    action: AuditActionType | None = Query(None, description="Filter by action type"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    success: bool | None = Query(None, description="Filter by success status"),
    email: str | None = Query(None, description="Filter by email"),
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user(required_roles=["admin"]))
) -> AuditLogListResponse:
    """
    Get audit logs with optional filtering.
    
    This endpoint requires admin role and provides comprehensive filtering options
    for security and compliance purposes.
    
    **Filtering Options:**
    - `user_id`: Filter by specific user
    - `action`: Filter by action type (login, logout, password_change, etc.)
    - `resource_type`: Filter by resource type (user, exam_paper, etc.)
    - `success`: Filter by success/failure status
    - `email`: Filter by email address
    - `start_date`/`end_date`: Filter by date range
    
    **Pagination:**
    - `limit`: Maximum records to return (1-1000)
    - `offset`: Number of records to skip
    """
    try:
        # Build filter conditions
        filters = []
        if user_id:
            filters.append(crud.audit_log.model.user_id == user_id)
        if action:
            filters.append(crud.audit_log.model.action == action)
        if resource_type:
            filters.append(crud.audit_log.model.resource_type == resource_type)
        if success is not None:
            filters.append(crud.audit_log.model.success == success)
        if email:
            filters.append(crud.audit_log.model.email == email)
        if start_date:
            filters.append(crud.audit_log.model.created_at >= start_date)
        if end_date:
            filters.append(crud.audit_log.model.created_at <= end_date)
            
        # Get total count for pagination
        from sqlmodel import select, func
        count_query = select(func.count(crud.audit_log.model.id))
        if filters:
            from sqlalchemy import and_
            count_query = count_query.where(and_(*filters))
        total_result = await db.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get logs with pagination
        from sqlmodel import select
        query = select(crud.audit_log.model)
        
        if filters:
            from sqlalchemy import and_
            query = query.where(and_(*filters))
            
        query = query.offset(offset).limit(limit).order_by(crud.audit_log.model.created_at.desc())
        
        result = await db.session.execute(query)
        logs = result.scalars().all()
        
        return AuditLogListResponse(
            data=logs,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit logs: {str(e)}")


@router.get("/activity", response_model=ActivityLogListResponse)
async def get_activity_logs(
    user_id: UUID | None = Query(None, description="Filter by user ID"),
    method: str | None = Query(None, description="Filter by HTTP method"),
    endpoint: str | None = Query(None, description="Filter by endpoint"),
    status_code: int | None = Query(None, description="Filter by status code"),
    start_date: datetime | None = Query(None, description="Start date filter"),
    end_date: datetime | None = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    current_user: User = Depends(get_current_user(required_roles=["admin"]))
) -> ActivityLogListResponse:
    """
    Get activity logs with optional filtering.
    
    This endpoint requires admin role and provides filtering for API request logs.
    
    **Filtering Options:**
    - `user_id`: Filter by specific user
    - `method`: Filter by HTTP method (GET, POST, etc.)
    - `endpoint`: Filter by API endpoint
    - `status_code`: Filter by HTTP status code
    - `start_date`/`end_date`: Filter by date range
    
    **Pagination:**
    - `limit`: Maximum records to return (1-1000)
    - `offset`: Number of records to skip
    """
    try:
        # Build filter conditions
        filters = []
        if user_id:
            filters.append(crud.activity_log.model.user_id == user_id)
        if method:
            filters.append(crud.activity_log.model.method == method)
        if endpoint:
            filters.append(crud.activity_log.model.endpoint == endpoint)
        if status_code:
            filters.append(crud.activity_log.model.status_code == status_code)
        if start_date:
            filters.append(crud.activity_log.model.created_at >= start_date)
        if end_date:
            filters.append(crud.activity_log.model.created_at <= end_date)
            
        # Get total count for pagination
        from sqlmodel import select, func
        count_query = select(func.count(crud.activity_log.model.id))
        if filters:
            from sqlalchemy import and_
            count_query = count_query.where(and_(*filters))
        total_result = await db.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get logs with pagination
        from sqlmodel import select
        query = select(crud.activity_log.model)
        
        if filters:
            from sqlalchemy import and_
            query = query.where(and_(*filters))
            
        query = query.offset(offset).limit(limit).order_by(crud.activity_log.model.created_at.desc())
        
        result = await db.session.execute(query)
        logs = result.scalars().all()
        
        return ActivityLogListResponse(
            data=logs,
            total=total,
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve activity logs: {str(e)}")


@router.get("/audit/stats", response_model=AuditLogStats)
async def get_audit_log_stats(
    start_date: datetime | None = Query(None, description="Start date for statistics"),
    end_date: datetime | None = Query(None, description="End date for statistics"),
    current_user: User = Depends(get_current_user(required_roles=["admin"]))
) -> AuditLogStats:
    """
    Get audit log statistics.
    
    Provides aggregated statistics for audit logs including:
    - Total log entries
    - Success rate
    - Failed attempt count
    - Top actions
    - Top users
    - Recent events
    """
    try:
        stats = await audit_log.get_stats(
            start_date=start_date,
            end_date=end_date
        )
        
        # Get recent events (last 10)
        recent_events = await audit_log.get_multi(
            skip=0,
            limit=10
        )
        
        return AuditLogStats(
            total_logs=stats["total_logs"],
            success_rate=stats["success_rate"],
            failed_attempts=stats["failed_attempts"],
            top_actions=[],  # TODO: Implement top actions query
            top_users=[],    # TODO: Implement top users query
            recent_events=recent_events
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve audit log stats: {str(e)}")


@router.get("/activity/stats", response_model=ActivityLogStats)
async def get_activity_log_stats(
    start_date: datetime | None = Query(None, description="Start date for statistics"),
    end_date: datetime | None = Query(None, description="End date for statistics"),
    current_user: User = Depends(get_current_user(required_roles=["admin"]))
) -> ActivityLogStats:
    """
    Get activity log statistics.
    
    Provides aggregated statistics for activity logs including:
    - Total requests
    - Average response time
    - Success rate
    - Top endpoints
    - Top users
    - Recent requests
    - Status code distribution
    """
    try:
        stats = await activity_log.get_stats(
            start_date=start_date,
            end_date=end_date
        )
        
        # Get recent requests (last 10)
        recent_requests = await activity_log.get_multi(
            skip=0,
            limit=10
        )
        
        # Get top endpoints
        top_endpoints = await activity_log.get_endpoint_stats(
            start_date=start_date,
            end_date=end_date,
            limit=10
        )
        
        return ActivityLogStats(
            total_requests=stats["total_requests"],
            avg_response_time=stats["avg_response_time"],
            success_rate=stats["success_rate"],
            top_endpoints=top_endpoints,
            top_users=[],  # TODO: Implement top users query
            recent_requests=recent_requests,
            status_code_distribution=[]  # TODO: Implement status code distribution
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve activity log stats: {str(e)}")


@router.get("/user/{user_id}/activity")
async def get_user_activity(
    user_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    current_user: User = Depends(get_current_user(required_roles=["admin"]))
) -> IGetResponseBase[Any]:
    """
    Get activity summary for a specific user.
    
    Provides a comprehensive view of user activity including:
    - Total events in the period
    - Success/failure breakdown
    - Action type breakdown
    - Recent activity
    
    **Access Control:**
    - Only admin users can view this information
    - Users can view their own activity (if endpoint is extended)
    """
    try:
        from app.services.audit_log_service import audit_log_service
        
        activity_summary = await audit_log_service.get_user_activity_summary(
            user_id=user_id,
            days=days
        )
        
        return create_response(
            data=activity_summary,
            message=f"Activity summary for user {user_id}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user activity: {str(e)}")


@router.get("/security/suspicious")
async def get_suspicious_activity(
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
    current_user: User = Depends(get_current_user(required_roles=["admin"]))
) -> IGetResponseBase[Any]:
    """
    Get suspicious activity indicators.
    
    Identifies potentially concerning patterns in user activity such as:
    - Multiple failed login attempts
    - Unusual login patterns
    - Rapid-fire requests
    - Suspicious IP addresses
    """
    try:
        from app.services.audit_log_service import audit_log_service
        
        # This is a simplified implementation
        # In a real system, you'd want more sophisticated detection
        suspicious_users = []
        
        # Get users with multiple failed attempts
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(hours=hours)
        
        failed_logs = await audit_log.get_multi(
            query=db.select(crud.audit_log.model).where(
                crud.audit_log.model.action == AuditActionType.LOGIN_FAILED,
                crud.audit_log.model.created_at >= since
            ),
            limit=1000
        )
        
        # Group by email to find suspicious patterns
        from collections import defaultdict
        failed_by_email = defaultdict(int)
        for log in failed_logs:
            if log.email:
                failed_by_email[log.email] += 1
                
        # Find users with more than 5 failed attempts
        for email, count in failed_by_email.items():
            if count > 5:
                suspicious_users.append({
                    "email": email,
                    "failed_attempts": count,
                    "reason": "Multiple failed login attempts"
                })
        
        return create_response(
            data={
                "period_hours": hours,
                "total_suspicious_users": len(suspicious_users),
                "suspicious_users": suspicious_users
            },
            message="Suspicious activity analysis complete"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze suspicious activity: {str(e)}")
