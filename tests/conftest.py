import datetime

if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.timezone.utc  # noqa: UP017

# Mock sentence-transformers to bypass heavy model loading and downloads in tests
import agentwatch.scoring.drift

agentwatch.scoring.drift._st_model = agentwatch.scoring.drift._ST_UNAVAILABLE
