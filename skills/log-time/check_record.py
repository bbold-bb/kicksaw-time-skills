#!/usr/bin/env python3
"""Check one time record payload before it is written.

    check_record.py payload.json             a new record
    check_record.py payload.json --update    a same-day merge (hours and the two notes fields)

Only the fields the org requires (task, date, hours) can stop a write, plus a leftover
placeholder anywhere. Other blanks are mentioned and don't stop it.
Prints OK (with any mentions) and exits 0, or lists every problem and exits 1. Calls nothing.
"""
import datetime
import json
import math
import re
import sys

HOURS = "TASKRAY__Hours__c"
DATE = "TASKRAY__Date__c"
TASK = "TASKRAY__Task__c"
TIME_TYPE = "TASKRAY__trTimeType__c"
NOTES = ("Notes__c", "Notes_Long_Text__c")
# Sent because they are useful, not because the org requires them.
USUAL = ("RecordTypeId", "TASKRAY__Project__c", "TASKRAY__Owner__c", "TASKRAY__Billable__c",
         TIME_TYPE, "Activity_Type__c") + NOTES
USUAL_INTERNAL = ("Category__c", "Non_Billable_Reason__c")
MERGE = (HOURS,) + NOTES


def blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def placeholder(v):
    return isinstance(v, str) and bool(re.fullmatch(r"\s*<[^<>]+>\s*", v))


def hours_problem(v):
    if blank(v):
        return "is blank"
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return "must be a number"
    return None if v > 0 else "must be more than zero"


def task_problem(v):
    if blank(v):
        return "is blank"
    if not isinstance(v, str) or not re.fullmatch(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?", v):
        return "is not a record Id"
    return None


def date_problem(v):
    if blank(v):
        return "is blank"
    try:
        datetime.datetime.strptime(v, "%Y-%m-%d")
    except (TypeError, ValueError):
        return "must be a date as YYYY-MM-DD"
    return None if len(v) == 10 else "must be a date as YYYY-MM-DD"


def check(payload, update=False):
    """Returns (problems that stop the write, mentions that don't)."""
    problems, mentions = [], []
    required = {HOURS: hours_problem}
    if not update:
        required = {TASK: task_problem, DATE: date_problem, HOURS: hours_problem}
    for field, rule in required.items():
        problem = rule(payload.get(field))
        if problem:
            problems.append(f"{field} {problem}")
    for field, value in payload.items():
        if field not in required and placeholder(value):
            problems.append(f"{field} still has a placeholder")
        if update and field not in MERGE:
            problems.append(f"{field} can't be changed in a same-day merge")
        if update and field in NOTES and blank(value):
            problems.append(f"{field} is blank and would erase the notes already there; leave it out")
    hours = payload.get(HOURS)
    if not hours_problem(hours) and (hours * 4) % 1:
        mentions.append(f"{HOURS} isn't in quarter hours")
    if not update:
        usual = USUAL + (USUAL_INTERNAL if payload.get(TIME_TYPE) == "Internal" else ())
        mentions += [f"{field} is blank" for field in usual if blank(payload.get(field))]
    return problems, mentions


def main(argv):
    args = [a for a in argv if a != "--update"]
    if len(args) != 1:
        print(__doc__.strip())
        return 1
    try:
        with open(args[0], encoding="utf-8-sig") as fh:
            payload = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"Can't read {args[0]}: {e}")
        return 1
    if not isinstance(payload, dict):
        print("The payload must be one record.")
        return 1
    problems, mentions = check(payload, "--update" in argv)
    if problems:
        print("Not written. Fix these first:")
        for p in problems:
            print(f"- {p}")
        return 1
    print("OK")
    for m in mentions:
        print(f"- {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
