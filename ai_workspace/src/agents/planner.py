"""Query Planner Module.

This module implements the planning pattern for query decomposition
and multi-step task planning in agentic RAG systems.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Types of tasks that can be planned."""
    SEARCH = "search"
    ANALYZE = "analyze"
    COMPARE = "compare"
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    VALIDATE = "validate"


@dataclass
class PlannedTask:
    """Represents a single task in the execution plan."""
    task_id: str
    task_type: TaskType
    description: str
    dependencies: List[str] = None
    parameters: Dict[str, Any] = None
    expected_output: str = ""
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.parameters is None:
            self.parameters = {}


class QueryPlanner:
    """Query planner for decomposing complex queries into executable tasks.
    
    This planner implements the planning pattern by:
    1. Analyzing query complexity
    2. Decomposing into sub-tasks
    3. Establishing dependencies
    4. Generating execution order
    """
    
    def __init__(self, llm_client: Any, max_tasks: int = 10):
        """Initialize the Query Planner.
        
        Args:
            llm_client: LLM client for task decomposition
            max_tasks: Maximum number of tasks to generate
        """
        self.llm = llm_client
        self.max_tasks = max_tasks
        logger.info(f"QueryPlanner initialized with max_tasks={max_tasks}")
    
    def plan(self, query: str, context: Optional[List[str]] = None) -> List[PlannedTask]:
        """Create a multi-step plan for the given query.
        
        Args:
            query: The user query to plan
            context: Optional additional context
            
        Returns:
            List[PlannedTask]: Ordered list of tasks to execute
        """
        logger.info(f"Planning query: {query[:50]}...")
        
        # Step 1: Analyze query complexity
        complexity = self._analyze_query_complexity(query)
        logger.info(f"Query complexity: {complexity}")
        
        # Step 2: Decompose into tasks
        tasks = self._decompose_query(query, complexity, context)
        
        # Step 3: Establish dependencies
        tasks = self._establish_dependencies(tasks)
        
        # Step 4: Sort by execution order
        tasks = self._sort_by_execution_order(tasks)
        
        logger.info(f"Created plan with {len(tasks)} tasks")
        return tasks
    
    def _analyze_query_complexity(self, query: str) -> str:
        """Analyze query complexity to guide planning.
        
        Args:
            query: The query to analyze
            
        Returns:
            str: Complexity level (simple, moderate, complex)
        """
        complexity_prompt = (
            f"Analyze the complexity of this query:\n\n"
            f"Query: {query}\n\n"
            f"Classify as:\n"
            f"- SIMPLE: Single concept, straightforward\n"
            f"- MODERATE: Multiple concepts, some relationships\n"
            f"- COMPLEX: Multiple concepts, comparisons, or requires synthesis\n\n"
            f"Return only: SIMPLE, MODERATE, or COMPLEX"
        )
        
        try:
            result = self.llm.generate(complexity_prompt).strip().upper()
            if result in ["SIMPLE", "MODERATE", "COMPLEX"]:
                return result
            else:
                # Default to moderate if parsing fails
                return "MODERATE"
        except Exception as e:
            logger.warning(f"Could not analyze complexity: {e}")
            return "MODERATE"
    
    def _decompose_query(
        self,
        query: str,
        complexity: str,
        context: Optional[List[str]] = None
    ) -> List[PlannedTask]:
        """Decompose query into executable tasks.
        
        Args:
            query: The original query
            complexity: Query complexity level
            context: Additional context
            
        Returns:
            List[PlannedTask]: Decomposed tasks
        """
        decomposition_prompt = (
            f"Decompose this query into executable tasks:\n\n"
            f"Query: {query}\n\n"
            f"Complexity: {complexity}\n"
        )
        
        if context:
            decomposition_prompt += f"\nContext: {' '.join(context)}\n"
        
        decomposition_prompt += (
            f"\nProvide tasks in JSON format as a list with fields:\n"
            f"- task_type: search, analyze, compare, summarize, extract, or validate\n"
            f"- description: Clear description of the task\n"
            f"- parameters: Key-value pairs for task parameters\n"
            f"- expected_output: What the task should produce\n\n"
            f"Example format:\n"
            f'[{{"task_type": "search", "description": "Find information about X", "parameters": {{}}, "expected_output": "List of relevant documents"}}]'
        )
        
        try:
            result = self.llm.generate(decomposition_prompt)
            
            # Try to parse as JSON
            try:
                tasks_data = json.loads(result)
                tasks = [self._task_data_to_planned_task(data, idx) for idx, data in enumerate(tasks_data)]
            except json.JSONDecodeError:
                # Fallback: create default tasks based on complexity
                tasks = self._create_default_tasks(query, complexity)
            
            return tasks[:self.max_tasks]
            
        except Exception as e:
            logger.error(f"Error decomposing query: {e}")
            return self._create_default_tasks(query, complexity)
    
    def _task_data_to_planned_task(self, data: Dict, task_id: int) -> PlannedTask:
        """Convert task data dictionary to PlannedTask object.
        
        Args:
            data: Task data dictionary
            task_id: Task identifier
            
        Returns:
            PlannedTask: Task object
        """
        return PlannedTask(
            task_id=f"task_{task_id}",
            task_type=TaskType(data.get("task_type", "search")),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            expected_output=data.get("expected_output", "")
        )
    
    def _create_default_tasks(
        self,
        query: str,
        complexity: str
    ) -> List[PlannedTask]:
        """Create default tasks based on query complexity.
        
        Args:
            query: Original query
            complexity: Complexity level
            
        Returns:
            List[PlannedTask]: Default tasks
        """
        if complexity == "SIMPLE":
            return [
                PlannedTask(
                    task_id="task_0",
                    task_type=TaskType.SEARCH,
                    description=f"Search for information about: {query}",
                    parameters={"query": query},
                    expected_output="Relevant documents and information"
                )
            ]
        elif complexity == "MODERATE":
            return [
                PlannedTask(
                    task_id="task_0",
                    task_type=TaskType.SEARCH,
                    description="Search for key entities and concepts",
                    parameters={"query": query},
                    expected_output="List of relevant documents"
                ),
                PlannedTask(
                    task_id="task_1",
                    task_type=TaskType.ANALYZE,
                    description="Analyze and synthesize retrieved information",
                    dependencies=["task_0"],
                    expected_output="Synthesized answer"
                )
            ]
        else:  # COMPLEX
            return [
                PlannedTask(
                    task_id="task_0",
                    task_type=TaskType.SEARCH,
                    description="Search for first set of information",
                    parameters={"query": query},
                    expected_output="Initial search results"
                ),
                PlannedTask(
                    task_id="task_1",
                    task_type=TaskType.SEARCH,
                    description="Search for additional related information",
                    dependencies=["task_0"],
                    expected_output="Secondary search results"
                ),
                PlannedTask(
                    task_id="task_2",
                    task_type=TaskType.COMPARE,
                    description="Compare and contrast different information sources",
                    dependencies=["task_0", "task_1"],
                    expected_output="Comparative analysis"
                ),
                PlannedTask(
                    task_id="task_3",
                    task_type=TaskType.SUMMARIZE,
                    description="Summarize all findings into coherent answer",
                    dependencies=["task_2"],
                    expected_output="Final synthesized answer"
                )
            ]
    
    def _establish_dependencies(self, tasks: List[PlannedTask]) -> List[PlannedTask]:
        """Establish dependencies between tasks.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            List[PlannedTask]: Tasks with dependencies established
        """
        # Simple dependency establishment based on task types
        for i, task in enumerate(tasks):
            if task.dependencies:
                continue  # Dependencies already set
            
            # If this is not the first task and previous task is not a search,
            # add dependency on previous task
            if i > 0 and tasks[i-1].task_type != TaskType.SEARCH:
                task.dependencies.append(f"task_{i-1}")
        
        return tasks
    
    def _sort_by_execution_order(self, tasks: List[PlannedTask]) -> List[PlannedTask]:
        """Sort tasks by execution order respecting dependencies.
        
        Args:
            tasks: List of tasks to sort
            
        Returns:
            List[PlannedTask]: Sorted tasks
        """
        # Simple topological sort
        sorted_tasks = []
        remaining = list(tasks)
        
        while remaining:
            # Find tasks with all dependencies satisfied
            ready = []
            for task in remaining:
                deps_satisfied = all(
                    dep in [t.task_id for t in sorted_tasks]
                    for dep in task.dependencies
                )
                if deps_satisfied:
                    ready.append(task)
            
            if not ready:
                # No progress possible, add remaining tasks
                sorted_tasks.extend(remaining)
                break
            
            # Add ready tasks to sorted list
            for task in ready:
                sorted_tasks.append(task)
                remaining.remove(task)
        
        return sorted_tasks
    
    def get_task_by_id(self, tasks: List[PlannedTask], task_id: str) -> Optional[PlannedTask]:
        """Get a specific task by ID.
        
        Args:
            tasks: List of tasks to search
            task_id: Task ID to find
            
        Returns:
            Optional[PlannedTask]: Task if found, None otherwise
        """
        for task in tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def get_next_task(
        self,
        tasks: List[PlannedTask],
        completed_tasks: List[str]
    ) -> Optional[PlannedTask]:
        """Get the next task to execute.
        
        Args:
            tasks: All planned tasks
            completed_tasks: IDs of completed tasks
            
        Returns:
            Optional[PlannedTask]: Next task or None if all complete
        """
        for task in tasks:
            if task.task_id not in completed_tasks:
                # Check if all dependencies are satisfied
                deps_satisfied = all(
                    dep in completed_tasks
                    for dep in task.dependencies
                )
                if deps_satisfied:
                    return task
        return None
    
    def validate_plan(self, tasks: List[PlannedTask]) -> bool:
        """Validate that the plan is executable.
        
        Args:
            tasks: Tasks to validate
            
        Returns:
            bool: True if plan is valid
        """
        # Check for circular dependencies
        task_ids = {task.task_id for task in tasks}
        
        for task in tasks:
            if task.task_id not in task_ids:
                return False
            if not task.description:
                return False
        
        # Check that all dependencies reference valid tasks
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    return False
        
        return True
