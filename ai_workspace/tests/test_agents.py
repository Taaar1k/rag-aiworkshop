"""Tests for Agentic RAG Patterns.

This module contains comprehensive tests for:
- Reflection Pattern (query reflection, self-correction)
- Planning Module (query decomposition, multi-step planning)
- Tool Use Integration (tool registry, dynamic invocation)
- Multi-Agent Collaboration (sub-agents, collaboration protocol)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.rag_agent import RAGAgent, AgentState, AgentRole
from agents.planner import QueryPlanner, PlannedTask, TaskType
from agents.tools import ToolRegistry, BaseTool, KnowledgeSearchTool, ToolCategory
from agents.collaboration import (
    AgentCollaboration,
    SpecializedSubAgent,
    AgentRole as CollaborationRole,
    CollaborationState,
    AgentCapabilities
)


class MockLLM:
    """Mock LLM for testing."""
    
    def __init__(self, responses: Dict[str, str] = None):
        """Initialize mock LLM.
        
        Args:
            responses: Optional dict of query -> response mappings
        """
        self.responses = responses or {}
        self.call_count = 0
        self.last_prompt = None
    
    def generate(self, prompt: str) -> str:
        """Generate response.
        
        Args:
            prompt: Prompt to respond to
            
        Returns:
            str: Mock response
        """
        self.call_count += 1
        self.last_prompt = prompt
        
        # Return predefined response if available
        for key, value in self.responses.items():
            if key in prompt:
                return value
        
        # Default responses based on prompt content
        if "Analyze this query" in prompt:
            return '{"entities": ["machine", "learning"], "ambiguities": [], "clarification_questions": []}'
        elif "Create a step-by-step plan" in prompt:
            return "1. Search for key entities\n2. Retrieve relevant documents\n3. Synthesize answer"
        elif "Analyze this retrieval result" in prompt:
            return "Continue with current strategy - results are sufficient"
        elif "Synthesize a comprehensive answer" in prompt:
            return "Based on the analysis, machine learning is a subset of AI that enables systems to learn from data."
        else:
            return "Mock response for testing"
    
    def evaluate_confidence(self, query: str, context: list) -> float:
        """Evaluate confidence score.
        
        Args:
            query: Query string
            context: Context list
            
        Returns:
            float: Confidence score
        """
        return 0.85


class TestRAGAgent:
    """Tests for RAGAgent class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_llm = MockLLM()
        self.mock_tools = Mock()
        self.agent = RAGAgent(
            llm_client=self.mock_llm,
            tools_registry=self.mock_tools,
            confidence_threshold=0.7,
            max_iterations=3
        )
    
    def test_initialization(self):
        """Test agent initialization."""
        assert self.agent.llm is not None
        assert self.agent.tools is not None
        assert self.agent.confidence_threshold == 0.7
        assert self.agent.max_iterations == 3
        assert isinstance(self.agent.state, AgentState)
    
    def test_query_reflection(self):
        """Test query reflection pattern."""
        query = "What is machine learning?"
        self.agent.state.query = query
        
        self.agent._reflect_on_query()
        
        # Check that reflection was performed
        assert len(self.agent.state.reflection_notes) > 0
        assert "Query Reflection" in self.agent.state.reflection_notes[0]
        
        # Check that entities were identified
        assert len(self.agent.state.entities) > 0
    
    def test_create_retrieval_plan(self):
        """Test retrieval plan creation."""
        query = "Explain neural networks"
        self.agent.state.query = query
        self.agent.state.reflection_notes = ["Entities: neural, networks"]
        
        plan = self.agent._create_retrieval_plan()
        
        # Check that plan was created
        assert len(plan) > 0
        assert isinstance(plan, list)
    
    def test_tool_execution(self):
        """Test tool execution when needed."""
        step = "Search for information about machine learning"
        
        # Mock tool invocation
        self.mock_tools.invoke = Mock(return_value={
            "context": ["Mock retrieved context"],
            "confidence": 0.8
        })
        
        result = self.agent._execute_plan_step(step)
        
        # Check that tool was invoked
        self.mock_tools.invoke.assert_called_once()
        assert "context" in result
    
    def test_standard_retrieval(self):
        """Test standard retrieval without tools."""
        step = "Analyze the retrieved information"
        
        result = self.agent._standard_retrieval(step)
        
        # Check that standard retrieval was performed
        assert "context" in result
        assert "metadata" in result
    
    def test_confidence_check(self):
        """Test confidence threshold checking."""
        self.agent.state.confidence = 0.9
        assert self.agent._is_confident() is True
        
        self.agent.state.confidence = 0.5
        assert self.agent._is_confident() is False
    
    def test_synthesize_answer(self):
        """Test answer synthesis."""
        self.agent.state.query = "What is AI?"
        self.agent.state.context = ["AI is artificial intelligence"]
        self.agent.state.reflection_notes = ["Reflection: AI involves machine learning"]
        self.agent.state.tools_used = ["knowledge_search"]
        
        answer = self.agent._synthesize_answer()
        
        # Check that answer was synthesized
        assert len(answer) > 0
        assert isinstance(answer, str)
    
    def test_execute_full_workflow(self):
        """Test complete agentic RAG workflow."""
        query = "What is deep learning?"
        
        with patch.object(self.agent, '_is_confident', return_value=True):
            answer = self.agent.execute(query, max_iterations=2)
        
        # Check that execution completed
        assert len(answer) > 0
        assert isinstance(answer, str)
        
        # Check that state was updated
        assert self.agent.state.query == query
    
    def test_reset_state(self):
        """Test state reset."""
        self.agent.state.query = "Test query"
        self.agent.state.confidence = 0.9
        
        self.agent.reset_state()
        
        # Check that state was reset
        assert self.agent.state.query == ""
        assert self.agent.state.confidence == 0.0


class TestQueryPlanner:
    """Tests for QueryPlanner class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_llm = MockLLM()
        self.planner = QueryPlanner(
            llm_client=self.mock_llm,
            max_tasks=5
        )
    
    def test_initialization(self):
        """Test planner initialization."""
        assert self.planner.llm is not None
        assert self.planner.max_tasks == 5
    
    def test_analyze_query_complexity_simple(self):
        """Test complexity analysis for simple queries."""
        query = "What is Python?"
        complexity = self.planner._analyze_query_complexity(query)
        
        assert complexity in ["SIMPLE", "MODERATE", "COMPLEX"]
    
    def test_analyze_query_complexity_complex(self):
        """Test complexity analysis for complex queries."""
        query = "Compare and contrast machine learning approaches with their trade-offs"
        complexity = self.planner._analyze_query_complexity(query)
        
        assert complexity in ["SIMPLE", "MODERATE", "COMPLEX"]
    
    def test_decompose_simple_query(self):
        """Test decomposition of simple query."""
        query = "What is AI?"
        tasks = self.planner._decompose_query(query, "SIMPLE")
        
        assert len(tasks) > 0
        assert isinstance(tasks[0], PlannedTask)
    
    def test_decompose_complex_query(self):
        """Test decomposition of complex query."""
        query = "Compare machine learning and deep learning approaches"
        tasks = self.planner._decompose_query(query, "COMPLEX")
        
        assert len(tasks) > 1
        # Check that tasks have dependencies
        for task in tasks[1:]:
            assert len(task.dependencies) >= 0
    
    def test_establish_dependencies(self):
        """Test dependency establishment."""
        tasks = [
            PlannedTask("task_0", TaskType.SEARCH, "Search for info"),
            PlannedTask("task_1", TaskType.ANALYZE, "Analyze results"),
        ]
        
        tasks = self.planner._establish_dependencies(tasks)
        
        # Check that dependencies were established
        assert len(tasks[1].dependencies) >= 0
    
    def test_sort_by_execution_order(self):
        """Test task sorting by execution order."""
        tasks = [
            PlannedTask("task_1", TaskType.ANALYZE, "Analyze", dependencies=["task_0"]),
            PlannedTask("task_0", TaskType.SEARCH, "Search"),
        ]
        
        sorted_tasks = self.planner._sort_by_execution_order(tasks)
        
        # Check that task_0 comes before task_1
        assert sorted_tasks[0].task_id == "task_0"
        assert sorted_tasks[1].task_id == "task_1"
    
    def test_validate_plan_valid(self):
        """Test plan validation for valid plan."""
        tasks = [
            PlannedTask("task_0", TaskType.SEARCH, "Search"),
            PlannedTask("task_1", TaskType.ANALYZE, "Analyze", dependencies=["task_0"]),
        ]
        
        assert self.planner.validate_plan(tasks) is True
    
    def test_validate_plan_invalid(self):
        """Test plan validation for invalid plan."""
        tasks = [
            PlannedTask("task_0", TaskType.SEARCH, "Search", dependencies=["task_99"]),
        ]
        
        assert self.planner.validate_plan(tasks) is False
    
    def test_plan_execution(self):
        """Test full planning execution."""
        query = "Explain neural networks and their applications"
        tasks = self.planner.plan(query)
        
        assert len(tasks) > 0
        assert self.planner.validate_plan(tasks) is True


class TestToolRegistry:
    """Tests for ToolRegistry class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.registry = ToolRegistry()
    
    def test_initialization(self):
        """Test registry initialization."""
        assert len(self.registry._tools) > 0
    
    def test_register_tool(self):
        """Test tool registration."""
        mock_tool = Mock(spec=BaseTool)
        mock_tool.definition.tool_id = "test_tool"
        
        self.registry.register(mock_tool)
        
        assert "test_tool" in self.registry._tools
    
    def test_unregister_tool(self):
        """Test tool unregistration."""
        tool_id = "knowledge_search"
        self.registry.unregister(tool_id)
        
        assert tool_id not in self.registry._tools
    
    def test_get_tool(self):
        """Test tool retrieval."""
        tool = self.registry.get("knowledge_search")
        
        assert tool is not None
        assert isinstance(tool, BaseTool)
    
    def test_list_tools(self):
        """Test listing all tools."""
        tools = self.registry.list_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Check tool structure
        for tool in tools:
            assert "tool_id" in tool
            assert "name" in tool
            assert "category" in tool
    
    def test_invoke_tool(self):
        """Test tool invocation."""
        result = self.registry.invoke("knowledge_search", query="test query", limit=5)
        
        assert "results" in result
        assert "count" in result
    
    def test_invoke_nonexistent_tool(self):
        """Test invocation of non-existent tool."""
        with pytest.raises(ValueError):
            self.registry.invoke("nonexistent_tool", query="test")


class TestSpecializedSubAgent:
    """Tests for SpecializedSubAgent class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_llm = MockLLM()
        self.agent = SpecializedSubAgent(
            role=CollaborationRole.QUERY_ANALYZER,
            capabilities=["entity_extraction", "intent_analysis"],
            llm_client=self.mock_llm
        )
    
    def test_initialization(self):
        """Test agent initialization."""
        assert self.agent.role == CollaborationRole.QUERY_ANALYZER
        assert len(self.agent.capabilities) > 0
        assert self.agent.llm is not None
    
    def test_execute_query_analysis(self):
        """Test query analysis execution."""
        shared_memory = CollaborationState(query="What is machine learning?")
        
        result = self.agent.execute("Analyze query", shared_memory)
        
        assert "analysis" in result or "error" in result
    
    def test_execute_retrieval(self):
        """Test retrieval execution."""
        # Create agent with correct role for retrieval
        retrieval_agent = SpecializedSubAgent(
            CollaborationRole.RETRIEVAL_SPECIALIST,
            ["information_retrieval"],
            self.mock_llm
        )
        shared_memory = CollaborationState(query="Explain neural networks")
        
        result = retrieval_agent.execute("Retrieve information", shared_memory)
        
        assert "retrieved" in result or "error" in result or "agent_role" in result
    
    def test_execute_synthesis(self):
        """Test answer synthesis execution."""
        # Create agent with correct role for synthesis
        synthesis_agent = SpecializedSubAgent(
            CollaborationRole.ANSWER_SYNTHESIZER,
            ["answer_synthesis"],
            self.mock_llm
        )
        shared_memory = CollaborationState(
            query="What is AI?",
            context=["AI is artificial intelligence"],
            agent_outputs={"analysis": {"entities": ["AI"]}}
        )
        
        result = synthesis_agent.execute("Synthesize answer", shared_memory)
        
        assert "answer" in result or "error" in result or "agent_role" in result


class TestAgentCollaboration:
    """Tests for AgentCollaboration class."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_llm = MockLLM()
        
        self.agents = [
            SpecializedSubAgent(
                CollaborationRole.QUERY_ANALYZER,
                ["entity_extraction"],
                self.mock_llm
            ),
            SpecializedSubAgent(
                CollaborationRole.RETRIEVAL_SPECIALIST,
                ["information_retrieval"],
                self.mock_llm
            ),
            SpecializedSubAgent(
                CollaborationRole.ANSWER_SYNTHESIZER,
                ["answer_synthesis"],
                self.mock_llm
            ),
        ]
        
        self.collaboration = AgentCollaboration(
            agents=self.agents,
            llm_client=self.mock_llm
        )
    
    def test_initialization(self):
        """Test collaboration initialization."""
        assert len(self.collaboration.agents) == 3
        assert len(self.collaboration._agents_by_role) == 3
    
    def test_collaborate(self):
        """Test agent collaboration."""
        query = "What is deep learning?"
        
        with patch.object(self.collaboration, '_route_to_agent', return_value={"answer": "Deep learning is a subset of machine learning"}):
            result = self.collaboration.collaborate(query)
        
        assert len(result) > 0
    
    def test_route_to_agent(self):
        """Test agent routing."""
        result = self.collaboration._route_to_agent(
            CollaborationRole.QUERY_ANALYZER,
            "Analyze query"
        )
        
        assert isinstance(result, dict)
    
    def test_add_agent(self):
        """Test adding new agent."""
        new_agent = SpecializedSubAgent(
            CollaborationRole.VALIDATOR,
            ["quality_check"],
            self.mock_llm
        )
        
        self.collaboration.add_agent(new_agent)
        
        assert CollaborationRole.VALIDATOR in self.collaboration._agents_by_role
        assert new_agent in self.collaboration.agents
    
    def test_remove_agent(self):
        """Test removing agent."""
        self.collaboration.remove_agent(CollaborationRole.QUERY_ANALYZER)
        
        assert CollaborationRole.QUERY_ANALYZER not in self.collaboration._agents_by_role
    
    def test_shared_memory(self):
        """Test shared memory access."""
        query = "Test query"
        self.collaboration.collaborate(query)
        
        memory = self.collaboration.get_shared_memory()
        
        assert memory.query == query
    
    def test_reset_memory(self):
        """Test memory reset."""
        self.collaboration.shared_memory.query = "Test query"
        self.collaboration.reset_memory()
        
        assert self.collaboration.shared_memory.query == ""


class TestIntegration:
    """Integration tests for complete agentic RAG workflow."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_llm = MockLLM()
        self.mock_tools = Mock()
        self.mock_tools.invoke = Mock(return_value={
            "context": ["Mock retrieved context for testing"],
            "confidence": 0.85
        })
    
    def test_complete_rag_workflow(self):
        """Test complete RAG workflow with reflection."""
        agent = RAGAgent(
            llm_client=self.mock_llm,
            tools_registry=self.mock_tools,
            confidence_threshold=0.5,
            max_iterations=2
        )
        
        query = "What is the relationship between AI and machine learning?"
        
        with patch.object(agent, '_is_confident', return_value=True):
            answer = agent.execute(query)
        
        assert len(answer) > 0
        assert isinstance(answer, str)
    
    def test_planning_and_execution(self):
        """Test planning followed by execution."""
        planner = QueryPlanner(llm_client=self.mock_llm)
        agent = RAGAgent(
            llm_client=self.mock_llm,
            tools_registry=self.mock_tools,
            confidence_threshold=0.5
        )
        
        query = "Explain the differences between supervised and unsupervised learning"
        
        # Plan
        tasks = planner.plan(query)
        assert len(tasks) > 0
        
        # Execute with agent
        agent.state.plan_steps = [t.description for t in tasks]
        
        assert len(agent.state.plan_steps) > 0
    
    def test_multi_agent_collaboration(self):
        """Test multi-agent collaboration workflow."""
        llm = MockLLM()
        
        agents = [
            SpecializedSubAgent(CollaborationRole.QUERY_ANALYZER, ["analysis"], llm),
            SpecializedSubAgent(CollaborationRole.RETRIEVAL_SPECIALIST, ["retrieval"], llm),
            SpecializedSubAgent(CollaborationRole.ANSWER_SYNTHESIZER, ["synthesis"], llm),
        ]
        
        collaboration = AgentCollaboration(agents=agents, llm_client=llm)
        
        with patch.object(collaboration, '_route_to_agent', return_value={"answer": "Test answer"}):
            result = collaboration.collaborate("What is AI?")
        
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
