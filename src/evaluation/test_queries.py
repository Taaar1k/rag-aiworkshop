"""Test Query Set - Representative queries for RAG evaluation."""

from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class TestQuery:
    """Represents a single test query with expected information."""
    query: str
    expected_topics: List[str]
    category: str
    difficulty: str  # "easy", "medium", "hard"
    ground_truth: str  # Optional ground truth for completeness check


class TestQuerySet:
    """
    Comprehensive test query set for RAG evaluation.
    
    Contains 50+ representative queries covering various aspects:
    - Product information
    - Technical specifications
    - Use cases
    - Comparison questions
    - Troubleshooting
    """
    
    def __init__(self):
        """Initialize test query set."""
        self.queries: List[TestQuery] = []
        self._load_queries()
    
    def _load_queries(self) -> None:
        """Load all test queries."""
        # Category: Product Information
        self.queries.extend([
            TestQuery(
                query="What is the main purpose of the RAG system?",
                expected_topics=["retrieval", "generation", "context"],
                category="product_info",
                difficulty="easy",
                ground_truth="RAG system combines retrieval and generation to provide context-aware answers"
            ),
            TestQuery(
                query="How does the hybrid retriever work?",
                expected_topics=["hybrid", "retriever", "bm25", "embedding"],
                category="technical",
                difficulty="medium",
                ground_truth="Hybrid retriever combines BM25 keyword search with embedding-based semantic search"
            ),
            TestQuery(
                query="What metrics does the evaluation framework track?",
                expected_topics=["groundedness", "completeness", "utilization", "relevancy"],
                category="evaluation",
                difficulty="easy",
                ground_truth="Tracks groundedness, completeness, utilization, and relevancy metrics"
            ),
            TestQuery(
                query="Explain the cross-encoder reranker implementation",
                expected_topics=["reranker", "cross-encoder", "re-ranking"],
                category="technical",
                difficulty="hard",
                ground_truth="Cross-encoder reranker re-ranks retrieved documents using a transformer model"
            ),
            TestQuery(
                query="What is the default embedding model used?",
                expected_topics=["embedding", "model", "sentence-transformers"],
                category="technical",
                difficulty="easy",
                ground_truth="Uses sentence-transformers embedding model for document encoding"
            ),
        ])
        
        # Category: Technical Specifications
        self.queries.extend([
            TestQuery(
                query="What are the configuration options for the retriever?",
                expected_topics=["configuration", "retriever", "settings"],
                category="technical",
                difficulty="medium",
                ground_truth="Configuration includes k, bm25_weight, and embedding model settings"
            ),
            TestQuery(
                query="How is the evaluation dashboard generated?",
                expected_topics=["dashboard", "visualization", "metrics"],
                category="evaluation",
                difficulty="medium",
                ground_truth="Dashboard aggregates results and provides statistical summaries"
            ),
            TestQuery(
                query="What is the weight distribution for evaluation metrics?",
                expected_topics=["weights", "groundedness", "completeness", "utilization", "relevancy"],
                category="evaluation",
                difficulty="medium",
                ground_truth="Weights: groundedness 0.3, completeness 0.25, utilization 0.25, relevancy 0.2"
            ),
            TestQuery(
                query="How does the system handle multi-part queries?",
                expected_topics=["query", "decomposition", "aspects"],
                category="technical",
                difficulty="hard",
                ground_truth="System decomposes queries into sub-questions and checks coverage"
            ),
            TestQuery(
                query="What file structure does the evaluation framework use?",
                expected_topics=["structure", "files", "organization"],
                category="technical",
                difficulty="easy",
                ground_truth="Framework uses src/evaluation/ with evaluator, dashboard, and test_queries modules"
            ),
        ])
        
        # Category: Use Cases
        self.queries.extend([
            TestQuery(
                query="When should I use hybrid search over BM25 alone?",
                expected_topics=["hybrid", "search", "BM25", "use case"],
                category="use_case",
                difficulty="medium",
                ground_truth="Use hybrid search when semantic understanding is needed alongside keyword matching"
            ),
            TestQuery(
                query="How can I improve answer groundedness?",
                expected_topics=["groundedness", "improvement", "retrieval"],
                category="use_case",
                difficulty="medium",
                ground_truth="Improve retrieval quality and use reranking to select most relevant context"
            ),
            TestQuery(
                query="What is the best way to evaluate RAG quality?",
                expected_topics=["evaluation", "quality", "metrics"],
                category="use_case",
                difficulty="easy",
                ground_truth="Use comprehensive evaluation framework with multiple metrics"
            ),
            TestQuery(
                query="How do I set up baseline measurements?",
                expected_topics=["baseline", "measurement", "benchmark"],
                category="use_case",
                difficulty="medium",
                ground_truth="Run evaluation on representative query set and document hyperparameters"
            ),
            TestQuery(
                query="What makes a good test query for RAG?",
                expected_topics=["test", "query", "representative"],
                category="use_case",
                difficulty="easy",
                ground_truth="Good test queries cover various difficulty levels and query types"
            ),
        ])
        
        # Category: Comparison Questions
        self.queries.extend([
            TestQuery(
                query="What is the difference between BM25 and embedding search?",
                expected_topics=["BM25", "embedding", "comparison", "search"],
                category="comparison",
                difficulty="medium",
                ground_truth="BM25 uses keyword matching, embedding search uses semantic similarity"
            ),
            TestQuery(
                query="How does cross-encoder reranking compare to re-ranking?",
                expected_topics=["cross-encoder", "reranking", "comparison"],
                category="comparison",
                difficulty="hard",
                ground_truth="Cross-encoder reranking evaluates query-document pairs jointly for better relevance"
            ),
            TestQuery(
                query="What are the trade-offs of different evaluation frameworks?",
                expected_topics=["evaluation", "frameworks", "trade-offs"],
                category="comparison",
                difficulty="hard",
                ground_truth="Different frameworks offer varying balances of accuracy, speed, and customization"
            ),
            TestQuery(
                query="How does the evaluation framework compare to Ragas?",
                expected_topics=["evaluation", "Ragas", "comparison"],
                category="comparison",
                difficulty="medium",
                ground_truth="Custom framework offers more control; Ragas provides pre-built metrics"
            ),
            TestQuery(
                query="What is the advantage of hybrid search?",
                expected_topics=["hybrid", "search", "advantage"],
                category="comparison",
                difficulty="easy",
                ground_truth="Hybrid search combines keyword and semantic matching for better recall"
            ),
        ])
        
        # Category: Troubleshooting
        self.queries.extend([
            TestQuery(
                query="What causes low groundedness scores?",
                expected_topics=["groundedness", "troubleshooting", "issues"],
                category="troubleshooting",
                difficulty="medium",
                ground_truth="Low groundedness indicates answer contains unsupported claims"
            ),
            TestQuery(
                query="How to fix incomplete answers?",
                expected_topics=["completeness", "troubleshooting", "answers"],
                category="troubleshooting",
                difficulty="medium",
                ground_truth="Improve query decomposition and ensure all aspects are addressed"
            ),
            TestQuery(
                query="Why is utilization score low?",
                expected_topics=["utilization", "troubleshooting", "context"],
                category="troubleshooting",
                difficulty="medium",
                ground_truth="Low utilization means model not effectively using retrieved context"
            ),
            TestQuery(
                query="What causes relevance issues?",
                expected_topics=["relevancy", "troubleshooting", "relevance"],
                category="troubleshooting",
                difficulty="easy",
                ground_truth="Relevance issues occur when answer doesn't directly address query"
            ),
            TestQuery(
                query="How to improve overall RAG performance?",
                expected_topics=["performance", "improvement", "optimization"],
                category="troubleshooting",
                difficulty="hard",
                ground_truth="Optimize retrieval, use reranking, and tune generation parameters"
            ),
        ])
        
        # Category: Advanced Topics
        self.queries.extend([
            TestQuery(
                query="How does the system handle ambiguous queries?",
                expected_topics=["ambiguous", "query", "handling"],
                category="advanced",
                difficulty="hard",
                ground_truth="System uses query decomposition and context analysis to resolve ambiguity"
            ),
            TestQuery(
                query="What is the role of the memory manager in RAG?",
                expected_topics=["memory", "manager", "context"],
                category="advanced",
                difficulty="hard",
                ground_truth="Memory manager maintains context across multiple interactions"
            ),
            TestQuery(
                query="How are evaluation results aggregated over time?",
                expected_topics=["aggregation", "results", "trends"],
                category="advanced",
                difficulty="medium",
                ground_truth="Results are aggregated with statistical measures for trend analysis"
            ),
            TestQuery(
                query="What is the impact of context window size?",
                expected_topics=["context", "window", "size"],
                category="advanced",
                difficulty="hard",
                ground_truth="Larger context windows allow more context but increase latency"
            ),
            TestQuery(
                query="How does the system handle long documents?",
                expected_topics=["documents", "long", "chunking"],
                category="advanced",
                difficulty="medium",
                ground_truth="Documents are chunked and indexed for efficient retrieval"
            ),
        ])
        
        # Category: Additional Queries (to reach 50+)
        self.queries.extend([
            TestQuery(
                query="What is the purpose of the evaluation metrics?",
                expected_topics=["metrics", "purpose", "evaluation"],
                category="product_info",
                difficulty="easy",
                ground_truth="Metrics measure different aspects of RAG quality"
            ),
            TestQuery(
                query="How is the total score calculated?",
                expected_topics=["total score", "calculation", "weighted"],
                category="technical",
                difficulty="medium",
                ground_truth="Total score is weighted average of all metrics"
            ),
            TestQuery(
                query="What is the minimum test query set size?",
                expected_topics=["test queries", "minimum", "size"],
                category="evaluation",
                difficulty="easy",
                ground_truth="Minimum 50 representative queries recommended"
            ),
            TestQuery(
                query="How do I customize evaluation weights?",
                expected_topics=["weights", "customization", "configuration"],
                category="use_case",
                difficulty="medium",
                ground_truth="Customize weights in RAGEvaluator initialization"
            ),
            TestQuery(
                query="What information is stored in evaluation results?",
                expected_topics=["results", "storage", "data"],
                category="technical",
                difficulty="easy",
                ground_truth="Stores query, answer, context, scores, and evaluation details"
            ),
            TestQuery(
                query="How can I visualize evaluation trends?",
                expected_topics=["visualization", "trends", "dashboard"],
                category="use_case",
                difficulty="medium",
                ground_truth="Use EvaluationDashboard for trend visualization"
            ),
            TestQuery(
                query="What is the role of ground truth in evaluation?",
                expected_topics=["ground truth", "evaluation", "completeness"],
                category="evaluation",
                difficulty="medium",
                ground_truth="Ground truth provides reference for completeness assessment"
            ),
            TestQuery(
                query="How does the system extract claims from answers?",
                expected_topics=["claims", "extraction", "sentences"],
                category="technical",
                difficulty="hard",
                ground_truth="Claims are extracted by splitting on sentence boundaries"
            ),
            TestQuery(
                query="What is the significance of query decomposition?",
                expected_topics=["query decomposition", "aspects", "coverage"],
                category="technical",
                difficulty="medium",
                ground_truth="Decomposition breaks queries into checkable aspects"
            ),
            TestQuery(
                query="How are context-specific patterns identified?",
                expected_topics=["patterns", "context", "identification"],
                category="technical",
                difficulty="hard",
                ground_truth="Patterns include numbers, dates, and proper nouns from context"
            ),
            TestQuery(
                query="What is the evaluation pipeline workflow?",
                expected_topics=["pipeline", "workflow", "evaluation"],
                category="use_case",
                difficulty="medium",
                ground_truth="Workflow: query -> retrieval -> generation -> evaluation -> aggregation"
            ),
            TestQuery(
                query="How do I run baseline evaluation?",
                expected_topics=["baseline", "evaluation", "run"],
                category="use_case",
                difficulty="easy",
                ground_truth="Use evaluation script with test query set"
            ),
            TestQuery(
                query="What file format are evaluation results saved in?",
                expected_topics=["file format", "JSON", "results"],
                category="technical",
                difficulty="easy",
                ground_truth="Results saved in JSON format for easy parsing"
            ),
            TestQuery(
                query="How can I compare different RAG configurations?",
                expected_topics=["comparison", "configurations", "evaluation"],
                category="use_case",
                difficulty="medium",
                ground_truth="Run evaluation on each configuration and compare aggregated scores"
            ),
            TestQuery(
                query="What is the importance of hyperparameter documentation?",
                expected_topics=["hyperparameters", "documentation", "reproducibility"],
                category="evaluation",
                difficulty="medium",
                ground_truth="Documentation ensures reproducible and comparable evaluations"
            ),
            TestQuery(
                query="How does the dashboard handle large result sets?",
                expected_topics=["dashboard", "large sets", "performance"],
                category="technical",
                difficulty="medium",
                ground_truth="Dashboard aggregates results and shows top/bottom performers"
            ),
            TestQuery(
                query="What is the standard deviation used for in evaluation?",
                expected_topics=["standard deviation", "statistics", "variability"],
                category="technical",
                difficulty="hard",
                ground_truth="Std dev measures consistency of metric scores across queries"
            ),
            TestQuery(
                query="How are evaluation timestamps recorded?",
                expected_topics=["timestamps", "recording", "tracking"],
                category="technical",
                difficulty="easy",
                ground_truth="Timestamps recorded in ISO format for each evaluation run"
            ),
            TestQuery(
                query="What makes a query 'hard' vs 'easy'?",
                expected_topics=["difficulty", "query", "classification"],
                category="evaluation",
                difficulty="medium",
                ground_truth="Difficulty based on query complexity and required reasoning"
            ),
            TestQuery(
                query="How does the system handle missing context?",
                expected_topics=["missing context", "handling", "edge cases"],
                category="technical",
                difficulty="hard",
                ground_truth="Returns low scores for groundedness and utilization when context missing"
            ),
            TestQuery(
                query="What is the purpose of evaluation explanations?",
                expected_topics=["explanations", "details", "interpretation"],
                category="evaluation",
                difficulty="easy",
                ground_truth="Explanations provide context for individual metric scores"
            ),
            TestQuery(
                query="How can I export evaluation reports?",
                expected_topics=["export", "reports", "format"],
                category="use_case",
                difficulty="easy",
                ground_truth="Use save_results or generate_report methods"
            ),
            TestQuery(
                query="What is the role of the evaluation model?",
                expected_topics=["evaluation model", "LLM", "assessment"],
                category="technical",
                difficulty="medium",
                ground_truth="Evaluation model can be used for more sophisticated assessments"
            ),
            TestQuery(
                query="How does the framework ensure reproducibility?",
                expected_topics=["reproducibility", "consistency", "evaluation"],
                category="evaluation",
                difficulty="medium",
                ground_truth="Consistent methodology and documented hyperparameters ensure reproducibility"
            ),
            TestQuery(
                query="What is the best practice for query selection?",
                expected_topics=["query selection", "best practice", "coverage"],
                category="use_case",
                difficulty="medium",
                ground_truth="Select queries covering all categories and difficulty levels"
            ),
            TestQuery(
                query="How are edge cases handled in evaluation?",
                expected_topics=["edge cases", "handling", "robustness"],
                category="technical",
                difficulty="hard",
                ground_truth="Edge cases return appropriate scores (e.g., 0 for empty inputs)"
            ),
        ])
    
    def get_all_queries(self) -> List[TestQuery]:
        """Get all test queries."""
        return self.queries
    
    def get_queries_by_category(self, category: str) -> List[TestQuery]:
        """Get queries filtered by category."""
        return [q for q in self.queries if q.category == category]
    
    def get_queries_by_difficulty(self, difficulty: str) -> List[TestQuery]:
        """Get queries filtered by difficulty."""
        return [q for q in self.queries if q.difficulty == difficulty]
    
    def get_sample_queries(self, n: int = 10) -> List[TestQuery]:
        """Get random sample of n queries."""
        import random
        return random.sample(self.queries, min(n, len(self.queries)))
    
    def to_evaluation_format(self) -> List[Tuple[str, str, List[str], str]]:
        """
        Convert queries to evaluation format.
        
        Returns:
            List of (query, simulated_answer, context, ground_truth) tuples
        """
        # Note: In production, this would generate simulated answers and contexts
        # For now, returns placeholder format
        return [
            (q.query, f"Simulated answer for: {q.query}", ["context placeholder"], q.ground_truth)
            for q in self.queries
        ]
    
    def __len__(self) -> int:
        """Return number of queries."""
        return len(self.queries)
    
    def __repr__(self) -> str:
        """String representation."""
        return f"TestQuerySet({len(self.queries)} queries)"
