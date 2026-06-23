import datetime
import sys
from unittest.mock import MagicMock

if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc  # noqa: UP017

# Mock sentence-transformers to bypass heavy model loading and downloads in tests
try:
    import numpy as np
except ImportError:
    np = None

class MockSentenceTransformer:
    def __init__(self, *args, **kwargs):
        pass
    def encode(self, texts, *args, **kwargs):
        if np is not None:
            return np.array([[0.1] * 384 for _ in texts])
        return [[0.1] * 384 for _ in texts]

mock_st = MagicMock()
mock_st.SentenceTransformer = MockSentenceTransformer
sys.modules["sentence_transformers"] = mock_st

import agentwatch.scoring.drift

agentwatch.scoring.drift._st_model = agentwatch.scoring.drift._ST_UNAVAILABLE

