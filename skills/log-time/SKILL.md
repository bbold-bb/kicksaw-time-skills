---
name: log-time
version: 1.17.0
description: Use when a Kicksaw consultant needs unlogged work reconstructed and entered as TaskRay time records, when they say "log my time", "fill in yesterday", or ask what they worked on for a date range, and on first use before any time record is written.
argument-hint: "[date | date range | 'yesterday' | 'today'] (default: from the last logged day before today through today)"
---

# Log time

Reconstruct what the user actually worked on, fill the gaps in their work calendar, and create TaskRay time records in the Kicksaw Salesforce org. **Propose first, write only after they approve.** Every run has judgment calls; never skip the review.

Requested scope: `$ARGUMENTS` (if empty, default to every day from **the date of the last time record** through **today**, inclusive of both ends).

The org queries, default picklist values, and the insert payload live in [reference/taskray.md](reference/taskray.md); record Ids are always looked up in the org, never stored in this repo. Everything about the individual user lives in `~/.claude/kicksaw-time/profile.json`.

## Ground rules

- The user's workday hours come from the profile. After-hours, evening, and weekend work counts equally and must be logged.
- Work goes in the calendar. **A gap usually means they worked and forgot to book it.**
- Never invent work. If there is no evidence for a gap, list it as unaccounted and ask.
- Don't update time records from prior days. If a date/project/activity already has one, **add another record**. Same-day corrections are the exception: a record created today can be merged in place (adjust hours, extend notes) instead of adding a duplicate in the same grouping.
- Reads in every other org, repo, and Slack stay read-only. Only the org named in the profile is written to, and only the time record object.
- **Slack is read-only for this skill, without exception.** It never sends, schedules, or drafts a message in any channel or DM, whether or not a client is in it.
- Nothing about Slack goes in the profile from a pasted Id, a name pattern, or a line in a repo's `CLAUDE.md`. Every channel is resolved live, shown, and confirmed by the user first (see *Channel matching*).

## Step 0: Load the profile, and set it up if it is missing

Read the profile from `~/.claude/kicksaw-time/profile.json`. If it is not there, look in the legacy locations (`profile.json` beside this file, then `~/.claude/skills/log-time/profile.json`); if it turns up in one of those, move it to the home location, say you did, and carry on. The profile is the user's data and lives outside the skill folder so that installing or updating a skill can never replace it. If it does not exist, or the user asks to reset it, run **Setup** below before anything else. If it exists, run the **org drift check** every time, and the **re-verification** when a trigger fires. Both finish before Step 1.

### Asking questions

The less the user types, the better. Every question in setup, drift, and the proposal's ambiguous calls goes through the option pop-up (`AskUserQuestion` in Claude Code), never as free text in chat:

- **Infer first, then offer.** Read the answer from the org, a connector, or the disk, and offer what was found as the options. Only ask when it cannot be inferred.
- **Multi-select** whenever more than one answer can be true (which projects, which channels, which folders). Single select otherwise, with the likely answer first and marked "(Recommended)".
- **Each option's description carries the evidence**: client, end date, where it was found, last logged date, message count.
- **"Other" is always there** (the pop-up adds it), so the user can type a name or a path the options missed.
- A pop-up holds up to four questions of up to four options each. With more candidates than fit, group them (assigned now, logged recently) across questions in one pop-up, then a second pop-up if needed. Only fall back to a numbered list when there are more than 16.
- In a client without the pop-up (Codex, for example), ask the same thing as a short numbered list and accept numbers as the answer.

### Setup (first run)

Setup asks as little as possible. What can be read is read; the user confirms it with a click. Do not write a time record during setup.

1. **Org.** Try `sf org display user -o Kicksaw-Prod --json` without asking. If it resolves, that is the org; `id` and `username` become `user.user_id` and `user.username`. If it fails, run `sf org list --json` and offer the logged-in aliases as options. If there are none, tell them to run `sf org login web -a Kicksaw-Prod` and stop setup until it succeeds. Never ask the user to type their own Id.
2. **Resource and timezone.** Query the Flux resource owned by that user (query in the reference). Save its Id and `DeliveryTeam__c`. If none is found, stop and tell them: time records need one, and someone in operations has to create it. Read the user's `TimeZoneSidKey` for `rhythm.timezone`, and the Resource Hero resource for `resource_hero.resource_id` (both in the reference). No question.
3. **Projects, inferred.** Gather candidates from the org, without asking first:
   - their current **Resource Hero assignments** that link to a TaskRay project (the *setup assignments* query in the Resource Hero reference);
   - the projects they **logged to in the last 90 days** (the *recent history* query).
   Drop any that are closed, completed, or archived, and drop the internal project (step 4 adds it). Show the rest in one **multi-select** pop-up: "These are the projects you're on. Pick the ones to log against." Each option is the project name; its description gives the client, the end date, and where it was found ("assigned through Dec 31", "logged 14 times, last Nov 3"). "Other" takes a client name: run the *active project* query for it and offer the matches as a follow-up pop-up. Zero client projects is a valid answer for someone new or on the bench.
   For each chosen project, resolve its live time-entry task with the *live task* query. Exactly one unarchived match is expected; if there are zero or several, offer them as options (the *live task rule*, used everywhere a task is resolved). `record_type` is `Client Work` for every client project. Save the Resource Hero assignment Id as `rh_assignment_id` when there is one.
   **Labels** default to the client's account name, shortened the obvious way ("Northwind Health Partners" becomes "Northwind"). Only ask when two projects would share a label, or a label holds a colon: then offer two suggestions per project, with "Other".
4. **Internal project.** Run the *internal project* query. One match: use it without asking. Several: one pop-up with the matches, each with its end date. Then resolve its live task the same way. Every user gets an internal project; it is not optional.
   **Allowed values.** Read the allowed picklist values for both record types (*allowed values* in the reference) and save them as `picklists`. Check that the fixed values the insert payload sets (time type, category, non-billable reason) are among them; if one isn't, stop and show the user the allowed values, because every insert would fail.
5. **Folders.** `transcript_root` is `~/.claude/projects` unless it does not exist. For `repo_roots`, look under the home folder, two levels down, for folders that hold git repos, and offer them as a **multi-select** (`~/Code`, `~/Projects`, and so on), with "Other" for a path. If none are found, save an empty list and move on.
   Then map folders to projects **without asking**: a repo or transcript folder whose path contains a project's label or client name goes in that project's `directories`. Discover repos as the immediate children of each root plus one level down (anything holding a `.git`). Discover transcript folders as those with a file modified in the last 90 days, and map each back to its real path by testing the path-encoded name against folders on disk; **the entry saved is always that real path**, written with `~` for the home folder, never a bare folder name. Everything else stays unmapped. It is asked about on the first run that finds work in it (*Evidence drift*), so nobody answers questions about folders they no longer use.
6. **Slack.** Confirm the Slack connector by searching for messages from the user in the last 30 days; the search tool reports the acting user's Id, which becomes `slack.user_id`. If the connector is not connected, say so, save `"slack": null`, and continue. Slack is an evidence source, not a gate, and every later run notes that it is missing.
   For each project, find its channels: a channel search across public and private channels using the account name and its obvious short forms, plus the channels the user posted in during the last 90 days whose name matches. **Verify every candidate live** (resolve the Id and read back the name, purpose, and the user's message count). Then one pop-up, one **multi-select** question per project: "Which of these channels are for <Label>?", each option a channel with its purpose and message count. A project with no candidates gets no question. Set `client_facing` to true for a `kicksaw_<client>` or `kicksaw-<client>` channel and false otherwise; the summary in step 8 shows it for correction.
   Every other channel stays unmapped and is asked about on the first run that finds the user posting in it. Group DMs and DMs are never mapped; they are attributed from content at run time (Step 3).
7. **Calendar.** `rhythm.calendar_account` is the org username. Confirm it by listing one day of that calendar. If that fails, offer the calendars the connector can see as options.
8. **Workday and save.** One last pop-up, two questions:
   - "What are your usual work hours?" Options: 9:00 to 5:00 (Recommended), 8:00 to 4:30, 8:30 to 5:00, with "Other" for anything else. They set `rhythm.workday_start` and `workday_end`. They only shape gap-finding; after-hours work is still logged.
   - "Save this profile?" Before it, show a short summary: projects with labels, mapped folders, mapped channels, calendar, timezone. Options: "Save it" (Recommended) and "Change something", where "Other" names the change.

`conventions` starts empty and grows only when the user states a rule during a run. Save the profile with `verified_on` set to today. Skip the drift check on a profile saved seconds ago, then continue into Step 1 with the scope the user originally asked for.

### Directory matching

A `directories` entry is the **working directory's path**, written with `~` for the home folder, as in `~/Desktop/Work/ClientA-Migration`. Paths survive being installed anywhere and on anyone's machine; bare folder names do not.

- **A repo** matches when its absolute path equals the entry's, after expanding `~`.
- **A transcript folder** matches when its name equals the entry's **encoded** form. Claude Code names each folder after the working directory with every character that is not a letter or a digit replaced by a hyphen, so `~/Desktop/Work/Client_A` becomes `-Users-name-Desktop-Work-Client-A`. Derive that name from the path at match time; never store it.

A folder that matches nothing is **unmapped**.

Bare folder names were the earlier rule and they fail on two ordinary cases:

- **Any folder whose name holds an underscore, a space, or a dot.** `Northwind_Health` encodes to `-Northwind-Health`, so an entry of `Northwind_Health` matched no transcript folder at all and the project went silently unmapped. Silently is the problem: the run looks clean and the hours simply never appear.
- **The home directory.** Running Claude Code from `~` produces the folder `-Users-name`, whose basename is the username. Saving that is meaningless on its own and would match any path ending in the same segment.

For compatibility, an entry with no `/` and no leading `~` is still read as a bare folder name under the old suffix rule. Rewrite those to paths the next time the profile is verified.

### Channel matching

A `slack_channels` entry is an object: the channel `id`, the `name` Slack returned when it was verified, and `client_facing`. A message matches an entry **by Id only**; the name is for the person reading the profile and can go stale. A channel in `slack.exclude_channels` is dropped. A channel the user posted in that matches neither is **unmapped**. DMs and group DMs never match an entry and are attributed from content at run time.

Verification is not a one-time setup step. Any time a channel is about to be added to the profile, from setup, drift, or re-verification, resolve its Id live, show what Slack returns, and let the user confirm it.

### Org drift check (every run, before Step 1, silent when clean)

One query for the profile's tasks and one for its projects (both in the reference). Either of these is drift and is resolved with the user right here, before any reconstruction:

- A task in the profile has `TASKRAY__Archived__c = true`. The org accepts inserts against archived tasks silently, so this is the failure that hides longest. Apply the *live task rule*, show the replacement, and save it once the user confirms. This is routine and on its own triggers nothing else.
- A client project in the profile is completed, archived, or past its end date. Ask whether to drop it from the profile or keep it as is (two options). For the internal project, re-resolve it by name instead (Setup step 4); it is never dropped.

### Evidence drift (surfaced in the Step 4 proposal)

These can only be seen after reconstruction. They go in the proposal's ambiguous-calls list and are answered before Step 5, through the option pop-up (*Asking questions*), and the answer is saved to the profile:

- A folder with evidence in scope is unmapped. Ask which home it gets, with the profile's project labels, "Serves several projects" (`shared_directories`, asked about on every run), and "Personal, leave it out" (`exclude_directories`) as the options, the likeliest first. Never guess. If it belongs to a client the profile does not know ("Other"), run the *active project* query for that client right there, offer the matches, and add the project.
- A Slack channel the user posted in during scope is unmapped. Verify it live (the *Channel matching* rule), show it, and ask which home it gets, with the profile's project labels, Internal, and "Not work, ignore it" (`slack.exclude_channels`) as the options. Never guess.
- A time record in scope is on a project the profile does not know. Ask whether to add it.

### Re-verification (every 30 days)

When `verified_on` is more than 30 days old, re-run Setup step 3's project inference and show it as the same multi-select, with the projects already in the profile listed first, re-resolve every task with the *live task rule*, and ask about any channel the user posted in during the last 90 days that is neither mapped nor excluded, one pop-up as in *Evidence drift*. Re-resolve every mapped channel Id at the same time and show any whose name changed or which no longer resolves. Do not re-ask already-mapped folders or channels, or the workday hours, unless the user wants to. Then set `verified_on` to today. The profile is saved once, at the end of Step 0, whatever combination of drift and re-verification ran.

## Step 1: Find the boundary

Run the *last records* query from the reference for the profile's username.

An explicit scope from the user wins outright; when they name a date or range, that is the scope and this section only supplies the reconciliation. The rest applies to the default.

**The boundary is the most recent date before today that has a record. The default scope runs from the boundary through today inclusive; today is part of the default scope even when it already has records.** People log in three rhythms: nothing for several days, two or three times within one day, and a quick stand-up logged for today before the previous days were touched. Anchoring on the last date *before today* is what survives all three; anchoring on the newest date collapses the scope to today and silently skips every unlogged day before it. Records dated after today (PTO booked ahead) are ignored for the boundary.

If the default is in play and the user has no records at all, ask for a start date and offer the Monday of the current week as the default. With an explicit scope, ask nothing.

Once the scope is known, run the *records in scope* query so reconciliation sees every booked record in range; the *last records* query is only for finding the boundary and is capped.

**Never key the boundary off `CreatedDate`.** Records are written retroactively, so when a record was submitted says nothing about how far the logging actually got. Scanning forward from a submit time silently swallows every hour that was worked before it and never logged.

**Reconcile the boundary date instead of skipping or re-proposing it.** Build the full picture for every date in scope from the calendar and the evidence, exactly as if nothing were logged. Then, for each date that already has records, compare per project and per Activity Type:

| Situation | Action |
| --- | --- |
| Evidence supports more hours than are booked | Propose the **difference only**, never the full day again |
| Booked hours match the evidence | Propose nothing for that grouping and say so in the table |
| Booked hours exceed the evidence | Leave it alone and flag it; never reduce a record to match a reconstruction |

Show the reconciliation in the proposal so the arithmetic is visible: booked, supported, proposed. A date already covered should appear in the table as settled rather than vanishing from it.

Writing the delta follows the existing rule: a record created **today** is merged in place, and a record from a prior day gets a **second record** alongside it.

## Step 2: Read the calendar

Use the Google Calendar connector on the profile's `calendar_account` for the scope dates, fetching each full day (midnight to midnight in the profile timezone) so after-hours meetings are seen, not just the workday window. If the connector is not connected, say so and stop; the calendar is not optional. The result is often too large for context; when it saves to a file, parse it with jq or python rather than reading it whole.

**Times come back already converted; do not shift them again.** Every event carries a `dateTime` with a UTC offset plus a separate `timeZone` label. When the request names a timezone, Google converts each `dateTime` into it but leaves the original `timeZone` label untouched. A meeting booked by someone in Chicago or Los Angeles therefore arrives at the correct local wall-clock time with a foreign-looking label sitting next to it. **Read the offset on `dateTime` and ignore the label.** Treating the label as the offset moves those meetings by hours, which both misplaces real meetings and drops reconstructed blocks on top of them.

Merge overlapping events, then find gaps of 25 minutes or more inside the workday. Skip `OUT_OF_OFFICE` events. Note any events that **overlap each other**: those are double-bookings the user must resolve, and they inflate the day if left alone.

## Step 3: Reconstruct the gaps

Evidence sources, in order. Use whichever exist on this machine; say which ones you used.

1. **Session transcripts** (Claude Code: `~/.claude/projects/*/*.jsonl`). Parse each line's `timestamp` (UTC, convert to the profile timezone), keep entries where `type == "user"` and the message content is real text. Skip system reminders, `<command-name>` blocks, `<local-command-*>` output, "Base directory for this skill", and compact-continuation preambles. The project directory name gives attribution through the profile's `directories` map.
2. **Git history.** `git log --all --since=... --date=format:'%Y-%m-%d %a %H:%M'` across the profile's `repo_roots`.
3. **Slack messages the user sent.** Search messages from the profile's `slack.user_id`, bounded to each scope day and sorted by time, paging until the day is exhausted (the search returns 20 at a time). For each hit read the channel, the timestamp, the participants, and the text or snippet; that is enough to place it. Open a full thread only when a message cannot be attributed otherwise. Messages the user received but did not answer are not evidence, because reading time cannot be observed. Skip this source when `slack` is null, and say so.

Attribution for transcripts and git uses the *Directory matching* rule in Step 0. Anything under `exclude_directories` is left off entirely. Anything under `shared_directories` is reconstructed but held as unattributed until the user says which project it served (see *Shared tooling* below). A folder that matches nothing is evidence drift: reconstruct it, hold it unattributed, and ask in the proposal. Never guess a project for it.

Attribution for Slack uses the *Channel matching* rule. A mapped channel books to its project, an excluded channel is dropped, and an unmapped channel is evidence drift. A DM or group DM is attributed from content: a client name or project label in the text, or a participant who only appears in one project's channels. When that is not clear, hold it unattributed and ask in the proposal.

A Slack message is a point in time, like a commit. A single reply that lands inside a block already supported by other evidence confirms the block and creates nothing. A cluster of messages in a gap with no other evidence becomes a **Communications** block on its project, sized first-to-last under the rounding rules.

Bound each block by its first and last piece of evidence. The evidence is for your reasoning only; it never appears in anything written to the calendar or Salesforce (see the wording rule in Step 5). Two projects interleaving in one window is common: split by subject matter and say you did.

### Break the block on dead space

**A block spans evidence, never silence.** Before bounding a block, check the interior. Any stretch of 45 minutes or more with no message and no commit ends the block; what follows is a new one. Bounding first-to-last across a two-hour hole invents hours nobody worked, and it is the single easiest way to inflate a day.

A long agent run is not evidence the user was at the keyboard. What counts is *their* activity: a message they typed, a commit that landed.

### Rounding

Rounding applies to reconstructed evidence blocks only. A calendar event keeps its booked length, which is why a 15-minute stand-up logs at 0.25h. The app's smallest unit is **0.25h (15 minutes)**, which is also the floor for any block.

| When | Round to |
| --- | --- |
| During the workday | nearest **30 minutes** |
| After hours, weekends, holidays | nearest **15 minutes** |

After hours especially, size the block to how long they were actually present, not to how long something ran. A cluster with one message and then silence is **0.25h**. A cluster of back and forth for half an hour is **0.5h**. Take each cluster's first-to-last span and round that; do not round outward to make clusters touch.

### Shared tooling: always ask, never assume

A repo in `shared_directories` (general migration tooling, internal utilities) books to whichever project it was serving that day, and heavy stretches may split. **Ask which project (or which split) every time it appears**, unless the user has already said so in that same run. If they answer that it always belongs to one project, move it to that project's `directories` and say you did. Standing folder-to-project answers live in `directories`, `shared_directories`, or `exclude_directories`, never in `conventions`.

### Overlapping sources: the calendar may overlap, the time records may not

Multitasking is normal: a client thread in Slack during a build in Claude Code, during a meeting. The calendar and the time records treat it differently.

**Calendar.** Concurrent work may overlap on the calendar; it shows how the day was actually spent. A concurrent activity earns its own event when it would stand as a block on its own (at least 0.5h in the workday, 0.25h after hours) **and** it is on a different project or a different kind of work from the block it overlaps. A few replies inside a coding block are not an event. A 40-minute client thread during a build for another client is.

**Time records.** Every minute is booked once. Where sources overlap, one wins the slot:

1. A calendar event the user created themselves.
2. Billable over non-billable.
3. Claude Code over Slack.
4. A calendar event someone else invited them to.

Hours come from this deduplicated timeline, never from summing the calendar events. Notes still list every event title touching that project and Activity Type, so the record reads as the multitasking it was while the hours stay honest. The user can name an exception in the moment; a standing exception goes in `conventions`.

### Work during a meeting someone else booked

The calendar is the default. When transcripts or Slack show heavy activity during an invited meeting, it folds into the meeting silently if the work is clearly on the same project. If it is on a different project, or the project is unclear, list it in the ambiguous calls with "attended the meeting" as the default answer and follow whatever the user says. Light activity during a meeting is ignored. Events the user created themselves are never questioned.

## Step 4: Propose

Show one table covering both halves of the work:

- **Proposed calendar events** for the gaps and for significant concurrent work: title, times, length, and the evidence behind each. Events may overlap under the *Overlapping sources* rule; say when they do.
- **Proposed time records**: one row per date, per project, per Activity Type, with hours from the deduplicated timeline and the comma-joined event titles that become the notes. Call the Activity Type out so it can be corrected before anything is written.
- Day totals, and a grand total. When calendar hours exceed record hours because of overlap, show both so the difference is visible.
- **The ambiguous calls**, listed explicitly. Overlapping meetings, heavy work during an invited meeting on another project, DMs with unclear attribution, work that spans midnight, anything internal versus billable, anything with thin evidence.
- **Unaccounted gaps** with no evidence at all. Group by day, one line per day, with a per-day subtotal and a grand total. Use 12-hour times with am/pm and the duration in parentheses:

```
**Unaccounted, 8.25h across 4 days**

Wed 9/2   1.0h    9:00 to 9:30 am (0.5)   ·   2:00 to 2:30 pm (0.5)
Thu 9/3   1.75h   9:00 to 9:45 am (0.75)  ·   2:00 to 2:30 pm (0.5)   ·   4:30 to 5:00 pm (0.5)
Fri 9/4   5.0h    10:30 to 11:30 am (1.0) ·   1:00 to 5:00 pm (4.0)
```

Never pad the list with sub-25-minute gaps, and say plainly when a day has none.

Then stop and wait. One approval covers both the calendar events and the time records; the user can also approve the records alone and skip the calendar. If a calendar write fails partway, report which events landed and still ask before writing any time record.

## Step 5: Write the calendar events

Title format: `<project label>: <what they did>`, using the profile's `label`. Describe the work itself in the description and mark after-hours or weekend blocks as such.

**Wording rule, important.** These records are read by other people. Never reference how the work was reconstructed. No mention of Claude, an LLM, AI tooling, prompts, sessions, transcripts, chat, or commits, and never the word "reconstructed." Describe what the user decided, built, or reviewed, in their voice, as ordinary work notes. The same rule applies to time record notes. Naming Slack as the medium is fine when the conversation was the work ("worked through cutover questions with the team in Slack"); saying that Slack, or anything else, was searched is not. Set `availability: AVAILABILITY_FREE` so historical availability is untouched. Create only where the calendar has nothing for that activity already; an event may overlap an existing one under the *Overlapping sources* rule, and never duplicates one.

**Never put the time worked in the description.** No start and end times, no duration. The event's own start and end are the sole record of time spent, so the user can drag or resize the event without a description that then contradicts it. Keep the after-hours or weekend marker, just without the clock.

## Step 6: Write the time records

One record per date, per project, per Activity Type, using the project and task Ids from the profile and the payload in the reference. Hours for each row come from the deduplicated timeline in Step 3, not from the summed length of the calendar events. Write each payload to a temporary file and insert one at a time so the org's flows fire the way they do from the UI. A same-day merge (Step 1) is a PATCH of hours and both notes fields on the existing record, using the *update* call in the reference; nothing else on the record is touched. Notes are the calendar event titles as written, label prefix included, comma-joined.

### Choosing the Activity Type

`Activity_Type__c` is a restricted picklist **scoped by record type**. Use only values in the profile's `picklists` for that record type; the tables below are the defaults. If a table names a value the profile doesn't have, say so and ask which allowed value to use. If an insert is rejected for a picklist value, read the allowed values again and update `picklists` before retrying. Pick from the evidence, not by habit. Most blocks are Coding and Configuration or Meeting, but collapsing everything into those two misreports the work.

| What the block produced | Activity Type |
| --- | --- |
| A written deliverable: register updates, guides, reports, internal notes, plan CSVs, doc revisions | **Documentation** |
| Client or team correspondence: Slack threads, email drafting, Notion pushes, chasing answers | **Communications** |
| Solo work producing config, metadata, scripts, queries, workbooks | **Coding and Configuration** |
| The calendar event has attendees | **Meeting** |
| Ambiguous, or genuinely mixed | **Coding and Configuration** |

Documentation is the value most often missed. On a discovery-heavy engagement a large share of what looks like build work is deliverable writing.

Internal work splits the same way. Do not default everything to People and Team Activities.

| What the block was | Activity Type |
| --- | --- |
| 1:1s, all-hands, company-wide calls, coffee chats, team socials | **People and Team Activities** |
| Time logging itself, and building or extending time tooling | **Admin and Overhead** |
| Training, certifications, courses, conference and webinar sessions | **Learning and Development** |
| Interview panels and candidate review | **Recruiting** |
| Scoping and SOW work that is not yet on a project | **Presales** |
| Vacation and holidays actually taken off | **PTO** |
| Unassigned time between projects, onboarding with no project yet | **Bench** |
| Travel for work, client or internal | **Travel** (on either record type) |

A block can split by activity type the same way it splits by project. An hour that was a 1:1 plus tooling work is two rows, not one. Do not split below 0.25h.

## Step 7: Verify

Run the *created today* query from the reference and confirm the automation-populated fields match the user's existing records. Internal records legitimately have no Monthly Billing Summary; client records should have one.

Report record names, day totals, and anything still unaccounted for.

## Step 8: Refresh the dashboards

Run this right after Step 7, on every run that wrote at least one time record. It never waits for the user to ask for a report. time-report is installed beside this skill; its script is `../time-report/time_report.py` from this folder. Run Python as python3 on a Mac, and as py -3 on Windows (or python if that is the one that prints a Python 3 version).

- **Local dashboard, inline.** Run `time_report.py week --dashboard` and give the user the `file://` link the script prints. It takes seconds. Do not open the browser; that is time-report's job when they ask.
- **Published dashboard, in the background.** Only when the profile has `dashboard.artifact_url`. Launch one background agent (the Agent tool) on a small, fast model, passing the model explicitly; the work is mechanical. Brief it with the artifact URL, the user's name, and the *Published dashboard* procedure in time-report's `SKILL.md`, which it follows step by step. Do not wait for it: finish the Step 7 report, and pass on its one-line result when it arrives. If it fails, say so, with what failed; the time records are already written and correct either way.

If either refresh lists *Forecast left out*, mention it in one line. If the Artifact tools are not available in the session, skip the published refresh and say so.

## Standing conventions

These hold for everyone. Per-user rules live in the profile's `conventions` list and are read at the start of every run.

- Recurring stand-ups log at their true length, usually **0.25h**.
- Meetings with attendees are **Meeting**; solo blocks default to **Coding and Configuration**, but check the Activity Type tables first.
- Work spanning midnight is split at midnight and lands on the day it happened.
- When meetings overlap, ask which one they attended. The other is trimmed or dropped.
- Overlapping events on the calendar are fine. On time records no minute is booked twice; the *Overlapping sources* order decides who gets it.
- Client-facing work is billable even when it is tooling or enablement, if it was built for a client deliverable.
- Meetings titled `[Internal]` are still billable to the client project they serve. Internal does not mean non-billable.
- **The org rejects time records dated in a previous month.** Check this before proposing a backfill that crosses a month boundary. If work is stranded in a closed month, ask where it should land. Never silently move hours across dates, and never move an hour that a closed record already bills, or it gets billed twice.

If a convention here ever conflicts with what the user says in the moment, they win. If they state a rule that should persist, add it to their profile's `conventions` and say you did.
