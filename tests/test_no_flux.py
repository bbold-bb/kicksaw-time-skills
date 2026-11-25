"""Flux is gone (1.20.1): never queried, asked about, stored or written, and never a reason to stop."""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def test_flux_is_not_queried_or_written():
    for p in ("skills/log-time/reference/taskray.md", "skills/log-time/reference/resource-hero.md",
              "skills/log-time/README.md", "skills/time-report/SKILL.md", "README.md", "SETUP.md"):
        assert "flux" not in read(p).lower(), p


def test_delivery_team_is_left_to_the_org():
    t = read("skills/log-time/reference/taskray.md")
    payload = t[t.index('"RecordTypeId"'):t.index("**Internal work** instead")]
    assert "DeliveryTeam__c" not in payload
    log = read("skills/log-time/SKILL.md")
    assert log.count("delivery_team") == 1  # only to say it is ignored


def test_profile_has_no_flux_fields():
    assert set(json.loads(read("skills/log-time/profile.example.json"))["user"]) == {"username", "user_id"}


def test_setup_never_stops_for_flux_and_old_fields_are_ignored():
    log = read("skills/log-time/SKILL.md")
    setup = log[log.index("### Setup (first run)"):log.index("### New questions for existing profiles")]
    assert "flux" not in setup.lower()
    assert "ignore them, and never mention them" in log


def test_guide_has_no_flux_requirement():
    g = read("docs/time-skills-guide.html")
    start = g[:g.index('id="whats-new"')]
    assert "flux" not in start.lower()
