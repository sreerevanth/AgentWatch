"""Base auditor interface for all providers"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class AuditorStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BYZANTINE = "byzantine"
    UNRESPONSIVE = "unresponsive"

@dataclass
class AuditResult:
    """Result from a single auditor"""
    score: float  # 0.0 - 1.0
    rationale: str
    provider: str
    model: str
    latency_ms: float
    confidence: float = 1.0
    is_byzantine: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_trusted(self) -> bool:
        return not self.is_byzantine and self.confidence > 0.5

class BaseAuditor(ABC):
    """Abstract base for all auditor implementations"""
    
    def __init__(self, provider: str, model: str, trust_threshold: float = 0.5):
        self.provider = provider
        self.model = model
        self.trust_threshold = trust_threshold
        self._status = AuditorStatus.HEALTHY
        
    @abstractmethod
    async def audit_step(
        self, 
        step_number: int, 
        step_data: Dict[str, Any],
        timeout: float = 10.0
    ) -> AuditResult:
        """Audit a single reasoning step"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if auditor is responsive"""
        pass
    
    @property
    def status(self) -> AuditorStatus:
        return self._status
    
    def mark_byzantine(self):
        """Mark this auditor as Byzantine (malicious)"""
        self._status = AuditorStatus.BYZANTINE
    
    def mark_unresponsive(self):
        """Mark this auditor as unresponsive"""
        self._status = AuditorStatus.UNRESPONSIVE
    
    def mark_healthy(self):
        """Restore to healthy status"""
        self._status = AuditorStatus.HEALTHY