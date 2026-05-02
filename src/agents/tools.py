"""Tool Registry and Base Tool Implementation.

This module implements the tool use pattern for dynamic tool invocation
in agentic RAG systems.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of tools available to agents."""
    SEARCH = "search"
    ANALYSIS = "analysis"
    DATA_ACCESS = "data_access"
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"


@dataclass
class ToolDefinition:
    """Definition of an available tool."""
    tool_id: str
    name: str
    category: ToolCategory
    description: str
    parameters: Dict[str, Dict[str, str]]  # param_name -> {type, description}
    returns: str
    examples: List[str] = field(default_factory=list)


class BaseTool:
    """Base class for all tools in the system."""
    
    def __init__(self, registry: "ToolRegistry"):
        """Initialize base tool.
        
        Args:
            registry: ToolRegistry instance for tool registration
        """
        self.registry = registry
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: int = 300  # 5 minutes default TTL
    
    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition.
        
        Returns:
            ToolDefinition: Tool metadata
        """
        raise NotImplementedError
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool.
        
        Args:
            **kwargs: Tool parameters
            
        Returns:
            Dict: Tool execution result
        """
        raise NotImplementedError
    
    def _get_cache_key(self, kwargs: Dict[str, Any]) -> str:
        """Generate cache key from parameters.
        
        Args:
            kwargs: Tool parameters
            
        Returns:
            str: Cache key
        """
        key_str = str(sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, kwargs: Dict[str, Any]) -> Optional[Any]:
        """Get result from cache if available.
        
        Args:
            kwargs: Tool parameters
            
        Returns:
            Optional[Any]: Cached result or None
        """
        key = self._get_cache_key(kwargs)
        return self._cache.get(key)
    
    def _set_in_cache(self, kwargs: Dict[str, Any], result: Any) -> None:
        """Store result in cache.
        
        Args:
            kwargs: Tool parameters
            result: Result to cache
        """
        key = self._get_cache_key(kwargs)
        self._cache[key] = result


class KnowledgeSearchTool(BaseTool):
    """Tool for searching knowledge base."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="knowledge_search",
            name="Knowledge Search",
            category=ToolCategory.SEARCH,
            description="Search the knowledge base for relevant documents",
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "int", "description": "Maximum results to return"},
                "filters": {"type": "dict", "description": "Optional filters"}
            },
            returns="List of relevant documents with metadata",
            examples=[
                "search(query='machine learning basics', limit=10)",
                "search(query='Python tutorials', filters={'type': 'tutorial'})"
            ]
        )
    
    def execute(self, query: str, limit: int = 10, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute knowledge search.
        
        Args:
            query: Search query
            limit: Maximum results
            filters: Optional filters
            
        Returns:
            Dict: Search results
        """
        logger.info(f"Executing knowledge search: {query[:50]}...")
        
        # Placeholder implementation - in production would integrate with actual search
        results = [
            {
                "id": f"doc_{i}",
                "title": f"Document {i} about {query[:20]}",
                "content": f"This is retrieved content related to: {query}",
                "score": 0.9 - (i * 0.05),
                "metadata": {"source": "knowledge_base", "filters_applied": filters or {}}
            }
            for i in range(limit)
        ]
        
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "filters": filters or {}
        }


class DataQueryTool(BaseTool):
    """Tool for querying structured data."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="data_query",
            name="Data Query",
            category=ToolCategory.DATA_ACCESS,
            description="Query structured data sources",
            parameters={
                "table": {"type": "string", "description": "Table name"},
                "conditions": {"type": "dict", "description": "Query conditions"},
                "columns": {"type": "list", "description": "Columns to retrieve"}
            },
            returns="Query results as list of records",
            examples=[
                "query(table='users', conditions={'active': True})",
                "query(table='products', columns=['name', 'price'])"
            ]
        )
    
    def execute(
        self,
        table: str,
        conditions: Optional[Dict] = None,
        columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute data query.
        
        Args:
            table: Table name
            conditions: Query conditions
            columns: Columns to retrieve
            
        Returns:
            Dict: Query results
        """
        logger.info(f"Executing data query: {table}")
        
        # Placeholder implementation
        return {
            "table": table,
            "results": [
                {"id": i, "name": f"Item {i}", "value": i * 10}
                for i in range(5)
            ],
            "count": 5,
            "conditions": conditions or {}
        }


class AnalysisTool(BaseTool):
    """Tool for data analysis."""
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="analysis",
            name="Analysis",
            category=ToolCategory.ANALYSIS,
            description="Perform analysis on data or text",
            parameters={
                "data": {"type": "list", "description": "Data to analyze"},
                "analysis_type": {"type": "string", "description": "Type of analysis"},
                "parameters": {"type": "dict", "description": "Analysis parameters"}
            },
            returns="Analysis results",
            examples=[
                "analyze(data=documents, analysis_type='sentiment')",
                "analyze(data=numbers, analysis_type='statistics')"
            ]
        )
    
    def execute(
        self,
        data: List[Any],
        analysis_type: str,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute analysis.
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis
            parameters: Analysis parameters
            
        Returns:
            Dict: Analysis results
        """
        logger.info(f"Executing {analysis_type} analysis on {len(data)} items")
        
        # Placeholder implementation
        return {
            "analysis_type": analysis_type,
            "input_count": len(data),
            "results": {
                "summary": f"Analysis of {len(data)} items completed",
                "metrics": {"count": len(data), "avg": sum(data) / len(data) if data else 0}
            },
            "parameters": parameters or {}
        }


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
        logger.info(f"ToolRegistry initialized with {len(self._tools)} tools")
    
    def _register_default_tools(self) -> None:
        """Register default tools."""
        self.register(KnowledgeSearchTool(self))
        self.register(DataQueryTool(self))
        self.register(AnalysisTool(self))
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool.
        
        Args:
            tool: Tool to register
        """
        tool_id = tool.definition.tool_id
        self._tools[tool_id] = tool
        logger.info(f"Registered tool: {tool_id}")
    
    def unregister(self, tool_id: str) -> None:
        """Unregister a tool.
        
        Args:
            tool_id: Tool ID to unregister
        """
        if tool_id in self._tools:
            del self._tools[tool_id]
            logger.info(f"Unregistered tool: {tool_id}")
    
    def get(self, tool_id: str) -> Optional[BaseTool]:
        """Get a tool by ID.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Optional[BaseTool]: Tool if found
        """
        return self._tools.get(tool_id)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools.
        
        Returns:
            List[Dict]: List of tool definitions
        """
        return [
            {
                "tool_id": tool.definition.tool_id,
                "name": tool.definition.name,
                "category": tool.definition.category.value,
                "description": tool.definition.description
            }
            for tool in self._tools.values()
        ]
    
    def invoke(self, tool_id: str, **kwargs) -> Dict[str, Any]:
        """Invoke a tool.
        
        Args:
            tool_id: Tool ID to invoke
            **kwargs: Tool parameters
            
        Returns:
            Dict: Tool execution result
            
        Raises:
            ValueError: If tool not found
        """
        tool = self._tools.get(tool_id)
        if not tool:
            raise ValueError(f"Tool not found: {tool_id}")
        
        logger.info(f"Invoking tool: {tool_id}")
        return tool.execute(**kwargs)
    
    def get_tool_definition(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get tool definition.
        
        Args:
            tool_id: Tool ID
            
        Returns:
            Optional[ToolDefinition]: Tool definition if found
        """
        tool = self._tools.get(tool_id)
        if tool:
            return tool.definition
        return None
