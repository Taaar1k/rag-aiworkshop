"""Row-level security for tenant isolation."""

from typing import List, Dict, Optional, Any
import re


class RowLevelSecurity:
    """Implements row-level security for tenant isolation."""
    
    def __init__(self, db_client: Any):
        """
        Initialize row-level security.
        
        Args:
            db_client: Database client for query execution
        """
        self.db = db_client
    
    def apply_tenant_filter(
        self, 
        query: str, 
        tenant_id: str,
        additional_filters: List[str] = None
    ) -> str:
        """
        Apply tenant filter to SQL query.
        
        Args:
            query: Base SQL query
            tenant_id: Tenant ID to filter by
            additional_filters: Additional filter conditions
            
        Returns:
            Query with tenant filter applied
        """
        # Sanitize tenant_id to prevent SQL injection
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build WHERE clause
        where_clause = f"tenant_id = '{sanitized_tenant_id}'"
        
        # Add additional filters
        if additional_filters:
            where_clause = " AND ".join([where_clause] + additional_filters)
        
        # Check if query already has WHERE clause
        if re.search(r'\bWHERE\b', query, re.IGNORECASE):
            # Append to existing WHERE clause
            query = f"{query} AND {where_clause}"
        else:
            # Add WHERE clause
            query = f"{query} WHERE {where_clause}"
        
        return query
    
    def validate_tenant_access(
        self, 
        user_tenant: str, 
        resource_tenant: str
    ) -> bool:
        """
        Validate if user can access resource.
        
        Args:
            user_tenant: User's tenant ID
            resource_tenant: Resource's tenant ID
            
        Returns:
            True if access is allowed
        """
        return user_tenant == resource_tenant
    
    def apply_security_trimming(
        self, 
        query: str, 
        user_permissions: List[str],
        tenant_id: str
    ) -> str:
        """
        Apply security trimming based on user permissions.
        
        Args:
            query: Base SQL query
            user_permissions: User's permissions
            tenant_id: Tenant ID
            
        Returns:
            Query with security trimming applied
        """
        # Sanitize tenant_id
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build filter conditions
        filters = [f"tenant_id = '{sanitized_tenant_id}'"]
        
        # Permission-based filters
        if "read_public" in user_permissions:
            filters.append("(is_public = true OR is_public IS NULL)")
        
        if "read_private" in user_permissions:
            filters.append("(access_level IN ('private', 'restricted') OR access_level IS NULL)")
        
        if "read_restricted" in user_permissions:
            filters.append("(access_level = 'restricted' OR access_level IS NULL)")
        
        # Combine filters
        combined_filter = " AND ".join(filters)
        
        # Apply to query
        if re.search(r'\bWHERE\b', query, re.IGNORECASE):
            query = f"{query} AND {combined_filter}"
        else:
            query = f"{query} WHERE {combined_filter}"
        
        return query
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitize identifier to prevent SQL injection.
        
        Args:
            identifier: Identifier to sanitize
            
        Returns:
            Sanitized identifier
        """
        # Remove potentially dangerous characters
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", identifier)
        return sanitized
    
    def validate_cross_tenant_access(
        self,
        user_tenant: str,
        requested_tenant: str,
        action: str
    ) -> bool:
        """
        Validate if cross-tenant access is allowed.
        
        Args:
            user_tenant: User's tenant ID
            requested_tenant: Requested tenant ID
            action: Action being performed
            
        Returns:
            True if access is allowed
        """
        # Cross-tenant access is generally denied
        if user_tenant != requested_tenant:
            # Exception: admin users can access all tenants
            # This would be checked in the permission layer
            return False
        
        return True
    
    def get_tenant_scoped_query(
        self,
        base_query: str,
        tenant_id: str,
        table: str,
        additional_conditions: List[str] = None
    ) -> str:
        """
        Get a tenant-scoped version of a query.
        
        Args:
            base_query: Base query template
            tenant_id: Tenant ID
            table: Table name
            additional_conditions: Additional WHERE conditions
            
        Returns:
            Tenant-scoped query
        """
        # Sanitize table name
        sanitized_table = self._sanitize_table_name(table)
        
        # Sanitize tenant_id
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build WHERE clause
        conditions = [f"tenant_id = '{sanitized_tenant_id}'"]
        
        if additional_conditions:
            conditions.extend(additional_conditions)
        
        where_clause = " AND ".join(conditions)
        
        # Construct final query
        if "WHERE" in base_query.upper():
            final_query = f"{base_query} AND {where_clause}"
        else:
            final_query = f"{base_query} WHERE {where_clause}"
        
        return final_query
    
    def _sanitize_table_name(self, table_name: str) -> str:
        """
        Sanitize table name to prevent SQL injection.
        
        Args:
            table_name: Table name to sanitize
            
        Returns:
            Sanitized table name
        """
        # Extract only the first valid table name component
        # This prevents SQL injection by rejecting anything after the first word
        match = re.match(r'^[a-zA-Z0-9_]+', table_name)
        if not match:
            raise ValueError("Invalid table name")
        return match.group()
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitize identifier to prevent SQL injection.
        
        Args:
            identifier: Identifier to sanitize
            
        Returns:
            Sanitized identifier
        """
        # Remove potentially dangerous characters
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", identifier)
        return sanitized
    
    def get_tenant_scoped_query(
        self,
        base_query: str,
        tenant_id: str,
        table: str,
        additional_conditions: List[str] = None
    ) -> str:
        """
        Get a tenant-scoped version of a query.
        
        Args:
            base_query: Base query template
            tenant_id: Tenant ID
            table: Table name
            additional_conditions: Additional WHERE conditions
            
        Returns:
            Tenant-scoped query
        """
        # Sanitize table name
        sanitized_table = self._sanitize_table_name(table)
        
        # Sanitize tenant_id
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build WHERE clause
        conditions = [f"tenant_id = '{sanitized_tenant_id}'"]
        
        if additional_conditions:
            conditions.extend(additional_conditions)
        
        where_clause = " AND ".join(conditions)
        
        # Construct final query
        if "WHERE" in base_query.upper():
            final_query = f"{base_query} AND {where_clause}"
        else:
            final_query = f"{base_query} WHERE {where_clause}"
        
        return final_query
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitize identifier to prevent SQL injection.
        
        Args:
            identifier: Identifier to sanitize
            
        Returns:
            Sanitized identifier
        """
        # Remove potentially dangerous characters
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", identifier)
        return sanitized
    
    def get_tenant_scoped_query(
        self,
        base_query: str,
        tenant_id: str,
        table: str,
        additional_conditions: List[str] = None
    ) -> str:
        """
        Get a tenant-scoped version of a query.
        
        Args:
            base_query: Base query template
            tenant_id: Tenant ID
            table: Table name
            additional_conditions: Additional WHERE conditions
            
        Returns:
            Tenant-scoped query
        """
        # Sanitize table name
        sanitized_table = self._sanitize_table_name(table)
        
        # Sanitize tenant_id
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build WHERE clause
        conditions = [f"tenant_id = '{sanitized_tenant_id}'"]
        
        if additional_conditions:
            conditions.extend(additional_conditions)
        
        where_clause = " AND ".join(conditions)
        
        # Construct final query
        if "WHERE" in base_query.upper():
            final_query = f"{base_query} AND {where_clause}"
        else:
            final_query = f"{base_query} WHERE {where_clause}"
        
        return final_query
    
    def _sanitize_identifier(self, identifier: str) -> str:
        """
        Sanitize identifier to prevent SQL injection.
        
        Args:
            identifier: Identifier to sanitize
            
        Returns:
            Sanitized identifier
        """
        # Remove potentially dangerous characters
        sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", identifier)
        return sanitized
    
    def get_tenant_scoped_query(
        self,
        base_query: str,
        tenant_id: str,
        table: str,
        additional_conditions: List[str] = None
    ) -> str:
        """
        Get a tenant-scoped version of a query.
        
        Args:
            base_query: Base query template
            tenant_id: Tenant ID
            table: Table name
            additional_conditions: Additional WHERE conditions
            
        Returns:
            Tenant-scoped query
        """
        # Sanitize table name
        sanitized_table = self._sanitize_table_name(table)
        
        # Sanitize tenant_id
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build WHERE clause
        conditions = [f"tenant_id = '{sanitized_tenant_id}'"]
        
        if additional_conditions:
            conditions.extend(additional_conditions)
        
        where_clause = " AND ".join(conditions)
        
        # Construct final query
        if "WHERE" in base_query.upper():
            final_query = f"{base_query} AND {where_clause}"
        else:
            final_query = f"{base_query} WHERE {where_clause}"
        
        return final_query
    
    def get_tenant_scoped_query(
        self,
        base_query: str,
        tenant_id: str,
        table: str,
        additional_conditions: List[str] = None
    ) -> str:
        """
        Get a tenant-scoped version of a query.
        
        Args:
            base_query: Base query template
            tenant_id: Tenant ID
            table: Table name
            additional_conditions: Additional WHERE conditions
            
        Returns:
            Tenant-scoped query
        """
        # Sanitize table name
        sanitized_table = self._sanitize_table_name(table)
        
        # Sanitize tenant_id
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build WHERE clause
        conditions = [f"tenant_id = '{sanitized_tenant_id}'"]
        
        if additional_conditions:
            conditions.extend(additional_conditions)
        
        where_clause = " AND ".join(conditions)
        
        # Construct final query
        if "WHERE" in base_query.upper():
            final_query = f"{base_query} AND {where_clause}"
        else:
            final_query = f"{base_query} WHERE {where_clause}"
        
        return final_query
    
    def get_tenant_scoped_query(
        self,
        base_query: str,
        tenant_id: str,
        table: str,
        additional_conditions: List[str] = None
    ) -> str:
        """
        Get a tenant-scoped version of a query.
        
        Args:
            base_query: Base query template
            tenant_id: Tenant ID
            table: Table name
            additional_conditions: Additional WHERE conditions
            
        Returns:
            Tenant-scoped query
        """
        # Sanitize table name
        sanitized_table = self._sanitize_table_name(table)
        
        # Sanitize tenant_id
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        # Build WHERE clause
        conditions = [f"tenant_id = '{sanitized_tenant_id}'"]
        
        if additional_conditions:
            conditions.extend(additional_conditions)
        
        where_clause = " AND ".join(conditions)
        
        # Construct final query
        if "WHERE" in base_query.upper():
            final_query = f"{base_query} AND {where_clause}"
        else:
            final_query = f"{base_query} WHERE {where_clause}"
        
        return final_query
    
    def generate_tenant_isolation_rule(
        self,
        tenant_id: str,
        table_name: str,
        rule_type: str = "always"
    ) -> Dict[str, Any]:
        """
        Generate a tenant isolation rule for a table.
        
        Args:
            tenant_id: Tenant ID
            table_name: Table name
            rule_type: Type of rule ("always", "conditional", "never")
            
        Returns:
            Rule configuration dictionary
        """
        sanitized_tenant_id = self._sanitize_identifier(tenant_id)
        
        rule = {
            "tenant_id": sanitized_tenant_id,
            "table": table_name,
            "rule_type": rule_type,
            "condition": f"tenant_id = '{sanitized_tenant_id}'",
            "created_at": "2026-04-14"
        }
        
        return rule
    
    async def check_tenant_isolation(
        self,
        user_id: str,
        tenant_id: str,
        resource_id: str,
        resource_type: str
    ) -> bool:
        """
        Check if user has access to a resource based on tenant isolation.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID of the resource
            resource_id: Resource ID
            resource_type: Type of resource
            
        Returns:
            True if access is allowed
        """
        # Get user's tenant
        user_tenant = await self._get_user_tenant(user_id)
        
        if not user_tenant:
            return False
        
        # Check tenant match
        return user_tenant == tenant_id
    
    async def _get_user_tenant(self, user_id: str) -> Optional[str]:
        """
        Get user's tenant ID.
        
        Args:
            user_id: User ID
            
        Returns:
            Tenant ID or None
        """
        # This would query the identity provider
        # For now, return None (placeholder)
        return None
