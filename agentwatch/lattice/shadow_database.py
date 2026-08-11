"""Shadow database: answer "what would this query do?" without running it.

An agent issuing `DELETE FROM users` is not distinguishable, by syntax alone, from one
issuing `DELETE FROM users WHERE id = 42`. Both are valid SQL and both are a delete. The
difference is blast radius, and blast radius is a property of the data rather than the
statement — so it can only be answered by a model that knows how large the tables are.

This module holds that model. It takes a description of what a query intends to do and
returns what would happen, leaving the real database untouched.

Queries are accepted **pre-parsed**. Parsing SQL properly needs a real parser — dialect
differences, quoted identifiers, subqueries and CTEs all matter, and a regex that gets 90%
of them right is worse than none, because the 10% it misreads are exactly the queries an
attacker would craft. The issue permits either approach; taking pre-parsed intentions keeps
this module free of a parsing dependency and free of the false confidence that comes with a
half-correct one. A caller with a parser can feed it; a caller with an ORM already has the
structured form.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum

__all__ = [
    "DEFAULT_MAX_ROW_DELETE_PCT",
    "DEFAULT_PROTECTED_TABLES",
    "InvariantViolation",
    "QueryMutationResult",
    "QueryIntent",
    "QueryOperation",
    "ShadowDatabase",
    "StateInvariant",
]


class QueryOperation(str, Enum):
    """What an agent is asking the database to do."""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    DROP = "drop"
    TRUNCATE = "truncate"


class StateInvariant(str, Enum):
    """A property of the database that a mutation must not break."""

    MAX_ROW_DELETE_PCT = "max_row_delete_pct"
    PROTECTED_TABLES_IMMUTABLE = "protected_tables_immutable"
    NO_CASCADE_DELETES = "no_cascade_deletes"


#: Fraction of a table that may be removed in a single statement before
#: MAX_ROW_DELETE_PCT trips. The issue specifies 10%.
DEFAULT_MAX_ROW_DELETE_PCT = 0.10

#: Tables that hold credentials, permissions or audit history. A mutation to any of
#: these is refused regardless of size, because the damage is not proportional to the
#: row count — one altered row in `permissions` is worth more than a thousand in `logs`.
DEFAULT_PROTECTED_TABLES = frozenset(
    {
        "users",
        "accounts",
        "credentials",
        "permissions",
        "roles",
        "audit_log",
        "audit_logs",
        "billing",
        "payments",
    }
)


@dataclass(frozen=True)
class QueryIntent:
    """A pre-parsed description of what a query would do.

    Attributes:
        operation: The kind of statement.
        table: The table the statement names directly.
        rows_affected: Rows the caller expects to touch. `None` means "unknown", which is
            treated as the whole table for DELETE and UPDATE — an unqualified statement and
            one whose reach cannot be established are the same risk, and guessing low on an
            unknown is how a mass deletion gets through.
        cascade_tables: Tables reached indirectly, via foreign keys with ON DELETE CASCADE
            or via triggers. Named separately from `table` because a caller has to have
            thought about them for them to be here.
        has_where_clause: The statement is qualified. Recorded for reporting; the row count
            is what the invariants actually judge.
    """

    operation: QueryOperation
    table: str
    rows_affected: int | None = None
    cascade_tables: frozenset[str] = frozenset()
    has_where_clause: bool = False


@dataclass(frozen=True)
class InvariantViolation:
    """One reason a query was refused."""

    invariant: StateInvariant
    detail: str


@dataclass(frozen=True)
class QueryMutationResult:
    """What :meth:`ShadowDatabase.simulate` worked out about a query.

    Named distinctly from :class:`~agentwatch.lattice.shadow_filesystem.MutationResult`
    rather than shadowing it: both are lattice results, but they carry different fields,
    and a single package-level name that silently means one or the other depending on
    import order would be worse than two clear ones.

    Attributes:
        rows_affected: Rows the statement would touch. For DROP and TRUNCATE this is the
            whole table; for an unqualified DELETE or UPDATE likewise.
        tables_affected: Every table touched, directly or by cascade.
        is_destructive: The statement removes rows or structure.
        violations: Invariants the statement would break. Empty means it may proceed.
        estimated: `rows_affected` was derived from table size rather than supplied,
            so it is an upper bound rather than a count.
    """

    rows_affected: int
    tables_affected: frozenset[str]
    is_destructive: bool
    violations: tuple[InvariantViolation, ...] = ()
    estimated: bool = False

    @property
    def allowed(self) -> bool:
        """No invariant was broken."""
        return not self.violations


_DESTRUCTIVE = frozenset({QueryOperation.DELETE, QueryOperation.DROP, QueryOperation.TRUNCATE})

#: Operations with no WHERE clause in SQL: they always take the whole table, so a
#: caller-supplied row count is not believed for them.
_ALWAYS_WHOLE_TABLE = frozenset({QueryOperation.DROP, QueryOperation.TRUNCATE})

#: Operations that remove or overwrite existing rows wholesale when unqualified.
_WHOLE_TABLE_WHEN_UNQUALIFIED = frozenset(
    {QueryOperation.DELETE, QueryOperation.UPDATE, QueryOperation.DROP, QueryOperation.TRUNCATE}
)


@dataclass
class ShadowDatabase:
    """A database model that predicts a query's blast radius without executing it.

    Args:
        table_sizes: Row counts per table. Supplied rather than queried, because querying
            would mean touching the database this class exists to avoid touching.
        protected_tables: Tables no mutation may reach. Defaults to
            :data:`DEFAULT_PROTECTED_TABLES`.
        max_row_delete_pct: Fraction of a table a single statement may remove before
            :attr:`StateInvariant.MAX_ROW_DELETE_PCT` trips.
        approved_cascade_tables: Tables a cascade may legitimately reach. A cascade into
            anything outside this set trips :attr:`StateInvariant.NO_CASCADE_DELETES`.

    Example:
        >>> db = ShadowDatabase({"orders": 1000})
        >>> db.simulate(QueryIntent(QueryOperation.DELETE, "orders", rows_affected=5)).allowed
        True
        >>> db.simulate(QueryIntent(QueryOperation.DELETE, "orders")).allowed
        False
    """

    table_sizes: dict[str, int] = field(default_factory=dict)
    protected_tables: frozenset[str] = DEFAULT_PROTECTED_TABLES
    max_row_delete_pct: float = DEFAULT_MAX_ROW_DELETE_PCT
    approved_cascade_tables: frozenset[str] = frozenset()

    def __init__(
        self,
        table_sizes: Mapping[str, int] | None = None,
        *,
        protected_tables: Iterable[str] | None = None,
        max_row_delete_pct: float = DEFAULT_MAX_ROW_DELETE_PCT,
        approved_cascade_tables: Iterable[str] | None = None,
    ) -> None:
        if not 0.0 < max_row_delete_pct <= 1.0:
            raise ValueError(f"max_row_delete_pct must be in (0, 1], got {max_row_delete_pct!r}")

        # Table names are compared case-insensitively throughout. SQL identifiers are
        # case-insensitive unless quoted, and an invariant that can be sidestepped by
        # writing USERS instead of users is not an invariant.
        self.table_sizes = {self._key(name): size for name, size in (table_sizes or {}).items()}
        self.protected_tables = frozenset(
            self._key(t)
            for t in (DEFAULT_PROTECTED_TABLES if protected_tables is None else protected_tables)
        )
        self.max_row_delete_pct = max_row_delete_pct
        self.approved_cascade_tables = frozenset(
            self._key(t) for t in (approved_cascade_tables or ())
        )

    # ------------------------------------------------------------------ public API

    def simulate(self, intent: QueryIntent) -> QueryMutationResult:
        """Work out what `intent` would do. Touches nothing."""
        table = self._key(intent.table)
        cascades = {self._key(t) for t in intent.cascade_tables}
        tables_affected = frozenset({table} | cascades)

        rows, estimated = self._resolve_rows(intent, table)
        destructive = intent.operation in _DESTRUCTIVE

        violations: list[InvariantViolation] = []
        violations.extend(self._check_protected(intent, table, cascades))
        violations.extend(self._check_delete_pct(intent, table, rows))
        violations.extend(self._check_cascades(intent, cascades))

        return QueryMutationResult(
            rows_affected=rows,
            tables_affected=tables_affected,
            is_destructive=destructive,
            violations=tuple(violations),
            estimated=estimated,
        )

    def apply(self, intent: QueryIntent) -> QueryMutationResult:
        """Simulate `intent` and fold the outcome into the model's row counts.

        Refused queries leave the model unchanged: a statement that would have been blocked
        never ran, so pretending its rows are gone would make every later simulation wrong.
        """
        result = self.simulate(intent)
        if not result.allowed:
            return result

        table = self._key(intent.table)
        if intent.operation in (QueryOperation.DROP, QueryOperation.TRUNCATE):
            self.table_sizes[table] = 0
        elif intent.operation is QueryOperation.DELETE:
            current = self.table_sizes.get(table, 0)
            self.table_sizes[table] = max(0, current - result.rows_affected)
        elif intent.operation is QueryOperation.INSERT:
            self.table_sizes[table] = self.table_sizes.get(table, 0) + result.rows_affected

        return result

    def row_count(self, table: str) -> int:
        """Rows the model believes `table` holds. Unknown tables count as zero."""
        return self.table_sizes.get(self._key(table), 0)

    # ------------------------------------------------------------------ internals

    @staticmethod
    def _key(table: str) -> str:
        """Normalise a table name for comparison.

        Strips the quoting styles SQL dialects use, so `"users"`, `` `users` ``, `[users]`
        and `users` are one table rather than four ways past a protected-table check.
        """
        return table.strip().strip('"`[]').lower()

    def _resolve_rows(self, intent: QueryIntent, table: str) -> tuple[int, bool]:
        """Return (rows_affected, was_estimated).

        DROP and TRUNCATE cannot be scoped by a WHERE clause — by SQL semantics they take
        the entire table — so a caller-supplied count is ignored for them. Trusting it
        would let `TRUNCATE users` arrive with `rows_affected=0` and slip past
        MAX_ROW_DELETE_PCT entirely, which is the opposite of what that invariant is for.

        An unqualified DELETE or UPDATE reaches the whole table too. So does one whose
        reach the caller could not determine — `rows_affected=None` is treated as the full
        table rather than zero, because assuming the smaller number on an unknown is
        precisely how an unbounded statement slips through.
        """
        table_size = self.table_sizes.get(table, 0)

        if intent.operation in _ALWAYS_WHOLE_TABLE:
            return table_size, True

        if intent.rows_affected is not None:
            return max(0, intent.rows_affected), False

        if intent.operation in _WHOLE_TABLE_WHEN_UNQUALIFIED:
            return table_size, True

        # SELECT and INSERT with no count supplied touch nothing we can bound.
        return 0, True

    def _check_protected(
        self, intent: QueryIntent, table: str, cascades: set[str]
    ) -> list[InvariantViolation]:
        if intent.operation is QueryOperation.SELECT:
            return []

        hit = sorted(({table} | cascades) & self.protected_tables)
        if not hit:
            return []

        return [
            InvariantViolation(
                invariant=StateInvariant.PROTECTED_TABLES_IMMUTABLE,
                detail=(
                    f"{intent.operation.value} would mutate protected "
                    f"table{'s' if len(hit) > 1 else ''}: {', '.join(hit)}"
                ),
            )
        ]

    def _check_delete_pct(
        self, intent: QueryIntent, table: str, rows: int
    ) -> list[InvariantViolation]:
        if intent.operation not in _DESTRUCTIVE:
            return []

        table_size = self.table_sizes.get(table, 0)
        if table_size == 0:
            # Nothing known about the table, so there is no proportion to judge. The
            # protected-table check still applies, and an unknown table is not evidence
            # of safety — it is silence.
            return []

        limit = table_size * self.max_row_delete_pct
        if rows <= limit:
            return []

        pct = rows / table_size
        return [
            InvariantViolation(
                invariant=StateInvariant.MAX_ROW_DELETE_PCT,
                detail=(
                    f"{intent.operation.value} would remove {rows} of {table_size} rows "
                    f"({pct:.1%}) from {table}, over the "
                    f"{self.max_row_delete_pct:.0%} limit"
                ),
            )
        ]

    def _check_cascades(self, intent: QueryIntent, cascades: set[str]) -> list[InvariantViolation]:
        if intent.operation is QueryOperation.SELECT or not cascades:
            return []

        unapproved = sorted(cascades - self.approved_cascade_tables)
        if not unapproved:
            return []

        return [
            InvariantViolation(
                invariant=StateInvariant.NO_CASCADE_DELETES,
                detail=(
                    f"{intent.operation.value} would cascade into unapproved "
                    f"table{'s' if len(unapproved) > 1 else ''}: {', '.join(unapproved)}"
                ),
            )
        ]
