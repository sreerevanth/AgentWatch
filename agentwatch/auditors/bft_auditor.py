"""BFT Multi-Auditor Consensus System"""
from typing import List, Dict, Any, Optional
import asyncio
import logging
import time
from .base import BaseAuditor, AuditResult
from .openai import OpenAIAuditor
from .anthropic import AnthropicAuditor
from .google import GoogleAuditor
from .consensus import ConsensusEngine, ConsensusResult, ConsensusAlgorithm
from .trust import TrustScorer

logger = logging.getLogger(__name__)

class BFTAuditor:
    """Byzantine Fault Tolerant Multi-Auditor System"""
    
    def __init__(
        self,
        configs: List[Dict[str, Any]],
        trust_scorer: Optional[TrustScorer] = None,
        consensus_threshold: float = 0.6,
        quorum_size: int = 2,
        timeout_seconds: float = 2.0
    ):
        self.auditors: List[BaseAuditor] = []
        self.trust_scorer = trust_scorer or TrustScorer()
        self.consensus_engine = ConsensusEngine(threshold=consensus_threshold, trust_scorer=self.trust_scorer)
        self.quorum_size = quorum_size
        self.timeout_seconds = timeout_seconds
        
        # Initialize auditors from configs
        for config in configs:
            auditor = self._create_auditor(config)
            if auditor:
                self.auditors.append(auditor)
        
        if len(self.auditors) < 3:
            logger.warning("BFT auditor requires at least 3 auditors. Add more providers.")
    
    def _create_auditor(self, config: Dict[str, Any]) -> Optional[BaseAuditor]:
        """Create auditor from config"""
        provider = config.get('provider', '').lower()
        api_key = config.get('api_key', '')
        model = config.get('model', '')
        
        if not api_key:
            logger.warning(f"No API key provided for {provider}")
            return None
        
        if provider == 'openai':
            return OpenAIAuditor(api_key, model or 'gpt-4')
        elif provider == 'anthropic':
            return AnthropicAuditor(api_key, model or 'claude-3-sonnet-20240229')
        elif provider == 'google' or provider == 'gemini':
            return GoogleAuditor(api_key, model or 'gemini-pro')
        else:
            logger.warning(f"Unsupported provider: {provider}")
            return None
    
    async def audit_step(
        self, 
        step_number: int, 
        step_data: Dict[str, Any],
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.WEIGHTED
    ) -> ConsensusResult:
        """Audit a step using multiple auditors with consensus"""
        
        start_time = time.perf_counter()
        
        # Run all auditors in parallel
        tasks = []
        for auditor in self.auditors:
            tasks.append(self._audit_with_timeout(auditor, step_number, step_data))
        
        # Wait for all tasks with timeout
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"Audit step {step_number} timed out")
            # Use results from completed auditors
            results = [await task for task in tasks if not task.done()]
        
        # Filter out errors
        valid_results = []
        for result in results:
            if isinstance(result, AuditResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.warning(f"Auditor failed: {result}")
        
        if len(valid_results) < self.quorum_size:
            logger.warning(f"Quorum not reached: {len(valid_results)} < {self.quorum_size}")
            # Return fallback with best available
            return self._fallback_consensus(valid_results)
        
        # Run consensus
        consensus_result = await self.consensus_engine.run_consensus(
            valid_results, 
            algorithm=algorithm,
            byzantine_detection=True
        )
        
        # Update trust scores based on consensus
        if consensus_result.is_agreement_reached:
            for result in valid_results:
                is_correct = abs(result.score - consensus_result.final_score) < 0.3
                self.trust_scorer.update_score(
                    result.provider, 
                    result.model, 
                    is_correct
                )
        
        # Add timing metadata
        consensus_result.individual_scores = {r.provider: r.score for r in valid_results}
        
        logger.info(
            f"Audit step {step_number} complete: {consensus_result.final_score:.2f} "
            f"({len(valid_results)} auditors, "
            f"agreement: {consensus_result.agreement_level:.2f})"
        )
        
        return consensus_result
    
    async def _audit_with_timeout(
        self, 
        auditor: BaseAuditor, 
        step_number: int, 
        step_data: Dict[str, Any]
    ) -> AuditResult:
        """Audit with per-auditor timeout"""
        try:
            return await asyncio.wait_for(
                auditor.audit_step(step_number, step_data),
                timeout=self.timeout_seconds / 2
            )
        except asyncio.TimeoutError:
            auditor.mark_unresponsive()
            return AuditResult(
                score=0.5,
                rationale="Auditor timed out",
                provider=auditor.provider,
                model=auditor.model,
                latency_ms=self.timeout_seconds * 1000,
                confidence=0.1
            )
        except Exception as e:
            auditor.mark_unresponsive()
            return AuditResult(
                score=0.5,
                rationale=f"Auditor error: {str(e)}",
                provider=auditor.provider,
                model=auditor.model,
                latency_ms=0,
                confidence=0.1
            )
    
    def _fallback_consensus(self, results: List[AuditResult]) -> ConsensusResult:
        """Fallback when quorum not reached"""
        if not results:
            return ConsensusResult(
                final_score=0.5,
                rationale="No auditors available, using default",
                algorithm_used=ConsensusAlgorithm.MAJORITY,
                agreement_level=0,
                total_auditors=0,
                participating_auditors=0,
                individual_scores={},
                is_agreement_reached=False
            )
        
        # Use average of available scores
        avg_score = sum(r.score for r in results) / len(results)
        
        return ConsensusResult(
            final_score=avg_score,
            rationale=f"Fallback: {len(results)} auditors available",
            algorithm_used=ConsensusAlgorithm.MAJORITY,
            agreement_level=0.5,
            total_auditors=len(self.auditors),
            participating_auditors=len(results),
            individual_scores={r.provider: r.score for r in results},
            is_agreement_reached=False
        )
    
    def get_auditor_status(self) -> Dict[str, str]:
        """Get status of all auditors"""
        return {f"{a.provider}:{a.model}": a.status.value for a in self.auditors}
    
    def get_trust_ranking(self) -> list[tuple[str, float]]:
        """Get trust ranking of all auditors"""
        return self.trust_scorer.get_ranking()
