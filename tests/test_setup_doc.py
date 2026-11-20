"""SETUP.md is followed by an agent on someone else's machine. These pin what it must say."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
HEADINGS = [
    "## Before you start", "## 1. Detect", "## 2. Check everything, then ask once", "## 3. Skills",
    "## 4. Salesforce CLI", "## 5. Python", "## 6. Org login", "## 7. Connectors", "## 8. Hand off",
    "## If a step fails",
]
OPENING = ("I'll check what's already set up and install what's missing. You'll see prompts asking you to "
           "allow commands and downloads. Allow is right for these steps, and I'll say what each one is for "
           "just before it appears.")


def text():
    with open(os.path.join(ROOT, "SETUP.md"), encoding="utf-8") as fh:
        return fh.read()


def section(heading):
    t = text()
    start = t.index(heading + "\n")
    nxt = t.find("\n## ", start + len(heading))
    return t[start:] if nxt == -1 else t[start:nxt]


def test_headings_in_order():
    found = [line for line in text().splitlines() if line.startswith("## ")]
    assert found == HEADINGS


def test_install_steps_cover_both_systems():
    for h in HEADINGS[3:7]:
        s = section(h)
        assert "macOS" in s and "Windows (PowerShell)" in s, h


def test_archive_url_follows_the_branch():
    s = section("## 3. Skills")
    assert "https://github.com/bbold-bb/kicksaw-time-skills/archive/refs/heads/" in s
    assert "branch" in s


def test_asks_once_before_downloading():
    assert "If nothing is missing, skip to step 7." in section("## 2. Check everything, then ask once")


def test_opening_line_verbatim():
    assert OPENING in section("## Before you start")


def test_setup_names_sf_fallback_paths():
    s = section("## 4. Salesforce CLI")
    assert "/usr/local/bin/sf" in s and "sf.cmd" in s


def test_setup_rejects_store_python():
    s = section("## 5. Python")
    assert "Python 3." in s and "Microsoft Store" in s


def test_setup_rerun_is_quiet():
    assert 'say "log my time" whenever you\'re ready' in section("## 8. Hand off")


def test_never_asks_for_a_password():
    for line in text().splitlines():
        if re.search(r"(enter|type|paste|give me).{0,20}password", line, re.I):
            assert "their own" in line or "your own" in line, line


def test_never_touches_profile_folder_except_alias():
    t = text()
    assert "Never touch `~/.claude/kicksaw-time/`" in t or "never touch `~/.claude/kicksaw-time/`" in t


def test_no_em_dashes():
    assert "—" not in text()
