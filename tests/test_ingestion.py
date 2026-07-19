from agentwatch.telemetry.ingestion import IngestionMetrics, RateLimiter

def test_rate_limiter():
    limiter = RateLimiter()
    # Test allow under limit
    assert limiter.allow("tenant_1", 10) == True
    
    # Exhaust tokens
    for _ in range(9):
        assert limiter.allow("tenant_1", 10) == True
        
    assert limiter.allow("tenant_1", 10) == False
    
    metrics = IngestionMetrics()
    assert metrics.events_received == 0
