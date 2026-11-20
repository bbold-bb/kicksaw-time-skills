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
