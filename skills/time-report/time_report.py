#!/usr/bin/env python3
"""Report logged TaskRay time, grouped by project and activity type.

Reads the shared log-time profile for the org alias, username, project labels,
holidays, and weekly baseline. Read-only: never writes to Salesforce.

Usage:
    python3 time_report.py week            # current week (Mon-Sun)
    python3 time_report.py last-week
    python3 time_report.py month           # current calendar month
    python3 time_report.py last-month
    python3 time_report.py 2026-09         # a named month
    python3 time_report.py 2026-09-02 2026-09-08   # explicit range
    python3 time_report.py 2026-09-04      # that single day

Add --by-day to also print a per-day breakdown.
Add --profile PATH to point at a specific profile.json.
Add --dashboard [PATH] to also write an HTML dashboard for the period, with a
totals view and an over-time view (week by week for a month, day by day for a
week). Default path: ~/.claude/kicksaw-time/time-dashboard.html.
Add --export-data [DIR] to write only the four JSON files a published dashboard
reads, covering the profile's dashboard.since through today, with allocation six
months ahead. The period is ignored. Default: ~/.claude/kicksaw-time/dashboard-data.
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
# The profile is user data, not skill data: it lives outside any folder an
# installer replaces, so an update can never take it. The legacy paths below are
# where it used to live, inside the skill folder, and are read so an existing
# install keeps working until it is moved.
PROFILE_HOME = os.path.expanduser("~/.claude/kicksaw-time/profile.json")
PROFILE_LEGACY = [
    os.path.join(HERE, "..", "log-time", "profile.json"),
    os.path.join(HERE, "profile.json"),
    os.path.expanduser("~/.claude/skills/log-time/profile.json"),
]
PROFILE_CANDIDATES = [PROFILE_HOME] + PROFILE_LEGACY
SETUP_URL = "https://github.com/bbold-bb/kicksaw-time-skills#quick-start"


def sf_path():
    """The Salesforce CLI's full path. shutil.which finds sf.cmd on Windows, where a bare "sf" does not run."""
    path = shutil.which("sf")
    if not path:
        sys.exit("The Salesforce CLI (sf) isn't installed or isn't on your PATH. "
                 "To set it up, follow the quick start: " + SETUP_URL)
    return path


def run_sf(args):
    """Run sf and read its output as UTF-8, which Windows does not assume."""
    return subprocess.run([sf_path(), *args], capture_output=True, text=True, encoding="utf-8")


def day_label(d, weekday=True):
    """'Tue Nov 3', or 'Nov 3' without the weekday. Built by hand: Windows strftime has no flag for an unpadded day."""
    return f"{d:%a %b} {d.day}" if weekday else f"{d:%b} {d.day}"


def clock(t):
    """'3:07 PM', built by hand because Windows strftime can't drop the leading zero."""
    return f"{t.hour % 12 or 12}:{t:%M %p}"


def file_link(path):
    """A file:// link that opens on both systems, spaces and drive letters included."""
    return pathlib.Path(path).resolve().as_uri()


def load_profile(explicit):
    paths = [explicit] if explicit else PROFILE_CANDIDATES
    for path in paths:
        if path and os.path.isfile(path):
            if not explicit and os.path.normpath(path) != os.path.normpath(PROFILE_HOME):
                print(f"  note: profile found at {path}.\n"
                      f"        Move it to {PROFILE_HOME} so an update cannot replace it.")
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
    sys.exit(
        "No profile.json found. Run /log-time once to create it, or pass --profile PATH.\n"
        "Looked in: " + ", ".join(os.path.normpath(p) for p in paths)
    )


def label_map(profile):
    """Full project name -> short label, from the profile. Unknown names fall back to a prefix."""
    out = {}
    for proj in profile.get("projects", []):
        out[proj["name"]] = proj.get("label") or proj["name"][:24]
    internal = profile.get("internal", {})
    if internal.get("name"):
        out[internal["name"]] = "Internal"
    return out


def shorten(name, labels):
    if name in labels:
        return labels[name]
    for full, label in labels.items():
        if name.startswith(full.split(" - ")[0]):
            return label
    return name[:24]


def resolve(tokens):
    """Turn the period argument into a (start, end, label) triple, end inclusive."""
    today = dt.date.today()

    if len(tokens) == 2:
        start = dt.date.fromisoformat(tokens[0])
        end = dt.date.fromisoformat(tokens[1])
        return start, end, "Custom range"

    token = tokens[0] if tokens else "week"

    if token == "week":
        start = today - dt.timedelta(days=today.weekday())
        return start, start + dt.timedelta(days=6), f"Week of {day_label(start, weekday=False)}"
    if token == "last-week":
        start = today - dt.timedelta(days=today.weekday() + 7)
        return start, start + dt.timedelta(days=6), f"Week of {day_label(start, weekday=False)}"
    if token == "month":
        start = today.replace(day=1)
        return start, month_end(start), f"{start:%B %Y}"
    if token == "last-month":
        start = (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        return start, month_end(start), f"{start:%B %Y}"

    try:
        start = dt.date.fromisoformat(token + "-01")
        return start, month_end(start), f"{start:%B %Y}"
    except ValueError:
        pass
    day = dt.date.fromisoformat(token)
    return day, day, day_label(day)


def month_end(first):
    nxt = first.replace(day=28) + dt.timedelta(days=4)
    return nxt.replace(day=1) - dt.timedelta(days=1)


def fetch(profile, start, end):
    username = profile["user"]["username"]
    org = profile["org_alias"]
    soql = (
        "SELECT TASKRAY__Date__c, TASKRAY__Project__r.Name, Activity_Type__c, "
        "TASKRAY__Hours__c, TASKRAY__Billable__c "
        "FROM TASKRAY__trTaskTime__c "
        f"WHERE TASKRAY__Owner__r.Username='{username}' "
        f"AND TASKRAY__Date__c >= {start} AND TASKRAY__Date__c <= {end} "
        "ORDER BY TASKRAY__Date__c"
    )
    out = run_sf(["data", "query", "-o", org, "-q", soql, "--json"])
    if out.returncode != 0:
        sys.exit(f"Query failed:\n{out.stderr or out.stdout}")
    return json.loads(out.stdout)["result"]["records"]


def allocations_enabled(profile):
    return bool((profile.get("resource_hero") or {}).get("use_for_allocations"))


TIME_OFF = "Time off"


def sf_query(profile, soql):
    """Records for a query, or None when it fails."""
    out = run_sf(["data", "query", "-o", profile["org_alias"], "-q", soql, "--json"])
    if out.returncode != 0:
        return None
    return json.loads(out.stdout)["result"]["records"]


def fetch_assignments(profile, labels):
    """Every Resource Hero assignment for the user, archived ones included, so past months keep their staffing.

    Returns {assignment id: {label, name, start, end}}. A label comes from, in
    order: the profile project that names the assignment, the profile's
    resource_hero.assignment_labels map, Time off for holiday and PTO
    assignments, then the Resource Hero project name shortened like a TaskRay
    project name, then the assignment's own name.
    """
    rh = profile.get("resource_hero") or {}
    named = {p["rh_assignment_id"]: p["label"] for p in profile.get("projects", []) if p.get("rh_assignment_id")}
    named.update(rh.get("assignment_labels") or {})
    if rh.get("resource_id"):
        where = f"ResourceHeroApp__Resource__c = '{rh['resource_id']}'"
    elif named:
        # An older profile without the resource id still gets the assignments it names.
        where = "Id IN (%s)" % ",".join("'%s'" % i for i in named)
    else:
        return {}
    records = sf_query(profile, (
        "SELECT Id, Name, ResourceHeroApp__RH_Project__r.Name, ResourceHeroApp__Start_Date__c, "
        "ResourceHeroApp__End_Date__c, ResourceHeroApp__Is_Holiday_Time__c, ResourceHeroApp__Is_Time_Off_PTO__c "
        f"FROM ResourceHeroApp__Resource_Assignment__c WHERE {where}"
    ))
    if records is None:
        return None
    out = {}
    for r in records:
        project = (r.get("ResourceHeroApp__RH_Project__r") or {}).get("Name")
        if r["Id"] in named:
            label = named[r["Id"]]
        elif r["ResourceHeroApp__Is_Holiday_Time__c"] or r["ResourceHeroApp__Is_Time_Off_PTO__c"]:
            label = TIME_OFF
        elif project:
            label = shorten(project, labels)
        else:
            label = r["Name"]
        out[r["Id"]] = {
            "label": label,
            "name": project or r["Name"],
            "start": r["ResourceHeroApp__Start_Date__c"],
            "end": r["ResourceHeroApp__End_Date__c"],
        }
    return out


def fetch_allocation_days(profile, start, end, ignored=None):
    """Allocated hours per label per day for the period, from Resource Hero.

    Forecast rows are one per day, with forecast and actual on separate rows, so
    summing Forecast__c per day is safe. Resource Hero's own actuals lag the time
    records by days, so they are never read here; actuals come from TaskRay in
    fetch(). Returns {label: {iso date: hours}}, empty when not configured. The
    dashboard buckets these by week; the text report sums them.

    A forecast row dated outside its assignment's start and end dates is not
    counted: it is usually left over from an assignment whose dates moved. Pass
    a list as `ignored` to get one entry per assignment that had such rows, so
    the caller can say what was left out.
    """
    if not allocations_enabled(profile):
        return {}
    assignments = fetch_assignments(profile, label_map(profile))
    if not assignments:
        if assignments is None:
            # Allocation is a nice-to-have; a report without it is still correct.
            print("  (allocation lookup failed; reporting logged hours only)")
        return {}
    quoted = ",".join("'%s'" % i for i in assignments)
    records = sf_query(profile, (
        "SELECT ResourceHeroApp__Resource_Assignment__c, ResourceHeroApp__ForecastDate__c, "
        "SUM(ResourceHeroApp__Forecast__c) fc "
        "FROM ResourceHeroApp__Resource_Forecast__c "
        f"WHERE ResourceHeroApp__Resource_Assignment__c IN ({quoted}) "
        f"AND ResourceHeroApp__ForecastDate__c >= {start} "
        f"AND ResourceHeroApp__ForecastDate__c <= {end} "
        "GROUP BY ResourceHeroApp__Resource_Assignment__c, ResourceHeroApp__ForecastDate__c"
    ))
    if records is None:
        print("  (allocation lookup failed; reporting logged hours only)")
        return {}
    days = defaultdict(lambda: defaultdict(float))
    outside = {}
    for r in records:
        a = assignments[r["ResourceHeroApp__Resource_Assignment__c"]]
        day, fc = r["ResourceHeroApp__ForecastDate__c"], r.get("fc")
        if not fc:
            continue
        if (a["start"] and day < a["start"]) or (a["end"] and day > a["end"]):
            o = outside.setdefault(r["ResourceHeroApp__Resource_Assignment__c"], dict(a, hours=0.0, first=day, last=day))
            o["hours"] += fc
            o["first"], o["last"] = min(o["first"], day), max(o["last"], day)
            continue
        days[a["label"]][day] += fc
    if ignored is not None:
        ignored.extend(sorted(outside.values(), key=lambda o: o["first"]))
    return {label: dict(per_day) for label, per_day in days.items()}


def print_ignored(ignored):
    if not ignored:
        return
    print("\n  Forecast left out: dated outside its assignment's start and end dates")
    for o in ignored:
        window = f"{o['start'] or 'open'} to {o['end'] or 'open'}"
        print(f"  {o['label']}: {o['hours']:g}h on {o['first']} to {o['last']} (assignment runs {window})")
    print("  Ask whoever manages Resource Hero staffing to fix the dates or the forecast.")


def fetch_allocations(profile, start, end):
    """Allocated hours per project label for the whole period. Returns {label: hours}."""
    return {label: sum(per_day.values())
            for label, per_day in fetch_allocation_days(profile, start, end).items()}


def expected_hours(profile, start, end, today):
    """Baseline for the period: per weekday already passed, minus holidays. Returns (expected, holidays_in_period)."""
    per_day = profile.get("baseline_hours_per_week", 40) / 5
    holidays = profile.get("holidays", {})
    expected = 0.0
    hit = []
    cur = start
    while cur <= end and cur <= today:
        key = cur.isoformat()
        if cur.weekday() < 5:
            if key in holidays:
                hit.append((cur, holidays[key]))
            else:
                expected += per_day
        cur += dt.timedelta(days=1)
    return expected, hit


DASHBOARD_HOME = os.path.expanduser("~/.claude/kicksaw-time/time-dashboard.html")
DASHBOARD_TEMPLATE = os.path.join(HERE, "dashboard_template.html")
PALETTE_SLOTS = 8  # categorical colors in the template; a ninth project folds into Other


def dashboard_projects(profile, labels, records):
    """Projects in a fixed order, each with its color slot, so a project keeps its color run to run.

    Client projects in profile order, then the internal project, then anything
    the records name that the profile does not. Returns (projects, fold) where
    fold maps a label past the last slot to "Other".
    """
    ordered = []
    for p in profile.get("projects", []):
        ordered.append({"label": p.get("label") or p["name"][:24], "name": p["name"], "kind": "client"})
    internal = profile.get("internal", {})
    if internal.get("name"):
        ordered.append({"label": "Internal", "name": internal["name"], "kind": "internal"})
    known = {p["label"] for p in ordered}
    for r in records:
        name = r["TASKRAY__Project__r"]["Name"]
        label = shorten(name, labels)
        if label not in known:
            ordered.append({"label": label, "name": name, "kind": "other"})
            known.add(label)
    fold = {}
    if len(ordered) > PALETTE_SLOTS:
        for p in ordered[PALETTE_SLOTS - 1:]:
            fold[p["label"]] = "Other"
        ordered = ordered[:PALETTE_SLOTS - 1] + [{"label": "Other", "name": "Other projects", "kind": "other"}]
    for i, p in enumerate(ordered, 1):
        p["slot"] = i
    return ordered, fold


def write_dashboard(path, profile, labels, records, alloc_days, start, end, label, today):
    """Write a self-contained HTML dashboard for the period and return its path."""
    projects, fold = dashboard_projects(profile, labels, records)
    rows = []
    for r in records:
        proj = shorten(r["TASKRAY__Project__r"]["Name"], labels)
        rows.append({
            "d": r["TASKRAY__Date__c"],
            "p": fold.get(proj, proj),
            "a": r["Activity_Type__c"] or "(none)",
            "h": r["TASKRAY__Hours__c"] or 0,
            "b": bool(r["TASKRAY__Billable__c"]),
        })
    holidays = {d: n for d, n in profile.get("holidays", {}).items()
                if start.isoformat() <= d <= end.isoformat()}
    now = dt.datetime.now()
    data = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "label": label,
        "today": today.isoformat(),
        "generated": f"{day_label(now)}, {now.year} at {clock(now)}",
        "org": profile["org_alias"],
        "baselinePerDay": profile.get("baseline_hours_per_week", 40) / 5,
        "projects": projects,
        "records": rows,
        "holidays": holidays,
        "allocDaily": alloc_days,
        "hasAlloc": allocations_enabled(profile),
    }
    with open(DASHBOARD_TEMPLATE, encoding="utf-8") as fh:
        html = fh.read()
    # "</" inside the JSON would end the script block early; escape it.
    payload = json.dumps(data).replace("</", "<\\/")
    html = html.replace("/*__DATA__*/null", payload, 1)
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


DATA_HOME = os.path.expanduser("~/.claude/kicksaw-time/dashboard-data")


def export_window(profile, today):
    """Time records from the profile's dashboard.since (default: the first of the month two months back)
    through today; allocation through the end of the sixth month ahead, so upcoming staffing shows."""
    since = (profile.get("dashboard") or {}).get("since")
    if since:
        start = dt.date.fromisoformat(since)
    else:
        start = (today.replace(day=1) - dt.timedelta(days=40)).replace(day=1)
    ahead = today.replace(day=1)
    for _ in range(6):
        ahead = month_end(ahead) + dt.timedelta(days=1)
    return start, month_end(ahead)


def write_data(out_dir, profile, labels, today):
    """Write the four JSON files a published dashboard reads, and return (out_dir, ignored).

    time-records.json  one row per time record: date, project, activity, hours, billable
    allocation.json    Resource Hero forecast per day per label, inside assignment dates
    days-off.json      the profile's holidays
    run-info.json      the window, the baseline, and any forecast left out
    """
    start, alloc_end = export_window(profile, today)
    records = fetch(profile, start, today)
    rows = sorted(({
        "date": r["TASKRAY__Date__c"],
        "project": shorten(r["TASKRAY__Project__r"]["Name"], labels),
        "activity": r["Activity_Type__c"] or "(none)",
        "hours": r["TASKRAY__Hours__c"] or 0,
        "billable": bool(r["TASKRAY__Billable__c"]),
    } for r in records), key=lambda r: (r["date"], r["project"]))
    ignored = []
    alloc = fetch_allocation_days(profile, start.isoformat(), alloc_end.isoformat(), ignored)
    alloc_rows = sorted(({"date": d, "project": label, "hours": round(h, 2)}
                         for label, per_day in alloc.items() for d, h in per_day.items()),
                        key=lambda r: (r["date"], r["project"]))
    days_off = [{"date": d, "reason": n} for d, n in sorted(profile.get("holidays", {}).items())]
    info = [{
        "start": start.isoformat(),
        "as_of": today.isoformat(),
        "through": (today - dt.timedelta(days=1)).isoformat(),
        "baseline_hours_per_day": profile.get("baseline_hours_per_week", 40) / 5,
        "org": profile["org_alias"],
        "forecast_left_out": [{"project": o["label"], "hours": o["hours"], "from": o["first"], "to": o["last"],
                               "assignment_start": o["start"], "assignment_end": o["end"]} for o in ignored],
    }]
    out_dir = os.path.expanduser(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    for name, data in [("time-records.json", rows), ("allocation.json", alloc_rows),
                       ("days-off.json", days_off), ("run-info.json", info)]:
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    return out_dir, ignored


def bar(value, peak, width=22):
    if peak <= 0:
        return ""
    return "█" * max(1, round(value / peak * width))


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("period", nargs="*", default=["week"])
    ap.add_argument("--by-day", action="store_true")
    ap.add_argument("--profile", default=None)
    ap.add_argument("--dashboard", nargs="?", const=DASHBOARD_HOME, default=None, metavar="PATH",
                    help=f"also write an HTML dashboard (default {DASHBOARD_HOME})")
    ap.add_argument("--export-data", nargs="?", const=DATA_HOME, default=None, metavar="DIR",
                    help=f"only write the JSON files a published dashboard reads (default {DATA_HOME})")
    args = ap.parse_args()

    profile = load_profile(args.profile)
    labels = label_map(profile)
    holidays = profile.get("holidays", {})
    today = dt.date.today()

    if args.export_data:
        out_dir, ignored = write_data(args.export_data, profile, labels, today)
        print(f"Dashboard data written: {out_dir}")
        for name in ("time-records.json", "allocation.json", "days-off.json", "run-info.json"):
            print(f"  {os.path.join(out_dir, name)}")
        print_ignored(ignored)
        return

    start, end, label = resolve(args.period)
    records = fetch(profile, start, end)
    ignored = []
    alloc_days = fetch_allocation_days(profile, start.isoformat(), end.isoformat(), ignored)

    if args.dashboard:
        out = write_dashboard(args.dashboard, profile, labels, records, alloc_days, start, end, label, today)
        print(f"\nDashboard written: {out}\n  {file_link(out)}")

    if not records:
        print(f"\n{label}  ({start} to {end})\n\nNo time logged.\n")
        return

    grid = defaultdict(float)
    per_project = defaultdict(float)
    per_activity = defaultdict(float)
    per_day = defaultdict(float)
    billable = defaultdict(float)

    for r in records:
        proj = shorten(r["TASKRAY__Project__r"]["Name"], labels)
        act = r["Activity_Type__c"] or "(none)"
        hrs = r["TASKRAY__Hours__c"] or 0
        grid[(proj, act)] += hrs
        per_project[proj] += hrs
        per_activity[act] += hrs
        per_day[r["TASKRAY__Date__c"]] += hrs
        billable[bool(r["TASKRAY__Billable__c"])] += hrs

    total = sum(per_project.values())
    projects = sorted(per_project, key=lambda p: -per_project[p])
    activities = sorted(per_activity, key=lambda a: -per_activity[a])

    print(f"\n{label}   {start} to {end}")
    print(f"{total:g} hours logged across {len(records)} records")

    expected, hit = expected_hours(profile, start, end, today)
    holiday_hours = sum(per_day.get(d.isoformat(), 0) for d, _ in hit)
    if expected:
        delta = total - holiday_hours - expected
        sign = "+" if delta >= 0 else ""
        line = f"Expected {expected:g}h through today, {sign}{delta:g}h"
        if hit:
            names = ", ".join(f"{day_label(d)} {n}" for d, n in hit)
            line += f"   (holidays out of baseline: {names}"
            line += f"; {holiday_hours:g}h logged on them is on top)" if holiday_hours else ")"
        print(line)
    print()

    wp = max(len(p) for p in projects + ["Project"]) + 2
    wa = [max(len(a), 7) + 2 for a in activities]
    header = "Project".ljust(wp) + "".join(a.rjust(w) for a, w in zip(activities, wa)) + "Total".rjust(9)
    print(header)
    print("-" * len(header))
    for p in projects:
        row = p.ljust(wp)
        for a, w in zip(activities, wa):
            v = grid.get((p, a), 0)
            row += (f"{v:g}" if v else "-").rjust(w)
        row += f"{per_project[p]:g}".rjust(9)
        print(row)
    print("-" * len(header))
    footer = "Total".ljust(wp) + "".join(f"{per_activity[a]:g}".rjust(w) for a, w in zip(activities, wa))
    print(footer + f"{total:g}".rjust(9))

    print()
    peak = max(per_project.values())
    for p in projects:
        h = per_project[p]
        print(f"  {p.ljust(wp)}{h:>6g}h  {h/total*100:4.0f}%  {bar(h, peak)}")

    nb = billable.get(False, 0)
    if nb:
        print(f"\n  Billable {billable.get(True, 0):g}h   Non-billable {nb:g}h")

    # Time off is staffing, not work to log against, so it stays out of the comparison.
    allocated = {l: sum(per_day.values()) for l, per_day in alloc_days.items() if l != TIME_OFF}
    if allocated:
        client_labels = {cp["label"] for cp in profile["projects"]}
        shown = sorted(allocated, key=lambda l: -allocated[l])
        # A client project with hours but no assignment row is unstaffed, not an error.
        unstaffed = sorted(l for l in per_project if l in client_labels and l not in allocated)
        wl = max(len(l) for l in shown + unstaffed) + 2
        print("\n  Against allocation")
        for l in shown:
            logged = per_project.get(l, 0)
            delta = logged - allocated[l]
            sign = "+" if delta >= 0 else ""
            print(f"  {l.ljust(wl)}{logged:>6g}h logged /{allocated[l]:>5g}h allocated   {sign}{delta:g}h")
        for l in unstaffed:
            print(f"  {l.ljust(wl)}{per_project[l]:>6g}h logged / no allocation")
    print_ignored(ignored)

    if args.by_day:
        print("\nBy day")
        cur = start
        while cur <= end:
            key = cur.isoformat()
            h = per_day.get(key, 0)
            tag = ""
            if key in holidays:
                tag = f"  holiday: {holidays[key]}"
            elif cur.weekday() >= 5 and h:
                tag = "  weekend"
            print(f"  {day_label(cur)}  {h:>6g}h{tag}" if h else f"  {day_label(cur)}       -{tag}")
            cur += dt.timedelta(days=1)
    print()


if __name__ == "__main__":
    main()
