#!/usr/bin/env python3
"""Baseline Evaluation Script - Run evaluation on test query set."""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from evaluation.rag_evaluator import RAGEvaluator
from evaluation.dashboard import EvaluationDashboard
from evaluation.test_queries import TestQuerySet


def simulate_answer(query: str, context: list) -> str:
    """Simulate a generated answer for evaluation."""
    # In production, this would use the actual RAG system
    # For baseline, we simulate reasonable answers
    return f"Based on the context, the answer to '{query}' is that the information provided in the retrieved documents contains relevant details."


def simulate_context(query: str) -> list:
    """Simulate retrieved context for a query."""
    # In production, this would use the actual retriever
    # For baseline, we simulate context
    return [
        f"Document 1: Contains information about {query}",
        f"Document 2: Additional context related to {query}",
        f"Document 3: Supporting details for the query"
    ]


def run_baseline_evaluation():
    """Run baseline evaluation on test query set."""
    print("=" * 60)
    print("RAG EVALUATION - BASELINE MEASUREMENT")
    print("=" * 60)
    print()
    
    # Initialize components
    evaluator = RAGEvaluator()
    dashboard = EvaluationDashboard(results_dir="evaluation_results")
    query_set = TestQuerySet()
    
    print(f"Test Query Set: {len(query_set)} queries")
    print(f"Evaluation Weights: {evaluator.weights}")
    print()
    
    # Evaluate queries
    results = []
    for i, test_query in enumerate(query_set.get_all_queries(), 1):
        # Simulate RAG response
        context = simulate_context(test_query.query)
        answer = simulate_answer(test_query.query, context)
        
        # Evaluate
        result = evaluator.evaluate(
            query=test_query.query,
            answer=answer,
            context=context,
            ground_truth=test_query.ground_truth
        )
        results.append(result)
        dashboard.add_result(result)
        
        # Progress indicator
        if i % 10 == 0 or i == len(query_set):
            print(f"Evaluated {i}/{len(query_set)} queries...")
    
    print()
    print("=" * 60)
    print("BASELINE RESULTS")
    print("=" * 60)
    print()
    
    # Generate and display results
    agg = dashboard.aggregate_results()
    
    print("AGGREGATED METRICS")
    print("-" * 40)
    print(f"Total Evaluations: {agg.total_evaluations}")
    print(f"Average Total Score: {agg.avg_total_score:.3f} ({agg.avg_total_score*100:.1f}%)")
    print()
    print("Metric Breakdown:")
    print(f"  Groundedness:  {agg.avg_groundedness:.3f} (+/- {agg.std_groundedness:.3f})")
    print(f"  Completeness:  {agg.avg_completeness:.3f} (+/- {agg.std_completeness:.3f})")
    print(f"  Utilization:   {agg.avg_utilization:.3f} (+/- {agg.std_utilization:.3f})")
    print(f"  Relevancy:     {agg.avg_relevancy:.3f} (+/- {agg.std_relevancy:.3f})")
    print()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = dashboard.save_results(f"baseline_{timestamp}.json")
    print(f"Results saved to: {results_file}")
    
    # Generate report
    report = dashboard.generate_report()
    report_file = os.path.join("evaluation_results", f"baseline_report_{timestamp}.txt")
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"Report saved to: {report_file}")
    
    print()
    print("=" * 60)
    print("TOP 5 PERFORMING QUERIES")
    print("=" * 60)
    for i, result in enumerate(dashboard.get_top_results(n=5), 1):
        print(f"{i}. {result.query[:60]}... | Score: {result.total_score:.3f}")
    
    print()
    print("=" * 60)
    print("BOTTOM 5 PERFORMING QUERIES")
    print("=" * 60)
    for i, result in enumerate(dashboard.get_bottom_results(n=5), 1):
        print(f"{i}. {result.query[:60]}... | Score: {result.total_score:.3f}")
    
    print()
    print("=" * 60)
    print("BASELINE EVALUATION COMPLETE")
    print("=" * 60)
    
    return dashboard


if __name__ == "__main__":
    dashboard = run_baseline_evaluation()
