"""RAG Agent with Reflection Pattern.

This module implements the core RAGAgent class with reflection capabilities
for self-correction and adaptive query understanding.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Roles that agents can take in the agentic RAG system."""
    QUERY_ANALYZER = "query_analyzer"
    RETRIEVAL_PLANNER = "retrieval_planner"
    TOOL_ORCHESTRATOR = "tool_orchestrator"
    ANSWER_SYNTHESIZER = "answer_synthesizer"


@dataclass
class AgentState:
    """State management for agent execution across multiple steps."""
    query: str = ""
    context: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    reflection_notes: List[str] = field(default_factory=list)
    plan_steps: List[str] = field(default_factory=list)
    confidence: float = 0.0
    entities: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)


class RAGAgent:
    """Main RAG Agent with reflection and adaptive capabilities.
    
    This agent implements the reflection pattern for self-correction
    and adaptive query understanding.
    """
    
    def __init__(
        self,
        llm_client: Any,
        tools_registry: Optional[Any] = None,
        confidence_threshold: float = 0.8,
        max_iterations: int = 5
    ):
        """Initialize the RAG Agent.
        
        Args:
            llm_client: LLM client for generating reflections and answers
            tools_registry: Registry of available tools for dynamic invocation
            confidence_threshold: Minimum confidence to stop reflection loop
            max_iterations: Maximum iterations for reflection loop
        """
        self.llm = llm_client
        self.tools = tools_registry
        self.confidence_threshold = confidence_threshold
        self.max_iterations = max_iterations
        self.state = AgentState()
        
        logger.info(f"RAGAgent initialized with confidence_threshold={confidence_threshold}, max_iterations={max_iterations}")
    
    def execute(self, query: str, max_iterations: Optional[int] = None) -> str:
        """Execute agentic RAG with reflection and planning.
        
        Args:
            query: The user query to process
            max_iterations: Override default max iterations
            
        Returns:
            str: The synthesized answer
        """
        if max_iterations:
            self.max_iterations = max_iterations
            
        self.state = AgentState(query=query)
        logger.info(f"Starting agentic RAG execution for query: {query[:50]}...")
        
        # Phase 1: Reflection on query
        self._reflect_on_query()
        
        # Phase 2: Create retrieval plan
        plan = self._create_retrieval_plan()
        self.state.plan_steps = plan
        logger.info(f"Created plan with {len(plan)} steps")
        
        # Phase 3: Iterative execution with reflection
        for iteration in range(self.max_iterations):
            logger.info(f"Execution iteration {iteration + 1}/{self.max_iterations}")
            
            # Execute plan step
            result = self._execute_plan_step(plan[iteration])
            
            # Reflect on result
            self._reflect_on_result(result)
            
            # Check confidence
            if self._is_confident():
                logger.info(f"Confidence threshold met at iteration {iteration + 1}")
                break
        
        # Phase 4: Synthesize final answer
        answer = self._synthesize_answer()
        logger.info(f"Agentic RAG execution complete. Confidence: {self.state.confidence}")
        
        return answer
    
    def _reflect_on_query(self) -> None:
        """Reflect on query understanding and identify ambiguities.
        
        This implements the reflection pattern by analyzing the query
        for entities, ambiguities, and potential clarification needs.
        """
        logger.debug("Starting query reflection...")
        
        reflection_prompt = (
            f"Analyze this query and identify potential ambiguities:\n\n"
            f"Query: {self.state.query}\n\n"
            f"Provide:\n"
            f"1. Key entities identified\n"
            f"2. Potential ambiguities\n"
            f"3. Clarification questions if needed\n\n"
            f"Format your response as JSON with keys: entities, ambiguities, clarification_questions"
        )
        
        try:
            reflection = self.llm.generate(reflection_prompt)
            self.state.reflection_notes.append(f"Query Reflection: {reflection}")
            
            # Parse entities and ambiguities from reflection
            self._parse_reflection_results(reflection)
            
            logger.info(f"Query reflection complete. Entities: {self.state.entities}, Ambiguities: {len(self.state.ambiguities)}")
        except Exception as e:
            logger.error(f"Error during query reflection: {e}")
            self.state.reflection_notes.append(f"Query Reflection Error: {str(e)}")
    
    def _parse_reflection_results(self, reflection: str) -> None:
        """Parse reflection output to extract entities and ambiguities."""
        # Simple parsing - in production would use structured output
        try:
            # Extract entities (simplified)
            self.state.entities = [word for word in self.state.query.split() if len(word) > 4]
            
            # Check for common ambiguity patterns
            if "?" in self.state.query:
                self.state.ambiguities.append("Question mark indicates uncertainty")
            if "or" in self.state.query.lower():
                self.state.ambiguities.append("Alternative options may create ambiguity")
            if len(self.state.query.split()) < 5:
                self.state.ambiguities.append("Short query may lack context")
                
        except Exception as e:
            logger.warning(f"Could not parse reflection results: {e}")
    
    def _create_retrieval_plan(self) -> List[str]:
        """Create multi-step retrieval plan based on query and reflection.
        
        Returns:
            List[str]: Numbered list of retrieval steps
        """
        logger.debug("Creating retrieval plan...")
        
        plan_prompt = (
            f"Create a step-by-step plan to answer this query:\n\n"
            f"Query: {self.state.query}\n\n"
            f"Reflection: {' '.join(self.state.reflection_notes[-2:])}\n\n"
            f"Provide a numbered list of retrieval steps. Each step should be concise and actionable."
        )
        
        try:
            plan_text = self.llm.generate(plan_prompt)
            # Split into steps
            steps = [step.strip() for step in plan_text.split('\n') if step.strip() and not step.strip().startswith('1.') and not step.strip().startswith('2.') and not step.strip().startswith('3.')]
            
            # If no steps found, create default steps
            if not steps:
                steps = [
                    "Search for key entities in knowledge base",
                    "Retrieve relevant context documents",
                    "Synthesize answer from retrieved context"
                ]
            
            logger.info(f"Created plan with {len(steps)} steps")
            return steps
            
        except Exception as e:
            logger.error(f"Error creating retrieval plan: {e}")
            return [
                "Search for key entities in knowledge base",
                "Retrieve relevant context documents",
                "Synthesize answer from retrieved context"
            ]
    
    def _execute_plan_step(self, step: str) -> Dict[str, Any]:
        """Execute a single step in the retrieval plan.
        
        Args:
            step: The step to execute
            
        Returns:
            Dict: Execution result with context and metadata
        """
        logger.debug(f"Executing plan step: {step}")
        
        # Check if step requires tool use
        if self._needs_tool(step):
            tool_name = self._select_tool(step)
            try:
                result = self.tools.invoke(tool_name, step)
                self.state.tools_used.append(tool_name)
                logger.info(f"Executed tool: {tool_name}")
                return result
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                return {"error": str(e), "context": []}
        else:
            # Standard retrieval
            return self._standard_retrieval(step)
    
    def _needs_tool(self, step: str) -> bool:
        """Determine if a step requires tool invocation."""
        tool_keywords = ["search", "query", "lookup", "fetch", "retrieve"]
        return any(keyword in step.lower() for keyword in tool_keywords)
    
    def _select_tool(self, step: str) -> str:
        """Select appropriate tool for the step."""
        # Simple heuristic - in production would use LLM to select
        if "search" in step.lower():
            return "knowledge_search"
        elif "query" in step.lower():
            return "database_query"
        else:
            return "knowledge_search"
    
    def _standard_retrieval(self, step: str) -> Dict[str, Any]:
        """Perform standard retrieval without tool use."""
        # Placeholder for standard retrieval logic
        # In production, this would integrate with existing retrievers
        return {
            "context": [f"Retrieved context for step: {step}"],
            "confidence": 0.5,
            "metadata": {"step": step, "method": "standard"}
        }
    
    def _reflect_on_result(self, result: Dict[str, Any]) -> None:
        """Reflect on retrieval result and adjust strategy.
        
        Args:
            result: The result from plan step execution
        """
        logger.debug("Reflecting on result...")
        
        reflection_prompt = (
            f"Analyze this retrieval result:\n\n"
            f"Result: {result}\n\n"
            f"Should we:\n"
            f"1. Continue with current strategy\n"
            f"2. Adjust retrieval parameters\n"
            f"3. Try alternative approach\n\n"
            f"Provide reasoning for your recommendation."
        )
        
        try:
            reflection = self.llm.generate(reflection_prompt)
            self.state.reflection_notes.append(f"Result Reflection: {reflection}")
            
            # Update confidence based on reflection
            self._update_confidence_from_reflection(reflection, result)
            
        except Exception as e:
            logger.error(f"Error during result reflection: {e}")
            self.state.reflection_notes.append(f"Result Reflection Error: {str(e)}")
    
    def _update_confidence_from_reflection(self, reflection: str, result: Dict) -> None:
        """Update confidence score based on reflection analysis."""
        # Simple heuristic - in production would use LLM to evaluate
        context_count = len(result.get("context", []))
        base_confidence = min(context_count * 0.1, 0.7)
        
        # Adjust based on reflection keywords
        if "continue" in reflection.lower():
            self.state.confidence = base_confidence + 0.1
        elif "adjust" in reflection.lower():
            self.state.confidence = base_confidence + 0.05
        else:
            self.state.confidence = base_confidence
            
        self.state.confidence = min(max(self.state.confidence, 0.0), 1.0)
    
    def _is_confident(self) -> bool:
        """Check if current confidence is sufficient.
        
        Returns:
            bool: True if confidence meets threshold
        """
        is_confident = self.state.confidence >= self.confidence_threshold
        logger.debug(f"Confidence check: {self.state.confidence} >= {self.confidence_threshold} = {is_confident}")
        return is_confident
    
    def _synthesize_answer(self) -> str:
        """Synthesize final answer from all reflections and results.
        
        Returns:
            str: Well-structured answer with citations
        """
        logger.debug("Synthesizing final answer...")
        
        synthesis_prompt = (
            f"Synthesize a comprehensive answer based on:\n\n"
            f"Query: {self.state.query}\n\n"
            f"Context: {' '.join(self.state.context)}\n\n"
            f"Reflections: {' '.join(self.state.reflection_notes)}\n\n"
            f"Tools Used: {' '.join(self.state.tools_used)}\n\n"
            f"Provide a well-structured answer with citations."
        )
        
        try:
            answer = self.llm.generate(synthesis_prompt)
            logger.info("Answer synthesis complete")
            return answer
        except Exception as e:
            logger.error(f"Error synthesizing answer: {e}")
            return f"Error generating answer: {str(e)}"
    
    def get_state(self) -> AgentState:
        """Get current agent state.
        
        Returns:
            AgentState: Current execution state
        """
        return self.state
    
    def reset_state(self) -> None:
        """Reset agent state for new execution."""
        self.state = AgentState()
        logger.debug("Agent state reset")
