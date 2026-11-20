# time-report

Reports the time you have already logged in TaskRay, by project and activity type, against a weekly baseline with holidays taken out. Read-only. It never writes to Salesforce or your calendar.

## What it does

Say `/time-report` for the current week, or give it a period: `last-week`, `month`, `last-month`, a month like `2026-09`, a single day, or a start and end date. Claude runs `time_report.py`, prints the table, and adds a short reading: total against expected, where the hours concentrated, which weekdays look thin or empty, and anything that looks wrong.

Add `--dashboard` (or ask for a dashboard) to also get an HTML page with charts: totals for the period, and an over-time view that breaks a month into weeks so you can see how your allocation changed week to week. It is written to `~/.claude/kicksaw-time/time-dashboard.html` and opened in your browser.

If you keep a published dashboard on claude.ai, put its link in your profile as `dashboard.artifact_url`. `log-time` refreshes it after every run that writes time records, and `time_report.py --export-data` writes the four data files it reads.

Allocation counts every Resource Hero assignment you have, but only forecast dated inside each assignment's start and end dates. Forecast outside those dates is listed under *Forecast left out*, so it can be fixed in Resource Hero. Name an assignment the profile does not cover in `resource_hero.assignment_labels`.

Expected hours are your weekly baseline spread over the weekdays that have already passed, minus any holiday in the period. Hours you worked on a holiday count in the total but never against you.

## Profile

The script reads the `profile.json` that the `log-time` skill creates, for your org alias, username, project labels, holidays, and baseline. It looks in `~/.claude/kicksaw-time/profile.json` first, then in the older locations inside the skill folders. If you have not run `log-time` yet, do that once, or pass `--profile PATH`.

Holidays live in the profile's `holidays` map. Add one when you confirm it; the skill will not assume a light day was a holiday.

## Prerequisites

- Salesforce CLI (`sf`) logged in to the Kicksaw org
- Python 3
- A profile from `log-time`

## Files

| File | Purpose |
| --- | --- |
| `SKILL.md` | How Claude runs the script and what it says back |
| `time_report.py` | The report script |
| `dashboard_template.html` | The page `--dashboard` fills in with the period's data |

## Install

Install globally with the Skills CLI:

```
npx skills add bbold-bb/kicksaw-time-skills --agent claude-code --global --skill '*'
```

Do not install this one alone. It reads the profile `log-time` creates, so `--skill '*'` takes both skills and `npx skills update` keeps them in step. Keep `--agent claude-code`, because the agent is not named `claude` and leaving the flag off installs into every agent directory the CLI knows.

Run the same command without `--global` to install into the current project instead. The profile lives in your home directory either way, so one profile serves every project.

For Cowork, offline installs, and the rest of the detail, see the [repo README](https://github.com/bbold-bb/kicksaw-time-skills#install).
