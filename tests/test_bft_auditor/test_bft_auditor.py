"""Integration tests for BFT auditor"""
import pytest
from agentwatch.auditors.bft_auditor import BFTAuditor
from agentwatch.auditors.consensus import ConsensusAlgorithm

# Skip if no API keys
import os

@pytest.mark.asyncio
async def test_bft_auditor_init():
    configs = [
        {"provider": "openai", "api_key": "test_key", "model": "gpt-4"},
        {"provider": "anthropic", "api_key": "test_key", "model": "claude-3"},
        {"provider": "google", "api_key": "test_key", "model": "gemini-pro"},
    ]
    
    bft = BFTAuditor(configs, quorum_size=2)
    
    assert len(bft.auditors) == 3

@pytest.mark.asyncio
async def test_bft_auditor_audit():
    # Only run if API keys available
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if not openai_key:
        pytest.skip("No OPENAI_API_KEY available")
    
    configs = [
        {"provider": "openai", "api_key": openai_key, "model": "gpt-3.5-turbo"},
    ]
    
    bft = BFTAuditor(configs, quorum_size=1)
    
    step_data = {
        "action": "echo",
        "args": {"message": "Hello"},
        "context": "Simple test"
    }
    
    result = await bft.audit_step(1, step_data)
    
    assert result.final_score >= 0.5
    assert result.total_auditors == 1