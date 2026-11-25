#!/usr/bin/env python3
"""Check one time record payload before it is written. No zero or blank values get through.

    check_record.py payload.json             a new record
    check_record.py payload.json --update    a same-day merge (hours and the two notes fields)

Prints OK and exits 0, or lists every problem and exits 1. Reads the file; calls nothing.
"""
import datetime
import json
import math
import re
import sys

HOURS = "TASKRAY__Hours__c"
DATE = "TASKRAY__Date__c"
BILLABLE = "TASKRAY__Billable__c"
TIME_TYPE = "TASKRAY__trTimeType__c"
NOTES = ("Notes__c", "Notes_Long_Text__c")
IDS = ("RecordTypeId", "TASKRAY__Project__c", "TASKRAY__Task__c", "TASKRAY__Owner__c")
TEXT = (TIME_TYPE, "Activity_Type__c") + NOTES
INTERNAL_TEXT = ("Category__c", "Non_Billable_Reason__c")
MERGE = (HOURS,) + NOTES


def hours_problem(v):
    if v is None or v == "":
        return "is blank"
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return "must be a number"
    if v <= 0:
        return "must be more than zero"
    if (v * 4) % 1:
        return "must be in quarter hours"
    return None


def text_problem(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return "is blank"
    if not isinstance(v, str):
        return "must be text"
    if v.strip().startswith("<"):
        return "still has a placeholder"
    return None


def id_problem(v):
    return text_problem(v) or (None if re.fullmatch(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?", v)
                               else "is not a record Id")


def date_problem(v):
    problem = text_problem(v)
    if problem:
        return problem
    try:
        datetime.datetime.strptime(v, "%Y-%m-%d")
    except ValueError:
        return "must be a date as YYYY-MM-DD"
    return None if len(v) == 10 else "must be a date as YYYY-MM-DD"


def problems(payload, update=False):
    found = []

    def add(field, problem):
        if problem:
            found.append(f"{field} {problem}")

    add(HOURS, hours_problem(payload.get(HOURS)))
    if update:
        for f in NOTES:
            add(f, text_problem(payload.get(f)))
        for f in payload:
            if f not in MERGE:
                add(f, "can't be changed in a same-day merge")
        return found
    for f in IDS:
        add(f, id_problem(payload.get(f)))
    add(DATE, date_problem(payload.get(DATE)))
    for f in TEXT:
        add(f, text_problem(payload.get(f)))
    billable = payload.get(BILLABLE)
    if not isinstance(billable, bool):
        add(BILLABLE, "must be true or false")
    if payload.get(TIME_TYPE) == "Internal":
        for f in INTERNAL_TEXT:
            add(f, text_problem(payload.get(f)))
        if billable is True:
            add(BILLABLE, "must be false on internal time")
    return found


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
    found = problems(payload, "--update" in argv)
    if not found:
        print("OK")
        return 0
    print("Not written. Fix these first:")
    for p in found:
        print(f"- {p}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
