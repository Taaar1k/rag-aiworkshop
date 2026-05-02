"""Unit tests for tenant isolation security module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.security.tenant_context import TenantContext, TenantContextManager
from src.security.row_level_security import RowLevelSecurity
from src.security.audit import AuditLogger, AuditAction, SeverityLevel


class TestTenantContext:
    """Tests for TenantContext class."""
    
    def test_tenant_context_creation(self):
        """Test creating a tenant context."""
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
            permissions=["read_public", "read_private"],
            is_authenticated=True
        )
        
        assert context.tenant_id == "tenant-123"
        assert context.user_id == "user-456"
        assert "read_public" in context.permissions
        assert context.is_authenticated is True
    
    def test_has_permission(self):
        """Test permission checking."""
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
            permissions=["read_public", "read_private"]
        )
        
        assert context.has_permission("read_public") is True
        assert context.has_permission("read_private") is True
        assert context.has_permission("admin") is False
    
    def test_add_permission(self):
        """Test adding permissions."""
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
            permissions=["read_public"]
        )
        
        context.add_permission("read_private")
        
        assert "read_private" in context.permissions
        assert len(context.permissions) == 2
    
    def test_remove_permission(self):
        """Test removing permissions."""
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
            permissions=["read_public", "read_private"]
        )
        
        context.remove_permission("read_public")
        
        assert "read_public" not in context.permissions
        assert "read_private" in context.permissions
    
    def test_to_dict(self):
        """Test context serialization."""
        context = TenantContext(
            tenant_id="tenant-123",
            user_id="user-456",
            permissions=["read_public"],
            metadata={"key": "value"}
        )
        
        context_dict = context.to_dict()
        
        assert context_dict["tenant_id"] == "tenant-123"
        assert context_dict["user_id"] == "user-456"
        assert context_dict["permissions"] == ["read_public"]
        assert context_dict["metadata"]["key"] == "value"


class TestTenantContextManager:
    """Tests for TenantContextManager class."""
    
    @pytest.fixture
    def mock_identity_provider(self):
        """Create mock identity provider."""
        mock = AsyncMock()
        mock.verify_token = AsyncMock(return_value=True)
        mock.get_user_permissions = AsyncMock(return_value=["read_public", "read_private"])
        mock.get_user_tenant = AsyncMock(return_value={"tenant_id": "tenant-123"})
        mock.get_user = AsyncMock(return_value={
            "id": "user-456",
            "tenant_id": "tenant-123",
            "permissions": ["read_public", "read_private"]
        })
        return mock
    
    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client."""
        mock = AsyncMock()
        mock.query = AsyncMock(return_value=[])
        mock.insert = AsyncMock(return_value={"id": "1"})
        return mock
    
    @pytest.fixture
    def context_manager(self, mock_identity_provider, mock_db_client):
        """Create context manager instance."""
        return TenantContextManager(mock_identity_provider, mock_db_client)
    
    @pytest.mark.asyncio
    async def test_create_context_success(self, context_manager, mock_identity_provider):
        """Test successful context creation."""
        context = await context_manager.create_context(
            user_id="user-456",
            tenant_id="tenant-123",
            token="valid-token"
        )
        
        assert context is not None
        assert context.tenant_id == "tenant-123"
        assert context.user_id == "user-456"
        assert context.is_authenticated is True
    
    @pytest.mark.asyncio
    async def test_create_context_invalid_token(self, context_manager):
        """Test context creation with invalid token."""
        mock_identity = AsyncMock()
        mock_identity.verify_token = AsyncMock(return_value=False)
        
        context_manager.identity = mock_identity
        
        context = await context_manager.create_context(
            user_id="user-456",
            tenant_id="tenant-123",
            token="invalid-token"
        )
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_get_context_success(self, context_manager, mock_identity_provider):
        """Test successful context retrieval."""
        context = await context_manager.get_context(
            user_id="user-456",
            tenant_id="tenant-123"
        )
        
        assert context is not None
        assert context.tenant_id == "tenant-123"
    
    @pytest.mark.asyncio
    async def test_validate_tenant_access_match(self, context_manager):
        """Test tenant access validation with matching tenants."""
        result = await context_manager.validate_tenant_access(
            user_id="user-456",
            resource_tenant_id="tenant-123"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_tenant_access_mismatch(self, context_manager):
        """Test tenant access validation with mismatched tenants."""
        result = await context_manager.validate_tenant_access(
            user_id="user-456",
            resource_tenant_id="tenant-789"
        )
        
        assert result is False


class TestRowLevelSecurity:
    """Tests for RowLevelSecurity class."""
    
    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client."""
        mock = AsyncMock()
        mock.query = AsyncMock(return_value=[])
        mock.insert = AsyncMock(return_value={"id": "1"})
        return mock
    
    @pytest.fixture
    def rls(self, mock_db_client):
        """Create RowLevelSecurity instance."""
        return RowLevelSecurity(mock_db_client)
    
    def test_apply_tenant_filter_basic(self, rls):
        """Test basic tenant filter application."""
        query = "SELECT * FROM documents"
        result = rls.apply_tenant_filter(query, "tenant-123")
        
        assert "tenant_id = 'tenant-123'" in result
        assert "WHERE" in result
    
    def test_apply_tenant_filter_with_existing_where(self, rls):
        """Test tenant filter with existing WHERE clause."""
        query = "SELECT * FROM documents WHERE status = 'active'"
        result = rls.apply_tenant_filter(query, "tenant-123")
        
        assert "tenant_id = 'tenant-123'" in result
        assert "AND" in result
    
    def test_apply_tenant_filter_with_additional_filters(self, rls):
        """Test tenant filter with additional conditions."""
        query = "SELECT * FROM documents"
        additional = ["status = 'active'", "is_public = true"]
        result = rls.apply_tenant_filter(query, "tenant-123", additional)
        
        assert "tenant_id = 'tenant-123'" in result
        assert "status = 'active'" in result
        assert "is_public = true" in result
    
    def test_validate_tenant_access_match(self, rls):
        """Test tenant access validation with matching IDs."""
        result = rls.validate_tenant_access("tenant-123", "tenant-123")
        assert result is True
    
    def test_validate_tenant_access_mismatch(self, rls):
        """Test tenant access validation with mismatched IDs."""
        result = rls.validate_tenant_access("tenant-123", "tenant-456")
        assert result is False
    
    def test_sanitize_identifier(self, rls):
        """Test identifier sanitization."""
        # Should remove special characters
        result = rls._sanitize_identifier("tenant-123' OR '1'='1")
        assert "'" not in result
        assert "tenant-123" in result
    
    def test_sanitize_table_name(self, rls):
        """Test table name sanitization."""
        result = rls._sanitize_table_name("documents; DROP TABLE users")
        assert "documents" in result
        assert "DROP" not in result
        assert "TABLE" not in result
        assert result == "documents"
    
    def test_apply_security_trimming(self, rls):
        """Test security trimming application."""
        query = "SELECT * FROM documents"
        permissions = ["read_public", "read_private"]
        result = rls.apply_security_trimming(query, permissions, "tenant-123")
        
        assert "tenant_id = 'tenant-123'" in result
        assert "is_public" in result or "access_level" in result
    
    def test_generate_tenant_isolation_rule(self, rls):
        """Test tenant isolation rule generation."""
        rule = rls.generate_tenant_isolation_rule(
            tenant_id="tenant-123",
            table_name="documents",
            rule_type="always"
        )
        
        assert rule["tenant_id"] == "tenant-123"
        assert rule["table"] == "documents"
        assert rule["rule_type"] == "always"


class TestAuditLogger:
    """Tests for AuditLogger class."""
    
    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client."""
        mock = AsyncMock()
        mock.query = AsyncMock(return_value=[])
        mock.insert = AsyncMock(return_value={"id": "1"})
        return mock
    
    @pytest.fixture
    def audit_logger(self, mock_db_client):
        """Create AuditLogger instance."""
        return AuditLogger(mock_db_client)
    
    @pytest.mark.asyncio
    async def test_log_access(self, audit_logger):
        """Test logging an access event."""
        entry = await audit_logger.log_access(
            user_id="user-456",
            tenant_id="tenant-123",
            action="READ",
            resource="documents",
            ip_address="192.168.1.1"
        )
        
        assert entry.user_id == "user-456"
        assert entry.tenant_id == "tenant-123"
        assert entry.action == "READ"
        assert entry.resource == "documents"
        assert entry.ip_address == "192.168.1.1"
    
    @pytest.mark.asyncio
    async def test_log_login_success(self, audit_logger):
        """Test logging a successful login."""
        entry = await audit_logger.log_login(
            user_id="user-456",
            tenant_id="tenant-123",
            ip_address="192.168.1.1",
            success=True
        )
        
        assert entry.action == "LOGIN"
        assert entry.result == "success"
    
    @pytest.mark.asyncio
    async def test_log_login_failure(self, audit_logger):
        """Test logging a failed login."""
        entry = await audit_logger.log_login(
            user_id="user-456",
            tenant_id="tenant-123",
            ip_address="192.168.1.1",
            success=False,
            failure_reason="invalid_password"
        )
        
        assert entry.action == "ACCESS_DENIED"
        assert "failed" in entry.result
    
    @pytest.mark.asyncio
    async def test_log_admin_action(self, audit_logger):
        """Test logging an admin action."""
        entry = await audit_logger.log_admin_action(
            user_id="admin-123",
            tenant_id="tenant-123",
            action="user_create",
            target_user_id="user-456"
        )
        
        assert entry.action == "ADMIN"
        assert entry.resource == "admin:user_create"
    
    @pytest.mark.asyncio
    async def test_log_access_denied(self, audit_logger):
        """Test logging an access denied event."""
        entry = await audit_logger.log_access_denied(
            user_id="user-456",
            tenant_id="tenant-123",
            resource="documents",
            reason="insufficient_permissions"
        )
        
        assert entry.action == "ACCESS_DENIED"
        assert entry.severity == SeverityLevel.ERROR
    
    @pytest.mark.asyncio
    async def test_get_audit_logs(self, audit_logger):
        """Test retrieving audit logs."""
        logs = await audit_logger.get_audit_logs(
            tenant_id="tenant-123",
            limit=10
        )
        
        assert isinstance(logs, list)
    
    @pytest.mark.asyncio
    async def test_get_access_summary(self, audit_logger):
        """Test getting access summary."""
        summary = await audit_logger.get_access_summary(
            tenant_id="tenant-123",
            days=7
        )
        
        assert "tenant_id" in summary
        assert "action_counts" in summary
        assert "unique_users" in summary
    
    @pytest.mark.asyncio
    async def test_export_audit_logs_json(self, audit_logger):
        """Test exporting audit logs in JSON format."""
        export = await audit_logger.export_audit_logs(
            tenant_id="tenant-123",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            format="json"
        )
        
        assert isinstance(export, str)
        assert "[" in export or "{" in export
    
    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, audit_logger):
        """Test exporting audit logs in CSV format."""
        export = await audit_logger.export_audit_logs(
            tenant_id="tenant-123",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            format="csv"
        )
        
        assert isinstance(export, str)


class TestCrossTenantIsolation:
    """Tests for cross-tenant isolation security."""
    
    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client."""
        mock = AsyncMock()
        mock.query = AsyncMock(return_value=[])
        mock.insert = AsyncMock(return_value={"id": "1"})
        return mock
    
    @pytest.fixture
    def rls(self, mock_db_client):
        """Create RowLevelSecurity instance."""
        return RowLevelSecurity(mock_db_client)
    
    @pytest.mark.asyncio
    async def test_cross_tenant_access_denied(self, rls):
        """Test that cross-tenant access is denied."""
        result = await rls.check_tenant_isolation(
            user_id="user-1",
            tenant_id="tenant-1",
            resource_id="doc-1",
            resource_type="document"
        )
        
        # Should return False since user_tenant is None (mock)
        assert result is False
    
    def test_tenant_scoped_query(self, rls):
        """Test tenant-scoped query generation."""
        query = "SELECT * FROM documents WHERE status = 'active'"
        result = rls.get_tenant_scoped_query(
            base_query=query,
            tenant_id="tenant-123",
            table="documents"
        )
        
        assert "tenant_id = 'tenant-123'" in result
        assert "status = 'active'" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
