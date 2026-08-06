"""Tests for feature flags system."""

from __future__ import annotations

import pytest

from agentwatch.core.feature_flags import (
    FeatureFlag,
    FeatureFlagStore,
    FlagState,
)


def test_define_flag():
    store = FeatureFlagStore()
    flag = store.define("test_flag", enabled=True, description="test")
    assert flag.name == "test_flag"
    assert flag.is_on is True
    assert flag.description == "test"


def test_define_disabled_flag():
    store = FeatureFlagStore()
    flag = store.define("disabled", enabled=False)
    assert flag.is_on is False


def test_is_enabled():
    store = FeatureFlagStore()
    store.define("on", enabled=True)
    store.define("off", enabled=False)
    assert store.is_enabled("on") is True
    assert store.is_enabled("off") is False


def test_undefined_flag_returns_false():
    store = FeatureFlagStore()
    assert store.is_enabled("nonexistent") is False


def test_enable_disable():
    store = FeatureFlagStore()
    store.define("flag", enabled=False)
    assert store.is_enabled("flag") is False
    store.enable("flag")
    assert store.is_enabled("flag") is True
    store.disable("flag")
    assert store.is_enabled("flag") is False


def test_enable_nonexistent():
    store = FeatureFlagStore()
    assert store.enable("nope") is False


def test_disable_nonexistent():
    store = FeatureFlagStore()
    assert store.disable("nope") is False


def test_set_rollout():
    store = FeatureFlagStore()
    store.define("rollout")
    store.set_rollout("rollout", 50.0)
    flag = store.get("rollout")
    assert flag.state == FlagState.CONDITIONAL
    assert flag.rollout_percentage == 50.0


def test_set_rollout_100():
    store = FeatureFlagStore()
    store.define("rollout")
    store.set_rollout("rollout", 100.0)
    assert store.get("rollout").state == FlagState.ENABLED


def test_set_rollout_0():
    store = FeatureFlagStore()
    store.define("rollout", enabled=True)
    store.set_rollout("rollout", 0.0)
    assert store.get("rollout").state == FlagState.DISABLED


def test_environment_scoping():
    store = FeatureFlagStore(environment="production")
    store.define("prod_only", enabled=True, allowed_environments=["production"])
    store.define("dev_only", enabled=True, allowed_environments=["development"])
    assert store.is_enabled("prod_only") is True
    assert store.is_enabled("dev_only") is False


def test_rollout_percentage_user_based():
    store = FeatureFlagStore()
    store.define("rollout", rollout_percentage=50.0)
    results = [store.is_enabled("rollout", user_id=f"user-{i}") for i in range(1000)]
    enabled_count = sum(results)
    assert 300 < enabled_count < 700


def test_rollout_deterministic_per_user():
    store = FeatureFlagStore()
    store.define("rollout", rollout_percentage=50.0)
    r1 = store.is_enabled("rollout", user_id="user-abc")
    r2 = store.is_enabled("rollout", user_id="user-abc")
    r3 = store.is_enabled("rollout", user_id="user-abc")
    assert r1 == r2 == r3


def test_remove_flag():
    store = FeatureFlagStore()
    store.define("temp", enabled=True)
    assert store.remove("temp") is True
    assert store.is_enabled("temp") is False
    assert store.remove("temp") is False


def test_list_flags():
    store = FeatureFlagStore()
    store.define("a", enabled=True)
    store.define("b", enabled=False)
    flags = store.list_flags()
    assert len(flags) == 2


def test_list_enabled_disabled():
    store = FeatureFlagStore()
    store.define("a", enabled=True)
    store.define("b", enabled=False)
    store.define("c", enabled=True)
    assert sorted(store.list_enabled()) == ["a", "c"]
    assert store.list_disabled() == ["b"]


def test_on_change_callback():
    store = FeatureFlagStore()
    changes = []
    store.define("cb", enabled=False)
    store.on_change(lambda name, old, new: changes.append((name, old, new)), "cb")
    store.enable("cb")
    store.disable("cb")
    assert changes == [("cb", False, True), ("cb", True, False)]


def test_on_change_global_callback():
    store = FeatureFlagStore()
    changes = []
    store.define("x", enabled=False)
    store.on_change(lambda name, old, new: changes.append(name))
    store.enable("x")
    assert changes == ["x"]


def test_to_dict_roundtrip():
    store = FeatureFlagStore(environment="test")
    store.define("f1", enabled=True, description="flag one")
    store.define("f2", enabled=False)
    data = store.to_dict()
    restored = FeatureFlagStore.from_dict(data)
    assert restored.environment == "test"
    assert restored.is_enabled("f1") is True
    assert restored.is_enabled("f2") is False


def test_define_updates_existing():
    store = FeatureFlagStore()
    store.define("f", enabled=False)
    assert store.is_enabled("f") is False
    store.define("f", enabled=True)
    assert store.is_enabled("f") is True


def test_metadata_preserved():
    store = FeatureFlagStore()
    store.define("m", enabled=True, version="2.0", owner="team-a")
    flag = store.get("m")
    assert flag.metadata["version"] == "2.0"
    assert flag.metadata["owner"] == "team-a"


def test_flag_to_dict():
    flag = FeatureFlag(name="test", state=FlagState.ENABLED, description="desc")
    d = flag.to_dict()
    assert d["name"] == "test"
    assert d["state"] == "enabled"
    assert d["description"] == "desc"


def test_rollout_clamped():
    store = FeatureFlagStore()
    store.define("r")
    store.set_rollout("r", 150.0)
    assert store.get("r").rollout_percentage == 100.0
    store.set_rollout("r", -10.0)
    assert store.get("r").rollout_percentage == 0.0


def test_callback_error_does_not_crash():
    store = FeatureFlagStore()
    store.define("err", enabled=False)
    store.on_change(lambda n, o, e: 1 / 0, "err")
    store.enable("err")
    assert store.is_enabled("err") is True
