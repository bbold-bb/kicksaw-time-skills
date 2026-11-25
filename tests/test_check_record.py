"""Required fields are never zero or blank; other blanks are mentioned, not blocked (1.20.3)."""
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


REQUIRED = ("TASKRAY__Task__c", "TASKRAY__Date__c", "TASKRAY__Hours__c")
OPTIONAL = [k for k in client() if k not in REQUIRED]


@pytest.mark.parametrize("hours", [0, 0.0, -1, None, "", "1.5", True, float("nan"), float("inf")])
def test_hours_must_be_a_positive_number(tmp_path, hours):
    code, out = check(tmp_path, client(TASKRAY__Hours__c=hours))
    assert code == 1 and "TASKRAY__Hours__c" in out


@pytest.mark.parametrize("hours", [0.1, 0.33, 1.3])
def test_odd_hours_are_mentioned_not_blocked(tmp_path, hours):
    code, out = check(tmp_path, client(TASKRAY__Hours__c=hours))
    assert code == 0 and out.startswith("OK") and "quarter" in out


@pytest.mark.parametrize("field", REQUIRED)
@pytest.mark.parametrize("bad", ["missing", None, "", "   ", "\u00a0", "<from the profile>"])
def test_required_fields_must_be_filled(tmp_path, field, bad):
    p = client()
    if bad == "missing":
        del p[field]
    else:
        p[field] = bad
    code, out = check(tmp_path, p)
    assert code == 1 and field in out


@pytest.mark.parametrize("field", OPTIONAL)
@pytest.mark.parametrize("blank", ["missing", None, "", "   "])
def test_other_blanks_are_mentioned_not_blocked(tmp_path, field, blank):
    p = client()
    if blank == "missing":
        del p[field]
    else:
        p[field] = blank
    code, out = check(tmp_path, p)
    assert code == 0 and out.startswith("OK") and field in out


@pytest.mark.parametrize("field", ["Notes__c", "Activity_Type__c", "TASKRAY__Project__c"])
def test_a_leftover_placeholder_is_never_written(tmp_path, field):
    code, out = check(tmp_path, client(**{field: "<from the profile>"}))
    assert code == 1 and field in out


def test_notes_may_hold_angle_brackets(tmp_path):
    assert check(tmp_path, client(Notes__c="<5 records left, moved on"))[1].strip() == "OK"


def test_zero_in_another_field_is_not_blocked(tmp_path):
    assert check(tmp_path, client(Miscellaneous_Hours__c=0))[0] == 0


@pytest.mark.parametrize("bad", ["16/11/2026", "2026-13-01", "2026-11-16T00:00:00", 20261116])
def test_date_must_be_a_real_date(tmp_path, bad):
    code, out = check(tmp_path, client(TASKRAY__Date__c=bad))
    assert code == 1 and "TASKRAY__Date__c" in out


def test_the_task_must_be_a_record_id(tmp_path):
    code, out = check(tmp_path, client(TASKRAY__Task__c="the task"))
    assert code == 1 and "TASKRAY__Task__c" in out


def test_every_problem_is_listed_at_once(tmp_path):
    _, out = check(tmp_path, client(TASKRAY__Hours__c=0, TASKRAY__Task__c="", TASKRAY__Date__c=None))
    for f in REQUIRED:
        assert f in out, f


def test_same_day_merge_checks_hours_and_allows_only_its_three_fields(tmp_path):
    ok = {"TASKRAY__Hours__c": 1.5, "Notes__c": "A", "Notes_Long_Text__c": "A"}
    assert check(tmp_path, ok, "--update")[1].strip() == "OK"
    code, out = check(tmp_path, {**ok, "TASKRAY__Hours__c": 0}, "--update")
    assert code == 1 and "TASKRAY__Hours__c" in out
    code, out = check(tmp_path, {**ok, "Notes__c": ""}, "--update")
    assert code == 1 and "would erase" in out
    assert check(tmp_path, {"TASKRAY__Hours__c": 1.5}, "--update")[0] == 0
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

def test_payload_sends_only_needed_or_helpful_fields():
    t = read("skills/log-time/reference/taskray.md")
    payload = t[t.index('"RecordTypeId"'):t.index("**Internal work** instead")]
    for f in ("HourlyRate__c", "DeliveryTeam__c", "FluxResource__c", "TASKRAY__trUnsavedTimeEntry__c", "Bypass_Time_Flow__c"):
        assert f not in payload, f
    for f in client():
        assert f in payload, f
    assert "check_record.py" in t and "--update" in t


def test_the_skill_does_not_claim_what_org_automation_does():
    t = read("skills/log-time/reference/taskray.md")
    assert "is set by org automation" not in t
    assert "automation and validation rules can't be seen from here" in t


def test_rule_is_in_the_proposal_the_write_and_the_verify():
    log = read(LOG)
    s2 = log[log.index("### Stage 2: time records"):log.index("## Step 5")]
    s6 = log[log.index("## Step 6"):log.index("### Choosing the Activity Type")]
    s7 = log[log.index("## Step 7"):log.index("## Step 8")]
    assert "no row with zero or blank hours" in s2
    assert "no Activity Type or notes" not in s2 and "missing a project" not in s2
    assert "check_record.py" in s6 and "Never insert or update a record that doesn't pass" in s6
    assert "never invent a value" in s6
    assert "doesn't stop the write" in s6
    assert "task, date and hours" in s7
    assert "task, date and hours" in log[log.index("## Ground rules"):log.index("## Step 0")]
