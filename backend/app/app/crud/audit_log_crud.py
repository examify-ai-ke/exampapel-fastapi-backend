"""
CRUD operations for AuditLog and ActivityLog

Provides database operations for logging and querying user activities.
"""

from typing import Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, desc
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.audit_log_model import AuditLog, AuditActionType, ActivityLog
from app.crud.base_crud import CRUDBase
from app.schemas.audit_log_schema import AuditLogCreate, AuditLogUpdate, ActivityLogCreate, ActivityLogUpdate


class CRUDAuditLog(CRUDBase[AuditLog, AuditLogCreate, AuditLogUpdate]):
    """
    CRUD operations for audit logs.
    
    Handles security-related logging including:
    - Authentication events (login, logout, token refresh)
    - Password changes and resets
    - Permission and role changes
    - Data modifications
    """

    async def create(
        self,
        *,
        obj_in: AuditLogCreate,
        db_session: AsyncSession | None = None
    ) -> AuditLog:
        """
        Create a new audit log entry.
        
        Args:
            obj_in: Audit log data to create
            db_session: Optional database session
            
        Returns:
            Created audit log entry
        """
        db_obj = self.model.model_validate(obj_in.model_dump())
        db_session = db_session or self.db.session
        
        try:
            db_session.add(db_obj)
            await db_session.commit()
        except Exception as e:
            await db_session.rollback()
            # Log the error but don't raise - audit logging should not break the main operation
            print(f"Failed to create audit log: {str(e)}")
            
        return db_obj

    async def log_auth_event(
        self,
        *,
        action: AuditActionType,
        user_id: UUID | None,
        email: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
        error_message: str | None = None,
        details: dict | None = None,
        db_session: AsyncSession | None = None
    ) -> AuditLog:
        """
        Log an authentication-related event.
        
        Args:
            action: Type of auth event
            user_id: User ID (nullable for failed logins)
            email: User email
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether the action was successful
            error_message: Error message if failed
            details: Additional event details
            db_session: Optional database session
            
        Returns:
            Created audit log entry
        """
        auth_data = AuditLogCreate(
            action=action,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
            details=details
        )
        
        return await self.create(obj_in=auth_data, db_session=db_session)

    async def log_data_event(
        self,
        *,
        action: AuditActionType,
        user_id: UUID,
        resource_type: str,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict | None = None,
        db_session: AsyncSession | None = None
    ) -> AuditLog:
        """
        Log a data modification event.
        
        Args:
            action: Type of data event
            user_id: User who performed the action
            resource_type: Type of resource affected
            resource_id: ID of the affected resource
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
            db_session: Optional database session
            
        Returns:
            Created audit log entry
        """
        data = AuditLogCreate(
            action=action,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        
        return await self.create(obj_in=data, db_session=db_session)

    async def get_by_user(
        self,
        *,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        db_session: AsyncSession | None = None
    ) -> list[AuditLog]:
        """
        Get audit logs for a specific user.
        
        Args:
            user_id: User ID to filter by
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of records
            db_session: Optional database session
            
        Returns:
            List of audit logs
        """
        db_session = db_session or self.db.session
        query = select(AuditLog).where(AuditLog.user_id == user_id)
        
        if start_date:
            query = query.where(AuditLog.created_at >= start_date)
        if end_date:
            query = query.where(AuditLog.created_at <= end_date)
            
        query = query.order_by(desc(AuditLog.created_at)).limit(limit)
        
        result = await db_session.execute(query)
        return result.scalars().all()

    async def get_failed_attempts(
        self,
        *,
        email: str | None = None,
        ip_address: str | None = None,
        hours: int = 24,
        db_session: AsyncSession | None = None
    ) -> list[AuditLog]:
        """
        Get failed login attempts within a time period.
        
        Args:
            email: Email to filter by (optional)
            ip_address: IP address to filter by (optional)
            hours: Number of hours to look back
            db_session: Optional database session
            
        Returns:
            List of failed login attempts
        """
        db_session = db_session or self.db.session
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = select(AuditLog).where(
            and_(
                AuditLog.action == AuditActionType.LOGIN_FAILED,
                AuditLog.created_at >= since
            )
        )
        
        if email:
            query = query.where(AuditLog.email == email)
        if ip_address:
            query = query.where(AuditLog.ip_address == ip_address)
            
        query = query.order_by(desc(AuditLog.created_at))
        
        result = await db_session.execute(query)
        return result.scalars().all()

    async def get_stats(
        self,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        db_session: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Get audit log statistics.
        
        Args:
            start_date: Start date for stats
            end_date: End date for stats
            db_session: Optional database session
            
        Returns:
            Dictionary containing audit statistics
        """
        db_session = db_session or self.db.session
        
        # Build query conditions
        conditions = []
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)
            
        where_clause = and_(*conditions) if conditions else None
        
        # Total logs
        query = select(func.count(AuditLog.id))
        if where_clause:
            query = query.where(where_clause)
        total_result = await db_session.execute(query)
        total_logs = total_result.scalar() or 0
        
        # Success rate
        success_query = select(func.count(AuditLog.id)).where(
            and_(AuditLog.success == True) + (where_clause if where_clause else ())
        )
        if not where_clause:
            success_query = select(func.count(AuditLog.id)).where(AuditLog.success == True)
        success_result = await db_session.execute(success_query)
        success_count = success_result.scalar() or 0
        
        # Failed attempts
        failed_query = select(func.count(AuditLog.id)).where(AuditLog.success == False)
        if where_clause:
            failed_query = failed_query.where(where_clause)
        failed_result = await db_session.execute(failed_query)
        failed_attempts = failed_result.scalar() or 0
        
        success_rate = (success_count / total_logs * 100) if total_logs > 0 else 0
        
        return {
            "total_logs": total_logs,
            "success_count": success_count,
            "failed_attempts": failed_attempts,
            "success_rate": round(success_rate, 2)
        }


class CRUDActivityLog(CRUDBase[ActivityLog, ActivityLogCreate, ActivityLogUpdate]):
    """
    CRUD operations for activity logs.
    
    Handles API request tracking including:
    - HTTP method and endpoint
    - Response time and status codes
    - User context and request metadata
    """

    async def create(
        self,
        *,
        obj_in: ActivityLogCreate,
        db_session: AsyncSession | None = None
    ) -> ActivityLog:
        """
        Create a new activity log entry.
        
        Args:
            obj_in: Activity log data to create
            db_session: Optional database session
            
        Returns:
            Created activity log entry
        """
        db_obj = self.model.model_validate(obj_in.model_dump())
        db_session = db_session or self.db.session
        
        try:
            db_session.add(db_obj)
            await db_session.commit()
        except Exception as e:
            await db_session.rollback()
            # Log the error but don't raise - activity logging should not break the main operation
            print(f"Failed to create activity log: {str(e)}")
            
        return db_obj

    async def log_request(
        self,
        *,
        method: str,
        endpoint: str,
        path: str,
        user_id: UUID | None = None,
        status_code: int = 200,
        response_time_ms: float | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        query_params: dict | None = None,
        details: dict | None = None,
        db_session: AsyncSession | None = None
    ) -> ActivityLog:
        """
        Log an API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            path: Full request path
            user_id: User ID (nullable for unauthenticated requests)
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Unique request identifier
            query_params: Query parameters (excluding sensitive data)
            details: Additional request details
            db_session: Optional database session
            
        Returns:
            Created activity log entry
        """
        activity_data = ActivityLogCreate(
            method=method,
            endpoint=endpoint,
            path=path,
            user_id=user_id,
            status_code=status_code,
            response_time_ms=response_time_ms,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            query_params=query_params,
            details=details
        )
        
        return await self.create(obj_in=activity_data, db_session=db_session)

    async def get_user_activity(
        self,
        *,
        user_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 100,
        db_session: AsyncSession | None = None
    ) -> list[ActivityLog]:
        """
        Get activity logs for a specific user.
        
        Args:
            user_id: User ID to filter by
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of records
            db_session: Optional database session
            
        Returns:
            List of activity logs
        """
        db_session = db_session or self.db.session
        query = select(ActivityLog).where(ActivityLog.user_id == user_id)
        
        if start_date:
            query = query.where(ActivityLog.created_at >= start_date)
        if end_date:
            query = query.where(ActivityLog.created_at <= end_date)
            
        query = query.order_by(desc(ActivityLog.created_at)).limit(limit)
        
        result = await db_session.execute(query)
        return result.scalars().all()

    async def get_endpoint_stats(
        self,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 10,
        db_session: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """
        Get statistics for most accessed endpoints.
        
        Args:
            start_date: Start date for stats
            end_date: End date for stats
            limit: Maximum number of endpoints to return
            db_session: Optional database session
            
        Returns:
            List of endpoint statistics
        """
        db_session = db_session or self.db.session
        
        # Build query conditions
        conditions = []
        if start_date:
            conditions.append(ActivityLog.created_at >= start_date)
        if end_date:
            conditions.append(ActivityLog.created_at <= end_date)
            
        where_clause = and_(*conditions) if conditions else None
        
        # Group by endpoint and count
        query = select(
            ActivityLog.endpoint,
            func.count(ActivityLog.id).label('request_count'),
            func.avg(ActivityLog.response_time_ms).label('avg_response_time'),
            func.count(
                func.case([(ActivityLog.status_code >= 400, 1)], else_=0)
            ).label('error_count')
        ).group_by(ActivityLog.endpoint)
        
        if where_clause:
            query = query.where(where_clause)
            
        query = query.order_by(desc('request_count')).limit(limit)
        
        result = await db_session.execute(query)
        return result.mappings().all()

    async def get_stats(
        self,
        *,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        db_session: AsyncSession | None = None
    ) -> dict[str, Any]:
        """
        Get activity log statistics.
        
        Args:
            start_date: Start date for stats
            end_date: End date for stats
            db_session: Optional database session
            
        Returns:
            Dictionary containing activity statistics
        """
        db_session = db_session or self.db.session
        
        # Build query conditions
        conditions = []
        if start_date:
            conditions.append(ActivityLog.created_at >= start_date)
        if end_date:
            conditions.append(ActivityLog.created_at <= end_date)
            
        where_clause = and_(*conditions) if conditions else None
        
        # Total requests
        query = select(func.count(ActivityLog.id))
        if where_clause:
            query = query.where(where_clause)
        total_result = await db_session.execute(query)
        total_requests = total_result.scalar() or 0
        
        # Average response time
        avg_query = select(func.avg(ActivityLog.response_time_ms))
        if where_clause:
            avg_query = avg_query.where(where_clause)
        avg_result = await db_session.execute(avg_query)
        avg_response_time = avg_result.scalar() or 0
        
        # Success rate (status codes < 400)
        success_query = select(func.count(ActivityLog.id)).where(
            ActivityLog.status_code < 400
        )
        if where_clause:
            success_query = success_query.where(where_clause)
        success_result = await db_session.execute(success_query)
        success_count = success_result.scalar() or 0
        
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "avg_response_time": round(avg_response_time or 0, 2),
            "success_count": success_count,
            "success_rate": round(success_rate, 2)
        }


# Create CRUD instances
audit_log = CRUDAuditLog(AuditLog)
activity_log = CRUDActivityLog(ActivityLog)
