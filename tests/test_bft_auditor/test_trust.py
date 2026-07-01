"""Tests for trust scoring"""
import pytest
from agentwatch.auditors.trust import TrustScorer, TrustScore

def test_trust_score_update():
    score = TrustScore(provider="openai", model="gpt-4")
    
    assert score.score == 0.5
    assert score.total_audits == 0
    assert score.accuracy == 0.5
    
    score.update(was_correct=True)
    assert score.total_audits == 1
    assert score.correct_audits == 1
    assert score.accuracy == 1.0
    
    score.update(was_correct=False)
    assert score.total_audits == 2
    assert score.correct_audits == 1
    assert score.accuracy == 0.5

def test_trust_scorer():
    scorer = TrustScorer()
    
    trust = scorer.get_trust_score("openai", "gpt-4")
    assert trust == 0.5
    
    scorer.update_score("openai", "gpt-4", was_correct=True)
    
    trust = scorer.get_trust_score("openai", "gpt-4")
    assert trust > 0.5