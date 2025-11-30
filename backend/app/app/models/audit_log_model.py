"""
Audit Log and Activity Log Models

These models provide comprehensive logging for:
- AuditLog: Security and critical events (logins, password changes, permission changes)
- ActivityLog: User behavior and API request tracking
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID

from app.models.base_uuid_model import BaseUUIDModel
from sqlmodel import Field, Column, Text, JSON, String, Enum as SQLEnum, Index, SQLModel


class AuditActionType(str, Enum):
    """Types of audit actions for security events"""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"

    # Password events
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested"
    PASSWORD_RESET_COMPLETED = "password_reset_completed"

    # Account events
    ACCOUNT_CREATED = "account_created"
    ACCOUNT_UPDATED = "account_updated"
    ACCOUNT_DEACTIVATED = "account_deactivated"
    ACCOUNT_REACTIVATED = "account_reactivated"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"

    # Authorization events
    PERMISSION_DENIED = "permission_denied"
    ROLE_CHANGED = "role_changed"

    # Data events
    DATA_CREATED = "data_created"
    DATA_UPDATED = "data_updated"
    DATA_DELETED = "data_deleted"
    DATA_EXPORTED = "data_exported"

    # Admin events
    ADMIN_ACTION = "admin_action"
    SYSTEM_CONFIG_CHANGED = "system_config_changed"


class AuditLogBase(SQLModel):
    """Base schema for audit logs"""

    # User who performed the action (nullable for failed logins with invalid users)
    user_id: UUID | None = Field(default=None, foreign_key="User.id", index=True)

    # What action was performed
    action: AuditActionType = Field(
        sa_column=Column(SQLEnum(AuditActionType), nullable=False, index=True)
    )

    # What resource was affected (e.g., "user", "exam_paper", "institution")
    resource_type: str | None = Field(
        default=None, sa_column=Column(String(100), nullable=True, index=True)
    )

    # ID of the affected resource
    resource_id: str | None = Field(
        default=None, sa_column=Column(String(100), nullable=True)
    )

    # Request context
    ip_address: str | None = Field(
        default=None, sa_column=Column(String(45), nullable=True)  # IPv6 max length
    )
    user_agent: str | None = Field(
        default=None, sa_column=Column(String(500), nullable=True)
    )

    # Email for tracking (useful for failed logins)
    email: str | None = Field(
        default=None, sa_column=Column(String(255), nullable=True, index=True)
    )

    # Additional details as JSON
    details: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))

    # Outcome of the action
    success: bool = Field(default=True)
    error_message: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )


class AuditLog(BaseUUIDModel, AuditLogBase, table=True):
    """
    Persistent audit log for security and compliance.

    Tracks all security-relevant events including:
    - Authentication (login, logout, token refresh)
    - Authorization (permission denied, role changes)
    - Account management (creation, updates, deactivation)
    - Critical data changes

    This table should be append-only for compliance.
    Consider partitioning by created_at for large deployments.
    """

    __table_args__ = (
        Index("ix_auditlog_user_action", "user_id", "action"),
        Index("ix_auditlog_created_at", "created_at"),
        Index("ix_auditlog_resource", "resource_type", "resource_id"),
    )


# Activity Log for API request tracking


class ActivityLogBase(SQLModel):
    """Base schema for activity logs"""

    # User who made the request (nullable for unauthenticated requests)
    user_id: UUID | None = Field(default=None, foreign_key="User.id", index=True)

    # Request details
    method: str = Field(sa_column=Column(String(10), nullable=False))  # GET, POST, etc.
    endpoint: str = Field(sa_column=Column(String(500), nullable=False, index=True))
    path: str = Field(sa_column=Column(String(500), nullable=False))

    # Query parameters (excluding sensitive data)
    query_params: dict | None = Field(
        default=None, sa_column=Column(JSON, nullable=True)
    )

    # Response details
    status_code: int = Field(default=200)
    response_time_ms: float | None = Field(
        default=None
    )  # Response time in milliseconds

    # Request context
    ip_address: str | None = Field(
        default=None, sa_column=Column(String(45), nullable=True)
    )
    user_agent: str | None = Field(
        default=None, sa_column=Column(String(500), nullable=True)
    )

    # Request metadata
    request_id: str | None = Field(
        default=None, sa_column=Column(String(100), nullable=True, index=True)
    )

    # Additional context
    details: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))


class ActivityLog(BaseUUIDModel, ActivityLogBase, table=True):
    """
    Activity log for tracking API requests and user behavior.

    Logs all API requests for:
    - Usage analytics
    - Performance monitoring
    - User behavior analysis
    - Debugging and troubleshooting

    This table can grow large quickly.
    Implement retention policies (e.g., keep 30-90 days).
    Consider partitioning by created_at for large deployments.
    """

    __table_args__ = (
        Index("ix_activitylog_user_endpoint", "user_id", "endpoint"),
        Index("ix_activitylog_created_at", "created_at"),
        Index("ix_activitylog_status", "status_code"),
    )
