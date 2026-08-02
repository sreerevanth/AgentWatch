from __future__ import annotations

import pytest

from agentwatch.lattice.shadow_database import (
    InvariantViolation,
    QueryIntent,
    QueryOperation,
    ShadowDatabase,
    StateInvariant,
)


def _db(**sizes: int) -> ShadowDatabase:
    return ShadowDatabase(sizes)


def _delete(table: str, rows: int | None = None, **kw: object) -> QueryIntent:
    return QueryIntent(QueryOperation.DELETE, table, rows_affected=rows, **kw)  # type: ignore[arg-type]


def _invariants(result: object) -> set[StateInvariant]:
    violations: tuple[InvariantViolation, ...] = result.violations  # type: ignore[attr-defined]
    return {v.invariant for v in violations}


# --------------------------------------------------------------- blast radius


def test_supplied_row_count_is_used_as_given():
    db = _db(orders=1000)
    result = db.simulate(_delete("orders", rows=5))

    assert result.rows_affected == 5
    assert result.estimated is False
    assert result.allowed


def test_unqualified_delete_reaches_the_whole_table():
    """An unqualified DELETE is the mass-deletion case this class exists to catch."""
    db = _db(orders=1000)
    result = db.simulate(_delete("orders"))

    assert result.rows_affected == 1000
    assert result.estimated is True
    assert not result.allowed


def test_unknown_reach_is_treated_as_the_whole_table():
    """`rows_affected=None` must not be read as zero.

    A caller that could not work out a statement's reach has told us nothing about its
    size, and assuming the smallest possible value on no information is how an unbounded
    delete gets waved through. The upper bound is the safe reading.
    """
    db = _db(events=500)
    result = db.simulate(QueryIntent(QueryOperation.DELETE, "events", has_where_clause=True))

    assert result.rows_affected == 500
    assert StateInvariant.MAX_ROW_DELETE_PCT in _invariants(result)


def test_tables_affected_includes_cascades():
    db = ShadowDatabase({"orders": 100}, approved_cascade_tables={"order_items"})
    result = db.simulate(_delete("orders", rows=1, cascade_tables=frozenset({"order_items"})))

    assert result.tables_affected == frozenset({"orders", "order_items"})


# --------------------------------------------------- max_row_delete_pct


def test_delete_at_the_limit_is_allowed():
    """Exactly 10% passes; the invariant is 'more than', not 'at least'."""
    db = _db(orders=1000)
    assert db.simulate(_delete("orders", rows=100)).allowed


def test_delete_over_the_limit_is_blocked():
    db = _db(orders=1000)
    result = db.simulate(_delete("orders", rows=101))

    assert StateInvariant.MAX_ROW_DELETE_PCT in _invariants(result)
    assert "101 of 1000" in result.violations[0].detail


def test_truncate_is_judged_on_the_whole_table():
    db = _db(sessions=50)
    result = db.simulate(QueryIntent(QueryOperation.TRUNCATE, "sessions"))

    assert result.rows_affected == 50
    assert result.is_destructive
    assert StateInvariant.MAX_ROW_DELETE_PCT in _invariants(result)


def test_threshold_is_configurable():
    db = ShadowDatabase({"orders": 1000}, max_row_delete_pct=0.5)
    assert db.simulate(_delete("orders", rows=400)).allowed
    assert not db.simulate(_delete("orders", rows=600)).allowed


def test_unknown_table_size_yields_no_percentage_verdict():
    """With no row count there is no proportion to judge — silence, not approval."""
    db = _db()
    result = db.simulate(_delete("mystery", rows=999))

    assert StateInvariant.MAX_ROW_DELETE_PCT not in _invariants(result)


def test_updates_are_not_judged_on_delete_percentage():
    """The invariant is about rows removed. A wide UPDATE is a different concern."""
    db = _db(orders=1000)
    result = db.simulate(QueryIntent(QueryOperation.UPDATE, "orders", rows_affected=900))

    assert StateInvariant.MAX_ROW_DELETE_PCT not in _invariants(result)


# --------------------------------------------- protected_tables_immutable


def test_mutation_of_a_protected_table_is_blocked_regardless_of_size():
    """One row in `permissions` is not safer than a thousand in `logs`."""
    db = _db(users=1_000_000)
    result = db.simulate(_delete("users", rows=1))

    assert StateInvariant.PROTECTED_TABLES_IMMUTABLE in _invariants(result)


def test_reading_a_protected_table_is_allowed():
    db = _db(users=100)
    result = db.simulate(QueryIntent(QueryOperation.SELECT, "users"))

    assert result.allowed
    assert result.is_destructive is False


def test_protected_table_reached_by_cascade_is_blocked():
    """The direct target is innocuous; the cascade is not."""
    db = ShadowDatabase({"sessions": 100}, approved_cascade_tables={"users"})
    result = db.simulate(_delete("sessions", rows=1, cascade_tables=frozenset({"users"})))

    assert StateInvariant.PROTECTED_TABLES_IMMUTABLE in _invariants(result)


def test_table_names_are_matched_case_insensitively():
    """SQL identifiers are case-insensitive unless quoted.

    An invariant that `USERS` slips past while `users` does not is not an invariant.
    """
    db = _db()
    for name in ("USERS", "Users", '"users"', "`users`", "[users]", "  users  "):
        result = db.simulate(_delete(name, rows=1))
        assert StateInvariant.PROTECTED_TABLES_IMMUTABLE in _invariants(result), name


def test_protected_set_is_configurable():
    db = ShadowDatabase({"ledger": 100}, protected_tables={"ledger"})

    assert not db.simulate(_delete("ledger", rows=1)).allowed
    # `users` is no longer protected once the caller supplies its own set.
    assert db.simulate(_delete("users", rows=1)).allowed


# ------------------------------------------------------- no_cascade_deletes


def test_unapproved_cascade_is_blocked():
    db = _db(orders=1000)
    result = db.simulate(
        _delete("orders", rows=1, cascade_tables=frozenset({"order_items", "shipments"}))
    )

    assert StateInvariant.NO_CASCADE_DELETES in _invariants(result)
    assert "order_items, shipments" in result.violations[0].detail


def test_approved_cascade_is_allowed():
    db = ShadowDatabase({"orders": 1000}, approved_cascade_tables={"order_items"})
    result = db.simulate(_delete("orders", rows=1, cascade_tables=frozenset({"order_items"})))

    assert result.allowed


def test_a_query_can_break_several_invariants_at_once():
    """All violations are reported, not just the first — a caller fixing one at a time
    should not have to re-run to discover the next."""
    db = _db(users=1000)
    result = db.simulate(_delete("users", cascade_tables=frozenset({"sessions"})))

    assert _invariants(result) == {
        StateInvariant.MAX_ROW_DELETE_PCT,
        StateInvariant.PROTECTED_TABLES_IMMUTABLE,
        StateInvariant.NO_CASCADE_DELETES,
    }


# ----------------------------------------------------------------- apply


def test_apply_folds_an_allowed_delete_into_the_model():
    db = _db(orders=1000)
    db.apply(_delete("orders", rows=50))

    assert db.row_count("orders") == 950


def test_apply_leaves_the_model_alone_when_the_query_is_refused():
    """A blocked statement never ran, so its rows are still there."""
    db = _db(orders=1000)
    result = db.apply(_delete("orders"))

    assert not result.allowed
    assert db.row_count("orders") == 1000


def test_apply_handles_insert_and_truncate():
    db = _db(orders=100)
    db.apply(QueryIntent(QueryOperation.INSERT, "orders", rows_affected=10))
    assert db.row_count("orders") == 110

    db.apply(QueryIntent(QueryOperation.TRUNCATE, "orders", rows_affected=0))
    assert db.row_count("orders") == 0


def test_delete_cannot_drive_a_row_count_negative():
    """The clamp in apply() guards against the model drifting below zero.

    Reaching it needs a delete that is allowed but overshoots — an unprotected table
    whose recorded size is stale, so the statement legitimately removes more rows than
    the model thinks exist.
    """
    db = ShadowDatabase({"orders": 10}, max_row_delete_pct=1.0)
    db.apply(_delete("orders", rows=10))
    assert db.row_count("orders") == 0

    # The table is now empty as far as the model knows, so the percentage check has no
    # denominator and a further delete is allowed through.
    db.apply(_delete("orders", rows=5))
    assert db.row_count("orders") == 0


# ----------------------------------------------------------- construction


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_invalid_threshold_is_rejected_at_construction(bad: float):
    with pytest.raises(ValueError, match="max_row_delete_pct"):
        ShadowDatabase({}, max_row_delete_pct=bad)


def test_simulate_does_not_mutate_the_model():
    db = _db(orders=1000)
    db.simulate(_delete("orders", rows=100))

    assert db.row_count("orders") == 1000
