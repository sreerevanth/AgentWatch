import datetime

# Mock EmbeddingProvider._load to prevent downloading SentenceTransformer weights in tests
import agentwatch.memory.engine

# Mock sentence-transformers to bypass heavy model loading and downloads in tests
import agentwatch.scoring.drift

if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc  # noqa: UP017

agentwatch.scoring.drift._st_model = agentwatch.scoring.drift._ST_UNAVAILABLE


async def mock_load(self):
    self._disabled = True


agentwatch.memory.engine.EmbeddingProvider._load = mock_load
