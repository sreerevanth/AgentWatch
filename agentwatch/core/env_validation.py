"""Environment variable validation at startup.

Validates required environment variables, checks types, validates URLs,
and provides clear error messages for misconfigured deployments.
Prevents the production fail-closed guard from being triggered by
missing configuration.
"""

from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class EnvVarType(Enum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    URL = "url"
    FILE_PATH = "file_path"
    DIRECTORY = "directory"


class EnvVarSeverity(Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"


@dataclass
class EnvVarSpec:
    name: str
    var_type: EnvVarType = EnvVarType.STRING
    severity: EnvVarSeverity = EnvVarSeverity.REQUIRED
    default: Any = None
    description: str = ""
    validator: Callable[[str], bool] | None = None
    allowed_values: list[str] | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    pattern: str | None = None


@dataclass
class EnvVarResult:
    name: str
    present: bool
    valid: bool
    value: str | None = None
    error: str = ""
    severity: EnvVarSeverity = EnvVarSeverity.REQUIRED


@dataclass
class ValidationResult:
    valid: bool
    results: list[EnvVarResult]
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "results": [
                {
                    "name": r.name,
                    "present": r.present,
                    "valid": r.valid,
                    "value": "***" if r.present and r.valid else None,
                    "error": r.error,
                    "severity": r.severity.value,
                }
                for r in self.results
            ],
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _parse_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes", "on")


def _validate_url(value: str) -> bool:
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def _validate_int(value: str, min_val: int | None = None, max_val: int | None = None) -> bool:
    try:
        i = int(value)
        if min_val is not None and i < min_val:
            return False
        if max_val is not None and i > max_val:
            return False
        return True
    except ValueError:
        return False


def _validate_float(value: str, min_val: float | None = None, max_val: float | None = None) -> bool:
    try:
        f = float(value)
        if min_val is not None and f < min_val:
            return False
        if max_val is not None and f > max_val:
            return False
        return True
    except ValueError:
        return False


def _validate_file_path(value: str) -> bool:
    return os.path.isfile(value)


def _validate_directory(value: str) -> bool:
    return os.path.isdir(value)


class EnvValidator:
    """Validates environment variables against a set of specifications.

    Usage:
        validator = EnvValidator()
        validator.add_spec(EnvVarSpec(
            name="AGENTWATCH_API_KEY",
            var_type=EnvVarType.STRING,
            severity=EnvVarSeverity.REQUIRED,
            description="API key for authentication",
        ))
        validator.add_spec(EnvVarSpec(
            name="AGENTWATCH_PORT",
            var_type=EnvVarType.INT,
            severity=EnvVarSeverity.OPTIONAL,
            default="8000",
            min_value=1,
            max_value=65535,
        ))
        result = validator.validate()
        if not result.valid:
            raise SystemExit(1)
    """

    def __init__(self, env_overrides: dict[str, str] | None = None) -> None:
        self._specs: list[EnvVarSpec] = []
        self._env = env_overrides or dict(os.environ)

    def add_spec(self, spec: EnvVarSpec) -> None:
        self._specs.append(spec)

    def add_specs(self, specs: list[EnvVarSpec]) -> None:
        self._specs.extend(specs)

    def validate(self) -> ValidationResult:
        results: list[EnvVarResult] = []
        errors: list[str] = []
        warnings: list[str] = []

        for spec in self._specs:
            result = self._validate_one(spec)
            results.append(result)
            if not result.valid:
                if result.severity == EnvVarSeverity.REQUIRED:
                    errors.append(f"{result.error}")
                else:
                    warnings.append(f"{result.error}")

        return ValidationResult(
            valid=len(errors) == 0,
            results=results,
            errors=errors,
            warnings=warnings,
        )

    def _validate_one(self, spec: EnvVarSpec) -> EnvVarResult:
        value = self._env.get(spec.name)

        if value is None:
            if spec.severity == EnvVarSeverity.REQUIRED:
                return EnvVarResult(
                    name=spec.name,
                    present=False,
                    valid=False,
                    error=f"Required environment variable '{spec.name}' is not set ({spec.description})",
                    severity=spec.severity,
                )
            return EnvVarResult(
                name=spec.name,
                present=False,
                valid=True,
                value=spec.default,
                severity=spec.severity,
            )

        if spec.pattern and not re.match(spec.pattern, value):
            return EnvVarResult(
                name=spec.name,
                present=True,
                valid=False,
                value=value,
                error=f"Environment variable '{spec.name}' does not match pattern '{spec.pattern}'",
                severity=spec.severity,
            )

        if spec.allowed_values and value not in spec.allowed_values:
            return EnvVarResult(
                name=spec.name,
                present=True,
                valid=False,
                value=value,
                error=f"Environment variable '{spec.name}' must be one of {spec.allowed_values}, got '{value}'",
                severity=spec.severity,
            )

        type_valid = self._validate_type(spec, value)
        if not type_valid:
            return EnvVarResult(
                name=spec.name,
                present=True,
                valid=False,
                value=value,
                error=f"Environment variable '{spec.name}' has invalid {spec.var_type.value} value: '{value}'",
                severity=spec.severity,
            )

        if spec.validator and not spec.validator(value):
            return EnvVarResult(
                name=spec.name,
                present=True,
                valid=False,
                value=value,
                error=f"Environment variable '{spec.name}' failed custom validation",
                severity=spec.severity,
            )

        return EnvVarResult(
            name=spec.name,
            present=True,
            valid=True,
            value=value,
            severity=spec.severity,
        )

    def _validate_type(self, spec: EnvVarSpec, value: str) -> bool:
        if spec.var_type == EnvVarType.INT:
            return _validate_int(value, spec.min_value, spec.max_value)
        elif spec.var_type == EnvVarType.FLOAT:
            return _validate_float(value, spec.min_value, spec.max_value)
        elif spec.var_type == EnvVarType.BOOL:
            return value.lower() in ("true", "false", "1", "0", "yes", "no", "on", "off")
        elif spec.var_type == EnvVarType.URL:
            return _validate_url(value)
        elif spec.var_type == EnvVarType.FILE_PATH:
            return _validate_file_path(value)
        elif spec.var_type == EnvVarType.DIRECTORY:
            return _validate_directory(value)
        return True


def get_agentwatch_specs() -> list[EnvVarSpec]:
    """Return the standard AgentWatch environment variable specifications."""
    return [
        EnvVarSpec(
            name="AGENTWATCH_ENV",
            var_type=EnvVarType.STRING,
            severity=EnvVarSeverity.REQUIRED,
            allowed_values=["development", "staging", "production", "test"],
            description="Deployment environment",
        ),
        EnvVarSpec(
            name="AGENTWATCH_API_KEY",
            var_type=EnvVarType.STRING,
            severity=EnvVarSeverity.REQUIRED,
            min_value=16,
            description="API key for authentication (required in production)",
        ),
        EnvVarSpec(
            name="AGENTWATCH_PORT",
            var_type=EnvVarType.INT,
            severity=EnvVarSeverity.OPTIONAL,
            default="8000",
            min_value=1,
            max_value=65535,
            description="API server port",
        ),
        EnvVarSpec(
            name="DATABASE_URL",
            var_type=EnvVarType.URL,
            severity=EnvVarSeverity.REQUIRED,
            description="PostgreSQL connection URL",
        ),
        EnvVarSpec(
            name="REDIS_URL",
            var_type=EnvVarType.URL,
            severity=EnvVarSeverity.REQUIRED,
            description="Redis connection URL",
        ),
        EnvVarSpec(
            name="AGENTWATCH_CORS_ORIGINS",
            var_type=EnvVarType.STRING,
            severity=EnvVarSeverity.OPTIONAL,
            default="http://localhost:3000",
            description="Comma-separated CORS origins",
        ),
        EnvVarSpec(
            name="AGENTWATCH_LOG_LEVEL",
            var_type=EnvVarType.STRING,
            severity=EnvVarSeverity.OPTIONAL,
            default="INFO",
            allowed_values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            description="Logging level",
        ),
    ]


def validate_agentwatch_env(env_overrides: dict[str, str] | None = None) -> ValidationResult:
    """Validate the current AgentWatch environment variables.

    Convenience function that validates all standard AgentWatch env vars.
    """
    validator = EnvValidator(env_overrides=env_overrides)
    validator.add_specs(get_agentwatch_specs())
    result = validator.validate()
    if not result.valid:
        for err in result.errors:
            logger.error("Environment validation error: %s", err)
    for warn in result.warnings:
        logger.warning("Environment validation warning: %s", warn)
    return result
