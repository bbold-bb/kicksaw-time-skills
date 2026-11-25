# Changelog

The skills share one version number. log-time and time-report share a profile and are meant to be installed together.

**To see which version you have installed**, read the `version:` line at the top of your installed `SKILL.md`:

```
head -3 ~/.claude/skills/log-time/SKILL.md
```

If it is behind the latest below, update with `npx skills update`. For manual copy-based installs, copying is a snapshot, so `git pull` alone does not update an installed skill.

## 1.20.2 (2026-11-25)

- **No zero or blank time records.** log-time runs `check_record.py` on every payload before writing it: hours must be more than zero and in quarter hours, and the project, task, date, owner, record type, time type, Activity Type, billable flag and notes must all be filled (plus category and non-billable reason on internal time). A record that doesn't pass isn't written; the run asks for the missing value.
- **The hourly rate is left to the org.** log-time used to send 0, which the org replaced. It no longer sends it.

## 1.20.1 (2026-11-25)

- **Flux is no longer needed.** Setup doesn't look for a Flux resource, and a missing one no longer stops it. Time records are written without a Flux resource or a service line; the org sets the service line from the user's own record, as it does for records entered by hand. Older profiles keep their old fields, which are ignored.

## 1.20.0 (2026-11-25)

- **Setup asks how you work.** Short pop-ups cover what fills your week, what takes time but leaves no trace, how much goes through Claude, and where your meetings are recorded, plus which project any unlabeled recurring meetings belong to. Answers are saved as `work` in the profile (recurring meetings in `conventions`). Existing profiles are asked once, on the next run.
- **Unclear blocks fit the person.** A client block whose evidence doesn't settle its Activity Type takes `work.unclear_activity_type`: Communications for someone who manages projects, Documentation for someone who mostly writes, Coding and Configuration otherwise.
- **Meeting recordings make notes specific.** log-time reads the summary of a Notion or Wispr Flow recording that matches a work meeting. The topics follow the meeting's title in its note. A recording never changes hours and never proves attendance. A tool that also holds personal recordings needs a matching time and a matching title or attendee before anything is opened, and its other recordings are never shown. tl;dv, Zoom, ZoomInfo (Chorus) and Plaud are saved but not read yet. See `skills/log-time/reference/meetings.md`.
- **Older profiles get their allowed Activity Types.** A profile from before 1.17.0 has the org's picklist values read and saved on its next run.

## 1.19.4 (2026-11-21)

- **Pipeline staffing is no longer counted as allocation.** A Resource Hero assignment on an Opportunity, rather than on a project, is staffing for a deal that has no project yet. time-report used to add its forecast to allocation, which could count the same hours twice once the project had its own assignment. It now lists that forecast on its own line, *Pipeline staffing*, and leaves it out of allocation, pace and the published dashboard's data (`run-info.json` carries it as `pipeline_left_out`).

## 1.19.3 (2026-11-20)

- **Google Tasks from a screenshot.** A Tasks user can paste a screenshot of their calendar with tasks showing; log-time reads each task's title, day and time and proposes it as an event in the matching gap.
- **Guide header.** The shared guide has a navy header with the name and larger Get started and What's new tabs.

## 1.19.2 (2026-11-20)

- **A color for each new project.** When someone who color-codes their calendar adds a project later (at the 30-day check, from evidence drift, or on request), log-time asks its color, offering colors no other project uses. Saved as `rhythm.color_codes` and the project's `color_id`.
- **Google Tasks wording.** Setup no longer tells people Tasks can't be read. A Tasks user is asked, when unaccounted time is listed, whether any of it was a task.

## 1.19.1 (2026-11-20)

- **Existing profiles answer the new questions once.** A profile saved before 1.19.0 is asked about calendar colors, Google Tasks and the timezone once, on its next run. The 30-day profile check is unchanged.

## 1.19.0 (2026-11-20)

Changes from the first two teammate setups, one on Windows.

- **Two approvals, calendar first.** log-time proposes the calendar events, writes them once approved, and waits for the user to check their calendar before it proposes time records. Both proposals follow fixed templates, so every user sees the same layout.
- **Records are written exactly as approved.** Nothing is recomputed between the approval and the insert; any change is shown and asked again. Progress prints while records go in.
- **Setup asks for the timezone**, defaulting to the computer's, not the Salesforce user setting. It also asks whether the user color-codes projects (new events get the project's color, and colors help place events) and whether they use Google Tasks, which the calendar connector can't see.
- **Plainer setup questions.** Labels, the internal project and multiple live tasks each get a one-line reason.
- **An old last record asks for a range.** When the last record is more than 14 days back, log-time asks where to start.
- **Dashboards.** After a run, the local dashboard opens in the system browser, and the link to My Hours - Dashboard 2.0 in Salesforce is given. time-report does the same.
- **Sign-in on the Kicksaw domain.** SETUP.md signs in at kicksaw.my.salesforce.com and tells the user to use the tab that opens.
- **Docs.** The README opens with the install line for agents, so pasting the repo link starts guided setup. The README and the guide add "How a run goes" and where the Code tab is.

## 1.18.0 (2026-11-20)

**Guided setup.** Paste one line into Claude desktop's Code tab or Codex and the agent sets everything up, on a Mac or on Windows:

```
Download https://raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/main/SETUP.md with your shell, read all of it, and follow it to set up the Kicksaw time skills.
```

- **`SETUP.md`** is what the agent follows. It checks what's already set up, asks once before installing anything, installs the skills, the Salesforce CLI and Python from their official sources, opens the browser to sign in to the Kicksaw org, shows where to connect Calendar and Slack, and starts log-time's setup. It coaches you through the app's approval prompts and never asks for a password. Pasting the line again updates or repairs a setup.
- **Windows support.** time-report finds the Salesforce CLI the way Windows needs, reads its output as UTF-8, prints dates Windows can format, and gives dashboard links that open on both systems. Both skills give the Python and "open the dashboard" commands for each system. log-time matches session history and git folders on Windows paths too.
- **log-time preflight.** If the Salesforce CLI is missing or your sign-in expired, log-time offers to fix it with the matching `SETUP.md` step instead of printing a command.
- The README and guide lead with the setup line. `npx` and `install.sh` stay, under *For technical users*.

## Public repo (2026-11-19, repo only)

No skill changes, so the skill version stays 1.17.0.

- The skills now live in a public repo, `bbold-bb/kicksaw-time-skills`. Install commands and links point there, and the guide no longer lists GitHub access as a requirement or carries a copyright line.

## 1.17.0 (2026-11-19)

**For one person managing their own time.** The skills now cover only your own time: log-time writes your records, time-report reports on them.

- **Removed: team-time** (the team time check and teammate profiles) and log-time's *log time for a teammate* path, with their tests and design notes.
- **Examples and test data use made-up people and companies.** No real names, emails, record Ids or client details are in the repo.
- **Setup reads more from the org.** The internal project is found by its Internal type, not its name; a project's time-entry task is its one open task, whatever it's called; record type Ids are looked up by name; and the allowed Activity Types and other picklist values are read for each record type and saved in the profile as `picklists`. Re-run setup, or let the first run fill `picklists` in.

## README how it works, guide covers Codex (2026-11-17, repo only)

No skill changes, so the skill version stays 1.16.0.

- The README now opens with the two skills, what each does, and a *How it works* diagram that GitHub renders on the repo page, followed by what the skills will and won't do.
- `docs/time-skills-guide.html` covers Codex: install commands, `$log-time`, the shared profile, and the Codex version path when checking for updates.

## Codex support (2026-11-16, repo only)

No skill changes, so the skill version stays 1.16.0.

- `install.sh --codex` installs into `~/.agents/skills`, where Codex looks for skills (`--project PATH` uses `PATH/.agents/skills`, and `--check` works with it). Verified with Codex CLI 0.169, which lists both skills.
- `AGENTS.md` gives Codex and other coding agents the repo's rules: layout, release and versioning, tests, and what never gets committed.
- The README's new *Codex* section covers install and what differs from Claude Code.

## 1.16.0 (2026-11-13)

**Simpler first-run setup (log-time).** Setup now infers what it can and asks with clickable options instead of typed answers:

- Projects come from the user's Resource Hero assignments and the projects they logged to in the last 90 days, shown as one multi-select to confirm. "Other" takes a client name.
- Labels default to the client name and are only asked about when two would clash.
- Timezone comes from Salesforce, and the calendar from the org username.
- Repo folders are offered as a multi-select. Folders are mapped to projects by name; the rest are asked about on the first run that finds work in them.
- Slack channels that match each project are offered per project as a multi-select. Other channels are asked about on the first run that finds a message in them.
- Work hours are one click, with 9 to 5 as the default.

Every question in setup, drift, and the proposal now uses the option pop-up, with "Other" for anything the options miss.

**Removed: the morning-prep project.** Setup no longer asks which project morning prep and unlabelled admin default to, the `primary` flag is gone from the profile, and the standing rule that booked that time to it is removed. Unclear prep or admin time is asked about in the proposal like any other unclear block. Anyone who wants the old behavior can add it to their own `conventions`.

time-report is unchanged; its version moves because the skills share one number.

## 1.15.0 (2026-10-29)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.14.0 (2026-10-29)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.13.0 (2026-10-29)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.12.0 (2026-10-29)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.11.0 (2026-10-28)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.10.0 (2026-10-28)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.9.0 (2026-10-28)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.8.0 (2026-10-27)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.7.0 (2026-10-26)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.6.0 (2026-10-26)

Team-time and teammate logging only. Those were removed from this repo in 1.17.0.

## 1.5.0 (2026-10-23)

**log-time refreshes your dashboards after it writes time records.** A new Step 8 regenerates the local time dashboard for the week. If your profile has `dashboard.artifact_url`, a background agent also refreshes your published claude.ai dashboard, so you do not have to wait for a report run.

- **`time_report.py --export-data`** writes the four JSON files a published dashboard reads (time records, allocation, days off, run info) to `~/.claude/kicksaw-time/dashboard-data/`. Its window runs from the profile's `dashboard.since` through today, with allocation six months ahead.
- **Allocation covers every Resource Hero assignment you have**, not only the ones your profile projects name. Holiday and PTO assignments show as Time off and are never compared with logged hours. `resource_hero.assignment_labels` names an assignment the profile does not cover.
- **Forecast dated outside its assignment's start and end dates is left out**, and the text report lists it under *Forecast left out* so it can be fixed in Resource Hero.

## 1.4.0 (2026-10-10)

**time-report can draw a dashboard.** Add `--dashboard` (or ask `/time-report` for a dashboard) and it writes an HTML page next to the usual text report, then opens it.

- **Totals view**: hours logged, pace against expected, billable share, client allocation used, hours by day, logged against allocation per client project, hours by project and activity type, and the project split.
- **Over time view**: a month breaks into weeks, a week into days. Each client project gets a chart of hours logged against allocation, with the allocation as a share of a full-time week, and a table adds every client allocation together so a week staffed at 10% next to one at 80% stands out. Weeks still ahead show their allocation.

The page goes to `~/.claude/kicksaw-time/time-dashboard.html` by default, beside the profile and outside the skill folders. Allocations now come from Resource Hero per day, so the text report and the page share one query. log-time is unchanged; its version moves with time-report because the two share one number.

## 1.3.0 (2026-09-18)

**Installing is now one command, and it is the one the team already uses.**

```
npx skills add bbold-bb/kicksaw-time-skills --agent claude-code --global --skill '*'
```

The two skills moved under `skills/`, which is the layout the Skills CLI expects. Nothing inside either skill changed. Updating is `npx skills update`.

Keep `--agent claude-code` in the command. The agent is not named `claude`, and leaving the flag off installs into every agent directory the CLI knows (over fifty folders).

`install.sh` still works and is still the right choice with no npm, offline, or when migrating a profile from 1.1.0 or earlier.

## 1.2.0 (2026-09-18)

**The profile moved out of the skill folder.** It now lives at `~/.claude/kicksaw-time/profile.json`.

It used to sit inside `log-time/`, which is a folder an installer replaces. That made every update a chance to delete your org Ids, project mapping, channel map and conventions, and it is why `install.sh` had to carry the file across by hand. User data does not belong inside a package. Moving it also means one profile serves every project rather than one per project install.

Nothing is required of you: `./install.sh` moves an existing profile to the new location, and both skills read the old paths meanwhile and tell you to move it.

## Unreleased

- **`install.sh`** installs or updates both skills, preserving your `profile.json`. Updating by hand was a trap: copying onto an existing folder nested it instead of replacing it, and replacing it took the profile with it. `--check` compares your install against the repo; `--project PATH` installs into one project. The skills themselves were unchanged, so this shipped under 1.1.0.

## 1.1.0 (2026-09-18)

**Fixed a silent failure. Update if you are on 1.0.0.**

- **Evidence folders match by path, not by bare folder name.** A `directories` entry of `Northwind_Health` matched no transcript folder at all, because Claude Code encodes every non-alphanumeric character as a hyphen (`-Northwind-Health`). The project went unmapped and its hours never appeared, with nothing in the run to say so. Any folder name containing an underscore, a space or a dot was affected. Entries are now paths (`~/Desktop/Work/Client_A`); bare names still work, so existing profiles keep running until they are next verified.
- **Slack is now an evidence source**, read-only. Gaps are reconstructed from the messages you sent, attributed by channel. The skill never posts, and no channel enters the profile without being resolved live and placed by you. Optional: without a connector, setup saves Slack as off and every run says so.
- **Multitasking has a defined answer.** The calendar may show overlapping work, because it records how the day was actually spent. Time records may not: every minute is booked once and a fixed precedence decides which source wins the slot.
- **The time report compares logged hours to your Resource Hero allocation**, per project, so a week that totals 40 hours on the wrong split is visible. Opt in with `resource_hero.use_for_allocations`. Actuals always come from TaskRay; Resource Hero's own actuals lag by days.
- **Calendar times are not shifted twice.** The connector returns each `dateTime` already converted into the requested timezone while leaving the event's original `timeZone` label in place. Treating the label as the offset moved meetings booked in other timezones by hours.

## 1.0.0 (2026-09-15)

Initial release: `log-time` reconstructs unlogged work from the calendar, session transcripts and git history, then writes TaskRay time records after approval. `time-report` reports what is already logged against a weekly baseline.
