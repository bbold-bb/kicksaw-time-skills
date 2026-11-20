"""Checks on the skill text that tests can pin: per-OS commands, examples, and pointers."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
PY_LINE = ("Run Python as python3 on a Mac, and as py -3 on Windows "
           "(or python if that is the one that prints a Python 3 version).")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def test_python_command_per_os():
    for p in ("skills/time-report/SKILL.md", "skills/log-time/SKILL.md"):
        assert PY_LINE in read(p), p


def test_dashboard_open_per_os():
    t = read("skills/time-report/SKILL.md")
    assert 'open "<path>"' in t
    assert 'start "" "<path>"' in t


def encode(path):
    """How Claude Code names a session folder: every non letter or digit becomes a hyphen."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def table_rows(text, header):
    """Cells of the markdown table that starts with this header row, backticks stripped."""
    lines = text.splitlines()
    start = lines.index(header)
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        rows.append([c.strip().strip("`") for c in line.strip("|").split("|")])
    return rows


def test_directory_examples_match_the_encoder():
    rows = table_rows(read("skills/log-time/SKILL.md"), "| Working directory | Transcript folder |")
    assert len(rows) == 4
    assert any(r[0].startswith("C:\\") for r in rows)
    assert any(" " in r[0] for r in rows)
    for path, folder in rows:
        assert encode(path) == folder, path


SETUP_RAW = "https://raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/main/SETUP.md"


def step0(text):
    start = text.index("## Step 0:")
    return text[start:text.index("\n## Step 1:", start)]


def test_log_time_preflight_points_to_setup():
    s = step0(read("skills/log-time/SKILL.md"))
    assert "### Preflight" in s
    assert SETUP_RAW in s
