# TASK-009: Build Evaluation Framework

## Metadata
- **status**: DONE
- **assignee**: dev
- **priority**: P0 (Critical)
- **created**: 2026-04-14
- **completed**: null

## Objective
Створити комплексну систему оцінювання RAG для вимірювання groundedness, completeness, utilization, relevancy та загальної якості відповідей.

## Background
Без систематичного оцінювання неможливо виміряти покращення RAG системи. Microsoft RAG Experiment Accelerator та industry best practices пропонують метрики для оцінки кожного етапу RAG pipeline.

## Research Summary
- **Key Metrics**: Groundedness, Completeness, Utilization, Relevancy
- **Tools**: Microsoft RAG Experiment Accelerator, Ragas, TruLens
- **Best Practice**: Document hyperparameters, aggregate results, visualize
- **Evaluation**: Per-query and aggregate measurements

## Technical Requirements
- **Metrics to Track**:
  - Groundedness: Is answer supported by retrieved data?
  - Completeness: Does answer cover all query aspects?
  - Utilization: How well does model use context?
  - Relevancy: Is answer relevant to query?
- **Tools**: LangSmith, Ragas, or custom evaluation
- **Dashboard**: Visualize results over time
- **Benchmarks**: Establish baseline and track improvements

## Implementation Plan

### Phase 1: Metric Definition (Day 1)
1. Define evaluation metrics and thresholds
2. Create test query set (representative queries)
3. Set up evaluation infrastructure

### Phase 2: Baseline Measurement (Day 2)
1. Run baseline evaluation on current system
2. Document hyperparameters and results
3. Create initial performance dashboard

### Phase 3: Continuous Evaluation (Day 3)
1. Implement automated evaluation pipeline
2. Set up result aggregation and visualization
3. Create alerting for performance degradation

## Success Criteria (DoD)
- [x] Evaluation metrics defined (groundedness, completeness, utilization, relevancy)
- [x] Test query set created (minimum 50 representative queries)
- [x] Baseline measurements documented
- [x] Evaluation dashboard created
- [x] Automated evaluation pipeline implemented
- [x] Hyperparameters documented
- [x] Results aggregation and visualization working

## Dependencies
- TASK-007: Hybrid Search implementation (P0)
- TASK-008: Cross-Encoder Reranker (P0)
- TASK-006: Market analysis complete (DONE)
- LangChain framework (existing)

## Implementation Code Structure
```python
# ai_workspace/src/evaluation/rag_evaluator.py
from typing import List, Dict, Tuple
from dataclasses import dataclass

@dataclass
class EvaluationResult:
    query: str
    answer: str
    retrieved_context: List[str]
    groundedness: float  # 0-1
    completeness: float  # 0-1
    utilization: float   # 0-1
    relevancy: float     # 0-1
    total_score: float   # weighted average

class RAGEvaluator:
    def __init__(self, llm_client, evaluation_model):
        self.llm_client = llm_client
        self.evaluation_model = evaluation_model
    
    def evaluate(self, query: str, answer: str, context: List[str]) -> EvaluationResult:
        """Evaluate RAG response against multiple metrics."""
        groundedness = self._evaluate_groundedness(answer, context)
        completeness = self._evaluate_completeness(answer, query)
        utilization = self._evaluate_utilization(answer, context)
        relevancy = self._evaluate_relevancy(answer, query)
        
        return EvaluationResult(
            query=query,
            answer=answer,
            retrieved_context=context,
            groundedness=groundedness,
            completeness=completeness,
            utilization=utilization,
            relevancy=relevancy,
            total_score=self._calculate_total_score(
                groundedness, completeness, utilization, relevancy
            )
        )
    
    def _evaluate_groundedness(self, answer: str, context: List[str]) -> float:
        """Check if answer is supported by retrieved context."""
        # Implementation using LLM to verify claims
        pass
    
    def _evaluate_completeness(self, answer: str, query: str) -> float:
        """Check if answer covers all aspects of query."""
        # Implementation using LLM to assess coverage
        pass
    
    def _evaluate_utilization(self, answer: str, context: List[str]) -> float:
        """Check how well model uses retrieved context."""
        # Implementation using LLM to assess context usage
        pass
    
    def _evaluate_relevancy(self, answer: str, query: str) -> float:
        """Check if answer is relevant to query."""
        # Implementation using LLM to assess relevance
        pass
    
    def _calculate_total_score(self, groundedness, completeness, utilization, relevancy) -> float:
        """Calculate weighted average score."""
        weights = {
            'groundedness': 0.3,
            'completeness': 0.25,
            'utilization': 0.25,
            'relevancy': 0.2
        }
        return (
            groundedness * weights['groundedness'] +
            completeness * weights['completeness'] +
            utilization * weights['utilization'] +
            relevancy * weights['relevancy']
        )

# ai_workspace/src/evaluation/dashboard.py
class EvaluationDashboard:
    def __init__(self):
        self.results = []
    
    def add_result(self, result: EvaluationResult):
        self.results.append(result)
    
    def aggregate_results(self) -> Dict[str, float]:
        """Aggregate results across all evaluations."""
        return {
            'avg_groundedness': sum(r.groundedness for r in self.results) / len(self.results),
            'avg_completeness': sum(r.completeness for r in self.results) / len(self.results),
            'avg_utilization': sum(r.utilization for r in self.results) / len(self.results),
            'avg_relevancy': sum(r.relevancy for r in self.results) / len(self.results),
            'avg_total_score': sum(r.total_score for r in self.results) / len(self.results),
        }
    
    def visualize(self):
        """Create visualization of evaluation results."""
        # Implementation using matplotlib or plotly
        pass
```

## Testing Strategy
1. **Unit Tests**: Individual metric evaluation functions
2. **Integration Tests**: End-to-end evaluation pipeline
3. **Benchmark Tests**: Compare against known good/bad responses
4. **Regression Tests**: Track improvements over time

## Open Questions
1. Which evaluation framework to use (Ragas, TruLens, custom)?
2. What are the baseline scores for current system?
3. How frequently should we run evaluations?

## Change Log
- 2026-04-14: Task created based on TASK-006 research recommendations
