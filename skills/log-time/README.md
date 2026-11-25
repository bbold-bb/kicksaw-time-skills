# log-time

Reconstructs work you did but never logged, from your Google Calendar, the local evidence on your machine, and the Slack messages you sent, then creates TaskRay time records in the Kicksaw org. It proposes first and writes nothing until you approve.

## What it does on a run

1. Loads your profile. On the first run it walks you through setup instead (see below).
2. Checks the org for drift: a time-entry task that was archived, or a project that closed. Fixes it with you before going further.
3. Finds where your logging left off and builds every day from there through today.
4. Reads your calendar for those days and finds the gaps.
5. Fills the gaps from evidence: your Claude Code session transcripts and git commits, attributed to projects by folder, and the Slack messages you sent, attributed by channel. Where your meetings are recorded in Notion or Wispr Flow, the summaries make the notes specific; they never change hours. Overlapping work may share the calendar, but every minute is booked once on the time records.
6. Shows one proposal: calendar events to add, time records to create, the judgment calls, and the gaps it could not explain. Then it stops.
7. After you approve, writes the calendar events and the time records, one at a time, and verifies them.
8. Refreshes your dashboards: the local time dashboard for the week, and, if your profile names one under `dashboard.artifact_url`, your published claude.ai dashboard, in the background so you are not kept waiting.

## First run

Say `/log-time`. Setup is mostly clicks. It reads what it can from the org and your connectors: your user, Flux resource, timezone, and the projects you are staffed on in Resource Hero or logged to in the last 90 days. You tick the ones to log against. It offers the folders that hold your repos and the Slack channels that match each project, and you tick those too (every channel is resolved live before it is saved, and the skill never posts to Slack). Then it asks how you work and where your meetings are recorded, so unclear time and gaps are handled the way your job works. Last, you pick your work hours and save. Folders and channels it can't place are asked about later, on the first run that finds work in them. It saves `~/.claude/kicksaw-time/profile.json` and shows it back to you. Every field can be edited by hand.

Every 30 days it shows your projects again for you to confirm. It asks sooner when the org disagrees with your profile or when a folder with activity is not mapped to anything.

## Prerequisites

- Salesforce CLI (`sf`) logged in to the Kicksaw org
- A Google Calendar connector on your Kicksaw account
- Recommended: a Slack connector on the Kicksaw workspace, read-only in practice because the skill never posts
- Optional: a Notion or Wispr Flow connector, if your meetings are recorded there
- Claude Code transcripts or local git repos, if you want gaps reconstructed rather than described

## Files

| File | Purpose |
| --- | --- |
| `SKILL.md` | The process Claude follows. Read it to know exactly what it will and will not do |
| `reference/taskray.md` | Org-wide record types, picklists, queries, and the insert payload |
| `reference/meetings.md` | Which meeting recorders the skill reads, and how |
| `profile.example.json` | The shape of your profile |
| `~/.claude/kicksaw-time/profile.json` | Yours. Created by setup, stored outside this folder so updates cannot replace it. Never share it |

## Install

Install globally with the Skills CLI:

```
npx skills add bbold-bb/kicksaw-time-skills --agent claude-code --global --skill '*'
```

`--skill '*'` takes both skills on purpose: `time-report` reads the profile this skill creates, so the two are installed and updated as a pair. Keep `--agent claude-code`, because the agent is not named `claude` and leaving the flag off installs into every agent directory the CLI knows.

Run the same command without `--global` to install into the current project instead. Either way the profile stays in your home directory, so one profile serves every project.

Update with `npx skills update`. For Cowork, offline installs, and the rest of the detail, see the [repo README](https://github.com/bbold-bb/kicksaw-time-skills#install).

Pairs with the `time-report` skill, which reads the same profile and reports what is already logged.
