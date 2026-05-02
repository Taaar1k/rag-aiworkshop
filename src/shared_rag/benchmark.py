"""
Performance benchmarking script for Shared RAG Client SDK.
Tests query latency to ensure it meets the < 500ms requirement.
"""

import os
import time
import statistics
from typing import List, Dict, Any, Optional
import logging

# Add src to path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from shared_rag.client import SharedRAGClient, QueryResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Benchmark performance of the Shared RAG client."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: str = None,
        num_samples: int = 10
    ):
        """
        Initialize the benchmark.
        
        Args:
            base_url: URL of the RAG server
            api_key: API key for authentication
            num_samples: Number of samples to collect
        """
        actual_url = base_url or os.getenv("RAG_SERVER_URL", "http://localhost:8000")
        self.client = SharedRAGClient(base_url=actual_url, api_key=api_key)
        self.num_samples = num_samples
        self.latencies: List[float] = []
        
    def warmup(self, queries: List[str]) -> None:
        """Run warmup queries to initialize caches and connections."""
        logger.info("Running warmup queries...")
        for query in queries[:2]:  # Warmup with 2 queries
            try:
                result = self.client.query(query)
                logger.info(f"Warmup query completed in {result.query_time_ms:.2f}ms")
            except Exception as e:
                logger.warning(f"Warmup query failed: {e}")
    
    def benchmark_query(self, query: str) -> float:
        """
        Benchmark a single query.
        
        Args:
            query: The query to benchmark
            
        Returns:
            Query latency in milliseconds
        """
        start_time = time.time()
        result = self.client.query(query)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        return latency_ms
    
    def run_benchmark(self, queries: List[str]) -> Dict[str, Any]:
        """
        Run the full benchmark suite.
        
        Args:
            queries: List of queries to benchmark
            
        Returns:
            Dictionary with benchmark results
        """
        logger.info(f"Starting benchmark with {len(queries)} queries, {self.num_samples} samples each")
        
        all_results = {
            "queries": [],
            "latencies": [],
            "statistics": {},
            "passed": False
        }
        
        for query in queries:
            logger.info(f"Benchmarking query: '{query}'")
            query_latencies = []
            
            for i in range(self.num_samples):
                try:
                    latency = self.benchmark_query(query)
                    query_latencies.append(latency)
                    logger.info(f"  Sample {i+1}/{self.num_samples}: {latency:.2f}ms")
                except Exception as e:
                    logger.error(f"  Sample {i+1} failed: {e}")
                    continue
            
            if query_latencies:
                # Calculate statistics
                stats = {
                    "query": query,
                    "min": min(query_latencies),
                    "max": max(query_latencies),
                    "mean": statistics.mean(query_latencies),
                    "median": statistics.median(query_latencies),
                    "stdev": statistics.stdev(query_latencies) if len(query_latencies) > 1 else 0,
                    "samples": len(query_latencies)
                }
                
                all_results["queries"].append(stats)
                all_results["latencies"].extend(query_latencies)
                
                logger.info(f"  Statistics: min={stats['min']:.2f}ms, "
                           f"max={stats['max']:.2f}ms, "
                           f"mean={stats['mean']:.2f}ms, "
                           f"median={stats['median']:.2f}ms")
        
        # Calculate overall statistics
        if all_results["latencies"]:
            overall_stats = {
                "min": min(all_results["latencies"]),
                "max": max(all_results["latencies"]),
                "mean": statistics.mean(all_results["latencies"]),
                "median": statistics.median(all_results["latencies"]),
                "stdev": statistics.stdev(all_results["latencies"]) if len(all_results["latencies"]) > 1 else 0,
                "total_samples": len(all_results["latencies"]),
                "threshold_ms": 500,
                "passed": all(
                    latency < 500 for latency in all_results["latencies"]
                )
            }
            
            all_results["statistics"] = overall_stats
            all_results["passed"] = overall_stats["passed"]
            
            logger.info(f"\n=== BENCHMARK RESULTS ===")
            logger.info(f"Total samples: {overall_stats['total_samples']}")
            logger.info(f"Mean latency: {overall_stats['mean']:.2f}ms")
            logger.info(f"Median latency: {overall_stats['median']:.2f}ms")
            logger.info(f"Min latency: {overall_stats['min']:.2f}ms")
            logger.info(f"Max latency: {overall_stats['max']:.2f}ms")
            logger.info(f"Std deviation: {overall_stats['stdev']:.2f}ms")
            logger.info(f"Threshold: {overall_stats['threshold_ms']}ms")
            logger.info(f"Passed: {overall_stats['passed']}")
        
        return all_results
    
    def close(self):
        """Close the client connection."""
        self.client.close()


def main():
    """Run the performance benchmark."""
    # Test queries
    test_queries = [
        "What is the capital of France?",
        "Explain quantum computing",
        "What is Python?",
        "How does machine learning work?",
        "What is the meaning of life?"
    ]
    
    # Initialize benchmark
    benchmark = PerformanceBenchmark(
        base_url=os.getenv("RAG_SERVER_URL", "http://localhost:8000"),
        api_key=None,  # Set API key if needed
        num_samples=5  # 5 samples per query
    )
    
    try:
        # Run benchmark
        results = benchmark.run_benchmark(test_queries)
        
        # Print results
        print("\n" + "="*60)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("="*60)
        
        if results["passed"]:
            print("✅ PASSED: All queries completed within 500ms threshold")
        else:
            print("❌ FAILED: Some queries exceeded 500ms threshold")
        
        print(f"\nOverall Statistics:")
        print(f"  Mean latency: {results['statistics']['mean']:.2f}ms")
        print(f"  Median latency: {results['statistics']['median']:.2f}ms")
        print(f"  Min latency: {results['statistics']['min']:.2f}ms")
        print(f"  Max latency: {results['statistics']['max']:.2f}ms")
        
        print("\nPer-query Statistics:")
        for query_stats in results["queries"]:
            print(f"\n  Query: '{query_stats['query']}'")
            print(f"    Mean: {query_stats['mean']:.2f}ms")
            print(f"    Median: {query_stats['median']:.2f}ms")
            print(f"    Min: {query_stats['min']:.2f}ms")
            print(f"    Max: {query_stats['max']:.2f}ms")
        
        return 0 if results["passed"] else 1
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        return 1
    finally:
        benchmark.close()


if __name__ == "__main__":
    exit(main())
