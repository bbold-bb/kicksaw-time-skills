"""No time record goes in with zero or blank values (1.20.2): the checker, and the steps that run it."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "skills", "log-time", "check_record.py")
LOG = "skills/log-time/SKILL.md"


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def client(**over):
    p = {"RecordTypeId": "a" * 18, "TASKRAY__Project__c": "b" * 18, "TASKRAY__Task__c": "c" * 18,
         "TASKRAY__Date__c": "2026-11-16", "TASKRAY__Hours__c": 1.5, "TASKRAY__Owner__c": "d" * 18,
         "TASKRAY__Billable__c": True, "TASKRAY__trTimeType__c": "Standard",
         "Activity_Type__c": "Meeting", "Notes__c": "ClientA: Planning", "Notes_Long_Text__c": "ClientA: Planning"}
    p.update(over)
    return p


def internal(**over):
    p = client(TASKRAY__Billable__c=False, TASKRAY__trTimeType__c="Internal",
               Category__c="Internal", Non_Billable_Reason__c="Not Applicable")
    p.update(over)
    return p


def check(tmp_path, payload, *args):
    f = tmp_path / "payload.json"
    f.write_text(json.dumps(payload), encoding="utf-8")
    r = subprocess.run([sys.executable, SCRIPT, str(f), *args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


@pytest.mark.parametrize("payload", [client(), internal(), client(TASKRAY__Hours__c=0.25), client(TASKRAY__Hours__c=8)])
def test_complete_records_pass(tmp_path, payload):
    code, out = check(tmp_path, payload)
    assert code == 0 and out.strip() == "OK"


@pytest.mark.parametrize("hours", [0, 0.0, -1, None, "", "1.5", True, 0.1, 1.3, float("nan"), float("inf")])
def test_hours_must_be_a_positive_quarter(tmp_path, hours):
    code, out = check(tmp_path, client(TASKRAY__Hours__c=hours))
    assert code == 1 and "TASKRAY__Hours__c" in out


@pytest.mark.parametrize("field", [k for k in client()])
@pytest.mark.parametrize("bad", ["missing", None, "", "   ", " ", "<from the profile>"])
def test_every_standard_field_must_be_filled(tmp_path, field, bad):
    p = client()
    if bad == "missing":
        del p[field]
    else:
        p[field] = bad
    code, out = check(tmp_path, p)
    assert code == 1 and field in out


@pytest.mark.parametrize("field", ["Category__c", "Non_Billable_Reason__c"])
def test_internal_records_need_their_own_fields(tmp_path, field):
    p = internal()
    del p[field]
    code, out = check(tmp_path, p)
    assert code == 1 and field in out


def test_internal_is_never_billable(tmp_path):
    code, out = check(tmp_path, internal(TASKRAY__Billable__c=True))
    assert code == 1 and "TASKRAY__Billable__c" in out


@pytest.mark.parametrize("bad", ["16/11/2026", "2026-13-01", "2026-11-16T00:00:00", 20261116])
def test_date_must_be_a_real_date(tmp_path, bad):
    code, out = check(tmp_path, client(TASKRAY__Date__c=bad))
    assert code == 1 and "TASKRAY__Date__c" in out


def test_ids_must_look_like_ids(tmp_path):
    code, out = check(tmp_path, client(TASKRAY__Task__c="the task"))
    assert code == 1 and "TASKRAY__Task__c" in out


def test_every_problem_is_listed_at_once(tmp_path):
    _, out = check(tmp_path, client(TASKRAY__Hours__c=0, Notes__c="", Activity_Type__c=None))
    for f in ("TASKRAY__Hours__c", "Notes__c", "Activity_Type__c"):
        assert f in out, f


def test_same_day_merge_checks_its_three_fields(tmp_path):
    ok = {"TASKRAY__Hours__c": 1.5, "Notes__c": "A", "Notes_Long_Text__c": "A"}
    assert check(tmp_path, ok, "--update")[0] == 0
    for k in ok:
        code, out = check(tmp_path, {**ok, k: 0 if k.endswith("Hours__c") else ""}, "--update")
        assert code == 1 and k in out
    code, out = check(tmp_path, {**ok, "Activity_Type__c": "Meeting"}, "--update")
    assert code == 1 and "Activity_Type__c" in out


@pytest.mark.parametrize("text", ["", "not json", "[]"])
def test_unreadable_payload_fails_cleanly(tmp_path, text):
    f = tmp_path / "payload.json"
    f.write_text(text, encoding="utf-8")
    r = subprocess.run([sys.executable, SCRIPT, str(f)], capture_output=True, text=True)
    assert r.returncode == 1 and "Traceback" not in r.stderr


def test_missing_file_fails_cleanly(tmp_path):
    r = subprocess.run([sys.executable, SCRIPT, str(tmp_path / "none.json")], capture_output=True, text=True)
    assert r.returncode == 1 and "Traceback" not in r.stderr


def test_windows_byte_order_mark_is_accepted(tmp_path):
    f = tmp_path / "payload.json"
    f.write_text(json.dumps(client()), encoding="utf-8-sig")
    assert subprocess.run([sys.executable, SCRIPT, str(f)]).returncode == 0


# The steps that run it

def test_reference_payload_has_no_zero_and_passes_the_field_list():
    t = read("skills/log-time/reference/taskray.md")
    payload = t[t.index('"RecordTypeId"'):t.index("**Internal work** instead")]
    assert "HourlyRate__c" not in payload
    assert ": 0" not in payload
    for f in client():
        assert f in payload, f
    assert "check_record.py" in t and "--update" in t


def test_rule_is_in_the_proposal_the_write_and_the_verify():
    log = read(LOG)
    s2 = log[log.index("### Stage 2: time records"):log.index("## Step 5")]
    s6 = log[log.index("## Step 6"):log.index("### Choosing the Activity Type")]
    s7 = log[log.index("## Step 7"):log.index("## Step 8")]
    assert "no row with zero or blank hours" in s2
    assert "check_record.py" in s6 and "Never insert or update a record that doesn't pass" in s6
    assert "never invent a value" in s6
    assert "zero or blank" in s7
    assert "zero or blank" in log[log.index("## Ground rules"):log.index("## Step 0")]
