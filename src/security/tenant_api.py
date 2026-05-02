"""Tenant API layer for secure data access control."""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import secrets

from .tenant_context import TenantContext, TenantContextManager


class TenantAPI:
    """API layer for tenant isolation and access control."""
    
    def __init__(
        self, 
        db_client: Any, 
        identity_provider: Any,
        secret_key: str = None
    ):
        """
        Initialize the Tenant API.
        
        Args:
            db_client: Database client for data operations
            identity_provider: Identity provider for authentication
            secret_key: JWT secret key for token signing
        """
        self.db = db_client
        self.identity = identity_provider
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.api = FastAPI(title="Tenant Isolation API", version="1.0.0")
        self.security = HTTPBearer()
        self._setup_routes()
        self._setup_middleware()
    
    def _setup_routes(self):
        """Setup API routes for secure data access."""
        
        @self.api.get("/api/v1/documents")
        async def get_documents(
            credentials: HTTPAuthorizationCredentials = Security(self.security),
            tenant_filter: Optional[str] = None,
            limit: int = 100,
            offset: int = 0
        ):
            """
            Get documents with tenant isolation.
            
            Args:
                credentials: Authentication credentials
                tenant_filter: Optional tenant filter
                limit: Maximum number of results
                offset: Pagination offset
                
            Returns:
                List of documents accessible to the authenticated user
            """
            try:
                # Authenticate user
                user = await self._authenticate(credentials)
                
                # Get tenant context
                tenant_context = await self._get_tenant_context(user)
                
                # Apply security trimming
                filter_query = self._apply_security_trimming(tenant_context)
                
                # Query with tenant discriminator
                documents = await self.db.query(
                    f"""
                    SELECT * FROM documents 
                    WHERE {filter_query}
                    LIMIT {limit} OFFSET {offset}
                    """,
                    tenant_context.tenant_id
                )
                
                # Log access
                await self._audit_log(user, "GET", "documents", documents)
                
                return {"documents": documents, "count": len(documents)}
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.api.post("/api/v1/documents")
        async def create_document(
            document: Dict,
            credentials: HTTPAuthorizationCredentials = Security(self.security),
        ):
            """
            Create a new document with tenant association.
            
            Args:
                document: Document data
                credentials: Authentication credentials
                
            Returns:
                Created document
            """
            # Authenticate user
            user = await self._authenticate(credentials)
            
            # Get tenant context
            tenant_context = await self._get_tenant_context(user)
            
            # Associate document with tenant
            document["tenant_id"] = tenant_context.tenant_id
            document["created_by"] = user["id"]
            document["created_at"] = datetime.utcnow().isoformat()
            
            # Insert document
            result = await self.db.insert("documents", document)
            
            # Log access
            await self._audit_log(user, "POST", "documents", result)
            
            return result
        
        @self.api.get("/api/v1/documents/{document_id}")
        async def get_document(
            document_id: str,
            credentials: HTTPAuthorizationCredentials = Security(self.security)
        ):
            """
            Get a specific document with access validation.
            
            Args:
                document_id: Document identifier
                credentials: Authentication credentials
                
            Returns:
                Document if accessible
            """
            # Authenticate user
            user = await self._authenticate(credentials)
            
            # Get document
            document = await self.db.get("documents", document_id)
            
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Validate tenant access
            tenant_context = await self._get_tenant_context(user)
            if not self._validate_tenant_access(tenant_context, document):
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Log access
            await self._audit_log(user, "GET", f"documents:{document_id}", document)
            
            return document
        
        @self.api.delete("/api/v1/documents/{document_id}")
        async def delete_document(
            document_id: str,
            credentials: HTTPAuthorizationCredentials = Security(self.security)
        ):
            """
            Delete a document with access validation.
            
            Args:
                document_id: Document identifier
                credentials: Authentication credentials
                
            Returns:
                Success status
            """
            # Authenticate user
            user = await self._authenticate(credentials)
            
            # Get document to validate access
            document = await self.db.get("documents", document_id)
            
            if not document:
                raise HTTPException(status_code=404, detail="Document not found")
            
            # Validate tenant access
            tenant_context = await self._get_tenant_context(user)
            if not self._validate_tenant_access(tenant_context, document):
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Delete document
            result = await self.db.delete("documents", document_id)
            
            # Log access
            await self._audit_log(user, "DELETE", f"documents:{document_id}", result)
            
            return {"status": "deleted", "document_id": document_id}
        
        @self.api.post("/api/v1/queries")
        async def execute_query(
            query: Dict,
            credentials: HTTPAuthorizationCredentials = Security(self.security)
        ):
            """
            Execute a search query with tenant isolation.
            
            Args:
                query: Search query with content and options
                credentials: Authentication credentials
                
            Returns:
                Search results
            """
            # Authenticate user
            user = await self._authenticate(credentials)
            
            # Get tenant context
            tenant_context = await self._get_tenant_context(user)
            
            # Execute query with tenant isolation
            results = await self._execute_isolated_query(
                query.get("content", ""),
                tenant_context,
                query.get("options", {})
            )
            
            # Log access
            await self._audit_log(user, "QUERY", "documents", results)
            
            return {"results": results, "count": len(results)}
        
        @self.api.get("/api/v1/tenants/{tenant_id}/documents")
        async def get_tenant_documents(
            tenant_id: str,
            credentials: HTTPAuthorizationCredentials = Security(self.security),
            limit: int = 100,
            offset: int = 0
        ):
            """
            Get all documents for a tenant (admin function).
            
            Args:
                tenant_id: Tenant identifier
                credentials: Authentication credentials
                limit: Maximum results
                offset: Pagination offset
                
            Returns:
                All documents for the tenant
            """
            # Authenticate user
            user = await self._authenticate(credentials)
            
            # Check admin permissions
            tenant_context = await self._get_tenant_context(user)
            if "admin" not in tenant_context.permissions:
                raise HTTPException(status_code=403, detail="Admin access required")
            
            # Get documents for tenant
            documents = await self.db.query(
                f"""
                SELECT * FROM documents 
                WHERE tenant_id = '{tenant_id}'
                LIMIT {limit} OFFSET {offset}
                """
            )
            
            # Log access
            await self._audit_log(user, "GET", f"tenant:{tenant_id}:documents", documents)
            
            return {"documents": documents, "count": len(documents)}
    
    def _setup_middleware(self):
        """Setup API middleware."""
        
        @self.api.middleware("http")
        async def log_request(request, call_next):
            """Log all incoming requests."""
            start_time = datetime.utcnow()
            response = await call_next(request)
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log to audit system
            # This is simplified - in production use proper logging
            print(f"Request: {request.method} {request.url.path} - {duration:.3f}s")
            
            return response
    
    async def _authenticate(
        self, 
        credentials: HTTPAuthorizationCredentials
    ) -> Dict:
        """
        Authenticate user via credentials.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            User dictionary with id and permissions
            
        Raises:
            HTTPException: If authentication fails
        """
        token = credentials.credentials
        
        try:
            # Verify JWT token
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Get user info from identity provider
            user = await self.identity.get_user(user_id)
            
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            
            return user
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    async def _get_tenant_context(self, user: Dict) -> TenantContext:
        """
        Get tenant context for authenticated user.
        
        Args:
            user: User dictionary
            
        Returns:
            TenantContext
        """
        tenant_id = user.get("tenant_id")
        permissions = user.get("permissions", [])
        
        return TenantContext(
            tenant_id=tenant_id,
            user_id=user["id"],
            permissions=permissions,
            is_authenticated=True
        )
    
    def _apply_security_trimming(self, context: TenantContext) -> str:
        """
        Apply security trimming based on user permissions.
        
        Args:
            context: Tenant context
            
        Returns:
            SQL WHERE clause for filtering
        """
        filters = []
        
        # Tenant filter (required)
        filters.append(f"tenant_id = '{context.tenant_id}'")
        
        # Permission-based filters
        if "read_public" in context.permissions:
            filters.append("is_public = true OR is_public IS NULL")
        
        if "read_private" in context.permissions:
            filters.append("access_level IN ('private', 'restricted') OR access_level IS NULL")
        
        if "read_restricted" in context.permissions:
            filters.append("access_level = 'restricted' OR access_level IS NULL")
        
        return " AND ".join(filters) if filters else "1=1"
    
    def _validate_tenant_access(
        self, 
        context: TenantContext, 
        resource: Dict
    ) -> bool:
        """
        Validate if user can access a specific resource.
        
        Args:
            context: Tenant context
            resource: Resource to check access for
            
        Returns:
            True if access is allowed
        """
        # Check tenant match
        if resource.get("tenant_id") != context.tenant_id:
            return False
        
        # Check permissions based on resource access level
        access_level = resource.get("access_level", "public")
        
        if access_level == "public":
            return True
        
        if access_level == "private" and "read_private" in context.permissions:
            return True
        
        if access_level == "restricted" and "read_restricted" in context.permissions:
            return True
        
        return False
    
    async def _execute_isolated_query(
        self, 
        query: str, 
        context: TenantContext,
        options: Dict = None
    ) -> List[Dict]:
        """
        Execute query with full tenant isolation.
        
        Args:
            query: Search query content
            context: Tenant context
            options: Query options (limit, offset, etc.)
            
        Returns:
            Search results
        """
        # Apply tenant discriminator
        filter_query = self._apply_security_trimming(context)
        
        # Get query options
        limit = options.get("limit", 100) if options else 100
        offset = options.get("offset", 0) if options else 0
        
        # Execute query
        results = await self.db.query(
            f"""
            SELECT * FROM documents 
            WHERE {filter_query}
            AND content MATCH '{query}'
            LIMIT {limit} OFFSET {offset}
            """
        )
        
        return results
    
    async def _audit_log(
        self, 
        user: Dict, 
        action: str, 
        resource: str, 
        results: Any
    ) -> None:
        """
        Log data access for audit purposes.
        
        Args:
            user: User dictionary
            action: Action performed (GET, POST, DELETE, QUERY)
            resource: Resource accessed
            results: Query results or affected records
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user.get("id"),
            "tenant_id": user.get("tenant_id"),
            "action": action,
            "resource": resource,
            "result_count": len(results) if isinstance(results, (list, dict)) else 1,
            "ip_address": "unknown",  # Would get from request in production
            "user_agent": "unknown"   # Would get from request in production
        }
        
        # Insert audit log
        await self.db.insert("audit_log", audit_entry)
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """
        Run the API server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
        """
        import uvicorn
        uvicorn.run(self.api, host=host, port=port)
