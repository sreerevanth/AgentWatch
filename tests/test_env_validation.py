"""Tests for environment variable validation at startup."""

from __future__ import annotations

import pytest

from agentwatch.core.env_validation import (
    EnvVarResult,
    EnvVarSeverity,
    EnvVarSpec,
    EnvVarType,
    ValidationResult,
    EnvValidator,
    _parse_bool,
    _validate_float,
    _validate_int,
    _validate_url,
    get_agentwatch_specs,
    validate_agentwatch_env,
)


def test_parse_bool_true():
    assert _parse_bool("true") is True
    assert _parse_bool("True") is True
    assert _parse_bool("1") is True
    assert _parse_bool("yes") is True
    assert _parse_bool("on") is True


def test_parse_bool_false():
    assert _parse_bool("false") is False
    assert _parse_bool("0") is False
    assert _parse_bool("no") is False
    assert _parse_bool("") is False


def test_validate_url_valid():
    assert _validate_url("https://example.com") is True
    assert _validate_url("http://localhost:8000") is True
    assert _validate_url("postgres://user:pass@host/db") is True


def test_validate_url_invalid():
    assert _validate_url("not-a-url") is False
    assert _validate_url("") is False
    assert _validate_url("just-text") is False


def test_validate_int_valid():
    assert _validate_int("42") is True
    assert _validate_int("0") is True
    assert _validate_int("-5") is True


def test_validate_int_with_bounds():
    assert _validate_int("50", min_val=1, max_val=100) is True
    assert _validate_int("0", min_val=1, max_val=100) is False
    assert _validate_int("200", min_val=1, max_val=100) is False


def test_validate_int_invalid():
    assert _validate_int("abc") is False
    assert _validate_int("3.14") is False


def test_validate_float_valid():
    assert _validate_float("3.14") is True
    assert _validate_float("0.5", min_val=0.0, max_val=1.0) is True
    assert _validate_float("1.5", min_val=0.0, max_val=1.0) is False


# --- EnvValidator tests ---


def test_required_var_present():
    v = EnvValidator(env_overrides={"MY_VAR": "hello"})
    v.add_spec(EnvVarSpec(name="MY_VAR", severity=EnvVarSeverity.REQUIRED))
    result = v.validate()
    assert result.valid is True
    assert result.results[0].present is True
    assert result.results[0].value == "hello"


def test_required_var_missing():
    v = EnvValidator(env_overrides={})
    v.add_spec(EnvVarSpec(name="MY_VAR", severity=EnvVarSeverity.REQUIRED))
    result = v.validate()
    assert result.valid is False
    assert result.results[0].present is False
    assert len(result.errors) == 1


def test_optional_var_missing():
    v = EnvValidator(env_overrides={})
    v.add_spec(EnvVarSpec(name="MY_VAR", severity=EnvVarSeverity.OPTIONAL, default="fallback"))
    result = v.validate()
    assert result.valid is True
    assert result.results[0].present is False
    assert result.results[0].value == "fallback"


def test_int_validation():
    v = EnvValidator(env_overrides={"PORT": "8000"})
    v.add_spec(EnvVarSpec(name="PORT", var_type=EnvVarType.INT, min_value=1, max_value=65535))
    result = v.validate()
    assert result.valid is True


def test_int_validation_failure():
    v = EnvValidator(env_overrides={"PORT": "abc"})
    v.add_spec(EnvVarSpec(name="PORT", var_type=EnvVarType.INT))
    result = v.validate()
    assert result.valid is False
    assert "invalid" in result.errors[0].lower()


def test_url_validation():
    v = EnvValidator(env_overrides={"DB_URL": "postgres://localhost/db"})
    v.add_spec(EnvVarSpec(name="DB_URL", var_type=EnvVarType.URL))
    result = v.validate()
    assert result.valid is True


def test_url_validation_failure():
    v = EnvValidator(env_overrides={"DB_URL": "not-a-url"})
    v.add_spec(EnvVarSpec(name="DB_URL", var_type=EnvVarType.URL))
    result = v.validate()
    assert result.valid is False


def test_allowed_values():
    v = EnvValidator(env_overrides={"ENV": "production"})
    v.add_spec(EnvVarSpec(name="ENV", allowed_values=["development", "production", "test"]))
    result = v.validate()
    assert result.valid is True


def test_allowed_values_failure():
    v = EnvValidator(env_overrides={"ENV": "staging"})
    v.add_spec(EnvVarSpec(name="ENV", allowed_values=["development", "production", "test"]))
    result = v.validate()
    assert result.valid is False
    assert "must be one of" in result.errors[0]


def test_pattern_validation():
    v = EnvValidator(env_overrides={"KEY": "abc-123-def"})
    v.add_spec(EnvVarSpec(name="KEY", pattern=r"^[a-z]+-[0-9]+-[a-z]+$"))
    result = v.validate()
    assert result.valid is True


def test_pattern_validation_failure():
    v = EnvValidator(env_overrides={"KEY": "INVALID"})
    v.add_spec(EnvVarSpec(name="KEY", pattern=r"^[a-z]+-[0-9]+-[a-z]+$"))
    result = v.validate()
    assert result.valid is False
    assert "does not match pattern" in result.errors[0]


def test_custom_validator():
    v = EnvValidator(env_overrides={"TOKEN": "valid-token"})
    v.add_spec(EnvVarSpec(
        name="TOKEN",
        validator=lambda val: val.startswith("valid-"),
    ))
    result = v.validate()
    assert result.valid is True


def test_custom_validator_failure():
    v = EnvValidator(env_overrides={"TOKEN": "invalid-token"})
    v.add_spec(EnvVarSpec(
        name="TOKEN",
        validator=lambda val: val.startswith("valid-"),
    ))
    result = v.validate()
    assert result.valid is False
    assert "failed custom validation" in result.errors[0]


def test_multiple_specs():
    v = EnvValidator(env_overrides={"A": "1", "B": "hello"})
    v.add_spec(EnvVarSpec(name="A", var_type=EnvVarType.INT))
    v.add_spec(EnvVarSpec(name="B", severity=EnvVarSeverity.REQUIRED))
    result = v.validate()
    assert result.valid is True
    assert len(result.results) == 2


def test_add_specs_batch():
    v = EnvValidator(env_overrides={"A": "1"})
    v.add_specs([
        EnvVarSpec(name="A"),
        EnvVarSpec(name="B", severity=EnvVarSeverity.OPTIONAL),
    ])
    result = v.validate()
    assert len(result.results) == 2


def test_validation_result_to_dict():
    v = EnvValidator(env_overrides={"X": "val"})
    v.add_spec(EnvVarSpec(name="X"))
    result = v.validate()
    d = result.to_dict()
    assert "valid" in d
    assert "results" in d
    assert "errors" in d
    assert "warnings" in d
    assert d["results"][0]["value"] == "***"


def test_bool_validation():
    v = EnvValidator(env_overrides={"FLAG": "true"})
    v.add_spec(EnvVarSpec(name="FLAG", var_type=EnvVarType.BOOL))
    result = v.validate()
    assert result.valid is True


def test_optional_warning_not_error():
    v = EnvValidator(env_overrides={})
    v.add_spec(EnvVarSpec(name="MISSING", severity=EnvVarSeverity.OPTIONAL))
    result = v.validate()
    assert result.valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


# --- get_agentwatch_specs ---


def test_get_agentwatch_specs_returns_list():
    specs = get_agentwatch_specs()
    assert isinstance(specs, list)
    assert len(specs) > 0
    names = [s.name for s in specs]
    assert "AGENTWATCH_ENV" in names
    assert "AGENTWATCH_API_KEY" in names
    assert "DATABASE_URL" in names
    assert "REDIS_URL" in names


# --- validate_agentwatch_env ---


def test_validate_agentwatch_env_valid():
    overrides = {
        "AGENTWATCH_ENV": "development",
        "AGENTWATCH_API_KEY": "a" * 20,
        "DATABASE_URL": "postgres://localhost/db",
        "REDIS_URL": "redis://localhost:6379",
    }
    result = validate_agentwatch_env(env_overrides=overrides)
    assert result.valid is True


def test_validate_agentwatch_env_missing_required():
    result = validate_agentwatch_env(env_overrides={})
    assert result.valid is False
    assert len(result.errors) > 0
