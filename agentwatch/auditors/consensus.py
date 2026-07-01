"""Consensus algorithms for multi-auditor system"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import Counter
import logging
from .base import AuditResult, AuditorStatus

logger = logging.getLogger(__name__)

class ConsensusAlgorithm(Enum):
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    BYZANTINE = "byzantine"

@dataclass
class ConsensusResult:
    """Result of consensus algorithm"""
    final_score: float
    rationale: str
    algorithm_used: ConsensusAlgorithm
    agreement_level: float  # 0.0 - 1.0
    total_auditors: int
    participating_auditors: int
    byzantine_excluded: int = 0
    individual_scores: Dict[str, float] = field(default_factory=dict)
    is_agreement_reached: bool = True

class ConsensusEngine:
    """Engine for running consensus algorithms"""
    
    def __init__(self, threshold: float = 0.6, trust_scorer=None):
        self.threshold = threshold
        self.trust_scorer = trust_scorer
        self.logger = logging.getLogger(__name__)
    
    async def run_consensus(
        self,
        results: List[AuditResult],
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.WEIGHTED,
        byzantine_detection: bool = True
    ) -> ConsensusResult:
        """Run consensus on auditor results"""
        
        if not results:
            raise ValueError("No results to reach consensus on")
        
        # First, detect and exclude Byzantine auditors if enabled
        active_results = results
        byzantine_count = 0
        
        if byzantine_detection:
            active_results, byzantine_count = self._detect_byzantine(results)
        
        if not active_results:
            # All auditors are Byzantine - use median
            return self._fallback_consensus(results)
        
        # Run the selected algorithm
        if algorithm == ConsensusAlgorithm.MAJORITY:
            return await self._majority_consensus(active_results)
        elif algorithm == ConsensusAlgorithm.WEIGHTED:
            return await self._weighted_consensus(active_results)
        elif algorithm == ConsensusAlgorithm.BYZANTINE:
            return await self._byzantine_consensus(active_results)
        else:
            return await self._majority_consensus(active_results)
    
    def _detect_byzantine(self, results: List[AuditResult]) -> tuple[List[AuditResult], int]:
        """Detect and exclude Byzantine auditors"""
        
        if len(results) < 3:
            return results, 0
        
        scores = [r.score for r in results]
        
        # Calculate statistical outliers
        mean = sum(scores) / len(scores)
        std = (sum((x - mean) ** 2 for x in scores) / len(scores)) ** 0.5
        
        # Flag results that are > 3 standard deviations from mean
        byzantine_indices = []
        for i, result in enumerate(results):
            if abs(result.score - mean) > 3 * std:
                byzantine_indices.append(i)
                result.is_byzantine = True
        
        # Also flag results with very low confidence
        for i, result in enumerate(results):
            if result.confidence < 0.3 and i not in byzantine_indices:
                byzantine_indices.append(i)
                result.is_byzantine = True
        
        # If > 50% are Byzantine, use median instead
        if len(byzantine_indices) > len(results) / 2:
            self.logger.warning("More than 50% auditors flagged as Byzantine - using median")
            return results, 0
        
        # Return only non-Byzantine results
        active_results = [r for i, r in enumerate(results) if i not in byzantine_indices]
        return active_results, len(byzantine_indices)
    
    async def _majority_consensus(self, results: List[AuditResult]) -> ConsensusResult:
        """Simple majority vote consensus"""
        
        # Round scores to nearest 0.1 for voting
        rounded_scores = [round(r.score * 10) / 10 for r in results]
        score_counts = Counter(rounded_scores)
        
        # Find most common score
        majority_score = score_counts.most_common(1)[0][0]
        
        # Calculate agreement level
        agreement = score_counts[majority_score] / len(results)
        
        # Average rationale from all results
        rationale = self._aggregate_rationale(results)
        
        return ConsensusResult(
            final_score=majority_score,
            rationale=rationale,
            algorithm_used=ConsensusAlgorithm.MAJORITY,
            agreement_level=agreement,
            total_auditors=len(results),
            participating_auditors=len(results),
            individual_scores={r.provider: r.score for r in results}
        )
    
    async def _weighted_consensus(self, results: List[AuditResult]) -> ConsensusResult:
        """Weighted consensus using trust scores"""
        
        if self.trust_scorer is None:
            # Fallback to majority if no trust scorer
            return await self._majority_consensus(results)
        
        total_weight = 0
        weighted_sum = 0
        trust_scores = {}
        
        for result in results:
            trust = self.trust_scorer.get_trust_score(result.provider, result.model)
            trust_scores[result.provider] = trust
            total_weight += trust
            weighted_sum += result.score * trust
        
        if total_weight == 0:
            return await self._majority_consensus(results)
        
        final_score = weighted_sum / total_weight
        
        # Calculate agreement level
        # (how close individual scores are to final score)
        agreement = 1 - (sum(abs(r.score - final_score) for r in results) / len(results))
        
        return ConsensusResult(
            final_score=final_score,
            rationale=self._aggregate_rationale(results),
            algorithm_used=ConsensusAlgorithm.WEIGHTED,
            agreement_level=agreement,
            total_auditors=len(results),
            participating_auditors=len(results),
            individual_scores={r.provider: r.score for r in results}
        )
    
    async def _byzantine_consensus(self, results: List[AuditResult]) -> ConsensusResult:
        """Byzantine fault-tolerant consensus"""
        
        # Use weighted consensus internally
        result = await self._weighted_consensus(results)
        result.algorithm_used = ConsensusAlgorithm.BYZANTINE
        
        # Add Byzantine-specific metadata
        result.byzantine_excluded = len([r for r in results if r.is_byzantine])
        
        return result
    
    def _fallback_consensus(self, results: List[AuditResult]) -> ConsensusResult:
        """Fallback when all auditors are Byzantine"""
        
        # Use median score
        scores = sorted([r.score for r in results])
        median = scores[len(scores) // 2]
        
        return ConsensusResult(
            final_score=median,
            rationale="Fallback: Using median score due to Byzantine detection",
            algorithm_used=ConsensusAlgorithm.MAJORITY,
            agreement_level=0.5,
            total_auditors=len(results),
            participating_auditors=0,
            byzantine_excluded=len(results),
            individual_scores={r.provider: r.score for r in results},
            is_agreement_reached=False
        )
    
    def _aggregate_rationale(self, results: List[AuditResult]) -> str:
        """Aggregate rationales from multiple auditors"""
        if len(results) == 1:
            return results[0].rationale
        
        # Take the most confident rationale
        best_result = max(results, key=lambda r: r.confidence)
        return f"[Consensus from {len(results)} auditors] {best_result.rationale}"