"""time_report.py runs the same on Windows as on a Mac. Fakes only; never calls Salesforce."""
import ast
import datetime as dt
import subprocess

import pytest

import time_report


def test_sf_resolved_through_which(monkeypatch):
    monkeypatch.setattr(time_report.shutil, "which", lambda name: r"C:\sf\bin\sf.cmd" if name == "sf" else None)
    assert time_report.sf_path() == r"C:\sf\bin\sf.cmd"


def test_missing_sf_points_to_setup(monkeypatch):
    monkeypatch.setattr(time_report.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit) as e:
        time_report.sf_path()
    assert time_report.SETUP_URL in str(e.value)


def test_sf_runs_with_utf8(monkeypatch):
    seen = {}
    monkeypatch.setattr(time_report.shutil, "which", lambda name: "/usr/local/bin/sf")

    def fake_run(cmd, **kw):
        seen.update(kw, cmd=cmd)
        return subprocess.CompletedProcess(
            cmd, 0, stdout='{"result":{"records":[{"Name":"Café Ñandú"}]}}', stderr="")

    monkeypatch.setattr(time_report.subprocess, "run", fake_run)
    assert time_report.sf_query({"org_alias": "Kicksaw-Prod"}, "SELECT Name FROM X") == [{"Name": "Café Ñandú"}]
    assert seen["encoding"] == "utf-8"
    assert seen["cmd"][0] == "/usr/local/bin/sf"


def test_day_label_has_no_padding():
    assert time_report.day_label(dt.date(2026, 11, 3)) == "Tue Nov 3"
    assert time_report.day_label(dt.date(2026, 11, 3), weekday=False) == "Nov 3"


def test_clock_has_no_padding():
    assert time_report.clock(dt.datetime(2026, 11, 3, 15, 7)) == "3:07 PM"
    assert time_report.clock(dt.datetime(2026, 11, 3, 0, 5)) == "12:05 AM"


def test_no_dash_flag_in_strftime():
    with open(time_report.__file__, encoding="utf-8") as fh:
        assert "%-" not in fh.read()


def test_every_open_names_utf8():
    with open(time_report.__file__, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    opens = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open"]
    assert opens, "expected open() calls"
    for call in opens:
        enc = [k for k in call.keywords if k.arg == "encoding"]
        assert enc and getattr(enc[0].value, "value", None) == "utf-8", f"line {call.lineno}"


def test_file_link_handles_spaces(tmp_path):
    p = tmp_path / "Salesforce Projects" / "dash.html"
    p.parent.mkdir()
    p.write_text("x")
    link = time_report.file_link(str(p))
    assert link.startswith("file:///")
    assert "Salesforce%20Projects" in link
