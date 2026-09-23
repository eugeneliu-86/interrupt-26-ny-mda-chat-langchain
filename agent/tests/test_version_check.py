"""The pre-deploy version check must fail on a seeded violation (ph. 05 §6).

A guard nobody has watched fail is not a guard. These tests seed each of the
four states into a throwaway tree, so the failing path is exercised rather
than assumed — the same reason `check-contracts.sh` was rewritten after one of
its greps turned out to match every line.
"""

from __future__ import annotations

import json

import pytest

from contracts import check_version_bump as cvb


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A miniature agent tree the check can be pointed at."""
    (tmp_path / "contracts").mkdir()
    (tmp_path / "middleware").mkdir()
    (tmp_path / "agent.py").write_text("# agent\n")
    (tmp_path / "instructions.md").write_text("# instructions\n")
    (tmp_path / "contracts" / "grants.py").write_text("GRANTS = {}\n")
    (tmp_path / "middleware" / "role_gate.py").write_text("# gate\n")
    monkeypatch.setattr(cvb, "ROOT", tmp_path)
    monkeypatch.setattr(cvb, "STATE", tmp_path / "contracts" / ".deployed.json")
    return tmp_path


def at_version(monkeypatch, v: str) -> None:
    monkeypatch.setattr(cvb, "DEMO_VERSION", v)


def test_no_recorded_deploy_is_not_a_failure(tree, monkeypatch):
    at_version(monkeypatch, "v1")
    assert cvb.main() == 0


def test_nothing_changed_passes(tree, monkeypatch):
    at_version(monkeypatch, "v1")
    cvb.record()
    assert cvb.main() == 0


def test_a_changed_grant_without_a_bump_FAILS(tree, monkeypatch, capsys):
    """THE SEEDED VIOLATION. This is the test the criterion asks for."""
    at_version(monkeypatch, "v1")
    cvb.record()
    (tree / "contracts" / "grants.py").write_text("GRANTS = {'engineer': {'x'}}\n")
    assert cvb.main() == 1
    out = capsys.readouterr().out
    assert "FAIL" in out and "contracts/grants.py" in out
    assert "bump DEMO_VERSION" in out


@pytest.mark.parametrize(
    "path", ["instructions.md", "middleware/role_gate.py", "agent.py"]
)
def test_every_watched_path_triggers_it(tree, monkeypatch, path):
    at_version(monkeypatch, "v1")
    cvb.record()
    (tree / path).write_text("changed\n")
    assert cvb.main() == 1


def test_a_new_middleware_file_triggers_it(tree, monkeypatch):
    """An ADDED file changes behaviour as much as an edited one."""
    at_version(monkeypatch, "v1")
    cvb.record()
    (tree / "middleware" / "extra.py").write_text("# new hook\n")
    assert cvb.main() == 1


def test_a_deleted_file_triggers_it(tree, monkeypatch):
    at_version(monkeypatch, "v1")
    cvb.record()
    (tree / "middleware" / "role_gate.py").unlink()
    assert cvb.main() == 1


def test_changed_and_bumped_passes(tree, monkeypatch):
    at_version(monkeypatch, "v1")
    cvb.record()
    (tree / "contracts" / "grants.py").write_text("GRANTS = {'engineer': {'x'}}\n")
    at_version(monkeypatch, "v2")
    assert cvb.main() == 0


def test_a_bump_with_no_change_passes_with_a_warning(tree, monkeypatch, capsys):
    at_version(monkeypatch, "v1")
    cvb.record()
    at_version(monkeypatch, "v2")
    assert cvb.main() == 0
    assert "usually a mistake" in capsys.readouterr().out


def test_the_recorded_state_names_itself_generated(tree, monkeypatch):
    at_version(monkeypatch, "v1")
    cvb.record()
    state = json.loads((tree / "contracts" / ".deployed.json").read_text())
    assert "GENERATED" in state["_generated"]
    assert state["demo_version"] == "v1"


def test_tests_are_not_watched(tree, monkeypatch):
    """Editing a test must never demand a version bump — it cannot change an
    answer, and a check that cried wolf here would be turned off."""
    at_version(monkeypatch, "v1")
    cvb.record()
    (tree / "tests").mkdir()
    (tree / "tests" / "test_thing.py").write_text("# a test\n")
    assert cvb.main() == 0
