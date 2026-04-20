"""Tests for RAG Evaluator - Unit and integration tests."""

import pytest

from evaluation.rag_evaluator import RAGEvaluator, EvaluationResult, EvaluationMetric
from evaluation.dashboard import EvaluationDashboard, AggregatedMetrics
from evaluation.test_queries import TestQuerySet


class TestRAGEvaluator:
    """Unit tests for RAGEvaluator class."""
    
    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance with default weights."""
        return RAGEvaluator()
    
    @pytest.fixture
    def evaluator_custom_weights(self):
        """Create evaluator with custom weights."""
        custom_weights = {
            'groundedness': 0.4,
            'completeness': 0.3,
            'utilization': 0.2,
            'relevancy': 0.1
        }
        return RAGEvaluator(weights=custom_weights)
    
    def test_init_default_weights(self, evaluator):
        """Test initialization with default weights."""
        assert evaluator.weights['groundedness'] == 0.30
        assert evaluator.weights['completeness'] == 0.25
        assert evaluator.weights['utilization'] == 0.25
        assert evaluator.weights['relevancy'] == 0.20
    
    def test_init_custom_weights(self, evaluator_custom_weights):
        """Test initialization with custom weights."""
        assert evaluator_custom_weights.weights['groundedness'] == 0.4
        assert evaluator_custom_weights.weights['completeness'] == 0.3
        assert evaluator_custom_weights.weights['utilization'] == 0.2
        assert evaluator_custom_weights.weights['relevancy'] == 0.1
    
    def test_init_invalid_weights(self):
        """Test that invalid weights raise error."""
        with pytest.raises(ValueError):
            RAGEvaluator(weights={'a': 0.5, 'b': 0.5})  # Only 2 keys, sum != 1
    
    def test_evaluate_basic(self, evaluator):
        """Test basic evaluation functionality."""
        query = "What is RAG?"
        answer = "RAG is a retrieval-augmented generation system."
        context = ["RAG combines retrieval and generation for better answers."]
        
        result = evaluator.evaluate(query, answer, context)
        
        assert isinstance(result, EvaluationResult)
        assert result.query == query
        assert result.answer == answer
        assert len(result.retrieved_context) > 0
        assert 0 <= result.groundedness <= 1
        assert 0 <= result.completeness <= 1
        assert 0 <= result.utilization <= 1
        assert 0 <= result.relevancy <= 1
        assert 0 <= result.total_score <= 1
    
    def test_evaluate_empty_answer(self, evaluator):
        """Test evaluation with empty answer."""
        query = "What is RAG?"
        answer = ""
        context = ["RAG is a system."]
        
        result = evaluator.evaluate(query, answer, context)
        
        assert result.groundedness == 0.0
        assert result.completeness == 0.0
        assert result.utilization == 0.0
        assert result.relevancy == 0.0
    
    def test_evaluate_empty_context(self, evaluator):
        """Test evaluation with empty context."""
        query = "What is RAG?"
        answer = "RAG is a system."
        context = []
        
        result = evaluator.evaluate(query, answer, context)
        
        assert result.groundedness == 0.0
        assert result.utilization == 0.0
    
    def test_groundedness_high(self, evaluator):
        """Test high groundedness score."""
        query = "What is RAG?"
        answer = "RAG combines retrieval and generation."
        context = [
            "RAG is a framework that combines retrieval and generation.",
            "The system retrieves relevant documents and generates answers."
        ]
        
        result = evaluator.evaluate(query, answer, context)
        
        assert result.groundedness > 0.5
    
    def test_groundedness_low(self, evaluator):
        """Test low groundedness score."""
        query = "What is RAG?"
        answer = "RAG is a completely made up concept with no basis."
        context = [
            "RAG is a well-established framework in NLP.",
            "RAG combines retrieval and generation."
        ]
        
        result = evaluator.evaluate(query, answer, context)
        
        assert result.groundedness < 0.5
    
    def test_relevancy_high(self, evaluator):
        """Test high relevancy score."""
        query = "What is the purpose of RAG?"
        answer = "The purpose of RAG is to improve generation quality."
        
        result = evaluator.evaluate(query, answer, [])
        
        assert result.relevancy > 0.5
    
    def test_relevancy_low(self, evaluator):
        """Test low relevancy score."""
        query = "What is the purpose of RAG?"
        answer = "The weather is sunny today and I like ice cream."
        
        result = evaluator.evaluate(query, answer, [])
        
        assert result.relevancy < 0.5
    
    def test_evaluate_with_ground_truth(self, evaluator):
        """Test evaluation with ground truth."""
        query = "What is RAG?"
        answer = "RAG is a retrieval-augmented generation framework."
        context = ["RAG combines retrieval and generation."]
        ground_truth = "RAG is a framework that uses retrieval to enhance generation."
        
        result = evaluator.evaluate(query, answer, context, ground_truth)
        
        assert result.completeness > 0
    
    def test_evaluate_method(self, evaluator):
        """Test that evaluate method returns correct type."""
        query = "Test query"
        answer = "Test answer"
        context = ["Test context"]
        
        result = evaluator.evaluate(query, answer, context)
        
        assert result.query == query
        assert result.answer == answer
        assert result.retrieved_context == context
    
    def test_to_dict(self, evaluator):
        """Test conversion to dictionary."""
        query = "Test query"
        answer = "Test answer"
        context = ["Test context"]
        
        result = evaluator.evaluate(query, answer, context)
        result_dict = result.to_dict()
        
        assert 'query' in result_dict
        assert 'answer' in result_dict
        assert 'groundedness' in result_dict
        assert 'total_score' in result_dict


class TestEvaluationDashboard:
    """Unit tests for EvaluationDashboard class."""
    
    @pytest.fixture
    def dashboard(self, tmp_path):
        """Create dashboard instance."""
        return EvaluationDashboard(results_dir=str(tmp_path))
    
    def test_init(self, dashboard):
        """Test dashboard initialization."""
        assert dashboard.results == []
        assert dashboard.results_dir is not None
    
    def test_add_result(self, dashboard):
        """Test adding single result."""
        result = EvaluationResult(
            query="Test",
            answer="Test answer",
            retrieved_context=["context"],
            groundedness=0.8,
            completeness=0.7,
            utilization=0.6,
            relevancy=0.9,
            total_score=0.75,
            evaluation_details={}
        )
        
        dashboard.add_result(result)
        
        assert len(dashboard.results) == 1
    
    def test_add_results(self, dashboard):
        """Test adding multiple results."""
        results = [
            EvaluationResult(
                query=f"Query {i}",
                answer=f"Answer {i}",
                retrieved_context=["context"],
                groundedness=0.8,
                completeness=0.7,
                utilization=0.6,
                relevancy=0.9,
                total_score=0.75,
                evaluation_details={}
            )
            for i in range(5)
        ]
        
        dashboard.add_results(results)
        
        assert len(dashboard.results) == 5
    
    def test_aggregate_results_empty(self, dashboard):
        """Test aggregation with empty results."""
        agg = dashboard.aggregate_results()
        
        assert agg.total_evaluations == 0
        assert agg.avg_total_score == 0.0
    
    def test_aggregate_results(self, dashboard):
        """Test aggregation with results."""
        results = [
            EvaluationResult(
                query=f"Query {i}",
                answer=f"Answer {i}",
                retrieved_context=["context"],
                groundedness=0.8,
                completeness=0.7,
                utilization=0.6,
                relevancy=0.9,
                total_score=0.75,
                evaluation_details={}
            )
            for i in range(10)
        ]
        
        dashboard.add_results(results)
        agg = dashboard.aggregate_results()
        
        assert agg.total_evaluations == 10
        assert agg.avg_total_score == 0.75
        assert agg.std_total_score == 0.0
    
    def test_aggregate_results_varied(self, dashboard):
        """Test aggregation with varied scores."""
        results = [
            EvaluationResult(
                query=f"Query {i}",
                answer=f"Answer {i}",
                retrieved_context=["context"],
                groundedness=0.5 + (i * 0.05),
                completeness=0.6 + (i * 0.05),
                utilization=0.7 + (i * 0.05),
                relevancy=0.8 + (i * 0.05),
                total_score=0.65 + (i * 0.05),
                evaluation_details={}
            )
            for i in range(5)
        ]
        
        dashboard.add_results(results)
        agg = dashboard.aggregate_results()
        
        assert agg.std_total_score > 0
    
    def test_get_top_results(self, dashboard):
        """Test getting top results."""
        results = [
            EvaluationResult(
                query=f"Query {i}",
                answer=f"Answer {i}",
                retrieved_context=["context"],
                groundedness=0.8,
                completeness=0.7,
                utilization=0.6,
                relevancy=0.9,
                total_score=0.8 + (i * 0.05),
                evaluation_details={}
            )
            for i in range(10)
        ]
        
        dashboard.add_results(results)
        top = dashboard.get_top_results(n=3)
        
        assert len(top) == 3
        assert top[0].total_score >= top[1].total_score
    
    def test_get_bottom_results(self, dashboard):
        """Test getting bottom results."""
        results = [
            EvaluationResult(
                query=f"Query {i}",
                answer=f"Answer {i}",
                retrieved_context=["context"],
                groundedness=0.8,
                completeness=0.7,
                utilization=0.6,
                relevancy=0.9,
                total_score=0.8 + (i * 0.05),
                evaluation_details={}
            )
            for i in range(10)
        ]
        
        dashboard.add_results(results)
        bottom = dashboard.get_bottom_results(n=3)
        
        assert len(bottom) == 3
        assert bottom[0].total_score <= bottom[1].total_score
    
    def test_visualize_text(self, dashboard):
        """Test text visualization."""
        dashboard.add_result(EvaluationResult(
            query="Test",
            answer="Test answer",
            retrieved_context=["context"],
            groundedness=0.8,
            completeness=0.7,
            utilization=0.6,
            relevancy=0.9,
            total_score=0.75,
            evaluation_details={}
        ))
        
        viz = dashboard.visualize(output_format="text")
        
        assert "RAG EVALUATION DASHBOARD" in viz
        assert "METRICS SUMMARY" in viz
    
    def test_visualize_json(self, dashboard):
        """Test JSON visualization."""
        dashboard.add_result(EvaluationResult(
            query="Test",
            answer="Test answer",
            retrieved_context=["context"],
            groundedness=0.8,
            completeness=0.7,
            utilization=0.6,
            relevancy=0.9,
            total_score=0.75,
            evaluation_details={}
        ))
        
        viz = dashboard.visualize(output_format="json")
        
        assert '"avg_total_score"' in viz
        assert '"total_evaluations"' in viz
    
    def test_save_results(self, dashboard, tmp_path):
        """Test saving results to file."""
        dashboard.add_result(EvaluationResult(
            query="Test",
            answer="Test answer",
            retrieved_context=["context"],
            groundedness=0.8,
            completeness=0.7,
            utilization=0.6,
            relevancy=0.9,
            total_score=0.75,
            evaluation_details={}
        ))
        
        filepath = dashboard.save_results("test_results.json")
        
        assert os.path.exists(filepath)
        assert filepath.endswith(".json")
    
    def test_load_results(self, dashboard, tmp_path):
        """Test loading results from file."""
        # Save results
        dashboard.add_result(EvaluationResult(
            query="Test",
            answer="Test answer",
            retrieved_context=["context"],
            groundedness=0.8,
            completeness=0.7,
            utilization=0.6,
            relevancy=0.9,
            total_score=0.75,
            evaluation_details={}
        ))
        
        filepath = dashboard.save_results("test_results.json")
        
        # Create new dashboard and load
        new_dashboard = EvaluationDashboard(results_dir=str(tmp_path))
        count = new_dashboard.load_results(filepath)
        
        assert count == 1
        assert len(new_dashboard.results) == 1
    
    def test_generate_report(self, dashboard):
        """Test report generation."""
        dashboard.add_result(EvaluationResult(
            query="Test",
            answer="Test answer",
            retrieved_context=["context"],
            groundedness=0.8,
            completeness=0.7,
            utilization=0.6,
            relevancy=0.9,
            total_score=0.75,
            evaluation_details={}
        ))
        
        report = dashboard.generate_report()
        
        assert "RAG EVALUATION REPORT" in report
        assert "EXECUTIVE SUMMARY" in report
        assert "METRIC BREAKDOWN" in report


class TestIntegration:
    """Integration tests for the evaluation framework."""
    
    def test_full_evaluation_pipeline(self):
        """Test complete evaluation pipeline."""
        from evaluation.rag_evaluator import RAGEvaluator
        from evaluation.dashboard import EvaluationDashboard
        
        evaluator = RAGEvaluator()
        dashboard = EvaluationDashboard()
        
        # Evaluate multiple queries
        test_cases = [
            ("What is RAG?", "RAG is a retrieval-augmented generation system.", 
             ["RAG combines retrieval and generation for better answers."], None),
            ("How does hybrid search work?", "Hybrid search combines BM25 and embeddings.",
             ["Hybrid search uses both keyword and semantic matching."], None),
            ("What metrics are tracked?", "Groundedness, completeness, utilization, relevancy.",
             ["Evaluation framework tracks multiple quality metrics."], None),
        ]
        
        for query, answer, context, gt in test_cases:
            result = evaluator.evaluate(query, answer, context, gt)
            dashboard.add_result(result)
        
        # Aggregate and visualize
        agg = dashboard.aggregate_results()
        assert agg.total_evaluations == 3
        
        report = dashboard.generate_report()
        assert len(report) > 0
    
    def test_test_query_set(self):
        """Test test query set functionality."""
        query_set = TestQuerySet()
        
        assert len(query_set) >= 50
        
        # Check categories
        categories = set(q.category for q in query_set.get_all_queries())
        assert "product_info" in categories
        assert "technical" in categories
        assert "evaluation" in categories
        
        # Check difficulty levels
        difficulties = set(q.difficulty for q in query_set.get_all_queries())
        assert "easy" in difficulties
        assert "medium" in difficulties
        assert "hard" in difficulties
    
    def test_batch_evaluation(self):
        """Test batch evaluation functionality."""
        from evaluation.rag_evaluator import RAGEvaluator
        
        evaluator = RAGEvaluator()
        
        evaluations = [
            ("Query 1", "Answer 1", ["Context 1"], None),
            ("Query 2", "Answer 2", ["Context 2"], None),
            ("Query 3", "Answer 3", ["Context 3"], None),
        ]
        
        results = evaluator.batch_evaluate(evaluations)
        
        assert len(results) == 3
        assert all(isinstance(r, EvaluationResult) for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
