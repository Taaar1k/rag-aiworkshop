"""Evaluation Dashboard - Visualization and aggregation of RAG evaluation results."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import json
import os

from .rag_evaluator import EvaluationResult, RAGEvaluator


@dataclass
class AggregatedMetrics:
    """Aggregated metrics across multiple evaluations."""
    avg_groundedness: float
    avg_completeness: float
    avg_utilization: float
    avg_relevancy: float
    avg_total_score: float
    std_groundedness: float
    std_completeness: float
    std_utilization: float
    std_relevancy: float
    std_total_score: float
    total_evaluations: int
    timestamp: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "avg_groundedness": self.avg_groundedness,
            "avg_completeness": self.avg_completeness,
            "avg_utilization": self.avg_utilization,
            "avg_relevancy": self.avg_relevancy,
            "avg_total_score": self.avg_total_score,
            "std_groundedness": self.std_groundedness,
            "std_completeness": self.std_completeness,
            "std_utilization": self.std_utilization,
            "std_relevancy": self.std_relevancy,
            "std_total_score": self.std_total_score,
            "total_evaluations": self.total_evaluations,
            "timestamp": self.timestamp
        }


class EvaluationDashboard:
    """
    Dashboard for visualizing and analyzing RAG evaluation results.
    
    Provides:
    - Result aggregation and statistics
    - Visualization (text-based and JSON)
    - Result persistence
    - Trend analysis
    """
    
    def __init__(self, results_dir: str = "evaluation_results"):
        """
        Initialize dashboard.
        
        Args:
            results_dir: Directory to store evaluation results
        """
        self.results: List[EvaluationResult] = []
        self.results_dir = results_dir
        self._ensure_results_dir()
        
    def _ensure_results_dir(self) -> None:
        """Ensure results directory exists."""
        os.makedirs(self.results_dir, exist_ok=True)
    
    def add_result(self, result: EvaluationResult) -> None:
        """Add evaluation result to dashboard."""
        self.results.append(result)
    
    def add_results(self, results: List[EvaluationResult]) -> None:
        """Add multiple evaluation results."""
        self.results.extend(results)
    
    def aggregate_results(self) -> AggregatedMetrics:
        """
        Aggregate results across all evaluations.
        
        Returns:
            AggregatedMetrics with averages and standard deviations
        """
        if not self.results:
            return AggregatedMetrics(
                avg_groundedness=0.0,
                avg_completeness=0.0,
                avg_utilization=0.0,
                avg_relevancy=0.0,
                avg_total_score=0.0,
                std_groundedness=0.0,
                std_completeness=0.0,
                std_utilization=0.0,
                std_relevancy=0.0,
                std_total_score=0.0,
                total_evaluations=0,
                timestamp=datetime.now().isoformat()
            )
        
        n = len(self.results)
        
        # Calculate means
        groundedness_scores = [r.groundedness for r in self.results]
        completeness_scores = [r.completeness for r in self.results]
        utilization_scores = [r.utilization for r in self.results]
        relevancy_scores = [r.relevancy for r in self.results]
        total_scores = [r.total_score for r in self.results]
        
        avg_groundedness = sum(groundedness_scores) / n
        avg_completeness = sum(completeness_scores) / n
        avg_utilization = sum(utilization_scores) / n
        avg_relevancy = sum(relevancy_scores) / n
        avg_total_score = sum(total_scores) / n
        
        # Calculate standard deviations
        std_groundedness = self._calculate_std(groundedness_scores, avg_groundedness)
        std_completeness = self._calculate_std(completeness_scores, avg_completeness)
        std_utilization = self._calculate_std(utilization_scores, avg_utilization)
        std_relevancy = self._calculate_std(relevancy_scores, avg_relevancy)
        std_total_score = self._calculate_std(total_scores, avg_total_score)
        
        return AggregatedMetrics(
            avg_groundedness=avg_groundedness,
            avg_completeness=avg_completeness,
            avg_utilization=avg_utilization,
            avg_relevancy=avg_relevancy,
            avg_total_score=avg_total_score,
            std_groundedness=std_groundedness,
            std_completeness=std_completeness,
            std_utilization=std_utilization,
            std_relevancy=std_relevancy,
            std_total_score=std_total_score,
            total_evaluations=n,
            timestamp=datetime.now().isoformat()
        )
    
    def _calculate_std(self, values: List[float], mean: float) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def get_top_results(
        self,
        metric: str = "total_score",
        n: int = 5
    ) -> List[EvaluationResult]:
        """Get top N results by specified metric."""
        sorted_results = sorted(
            self.results,
            key=lambda r: getattr(r, metric),
            reverse=True
        )
        return sorted_results[:n]
    
    def get_bottom_results(
        self,
        metric: str = "total_score",
        n: int = 5
    ) -> List[EvaluationResult]:
        """Get bottom N results by specified metric."""
        sorted_results = sorted(
            self.results,
            key=lambda r: getattr(r, metric)
        )
        return sorted_results[:n]
    
    def visualize(self, output_format: str = "text") -> str:
        """
        Create visualization of evaluation results.
        
        Args:
            output_format: Output format ("text" or "json")
            
        Returns:
            Visualization string
        """
        if output_format == "json":
            return self._visualize_json()
        return self._visualize_text()
    
    def _visualize_text(self) -> str:
        """Generate text-based visualization."""
        agg = self.aggregate_results()
        
        lines = [
            "=" * 60,
            "RAG EVALUATION DASHBOARD",
            "=" * 60,
            f"Total Evaluations: {agg.total_evaluations}",
            f"Timestamp: {agg.timestamp}",
            "",
            "METRICS SUMMARY",
            "-" * 40,
            f"{'Metric':<15} {'Avg':<12} {'Std Dev':<12}",
            "-" * 40,
            f"{'Groundedness':<15} {agg.avg_groundedness:<12.3f} {agg.std_groundedness:<12.3f}",
            f"{'Completeness':<15} {agg.avg_completeness:<12.3f} {agg.std_completeness:<12.3f}",
            f"{'Utilization':<15} {agg.avg_utilization:<12.3f} {agg.std_utilization:<12.3f}",
            f"{'Relevancy':<15} {agg.avg_relevancy:<12.3f} {agg.std_relevancy:<12.3f}",
            "-" * 40,
            f"{'TOTAL SCORE':<15} {agg.avg_total_score:<12.3f} {agg.std_total_score:<12.3f}",
            "=" * 60,
            "",
            "TOP 5 PERFORMING QUERIES",
            "-" * 40
        ]
        
        for i, result in enumerate(self.get_top_results(n=5), 1):
            lines.append(
                f"{i}. Query: {result.query[:50]}... | Score: {result.total_score:.3f}"
            )
        
        lines.extend([
            "",
            "BOTTOM 5 PERFORMING QUERIES",
            "-" * 40
        ])
        
        for i, result in enumerate(self.get_bottom_results(n=5), 1):
            lines.append(
                f"{i}. Query: {result.query[:50]}... | Score: {result.total_score:.3f}"
            )
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def _visualize_json(self) -> str:
        """Generate JSON visualization."""
        data = {
            "summary": self.aggregate_results().to_dict(),
            "top_results": [r.to_dict() for r in self.get_top_results(n=10)],
            "bottom_results": [r.to_dict() for r in self.get_bottom_results(n=10)],
            "all_results": [r.to_dict() for r in self.results]
        }
        return json.dumps(data, indent=2)
    
    def save_results(self, filename: Optional[str] = None) -> str:
        """
        Save evaluation results to file.
        
        Args:
            filename: Custom filename (optional)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"
        
        filepath = os.path.join(self.results_dir, filename)
        
        data = {
            "summary": self.aggregate_results().to_dict(),
            "all_results": [r.to_dict() for r in self.results]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return filepath
    
    def load_results(self, filepath: str) -> int:
        """
        Load evaluation results from file.
        
        Args:
            filepath: Path to results file
            
        Returns:
            Number of results loaded
        """
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.results = [
            EvaluationResult(
                query=r["query"],
                answer=r["answer"],
                retrieved_context=r["retrieved_context"],
                groundedness=r["groundedness"],
                completeness=r["completeness"],
                utilization=r["utilization"],
                relevancy=r["relevancy"],
                total_score=r["total_score"],
                evaluation_details=r["evaluation_details"]
            )
            for r in data.get("all_results", [])
        ]
        
        return len(self.results)
    
    def compare_evaluations(
        self,
        other_dashboard: "EvaluationDashboard"
    ) -> Dict[str, float]:
        """
        Compare results with another evaluation run.
        
        Args:
            other_dashboard: Another EvaluationDashboard to compare against
            
        Returns:
            Dictionary with improvement percentages
        """
        current = self.aggregate_results()
        other = other_dashboard.aggregate_results()
        
        improvements = {
            "groundedness": (current.avg_groundedness - other.avg_groundedness) / max(other.avg_groundedness, 0.01) * 100,
            "completeness": (current.avg_completeness - other.avg_completeness) / max(other.avg_completeness, 0.01) * 100,
            "utilization": (current.avg_utilization - other.avg_utilization) / max(other.avg_utilization, 0.01) * 100,
            "relevancy": (current.avg_relevancy - other.avg_relevancy) / max(other.avg_relevancy, 0.01) * 100,
            "total_score": (current.avg_total_score - other.avg_total_score) / max(other.avg_total_score, 0.01) * 100
        }
        
        return improvements
    
    def generate_report(self) -> str:
        """Generate comprehensive evaluation report."""
        agg = self.aggregate_results()
        
        report_lines = [
            "RAG EVALUATION REPORT",
            "=" * 60,
            "",
            "EXECUTIVE SUMMARY",
            "-" * 40,
            f"Total Evaluations: {agg.total_evaluations}",
            f"Average Total Score: {agg.avg_total_score:.3f} ({agg.avg_total_score*100:.1f}%)",
            "",
            "METRIC BREAKDOWN",
            "-" * 40,
            f"Groundedness: {agg.avg_groundedness:.3f} (+/- {agg.std_groundedness:.3f})",
            f"Completeness: {agg.avg_completeness:.3f} (+/- {agg.std_completeness:.3f})",
            f"Utilization: {agg.avg_utilization:.3f} (+/- {agg.std_utilization:.3f})",
            f"Relevancy: {agg.avg_relevancy:.3f} (+/- {agg.std_relevancy:.3f})",
            "",
            "ASSESSMENT",
            "-" * 40
        ]
        
        # Generate assessment
        if agg.avg_total_score >= 0.8:
            assessment = "EXCELLENT - RAG system performing at high quality"
        elif agg.avg_total_score >= 0.6:
            assessment = "GOOD - RAG system performing well with room for improvement"
        elif agg.avg_total_score >= 0.4:
            assessment = "MODERATE - RAG system needs optimization"
        else:
            assessment = "POOR - RAG system requires significant improvements"
        
        report_lines.append(assessment)
        report_lines.extend([
            "",
            "RECOMMENDATIONS",
            "-" * 40
        ])
        
        if agg.avg_groundedness < 0.7:
            report_lines.append("- Improve retrieval quality to enhance groundedness")
        if agg.avg_completeness < 0.7:
            report_lines.append("- Enhance answer generation to cover more query aspects")
        if agg.avg_utilization < 0.7:
            report_lines.append("- Better leverage retrieved context in responses")
        if agg.avg_relevancy < 0.7:
            report_lines.append("- Refine generation to stay more relevant to queries")
        
        report_lines.extend([
            "",
            "=" * 60,
            f"Report generated: {agg.timestamp}",
            "=" * 60
        ])
        
        return "\n".join(report_lines)
