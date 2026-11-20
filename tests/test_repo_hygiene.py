"""Guards that keep real people, clients and org records out of the repo.

These run on every commit (AGENTS.md: run the tests). A failure here means a real-looking
value slipped in. Replace it with a made-up one; don't widen the allow lists without a reason.
"""
import os
import re
import subprocess

ROOT = os.path.join(os.path.dirname(__file__), "..")

# Emails that may appear. Anything at example.com, example.org or example.net is always fine.
ALLOWED_EMAILS = {"noreply@anthropic.com"}

# Salesforce record Ids are 15 or 18 letters and digits, and every Id this org issues has
# a 0 in its sixth place (the pod and reserved characters). No Id belongs in the repo:
# the skills look records up in the org at runtime.
SF_ID = re.compile(r"(?<![A-Za-z0-9])[a-zA-Z0-9]{5}0[A-Za-z0-9]{9}(?:[A-Za-z0-9]{3})?(?![A-Za-z0-9])")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
BINARY = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip")


def tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    for path in out.split():
        if not path.endswith(BINARY):
            with open(os.path.join(ROOT, path), encoding="utf-8", errors="ignore") as fh:
                yield path, fh.read()


def test_no_salesforce_record_ids():
    found = [(path, m) for path, text in tracked_text_files() for m in SF_ID.findall(text)
             if any(c.isdigit() for c in m) and any(c.isalpha() for c in m)]
    assert found == [], f"Record Id-shaped values in the repo: {found}"


def test_only_placeholder_emails():
    found = [(path, e) for path, text in tracked_text_files() for e in EMAIL.findall(text)
             if e.lower() not in ALLOWED_EMAILS and not re.search(r"@example\.(com|org|net)$", e.lower())]
    assert found == [], f"Emails that aren't placeholders: {found}"


def test_no_team_feature():
    assert not os.path.exists(os.path.join(ROOT, "skills", "team-time"))
    for path, text in tracked_text_files():
        if path.startswith("skills/"):
            assert "Logging time for a teammate" not in text, path


def test_skill_versions_match_the_changelog():
    versions = {}
    for name in ("log-time", "time-report"):
        with open(os.path.join(ROOT, "skills", name, "SKILL.md"), encoding="utf-8") as fh:
            versions[name] = re.search(r"^version: (\S+)$", fh.read(), re.M).group(1)
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as fh:
        latest = re.search(r"^## (\d+\.\d+\.\d+) \(", fh.read(), re.M).group(1)
    assert set(versions.values()) == {latest}, (versions, latest)
