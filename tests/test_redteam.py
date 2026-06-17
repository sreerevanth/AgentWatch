"""SAF-008 — Automated red-team safety harness tests."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agentwatch.cli.main import app
from agentwatch.security.owasp import OwaspVector
from agentwatch.security.redteam import (
    AttackCategory,
    AttackScenario,
    RedTeamHarness,
    default_corpus,
)

runner = CliRunner()


def test_default_corpus_covers_all_categories():
    corpus = default_corpus()
    assert corpus
    covered = {s.category for s in corpus}
    assert covered == set(AttackCategory)


def test_run_scores_every_scenario():
    report = RedTeamHarness().run()
    assert report.total == len(default_corpus())
    assert report.defended_count + len(report.bypassed) == report.total
    assert 0.0 <= report.resilience_score <= 1.0


def test_known_attacks_are_defended():
    report = RedTeamHarness().run()
    by_id = {r.scenario.id: r for r in report.results}
    # Destructive command, RCE pipe, and an explicit injection must be caught.
    assert by_id["pt-rm-parent"].defended
    assert by_id["tm-curl-pipe-sh"].defended
    assert by_id["tm-drop-table"].defended
    assert by_id["pi-override"].defended


def test_harness_surfaces_a_known_gap():
    # A read-only traversal slips past the command risk patterns; the harness
    # should report it as bypassed rather than hide the gap.
    report = RedTeamHarness().run()
    by_id = {r.scenario.id: r for r in report.results}
    assert by_id["pt-read-passwd"].defended is False
    assert any(r.scenario.id == "pt-read-passwd" for r in report.bypassed)


def test_by_category_counts_consistent():
    report = RedTeamHarness().run()
    cats = report.by_category()
    assert set(cats) == {c.value for c in AttackCategory}
    assert sum(v["total"] for v in cats.values()) == report.total
    assert sum(v["defended"] for v in cats.values()) == report.defended_count


def test_custom_scenarios_are_honored():
    scenarios = [
        AttackScenario(
            "custom-rm",
            AttackCategory.TOOL_MISUSE,
            OwaspVector.UNSAFE_CODE_EXEC,
            "rm -rf /",
            "Wipe root.",
        )
    ]
    report = RedTeamHarness(scenarios).run()
    assert report.total == 1
    assert report.results[0].defended


def test_empty_corpus_scores_one():
    report = RedTeamHarness([]).run()
    assert report.total == 0
    assert report.resilience_score == 1.0


def test_cli_redteam_runs():
    result = runner.invoke(app, ["redteam"])
    assert result.exit_code == 0
    assert "Red-Team Resilience" in result.stdout


def test_cli_redteam_json():
    result = runner.invoke(app, ["redteam", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert 0.0 <= data["resilience_score"] <= 1.0
    assert data["total"] == len(default_corpus())
    assert set(data["by_category"]) == {c.value for c in AttackCategory}
