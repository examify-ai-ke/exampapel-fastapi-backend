"""
Audit Log and Activity Log Schemas

Pydantic schemas for audit log and activity log operations.
Used for API request/response validation and serialization.
"""

from datetime import datetime
from uuid import UUID
from typing import Optional, Any

from pydantic import BaseModel, Field
from app.models.audit_log_model import AuditActionType


# Audit Log Schemas

class AuditLogBase(BaseModel):
    """Base schema for audit logs (used for API responses)"""
    user_id: Optional[UUID] = None
    action: AuditActionType
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    email: Optional[str] = None
    details: Optional[dict] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit logs"""
    pass


class AuditLogRead(AuditLogBase):
    """Schema for reading audit logs (includes timestamps and ID)"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditLogUpdate(BaseModel):
    """Schema for updating audit logs"""
    details: Optional[dict] = None
    error_message: Optional[str] = None
    success: Optional[bool] = None


# Activity Log Schemas

class ActivityLogBase(BaseModel):
    """Base schema for activity logs (used for API responses)"""
    user_id: Optional[UUID] = None
    method: str
    endpoint: str
    path: str
    query_params: Optional[dict] = None
    status_code: int = 200
    response_time_ms: Optional[float] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    details: Optional[dict] = None


class ActivityLogCreate(ActivityLogBase):
    """Schema for creating activity logs"""
    pass


class ActivityLogRead(ActivityLogBase):
    """Schema for reading activity logs (includes timestamps and ID)"""
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActivityLogUpdate(BaseModel):
    """Schema for updating activity logs"""
    response_time_ms: Optional[float] = None
    status_code: Optional[int] = None
    details: Optional[dict] = None


# Filter Schemas

class AuditLogFilter(BaseModel):
    """Schema for filtering audit logs"""
    user_id: Optional[UUID] = None
    action: Optional[AuditActionType] = None
    resource_type: Optional[str] = None
    success: Optional[bool] = None
    email: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)  # Max 1000 records
    offset: int = Field(default=0, ge=0)


class ActivityLogFilter(BaseModel):
    """Schema for filtering activity logs"""
    user_id: Optional[UUID] = None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    status_code: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)  # Max 1000 records
    offset: int = Field(default=0, ge=0)


# Statistics Schemas

class AuditLogStats(BaseModel):
    """Schema for audit log statistics"""
    total_logs: int
    success_rate: float
    failed_attempts: int
    top_actions: list[dict]  # [{"action": "login_success", "count": 150}]
    top_users: list[dict]    # [{"user_id": "uuid", "count": 25}]
    recent_events: list[AuditLogRead]


class ActivityLogStats(BaseModel):
    """Schema for activity log statistics"""
    total_requests: int
    avg_response_time: float
    success_rate: float
    top_endpoints: list[dict]     # [{"endpoint": "/api/v1/user", "count": 1200}]
    top_users: list[dict]         # [{"user_id": "uuid", "count": 89}]
    recent_requests: list[ActivityLogRead]
    status_code_distribution: list[dict]  # [{"status_code": 200, "count": 9500}]


# Response Schemas for List Endpoints

class AuditLogListResponse(BaseModel):
    """Response schema for audit log list endpoint"""
    data: list[AuditLogRead]
    total: int
    limit: int
    offset: int


class ActivityLogListResponse(BaseModel):
    """Response schema for activity log list endpoint"""
    data: list[ActivityLogRead]
    total: int
    limit: int
    offset: int
