"""Tests for consensus engine"""
import pytest
from agentwatch.auditors.base import AuditResult
from agentwatch.auditors.consensus import ConsensusEngine, ConsensusAlgorithm

@pytest.mark.asyncio
async def test_majority_consensus():
    engine = ConsensusEngine()
    
    results = [
        AuditResult(score=0.9, rationale="Good", provider="openai", model="gpt-4", latency_ms=100),
        AuditResult(score=0.9, rationale="Good", provider="anthropic", model="claude", latency_ms=100),
        AuditResult(score=0.9, rationale="Good", provider="google", model="gemini", latency_ms=100),
    ]
    
    result = await engine.run_consensus(results, ConsensusAlgorithm.MAJORITY)
    
    assert result.final_score == 0.9
    assert result.agreement_level == 1.0

@pytest.mark.asyncio
async def test_byzantine_detection():
    engine = ConsensusEngine()
    
    results = [
        AuditResult(score=0.9, rationale="Good", provider="openai", model="gpt-4", latency_ms=100),
        AuditResult(score=0.9, rationale="Good", provider="anthropic", model="claude", latency_ms=100),
        AuditResult(score=0.1, rationale="Bad", provider="google", model="gemini", latency_ms=100),
    ]
    
    active, byzantine_count = engine._detect_byzantine(results)
    
    assert len(active) == 2  # Google should be excluded
    assert byzantine_count == 1

@pytest.mark.asyncio
async def test_weighted_consensus():
    # Mock trust scorer
    class MockTrustScorer:
        def get_trust_score(self, provider, model):
            if provider == "openai":
                return 0.9
            elif provider == "anthropic":
                return 0.8
            else:
                return 0.5
    
    engine = ConsensusEngine(trust_scorer=MockTrustScorer())
    
    results = [
        AuditResult(score=0.9, rationale="Good", provider="openai", model="gpt-4", latency_ms=100),
        AuditResult(score=0.8, rationale="Good", provider="anthropic", model="claude", latency_ms=100),
        AuditResult(score=0.7, rationale="Good", provider="google", model="gemini", latency_ms=100),
    ]
    
    result = await engine.run_consensus(results, ConsensusAlgorithm.WEIGHTED)
    
    # Weighted should favor OpenAI (0.9 trust) score
    assert result.final_score < 0.85  # Weighted lower due to Google
    assert result.final_score > 0.78  # But still near majority