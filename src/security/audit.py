"""Audit logging system for security monitoring and compliance."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json


class AuditAction(Enum):
    """Audit action types."""
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    QUERY = "QUERY"
    ADMIN = "ADMIN"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ACCESS_DENIED = "ACCESS_DENIED"


class SeverityLevel(Enum):
    """Audit log severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class AuditEntry:
    """Represents an audit log entry."""
    
    timestamp: datetime
    user_id: str
    tenant_id: str
    action: str
    resource: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    result: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    severity: SeverityLevel = SeverityLevel.INFO
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "result": self.result,
            "details": self.details,
            "severity": self.severity.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Create entry from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data["user_id"],
            tenant_id=data["tenant_id"],
            action=data["action"],
            resource=data["resource"],
            resource_id=data.get("resource_id"),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            result=data.get("result"),
            details=data.get("details", {}),
            severity=SeverityLevel(data.get("severity", "INFO"))
        )


class AuditLogger:
    """Handles audit logging for security events."""
    
    def __init__(self, db_client: Any):
        """
        Initialize audit logger.
        
        Args:
            db_client: Database client for storing audit logs
        """
        self.db = db_client
        self._anomaly_cache: Dict[str, List[datetime]] = {}
    
    async def log_access(
        self,
        user_id: str,
        tenant_id: str,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: SeverityLevel = SeverityLevel.INFO
    ) -> AuditEntry:
        """
        Log a data access event.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            action: Action performed
            resource: Resource accessed
            resource_id: Specific resource ID
            ip_address: Client IP address
            user_agent: Client user agent
            result: Operation result
            details: Additional details
            severity: Log severity level
            
        Returns:
            Created audit entry
        """
        entry = AuditEntry(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
            details=details or {},
            severity=severity
        )
        
        # Store in database
        await self.db.insert("audit_log", entry.to_dict())
        
        # Check for anomalies
        await self._check_anomalies(entry)
        
        return entry
    
    async def log_login(
        self,
        user_id: str,
        tenant_id: str,
        ip_address: str,
        success: bool,
        failure_reason: Optional[str] = None
    ) -> AuditEntry:
        """
        Log a login event.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            ip_address: Client IP address
            success: Whether login was successful
            failure_reason: Reason for failure
            
        Returns:
            Created audit entry
        """
        action = AuditAction.LOGIN.value if success else AuditAction.ACCESS_DENIED.value
        result = "success" if success else f"failed: {failure_reason}"
        
        return await self.log_access(
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource="authentication",
            ip_address=ip_address,
            result=result,
            severity=SeverityLevel.WARNING if not success else SeverityLevel.INFO
        )
    
    async def log_logout(
        self,
        user_id: str,
        tenant_id: str
    ) -> AuditEntry:
        """
        Log a logout event.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            Created audit entry
        """
        return await self.log_access(
            user_id=user_id,
            tenant_id=tenant_id,
            action=AuditAction.LOGOUT.value,
            resource="session"
        )
    
    async def log_admin_action(
        self,
        user_id: str,
        tenant_id: str,
        action: str,
        target_user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Log an admin action.
        
        Args:
            user_id: Admin user identifier
            tenant_id: Tenant identifier
            action: Admin action performed
            target_user_id: Target user (if applicable)
            details: Additional details
            
        Returns:
            Created audit entry
        """
        return await self.log_access(
            user_id=user_id,
            tenant_id=tenant_id,
            action=AuditAction.ADMIN.value,
            resource=f"admin:{action}",
            resource_id=target_user_id,
            details=details or {"admin_action": action},
            severity=SeverityLevel.WARNING
        )
    
    async def log_access_denied(
        self,
        user_id: str,
        tenant_id: str,
        resource: str,
        reason: str,
        ip_address: Optional[str] = None
    ) -> AuditEntry:
        """
        Log an access denied event.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            resource: Resource accessed
            reason: Reason for denial
            ip_address: Client IP address
            
        Returns:
            Created audit entry
        """
        return await self.log_access(
            user_id=user_id,
            tenant_id=tenant_id,
            action=AuditAction.ACCESS_DENIED.value,
            resource=resource,
            ip_address=ip_address,
            result=f"denied: {reason}",
            severity=SeverityLevel.ERROR
        )
    
    async def _check_anomalies(self, entry: AuditEntry) -> None:
        """
        Check for anomalous patterns in audit logs.
        
        Args:
            entry: Audit entry to check
        """
        # Create anomaly key
        anomaly_key = f"{entry.user_id}:{entry.action}"
        
        # Initialize cache entry
        if anomaly_key not in self._anomaly_cache:
            self._anomaly_cache[anomaly_key] = []
        
        # Add timestamp
        self._anomaly_cache[anomaly_key].append(entry.timestamp)
        
        # Keep only last hour of data
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self._anomaly_cache[anomaly_key] = [
            ts for ts in self._anomaly_cache[anomaly_key]
            if ts > cutoff
        ]
        
        # Check for high frequency
        if len(self._anomaly_cache[anomaly_key]) > 100:
            await self._alert_anomaly(entry, "high_frequency")
    
    async def _alert_anomaly(
        self, 
        entry: AuditEntry, 
        anomaly_type: str
    ) -> None:
        """
        Alert on detected anomaly.
        
        Args:
            entry: Related audit entry
            anomaly_type: Type of anomaly detected
        """
        # In production, send to monitoring system
        # For now, log to console
        print(f"ALERT: Anomaly detected - {anomaly_type}")
        print(f"  User: {entry.user_id}")
        print(f"  Action: {entry.action}")
        print(f"  Time: {entry.timestamp}")
    
    async def detect_anomalies(
        self,
        hours: int = 1,
        threshold: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Detect suspicious access patterns.
        
        Args:
            hours: Time window in hours
            threshold: Action count threshold
            
        Returns:
            List of detected anomalies
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Query for anomalies
        query = f"""
            SELECT user_id, tenant_id, action, COUNT(*) as count
            FROM audit_log
            WHERE timestamp > '{cutoff.isoformat()}'
            GROUP BY user_id, tenant_id, action
            HAVING COUNT(*) > {threshold}
        """
        
        anomalies = await self.db.query(query)
        
        return anomalies
    
    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with filters.
        
        Args:
            user_id: Filter by user ID
            tenant_id: Filter by tenant ID
            action: Filter by action
            resource: Filter by resource
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of audit log entries
        """
        # Build WHERE clause
        conditions = []
        params = []
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if tenant_id:
            conditions.append("tenant_id = ?")
            params.append(tenant_id)
        
        if action:
            conditions.append("action = ?")
            params.append(action)
        
        if resource:
            conditions.append("resource = ?")
            params.append(resource)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Build query
        query = f"""
            SELECT * FROM audit_log
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT {limit} OFFSET {offset}
        """
        
        logs = await self.db.query(query, *params)
        
        return logs
    
    async def get_access_summary(
        self,
        tenant_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get access summary for a tenant.
        
        Args:
            tenant_id: Tenant ID
            days: Number of days to analyze
            
        Returns:
            Summary statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Get counts by action
        action_counts = await self.db.query(f"""
            SELECT action, COUNT(*) as count
            FROM audit_log
            WHERE tenant_id = '{tenant_id}'
            AND timestamp > '{cutoff.isoformat()}'
            GROUP BY action
        """)
        
        # Get unique users
        unique_users = await self.db.query(f"""
            SELECT COUNT(DISTINCT user_id) as count
            FROM audit_log
            WHERE tenant_id = '{tenant_id}'
            AND timestamp > '{cutoff.isoformat()}'
        """)
        
        # Get denied access count
        denied_count = await self.db.query(f"""
            SELECT COUNT(*) as count
            FROM audit_log
            WHERE tenant_id = '{tenant_id}'
            AND timestamp > '{cutoff.isoformat()}'
            AND action = 'ACCESS_DENIED'
        """)
        
        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "start_date": cutoff.isoformat(),
            "action_counts": {item["action"]: item["count"] for item in action_counts},
            "unique_users": unique_users[0]["count"] if unique_users else 0,
            "denied_access_count": denied_count[0]["count"] if denied_count else 0
        }
    
    async def export_audit_logs(
        self,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
        format: str = "json"
    ) -> str:
        """
        Export audit logs for compliance.
        
        Args:
            tenant_id: Tenant ID
            start_time: Start time
            end_time: End time
            format: Export format (json, csv)
            
        Returns:
            Exported data as string
        """
        logs = await self.get_audit_logs(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        if format == "json":
            return json.dumps(logs, indent=2)
        elif format == "csv":
            # Convert to CSV format
            if not logs:
                return ""
            
            headers = list(logs[0].keys())
            lines = [",".join(headers)]
            
            for log in logs:
                values = [str(log.get(h, "")) for h in headers]
                lines.append(",".join(values))
            
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")
