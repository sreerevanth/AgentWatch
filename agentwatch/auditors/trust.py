"""Trust scoring system for auditors"""
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import redis
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class TrustScore:
    """Trust score for an auditor"""
    provider: str
    model: str
    score: float = 0.5  # 0.0 - 1.0
    total_audits: int = 0
    correct_audits: int = 0
    last_update: datetime = field(default_factory=datetime.now)
    decay_rate: float = 0.01  # Decay per day
    
    @property
    def accuracy(self) -> float:
        if self.total_audits == 0:
            return 0.5
        return self.correct_audits / self.total_audits
    
    def update(self, was_correct: bool):
        """Update trust score based on audit outcome"""
        self.total_audits += 1
        if was_correct:
            self.correct_audits += 1
        self.last_update = datetime.now()
        
        # Recalculate score (weighted recent accuracy)
        self.score = self._calculate_score()
    
    def _calculate_score(self) -> float:
        """Calculate trust score with time decay"""
        if self.total_audits == 0:
            return 0.5
        
        # Base score: accuracy
        base = self.accuracy
        
        # Confidence factor (more audits = more confidence)
        confidence = min(1.0, self.total_audits / 100)
        
        # Time decay
        age_days = (datetime.now() - self.last_update).days
        decay = 1.0 - (age_days * self.decay_rate)
        decay = max(0.5, decay)
        
        score = base * confidence * decay
        return max(0.0, min(1.0, score))

class TrustScorer:
    """Manages trust scores for all auditors"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client
        self.scores: Dict[str, TrustScore] = {}
        self._load_scores()
    
    def _get_key(self, provider: str, model: str) -> str:
        return f"trust:{provider}:{model}"
    
    def _load_scores(self):
        """Load scores from Redis if available"""
        if self.redis is None:
            return
        
        try:
            keys = self.redis.keys("trust:*")
            for key in keys:
                data = self.redis.get(key)
                if data:
                    score_data = json.loads(data)
                    self.scores[f"{score_data['provider']}:{score_data['model']}"] = TrustScore(
                        provider=score_data['provider'],
                        model=score_data['model'],
                        score=score_data['score'],
                        total_audits=score_data['total_audits'],
                        correct_audits=score_data['correct_audits'],
                        last_update=datetime.fromisoformat(score_data['last_update'])
                    )
        except Exception as e:
            logger.warning(f"Failed to load trust scores from Redis: {e}")
    
    def _save_score(self, trust_score: TrustScore):
        """Save score to Redis"""
        if self.redis is None:
            return
        
        try:
            key = self._get_key(trust_score.provider, trust_score.model)
            data = {
                'provider': trust_score.provider,
                'model': trust_score.model,
                'score': trust_score.score,
                'total_audits': trust_score.total_audits,
                'correct_audits': trust_score.correct_audits,
                'last_update': trust_score.last_update.isoformat()
            }
            self.redis.setex(key, timedelta(days=30), json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to save trust score: {e}")
    
    def get_trust_score(self, provider: str, model: str) -> float:
        """Get trust score for an auditor"""
        key = f"{provider}:{model}"
        if key in self.scores:
            return self.scores[key].score
        return 0.5  # Default trust
    
    def get_or_create(self, provider: str, model: str) -> TrustScore:
        """Get or create a trust score"""
        key = f"{provider}:{model}"
        if key not in self.scores:
            self.scores[key] = TrustScore(provider=provider, model=model)
        return self.scores[key]
    
    def update_score(self, provider: str, model: str, was_correct: bool):
        """Update trust score after an audit"""
        trust_score = self.get_or_create(provider, model)
        trust_score.update(was_correct)
        self._save_score(trust_score)
    
    def get_all_scores(self) -> Dict[str, TrustScore]:
        """Get all trust scores"""
        return self.scores
    
    def get_ranking(self) -> list[tuple[str, float]]:
        """Get auditor ranking by trust score"""
        ranking = []
        for key, score in self.scores.items():
            ranking.append((key, score.score))
        return sorted(ranking, key=lambda x: x[1], reverse=True)