"""RAG Evaluator - Core evaluation framework for RAG quality metrics."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum
import re


class EvaluationMetric(Enum):
    """Supported evaluation metrics."""
    GROUNDEDNESS = "groundedness"
    COMPLETENESS = "completeness"
    UTILIZATION = "utilization"
    RELEVANCY = "relevancy"


@dataclass
class EvaluationResult:
    """Result of RAG evaluation for a single query-response pair."""
    query: str
    answer: str
    retrieved_context: List[str]
    groundedness: float  # 0-1: Is answer supported by retrieved data?
    completeness: float  # 0-1: Does answer cover all query aspects?
    utilization: float   # 0-1: How well does model use context?
    relevancy: float     # 0-1: Is answer relevant to query?
    total_score: float   # weighted average
    evaluation_details: Dict[str, str]  # Additional context about evaluation
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "answer": self.answer,
            "retrieved_context": self.retrieved_context,
            "groundedness": self.groundedness,
            "completeness": self.completeness,
            "utilization": self.utilization,
            "relevancy": self.relevancy,
            "total_score": self.total_score,
            "evaluation_details": self.evaluation_details
        }


class RAGEvaluator:
    """
    Comprehensive RAG evaluation framework.
    
    Evaluates RAG responses against multiple quality metrics:
    - Groundedness: Is the answer supported by retrieved context?
    - Completeness: Does the answer cover all aspects of the query?
    - Utilization: How effectively does the model use retrieved context?
    - Relevancy: Is the answer relevant to the original query?
    """
    
    # Weight configuration for metrics
    DEFAULT_WEIGHTS = {
        'groundedness': 0.30,
        'completeness': 0.25,
        'utilization': 0.25,
        'relevancy': 0.20
    }
    
    VALID_KEYS = {'groundedness', 'completeness', 'utilization', 'relevancy'}
    
    def __init__(
        self,
        llm_client: Optional[object] = None,
        evaluation_model: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize RAG evaluator.
        
        Args:
            llm_client: Optional LLM client for evaluation (can be None for rule-based)
            evaluation_model: Model name for evaluation tasks
            weights: Custom metric weights (must sum to 1.0)
        """
        self.llm_client = llm_client
        self.evaluation_model = evaluation_model or "default"
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()
        
    def _validate_weights(self) -> None:
        """Validate that weights sum to approximately 1.0."""
        # Check keys
        if set(self.weights.keys()) != self.VALID_KEYS:
            raise ValueError(f"Weights must have keys {self.VALID_KEYS}, got {set(self.weights.keys())}")
        
        # Check sum
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.4f}")
    
    def evaluate(
        self,
        query: str,
        answer: str,
        context: List[str],
        ground_truth: Optional[str] = None
    ) -> EvaluationResult:
        """
        Evaluate RAG response against all metrics.
        
        Args:
            query: User query
            answer: Generated answer
            context: Retrieved context documents
            ground_truth: Optional ground truth for completeness check
            
        Returns:
            EvaluationResult with all metric scores
        """
        groundedness = self._evaluate_groundedness(answer, context)
        completeness = self._evaluate_completeness(answer, query, ground_truth)
        utilization = self._evaluate_utilization(answer, context)
        relevancy = self._evaluate_relevancy(answer, query)
        
        total_score = self._calculate_total_score(
            groundedness, completeness, utilization, relevancy
        )
        
        evaluation_details = {
            "groundedness_explanation": self._get_groundedness_explanation(answer, context),
            "completeness_explanation": self._get_completeness_explanation(answer, query),
            "utilization_explanation": self._get_utilization_explanation(answer, context),
            "relevancy_explanation": self._get_relevancy_explanation(answer, query)
        }
        
        return EvaluationResult(
            query=query,
            answer=answer,
            retrieved_context=context,
            groundedness=groundedness,
            completeness=completeness,
            utilization=utilization,
            relevancy=relevancy,
            total_score=total_score,
            evaluation_details=evaluation_details
        )
    
    def _evaluate_groundedness(self, answer: str, context: List[str]) -> float:
        """
        Evaluate if answer is supported by retrieved context.
        
        Uses claim verification: extracts claims from answer and checks
        if each claim is supported by at least one context document.
        """
        if not context or not answer.strip():
            return 0.0
        
        # Extract claims from answer (simplified: sentence-level)
        claims = self._extract_claims(answer)
        if not claims:
            return 1.0  # No claims to verify
        
        # Check each claim against context
        supported_claims = 0
        for claim in claims:
            if self._is_claim_supported(claim, context):
                supported_claims += 1
        
        return supported_claims / len(claims)
    
    def _is_claim_supported(self, claim: str, context: List[str]) -> bool:
        """Check if a claim is supported by any context document."""
        claim_lower = claim.lower().strip()
        
        for doc in context:
            doc_lower = doc.lower()
            # Check for exact or partial match
            if claim_lower in doc_lower:
                return True
            # Check for key phrase overlap
            claim_words = set(claim_lower.split())
            doc_words = set(doc_lower.split())
            overlap = len(claim_words & doc_words)
            if overlap >= len(claim_words) * 0.5:
                return True
        
        return False
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract declarative claims from text."""
        # Split by sentence boundaries
        sentences = re.split(r'[.!?]+', text)
        claims = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        return claims[:10]  # Limit to first 10 claims
    
    def _evaluate_completeness(
        self,
        answer: str,
        query: str,
        ground_truth: Optional[str] = None
    ) -> float:
        """
        Evaluate if answer covers all aspects of query.
        
        Uses query decomposition: breaks query into sub-questions
        and checks if answer addresses each.
        """
        if not answer.strip():
            return 0.0
        
        # If ground truth available, compare answer coverage
        if ground_truth:
            return self._compare_with_ground_truth(answer, ground_truth)
        
        # Otherwise, use query-based assessment
        query_aspects = self._decompose_query(query)
        if not query_aspects:
            return 1.0
        
        covered_aspects = 0
        for aspect in query_aspects:
            if self._aspect_covered(aspect, answer):
                covered_aspects += 1
        
        return covered_aspects / len(query_aspects)
    
    def _decompose_query(self, query: str) -> List[str]:
        """Break query into key aspects/sub-questions."""
        # Simplified: extract key phrases
        query_lower = query.lower()
        aspects = []
        
        # Common question patterns
        patterns = [
            r'what (?:is|are) ([^\?]+)',
            r'how (?:to|does|did) ([^\?]+)',
            r'why (?:is|are) ([^\?]+)',
            r'when (?:is|are) ([^\?]+)',
            r'who (?:is|are) ([^\?]+)',
            r'where (?:is|are) ([^\?]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query_lower, re.IGNORECASE)
            aspects.extend(matches)
        
        # Add key noun phrases if no patterns matched
        if not aspects:
            # Extract key terms (nouns/phrases)
            key_terms = re.findall(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)*)\b', query)
            aspects = key_terms[:5]
        
        return aspects[:5]
    
    def _aspect_covered(self, aspect: str, answer: str) -> bool:
        """Check if an aspect is covered in the answer."""
        aspect_lower = aspect.lower().strip()
        answer_lower = answer.lower()
        
        # Direct match
        if aspect_lower in answer_lower:
            return True
        
        # Partial match with context
        aspect_words = set(aspect_lower.split())
        answer_words = set(answer_lower.split())
        overlap = len(aspect_words & answer_words)
        
        return overlap >= len(aspect_words) * 0.4
    
    def _compare_with_ground_truth(self, answer: str, ground_truth: str) -> float:
        """Compare answer coverage against ground truth."""
        # Simplified: check overlap of key terms
        answer_terms = set(re.findall(r'\b\w+\b', answer.lower()))
        gt_terms = set(re.findall(r'\b\w+\b', ground_truth.lower()))
        
        if not gt_terms:
            return 0.0
        
        # Coverage ratio
        coverage = len(answer_terms & gt_terms) / len(gt_terms)
        
        # Bonus for including important phrases
        important_phrases = self._extract_important_phrases(ground_truth)
        for phrase in important_phrases:
            if phrase in answer.lower():
                coverage = min(coverage + 0.1, 1.0)
        
        return coverage
    
    def _extract_important_phrases(self, text: str) -> List[str]:
        """Extract important phrases from text."""
        phrases = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+){1,2}\b', text)
        return phrases[:3]
    
    def _evaluate_utilization(self, answer: str, context: List[str]) -> float:
        """
        Evaluate how well model uses retrieved context.
        
        Measures if answer contains information that can only
        be derived from the context (not general knowledge).
        """
        if not context or not answer.strip():
            return 0.0
        
        # Extract unique information from answer
        answer_sentences = self._extract_claims(answer)
        if not answer_sentences:
            return 0.0
        
        # Check how many sentences contain context-specific info
        context_specific_count = 0
        for sentence in answer_sentences:
            if self._is_context_specific(sentence, context):
                context_specific_count += 1
        
        return context_specific_count / len(answer_sentences)
    
    def _is_context_specific(self, sentence: str, context: List[str]) -> bool:
        """Check if sentence contains context-specific information."""
        sentence_lower = sentence.lower()
        
        # Check for specific entities, numbers, or phrases from context
        for doc in context:
            doc_lower = doc.lower()
            # Look for specific patterns
            if self._find_specific_patterns(sentence_lower, doc_lower):
                return True
        
        return False
    
    def _find_specific_patterns(self, sentence: str, context: str) -> bool:
        """Find specific patterns that indicate context usage."""
        # Check for numbers, dates, proper nouns
        numbers = re.findall(r'\b\d+\b', sentence)
        if any(num in context for num in numbers):
            return True
        
        # Check for unique phrases
        phrases = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+){1,2}\b', sentence)
        if any(phrase in context for phrase in phrases):
            return True
        
        return False
    
    def _evaluate_relevancy(self, answer: str, query: str) -> float:
        """
        Evaluate if answer is relevant to query.
        
        Checks if answer directly addresses the user's question
        without unnecessary tangents.
        """
        if not answer.strip() or not query.strip():
            return 0.0
        
        # Extract key query terms
        query_terms = set(re.findall(r'\b\w+\b', query.lower()))
        answer_terms = set(re.findall(r'\b\w+\b', answer.lower()))
        
        if not query_terms:
            return 0.0
        
        # Relevance ratio
        relevance = len(query_terms & answer_terms) / len(query_terms)
        
        # Penalty for irrelevant content
        irrelevant_patterns = [
            r'i\s+am\s+a',
            r'this\s+is\s+a',
            r'as\s+an\s+ai'
        ]
        
        for pattern in irrelevant_patterns:
            if re.search(pattern, answer.lower()):
                relevance = max(relevance - 0.1, 0.0)
        
        return min(relevance, 1.0)
    
    def _calculate_total_score(
        self,
        groundedness: float,
        completeness: float,
        utilization: float,
        relevancy: float
    ) -> float:
        """Calculate weighted average score."""
        return (
            groundedness * self.weights['groundedness'] +
            completeness * self.weights['completeness'] +
            utilization * self.weights['utilization'] +
            relevancy * self.weights['relevancy']
        )
    
    def _get_groundedness_explanation(self, answer: str, context: List[str]) -> str:
        """Get explanation for groundedness score."""
        claims = self._extract_claims(answer)
        supported = sum(1 for c in claims if self._is_claim_supported(c, context))
        return f"{supported}/{len(claims)} claims supported by context"
    
    def _get_completeness_explanation(self, answer: str, query: str) -> str:
        """Get explanation for completeness score."""
        aspects = self._decompose_query(query)
        covered = sum(1 for a in aspects if self._aspect_covered(a, answer))
        return f"{covered}/{len(aspects)} query aspects covered"
    
    def _get_utilization_explanation(self, answer: str, context: List[str]) -> str:
        """Get explanation for utilization score."""
        sentences = self._extract_claims(answer)
        specific = sum(1 for s in sentences if self._is_context_specific(s, context))
        return f"{specific}/{len(sentences)} sentences use context-specific info"
    
    def _get_relevancy_explanation(self, answer: str, query: str) -> str:
        """Get explanation for relevancy score."""
        query_terms = set(re.findall(r'\b\w+\b', query.lower()))
        answer_terms = set(re.findall(r'\b\w+\b', answer.lower()))
        overlap = len(query_terms & answer_terms)
        return f"{overlap}/{len(query_terms)} query terms in answer"
    
    def batch_evaluate(
        self,
        evaluations: List[Tuple[str, str, List[str], Optional[str]]]
    ) -> List[EvaluationResult]:
        """
        Evaluate multiple query-response pairs.
        
        Args:
            evaluations: List of (query, answer, context, ground_truth) tuples
            
        Returns:
            List of EvaluationResult objects
        """
        return [
            self.evaluate(query, answer, context, ground_truth)
            for query, answer, context, ground_truth in evaluations
        ]
