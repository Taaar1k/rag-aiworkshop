"""Tenant context management for multi-tenant RAG systems."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class TenantContext:
    """Represents the context for a tenant session."""
    
    tenant_id: str
    user_id: str
    permissions: List[str] = field(default_factory=list)
    is_authenticated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, permission: str) -> bool:
        """Check if the tenant context has a specific permission."""
        return permission in self.permissions
    
    def add_permission(self, permission: str) -> None:
        """Add a permission to the context."""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission: str) -> None:
        """Remove a permission from the context."""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary representation."""
        return {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "permissions": self.permissions,
            "is_authenticated": self.is_authenticated,
            "metadata": self.metadata,
            "created_at": datetime.utcnow().isoformat()
        }


class TenantContextManager:
    """Manages tenant context creation and validation."""
    
    def __init__(self, identity_provider: Any, db_client: Any):
        """
        Initialize the tenant context manager.
        
        Args:
            identity_provider: Service for user authentication and identity management
            db_client: Database client for tenant data access
        """
        self.identity = identity_provider
        self.db = db_client
    
    async def create_context(
        self, 
        user_id: str, 
        tenant_id: str,
        token: str
    ) -> Optional[TenantContext]:
        """
        Create a new tenant context for an authenticated user.
        
        Args:
            user_id: Unique identifier for the user
            tenant_id: Unique identifier for the tenant
            token: Authentication token
            
        Returns:
            TenantContext if authentication successful, None otherwise
        """
        # Verify token
        is_valid = await self.identity.verify_token(token)
        if not is_valid:
            return None
        
        # Get user permissions
        permissions = await self.identity.get_user_permissions(user_id)
        
        # Create context
        context = TenantContext(
            tenant_id=tenant_id,
            user_id=user_id,
            permissions=permissions,
            is_authenticated=True
        )
        
        return context
    
    async def get_context(self, user_id: str, tenant_id: str) -> Optional[TenantContext]:
        """
        Retrieve existing tenant context.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            TenantContext if found, None otherwise
        """
        # Check cache first
        cache_key = f"{user_id}:{tenant_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # Fetch from identity provider
        permissions = await self.identity.get_user_permissions(user_id)
        tenant_data = await self.identity.get_user_tenant(user_id)
        
        if tenant_data and tenant_data.get("tenant_id") == tenant_id:
            context = TenantContext(
                tenant_id=tenant_id,
                user_id=user_id,
                permissions=permissions,
                is_authenticated=True
            )
            self._cache_context(cache_key, context)
            return context
        
        return None
    
    async def refresh_context(self, context: TenantContext) -> TenantContext:
        """
        Refresh tenant context with latest permissions.
        
        Args:
            context: Existing tenant context
            
        Returns:
            Updated TenantContext
        """
        permissions = await self.identity.get_user_permissions(context.user_id)
        context.permissions = permissions
        context.is_authenticated = True
        
        return context
    
    def _get_from_cache(self, key: str) -> Optional[TenantContext]:
        """Get context from local cache."""
        # Implementation depends on caching strategy
        # For now, return None
        return None
    
    def _cache_context(self, key: str, context: TenantContext) -> None:
        """Cache a tenant context."""
        # Implementation depends on caching strategy
        # For now, no caching
        pass
    
    async def invalidate_context(self, user_id: str, tenant_id: str) -> bool:
        """
        Invalidate a tenant context (e.g., on logout).
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier
            
        Returns:
            True if invalidated successfully
        """
        cache_key = f"{user_id}:{tenant_id}"
        # Implementation depends on cache invalidation strategy
        return True
    
    async def validate_tenant_access(
        self, 
        user_id: str, 
        resource_tenant_id: str
    ) -> bool:
        """
        Validate if a user can access a resource in a specific tenant.
        
        Args:
            user_id: User identifier
            resource_tenant_id: Tenant ID of the resource
            
        Returns:
            True if access is allowed
        """
        # Get user's tenant
        user_tenant = await self.identity.get_user_tenant(user_id)
        
        if not user_tenant:
            return False
        
        return user_tenant.get("tenant_id") == resource_tenant_id
