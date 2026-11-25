"""The internal project's time task is the newest open one, taken without asking (1.20.4), on every run (1.20.5)."""
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


LOG = read("skills/log-time/SKILL.md")
REF = read("skills/log-time/reference/taskray.md")


def test_setup_takes_the_newest_internal_task_without_asking():
    step = LOG[LOG.index("4. **Internal project.**"):LOG.index("**Allowed values.**")]
    assert "newest" in step and "never ask which one" in step
    assert "resolve its live task the same way" not in step


def test_live_task_rule_separates_client_and_internal():
    rule = REF[REF.index("**Live task for a project.**"):REF.index("**Drift check, tasks**")]
    assert "**The internal project** never asks" in rule
    assert "On a client project, zero or several" in rule
    assert "ORDER BY CreatedDate DESC" in rule


def test_every_run_moves_to_the_newest_internal_task():
    """A saved task that is still open isn't enough: an older one left open would keep taking time."""
    drift = LOG[LOG.index("### Org drift check"):LOG.index("### Evidence drift")]
    assert "**Internal task, every run.**" in drift
    assert "even when the saved one is still open" in drift
    assert "save it without asking, and say so in one line" in drift
    assert "Say nothing when it already matches" in drift
    assert "A client task in the profile has `TASKRAY__Archived__c = true`" in drift


def test_reference_has_the_internal_drift_check():
    rule = REF[REF.index("**Drift check, tasks**"):REF.index("## Run queries")]
    assert "**Drift check, internal task** (every run)" in rule


def test_no_task_number_is_hardcoded():
    for text in (LOG, REF):
        assert "Date #" not in text
