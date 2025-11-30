"""
Audit Log Service

Centralized service for logging security events and user activities.
Provides easy-to-use methods for recording various types of events.
"""

import logging
from typing import Optional, Any, Dict
from uuid import UUID
from datetime import datetime

from app.crud.audit_log_crud import audit_log
from app.models.audit_log_model import AuditActionType
from app.core.config import settings


logger = logging.getLogger(__name__)


class AuditLogService:
    """
    Service for centralized audit logging.
    
    Provides a convenient interface for logging various types of events
    including authentication, authorization, and data modification events.
    """

    async def log_authentication(
        self,
        *,
        action: AuditActionType,
        user_id: Optional[UUID] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an authentication-related event.
        
        Args:
            action: Type of authentication event
            user_id: User ID (nullable for failed logins with invalid users)
            email: User email address
            ip_address: Client IP address
            user_agent: Client user agent
            success: Whether the action was successful
            error_message: Error message if action failed
            details: Additional event details
        """
        try:
            await audit_log.log_auth_event(
                action=action,
                user_id=user_id,
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message,
                details=details
            )
            
            # Also log to file for immediate visibility
            if not success:
                logger.warning(f"Audit: {action} failed for {email} ({user_id}) - {error_message}")
            else:
                logger.info(f"Audit: {action} successful for {email} ({user_id})")
                
        except Exception as e:
            logger.error(f"Failed to log authentication event: {str(e)}")

    async def log_authorization(
        self,
        *,
        action: AuditActionType,
        user_id: UUID,
        resource_type: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an authorization-related event.
        
        Args:
            action: Type of authorization event
            user_id: User ID
            resource_type: Type of resource accessed
            resource_id: ID of the resource
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
        """
        try:
            await audit_log.log_data_event(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            
            logger.info(f"Audit: {action} by user {user_id} on {resource_type}:{resource_id}")
            
        except Exception as e:
            logger.error(f"Failed to log authorization event: {str(e)}")

    async def log_data_change(
        self,
        *,
        action: AuditActionType,
        user_id: UUID,
        resource_type: str,
        resource_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log a data modification event.
        
        Args:
            action: Type of data modification event
            user_id: User ID
            resource_type: Type of resource modified
            resource_id: ID of the resource
            old_values: Previous values (for updates)
            new_values: New values (for creates/updates)
            ip_address: Client IP address
            user_agent: Client user agent
        """
        details = {}
        if old_values:
            details["old_values"] = old_values
        if new_values:
            details["new_values"] = new_values
            
        try:
            await audit_log.log_data_event(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            
            logger.info(f"Audit: {action} on {resource_type}:{resource_id} by user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log data change event: {str(e)}")

    async def log_security_event(
        self,
        *,
        action: AuditActionType,
        user_id: Optional[UUID] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a security-related event.
        
        Args:
            action: Type of security event
            user_id: User ID (nullable)
            email: User email
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
        """
        try:
            await audit_log.log_data_event(
                action=action,
                user_id=user_id,
                resource_type="security",
                ip_address=ip_address,
                user_agent=user_agent,
                details=details
            )
            
            logger.warning(f"Security: {action} for {email or user_id}")
            
        except Exception as e:
            logger.error(f"Failed to log security event: {str(e)}")

    async def log_admin_action(
        self,
        *,
        action: AuditActionType,
        user_id: UUID,
        target_user_id: Optional[UUID] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an admin action.
        
        Args:
            action: Type of admin action
            user_id: Admin user ID
            target_user_id: User affected by the action
            resource_type: Type of resource
            resource_id: ID of the resource
            ip_address: Client IP address
            user_agent: Client user agent
            details: Additional event details
        """
        admin_details = details or {}
        if target_user_id:
            admin_details["target_user_id"] = str(target_user_id)
            
        try:
            await audit_log.log_data_event(
                action=action,
                user_id=user_id,
                resource_type=resource_type or "admin",
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                details=admin_details
            )
            
            logger.warning(f"Admin: {action} by user {user_id} on {resource_type or 'admin'}:{resource_id}")
            
        except Exception as e:
            logger.error(f"Failed to log admin action: {str(e)}")

    async def get_user_activity_summary(
        self,
        *,
        user_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get activity summary for a user.
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Dictionary containing activity summary
        """
        try:
            from datetime import timedelta
            start_date = datetime.utcnow() - timedelta(days=days)
            
            logs = await audit_log.get_by_user(
                user_id=user_id,
                start_date=start_date,
                limit=1000
            )
            
            # Calculate statistics
            total_events = len(logs)
            successful_events = len([log for log in logs if log.success])
            failed_events = total_events - successful_events
            
            # Count by action type
            action_counts = {}
            for log in logs:
                action_counts[log.action] = action_counts.get(log.action, 0) + 1
                
            # Recent activity (last 10 events)
            recent_activity = logs[:10] if logs else []
            
            return {
                "user_id": str(user_id),
                "period_days": days,
                "total_events": total_events,
                "successful_events": successful_events,
                "failed_events": failed_events,
                "success_rate": round((successful_events / total_events * 100) if total_events > 0 else 0, 2),
                "action_breakdown": dict(sorted(action_counts.items(), key=lambda x: x[1], reverse=True)),
                "recent_activity": recent_activity
            }
            
        except Exception as e:
            logger.error(f"Failed to get user activity summary: {str(e)}")
            return {}

    async def detect_suspicious_activity(
        self,
        *,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        hours: int = 24
    ) -> bool:
        """
        Detect potentially suspicious activity.
        
        Args:
            user_id: User ID to check (optional)
            ip_address: IP address to check (optional)
            hours: Number of hours to look back
            
        Returns:
            True if suspicious activity detected
        """
        try:
            failed_attempts = await audit_log.get_failed_attempts(
                user_id=user_id,
                ip_address=ip_address,
                hours=hours
            )
            
            # Consider it suspicious if there are more than 10 failed attempts in the period
            if len(failed_attempts) > 10:
                logger.warning(f"Suspicious activity detected: {len(failed_attempts)} failed attempts for {user_id or ip_address}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Failed to detect suspicious activity: {str(e)}")
            return False


# Create global instance
audit_log_service = AuditLogService()
