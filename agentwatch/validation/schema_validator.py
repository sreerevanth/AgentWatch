"""Task Parameter Schema Validation"""
from __future__ import annotations
import jsonschema

class SchemaValidator:
    """Validates task parameters against agent schemas."""
    
    def __init__(self) -> None:
        self.schemas = {}

    def validate_task_parameters(self, agent_type: str, parameters: dict):
        """Validate task parameters against schema."""
        schema = self.schemas.get(agent_type)
        if not schema:
            return False, f"No schema found for {agent_type}"
        try:
            jsonschema.validate(instance=parameters, schema=schema)
            return True, None
        except jsonschema.ValidationError as e:
            return False, f"Validation failed: {e.message}"
