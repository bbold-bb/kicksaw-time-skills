---
name: time-report
version: 1.19.3
description: Use when a Kicksaw consultant asks how much time they have logged, whether they are on pace for the week or month, or which projects their hours went to. Read-only; pairs with log-time, which writes.
argument-hint: "[week | last-week | month | last-month | YYYY-MM | YYYY-MM-DD | start end] [--dashboard] (default: week)"
---

# Time report

Report the time the user has already logged in TaskRay, broken out by project and activity type. Read-only; this never writes to Salesforce or the calendar.

Requested period: `$ARGUMENTS` (if empty, default to the current week).

## Profile

The script reads the same `profile.json` that the log-time skill creates, for the org alias, username, project labels, holidays, and weekly baseline. It looks in `~/.claude/kicksaw-time/profile.json` first, then in the legacy locations inside the skill folders. The profile lives outside the skill folders so that updating a skill cannot replace it; when the script reports finding one in a legacy path, tell the user to move it. If none exists, tell the user to run log-time once (its setup creates the profile) or to pass `--profile PATH`. Do not build a report from guessed values.

## Run it

```
python3 <this folder>/time_report.py <period> [--by-day] [--dashboard [PATH]] [--profile PATH]
python3 <this folder>/time_report.py --export-data [DIR] [--profile PATH]
```

Run Python as python3 on a Mac, and as py -3 on Windows (or python if that is the one that prints a Python 3 version).

Accepted periods:

| Argument | Meaning |
| --- | --- |
| `week` | current week, Monday through Sunday (the default) |
| `last-week` | previous Monday through Sunday |
| `month` | current calendar month |
| `last-month` | previous calendar month |
| `2026-09` | that named month |
| `2026-09-02 2026-09-08` | explicit inclusive range |
| `2026-09-04` | that single day |

Add `--by-day` whenever the user asks for a week, or any time the shape of the days matters. Skip it on a full month unless asked, since 30 rows buries the summary.

Add `--dashboard` whenever the user asks for a dashboard, a chart, or to see it visually. See *Dashboard* below.

## Dashboard

`--dashboard` also writes a self-contained HTML page for the period, to `~/.claude/kicksaw-time/time-dashboard.html` unless a path follows the flag. The script prints the path and a `file://` link. Open it for the user in their system browser, not a browser inside the agent app (`open "<path>"` on a Mac; on Windows, `Start-Process "<path>"` in PowerShell or `start "" "<path>"` in cmd or Git Bash), and give them the link. Also give the link to the company's Salesforce view of the same records, *My Hours - Dashboard 2.0*, found with the *time dashboard* query in log-time's `reference/taskray.md` and built as `<instanceUrl>/lightning/r/Dashboard/<Id>/view` (the `instanceUrl` comes from `sf org display -o <alias> --json`); leave it out if the query finds nothing.

The page has two views, toggled at the top:

- **Totals**: hours logged, pace against expected, billable share, client allocation used, hours by day, logged against allocation per client project (with a pace marker when the period is part done), hours by project and activity type, the project split, and a day-by-day table.
- **Over time**: week by week for anything longer than seven days (Monday to Sunday, the first and last weeks trimmed to the period), day by day for a week. Hours per week by project against expected, then one chart per client project of hours logged against allocation, with the allocation as a share of a full-time week. The table's last column adds every client allocation together, which is where a jump from 10% to 80% staffed shows up. Weeks still ahead show their allocation as upcoming.

The page reads the same records and Resource Hero forecast as the text report, so its numbers match it. It is a snapshot; rerun to refresh. Colors follow project order in the profile, so a project keeps its color from run to run. Still print and read the text report as usual; the dashboard is in addition, not instead. log-time also regenerates this page for the current week after it writes time records.

## Published dashboard

Some users also keep a published dashboard on claude.ai, a Dashboard artifact whose profile entry is `dashboard.artifact_url`. It reads four uploaded JSON files, not the HTML page above. log-time refreshes it in the background after every run that writes records; refresh it here only when the user asks. Without `dashboard.artifact_url` in the profile, there is nothing to refresh: say so, and do not create an artifact unasked.

`--export-data` writes the four files to `~/.claude/kicksaw-time/dashboard-data/` unless a directory follows the flag. It ignores the period: time records run from the profile's `dashboard.since` (default, the first of the month two months back) through today, and allocation runs six months ahead so upcoming staffing shows.

| File | Dataset id | Rows |
| --- | --- | --- |
| `time-records.json` | `time_records` | date, project, activity, hours, billable |
| `allocation.json` | `allocation` | date, project, hours of Resource Hero forecast |
| `days-off.json` | `days_off` | date, reason, from the profile's holidays |
| `run-info.json` | `run_info` | the window, the baseline, and any forecast left out |

To refresh it:

1. Run `--export-data`.
2. Read the artifact with the Artifact tool (`action: "read"`), then list its `datasets` collection with ArtifactData. Each dataset document holds a `source` (`kind: "file"`, `url`, `name`, `format`) and a `version`. If the four dataset ids above are not there, stop and tell the user; this procedure updates an existing dashboard and never builds one.
3. Upload each file to the artifact as an asset (Artifact `publish` with `url`, `asset: true`, `file_path`; one JSON file per call). Each upload returns a new `/_blob/<id>` url.
4. In one ArtifactData `batch`, `update` each dataset with `if_version` set to the version read in step 2: `source` with the new `url` (keep `kind`, `name` and `format`) and `updated: {at: <the output of date -u +%Y-%m-%dT%H:%M:%SZ>, by: "Claude for <user's name>"}`. Read the time from the clock; never estimate it.
5. Delete each replaced asset (Artifact `delete` with `url` and the old blob id as `path`), so uploads do not pile up.
6. Report one line: the artifact link, the window covered, and the forecast left out, if any.

## What to say back

Print the script's table, then add the reading. Do not just dump the output.

- **Report against allocation, not just the total.** When the profile has `resource_hero.use_for_allocations`, the script prints an *Against allocation* block: hours logged versus hours staffed, per project. The total tells them whether they worked a full week; this tells them whether they worked it on the right things. A project well under its allocation while another is well over is the finding, even when the total lands exactly on 40.
- **A client project with hours but no allocation** prints as `no allocation`. That means no Resource Hero forecast inside an assignment's dates covers the period. It usually means the staffing has not been set up yet or the engagement is winding down. Say it plainly and ask; never treat it as zero allocation and report a large overage.
- **Forecast left out.** Allocation counts every Resource Hero assignment the user has, archived ones included, but only forecast dated inside each assignment's start and end dates. Rows outside those dates are usually left over from an assignment whose dates moved. The script lists them under *Forecast left out*. Name them, say they were not counted, and offer to draft a note to whoever manages Resource Hero staffing (or the user's supervisor) asking for the dates or the forecast to be fixed.
- **Time off** (holiday and PTO assignments) is never compared with logged hours.

- **Lead with the total and how it compares** to the expected line the script prints. Expected is the profile's weekly baseline spread over the weekdays that have already passed, less every holiday in the period. Say whether they are ahead or behind.
- **Name the concentration.** One project at 90% is worth stating out loud, especially when they are staffed on several.
- **Flag the gaps.** Any weekday under 6 hours, and any weekday inside the period with nothing logged at all. That usually means unlogged work rather than a day off, which is the whole reason they ask. **Never flag a holiday as a gap.**
- **Flag anything that looks wrong**: a day over 12 hours, non-billable time on a client project, an activity type that does not normally appear on that project.

Keep it to a few lines. They are checking pace, not reading an analysis.

## Holidays

A holiday **drops out of the expected baseline entirely**. It does not lower the bar for the other days; it removes its own day from the period. A week with one holiday expects four days of hours, a week with two expects three.

People often work a little on a holiday anyway. **Those hours are bonus, not expected.** The script counts them in the logged total, excludes them from the comparison, and says so on the expected line. Never treat a light holiday as a shortfall.

The holiday list lives in the profile's `holidays` map and only grows when the user says so. If a weekday inside the period is empty or unusually light and is **not** in the list, do not assume it was a holiday. Report it as a gap and ask; if they confirm it was a holiday, add it to the profile and say you did.

## When the numbers look short

Logged time only reflects what has been written. If a recent day looks thin or missing, say so and offer log-time for that range rather than speculating about what they did. The two skills are a pair: this one reads, that one reconstructs and writes.
