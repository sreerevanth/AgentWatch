from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from agentwatch.core.models import Base


class SemanticCacheEntry(Base):
    __tablename__ = "semantic_cache"

    id = Column(Integer, primary_key=True, index=True)
    prompt_hash = Column(String, index=True, nullable=False)
    prompt_vector = Column(Vector(384))  # all-MiniLM-L6-v2 produces 384-dimensional vectors
    response_text = Column(String, nullable=False)
    framework = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
