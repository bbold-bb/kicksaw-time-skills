---
name: log-time
version: 1.20.2
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
- **No time record has zero or blank values.** Every standard field is filled and the hours are more than zero, checked before every write (Step 6). When a value is missing, ask for it; never invent one to get a record through.
- Don't update time records from prior days. If a date/project/activity already has one, **add another record**. Same-day corrections are the exception: a record created today can be merged in place (adjust hours, extend notes) instead of adding a duplicate in the same grouping.
- **Meeting recorders are read-only.** Never create, edit, share or delete a note or recording, and never open a personal one.
- Reads in every other org, repo, and Slack stay read-only. Only the org named in the profile is written to, and only the time record object.
- **Slack is read-only for this skill, without exception.** It never sends, schedules, or drafts a message in any channel or DM, whether or not a client is in it.
- Nothing about Slack goes in the profile from a pasted Id, a name pattern, or a line in a repo's `CLAUDE.md`. Every channel is resolved live, shown, and confirmed by the user first (see *Channel matching*).

## Step 0: Load the profile, and set it up if it is missing

### Preflight

Before anything else, check the tools this skill needs. Silent when everything is fine.

- `sf --version` runs (on Windows, in a session started before it was installed, run it by its full path: `& "C:\Program Files\sf\bin\sf.cmd" --version` in PowerShell).
- `sf org display user -o <alias> --json` succeeds, where `<alias>` is the profile's `org_alias`, or `Kicksaw-Prod` when there is no profile yet.

If `sf` isn't found, or the org check fails with an authentication error (expired or missing login), stop and offer to fix it: "The Salesforce CLI isn't set up (or your Kicksaw sign-in expired). Want me to fix that now?" On a yes, download https://raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/main/SETUP.md with your shell, read all of it, and follow its *Salesforce CLI* or *Org login* step, whichever failed. Don't print a login command for the user to run. Any other failure (a network error, a query error) is not a setup problem: report it as usual.

Read the profile from `~/.claude/kicksaw-time/profile.json`. If it is not there, look in the legacy locations (`profile.json` beside this file, then `~/.claude/skills/log-time/profile.json`); if it turns up in one of those, move it to the home location, say you did, and carry on. The profile is the user's data and lives outside the skill folder so that installing or updating a skill can never replace it. If it does not exist, or the user asks to reset it, run **Setup** below before anything else. If it exists, run the **org drift check** every time, the **re-verification** when a trigger fires, and the **new questions** when the profile predates any of them. All finish before Step 1.

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

1. **Org.** Try `sf org display user -o Kicksaw-Prod --json` without asking. If it resolves, that is the org; `id` and `username` become `user.user_id` and `user.username`. If it fails, run `sf org list --json` and offer the logged-in aliases as options. If there are none, run the *Org login* step of `SETUP.md` (see *Preflight*) and continue once it succeeds. Never ask the user to type their own Id.
2. **Resource and timezone.** Read the Resource Hero resource for `resource_hero.resource_id` and the user's `TimeZoneSidKey` (both in the reference). No question here; the timezone is confirmed in step 9, because the Salesforce setting is often the company's default rather than where the user works.
3. **Projects, inferred.** Gather candidates from the org, without asking first:
   - their current **Resource Hero assignments** that link to a TaskRay project (the *setup assignments* query in the Resource Hero reference);
   - the projects they **logged to in the last 90 days** (the *recent history* query).
   Drop any that are closed, completed, or archived, and drop the internal project (step 4 adds it). Show the rest in one **multi-select** pop-up: "These are the projects you're on. Pick the ones to log against." Each option is the project name; its description gives the client, the end date, and where it was found ("assigned through Dec 31", "logged 14 times, last Nov 3"). "Other" takes a client name: run the *active project* query for it and offer the matches as a follow-up pop-up. Zero client projects is a valid answer for someone new or on the bench.
   For each chosen project, resolve its live time-entry task with the *live task* query. Exactly one unarchived match is expected; if there are zero or several, offer them as options (the *live task rule*, used everywhere a task is resolved). `record_type` is `Client Work` for every client project. Save the Resource Hero assignment Id as `rh_assignment_id` when there is one.
   When the *live task rule* has to offer several tasks, say why in plain words first: "This project has more than one place to log time. The one marked Recommended is the newest." Mark the newest unarchived one "(Recommended)".
   **Labels** default to the client's account name, shortened the obvious way ("Northwind Health Partners" becomes "Northwind"). Only ask when two projects would share a label, or a label holds a colon: then offer two suggestions per project, with "Other". Start that question with why it matters: "Labels go at the front of every calendar event this creates, so it can tell your projects apart. These two need different ones."
4. **Internal project.** Run the *internal project* query. One match: use it without asking. Several: one pop-up with the matches, each with its end date. Then resolve its live task the same way. Every user gets an internal project; it is not optional. When a question about it is needed, say: "Every user logs internal time (1:1s, all-hands, time logging itself) to the company's internal project. Which of these is it?"
   **Allowed values.** Read the allowed picklist values for both record types (*allowed values* in the reference) and save them as `picklists`. Check that the fixed values the insert payload sets (time type, category, non-billable reason) are among them; if one isn't, stop and show the user the allowed values, because every insert would fail.
5. **Folders.** `transcript_root` is `~/.claude/projects` unless it does not exist (on Windows that is `%USERPROFILE%\.claude\projects`). For `repo_roots`, look under the home folder on either system, two levels down, for folders that hold git repos, and offer them as a **multi-select** (`~/Code`, `~/Projects`, and so on), with "Other" for a path. If none are found, save an empty list and move on.
   Then map folders to projects **without asking**: a repo or transcript folder whose path contains a project's label or client name goes in that project's `directories`. Discover repos as the immediate children of each root plus one level down (anything holding a `.git`). Discover transcript folders as those with a file modified in the last 90 days, and map each back to its real path by testing the path-encoded name against folders on disk (see *Directory matching*, drive letters included); **the entry saved is always that real path**, written with `~` for the home folder and forward slashes, never a bare folder name. Everything else stays unmapped. It is asked about on the first run that finds work in it (*Evidence drift*), so nobody answers questions about folders they no longer use.
6. **Slack.** Confirm the Slack connector by searching for messages from the user in the last 30 days; the search tool reports the acting user's Id, which becomes `slack.user_id`. If the connector is not connected, say so, save `"slack": null`, and continue. Slack is an evidence source, not a gate, and every later run notes that it is missing.
   For each project, find its channels: a channel search across public and private channels using the account name and its obvious short forms, plus the channels the user posted in during the last 90 days whose name matches. **Verify every candidate live** (resolve the Id and read back the name, purpose, and the user's message count). Then one pop-up, one **multi-select** question per project: "Which of these channels are for <Label>?", each option a channel with its purpose and message count. A project with no candidates gets no question. Set `client_facing` to true for a `kicksaw_<client>` or `kicksaw-<client>` channel and false otherwise; the summary in step 9 shows it for correction.
   Every other channel stays unmapped and is asked about on the first run that finds the user posting in it. Group DMs and DMs are never mapped; they are attributed from content at run time (Step 3).
7. **Calendar.** `rhythm.calendar_account` is the org username. Confirm it by listing one day of that calendar. If that fails, offer the calendars the connector can see as options. Then one pop-up, two questions (the per-project color questions follow in their own pop-ups):
   - "Do you color-code projects on your calendar?" Options: "No" and "Yes". On a yes, list the last 30 days of events, and for each project take the color most used on events whose title carries its label or client name. Show the result as one question per project, four projects per pop-up ("ClientA looks like Peacock. Right?"), with three options: the inferred color (Recommended), the runner-up color, and "No color for this project"; "Other" takes a color name. Save the Google event color Id as the project's `color_id`. When two projects share a color, save no `color_id` for either and say why. Color names: 1 Lavender, 2 Sage, 3 Grape, 4 Flamingo, 5 Banana, 6 Tangerine, 7 Peacock, 8 Graphite, 9 Blueberry, 10 Basil, 11 Tomato. On a no, `color_id` stays null for every project. Save the answer as `rhythm.color_codes`. Labels stay the main signal either way, since people change colors between projects.
   - "Do you track work as Google Tasks?" Options: "No" and "Yes". On a yes, say: "Got it. When I list unaccounted time, I'll ask whether any of it was a task. You can tell me, or paste a screenshot of your calendar with your tasks showing." Save `rhythm.uses_google_tasks` either way. (The calendar connector doesn't include Google Tasks, which is why the run asks instead of reading them.)
8. **How you work.** What counts as evidence depends on how a person works, so learn it before the first run. Run the *work pattern* queries in the reference, and mark the best-supported options "(Recommended)" with the evidence in their descriptions ("38h in the last 90 days"). Every question here can be skipped; a skipped one saves an empty list or null.
   **First pop-up, three questions:**
   - "What fills most of your week?" Multi-select: "Building and configuring", "Documents and design", "Managing projects and clients", "Testing and reviews". Recommend by hours logged in the last 90 days: Coding and Configuration points to building, Documentation to documents, Communications to managing, and Meeting and Travel to nothing. Testing is never inferred. Recommend managing when the role names a project, program, engagement or delivery manager. Saved as `work.main_work` (`building`, `documents`, `managing`, `testing`, or the words typed under "Other").
   - "What takes time but leaves no trace here? Pick any, or type none." Multi-select: "Salesforce work by hand", "Planning and Jira boards", "Documents and slides", "Calls and chats not on the calendar". Saved as `work.no_trace` (`salesforce`, `planning`, `documents`, `calls`, or the words typed under "Other").
   - "How much of your work goes through Claude?" Options: "Most", "Some", "Rarely". Recommend by session history: most of the last 10 workdays, a few of them, or none. Saved as `work.claude_use` (`most`, `some`, `rarely`); Step 3 uses it.

   The main work sets `work.unclear_activity_type`, the Activity Type for a client block whose evidence doesn't settle it:

   | Main work | Unclear blocks become |
   | --- | --- |
   | Building and configuring | Coding and Configuration |
   | Testing and reviews | Coding and Configuration |
   | Documents and design | Documentation |
   | Managing projects and clients | Communications |

   When the picks lead to different types, the one with the most hours in the last 90 days wins; with no hours to compare, ask "Which of these takes the most time?" For work typed under "Other", ask which allowed Activity Type fits. With none picked, it is Coding and Configuration. The value must be in the profile's `picklists` for Client Work; if it isn't, say so and offer the allowed values. Save the Activity Type with the most hours, Meeting and Travel aside, as `work.type_checked` (null when there are no records).
   **Recurring meetings, only when there are some.** Find events with attendees, not declined, that appear 3 or more times in the last 30 days, whose title names no project label or client, whose color points to no project, and that no line in `conventions` covers. Ask about the four most frequent, one question each: "Which project does '<title>' belong to?" Options: up to two project labels, the likeliest first, then Internal, and "It varies, ask me"; "Other" takes another label or "not work". Save each answer as a line in `conventions`: "Meetings titled '<title>' book to <label>.", "Ask each time which project '<title>' belongs to.", or "'<title>' is not work." A line in `conventions` wins over what a recording suggests.
   **Meetings pop-up, two questions.** "Where are your meetings recorded or transcribed?" Multi-select: Notion, Wispr Flow, tl;dv, Zoom, the connected ones first. "Any of these too?" Multi-select: "ZoomInfo (Chorus)", "Plaud", "Google Meet or Teams", "I don't record". "Other" takes another tool's name. A tool that is ticked wins over "I don't record". Read only whether a connector exists: never list a tool's recordings during setup, because a list shows titles before the user has said what is personal.
   For each tool picked that [reference/meetings.md](reference/meetings.md) marks as read, ask in one more pop-up, one question per tool: "Does <tool> hold only work meetings?" Options: "Only work meetings", "Personal ones too". Without an answer, treat it as personal ones too.
   Save `work.recorders`, one entry per tool picked: `{ "tool": "notion", "connected": true, "work_only": true }`, with `"connected": false` when its connector isn't available, and `"work_only": null` for a tool that isn't read yet. Save each connected tool that is read but wasn't picked in `work.not_used`, so it isn't asked about again. For an unconnected tool that is read, say once where to connect it (Claude's connector settings), and that the run works without it. The user signs in themselves; the skill never asks for a password. For a tool the reference marks *Not read yet*, say the answer is saved and that the skill doesn't read that tool yet.
9. **Workday, timezone, and save.** One last pop-up, three questions:
   - "What are your usual work hours?" Options: 9:00 to 5:00 (Recommended), 8:00 to 4:30, 8:30 to 5:00, with "Other" for anything else. They set `rhythm.workday_start` and `workday_end`. They only shape gap-finding; after-hours work is still logged.
   - "What timezone do you work in?" The first option, marked "(Recommended)", is the computer's timezone: on a Mac, the part of `readlink /etc/localtime` after `zoneinfo/`; on Windows, `(Get-TimeZone).Id` in PowerShell, converted to its IANA name with `$iana = $null; [System.TimeZoneInfo]::TryConvertWindowsIdToIanaId((Get-TimeZone).Id, [ref]$iana); $iana` (PowerShell 7). Where that isn't available, use this table: Eastern Standard Time is `America/New_York`, Central Standard Time `America/Chicago`, Mountain Standard Time `America/Denver`, US Mountain Standard Time `America/Phoenix`, Pacific Standard Time `America/Los_Angeles`, Alaskan Standard Time `America/Anchorage`, Hawaiian Standard Time `Pacific/Honolulu`. Put the IANA name in the option label so the user confirms it. Add the Salesforce `TimeZoneSidKey` as a second option when it differs. The answer is `rhythm.timezone`.
   - "Save this profile?" Before it, show a short summary: projects with labels, mapped folders, mapped channels, calendar, how you work, meeting recorders, timezone. Options: "Save it" (Recommended) and "Change something", where "Other" names the change.

`conventions` holds the recurring-meeting answers from step 8, if any, and otherwise grows only when the user states a rule during a run. Save the profile with `verified_on` set to today. Skip the drift check on a profile saved seconds ago, then continue into Step 1 with the scope the user originally asked for.

### New questions for existing profiles

Profiles saved before 1.19.0 never answered three setup questions. When the profile has no `uses_google_tasks` key in `rhythm`, ask them now, asked once and never again, in one pop-up before Step 1. Start with one line: "A few new setup questions, asked once."

- "Do you color-code projects on your calendar?" and, on a yes, the per-project color questions, exactly as in Setup step 7.
- "Do you track work as Google Tasks?" as in Setup step 7, including what to say on a yes.
- "What timezone do you work in?" as in Setup step 9, with the profile's current `rhythm.timezone` as the first option when it matches the computer's, and the computer's timezone first, marked "(Recommended)", when it doesn't.

Save `rhythm.uses_google_tasks`, `rhythm.color_codes`, a `color_id` on every project (null when there is none), and `rhythm.timezone`, together with anything the drift check or re-verification changed. The `uses_google_tasks` key being present is what marks the questions as answered.

Profiles saved before 1.20.0 also have no `work` key. When it is missing, ask everything in Setup step 8, once, before Step 1, after the questions above if those are due too. Start with one line: "A few questions about how you work, asked once." The `work` key being present, even with skipped answers, is what marks them as answered.

Profiles saved before 1.17.0 have no `picklists`. When they are missing, read and save them first (*Allowed values* in Setup step 4), because the unclear Activity Type is checked against them. No question is needed.

Older profiles may hold `flux_resource_id` and `delivery_team` under `user`. They aren't used anymore: ignore them, and never mention them. Never look up a Flux resource, and never stop because one is missing.

### Color for a new project

Whenever a client project is added to the profile after setup (at re-verification, from evidence drift, or because the user asks), and `rhythm.color_codes` is true, ask its color in the same pop-up that adds it: "What color should <Label> be on your calendar?" Offer up to three colors not already used by another project's `color_id`, the first marked "(Recommended)", plus "No color for this project"; "Other" takes any color name. Use the names from Setup step 7. Save the choice as the project's `color_id`. When all eleven colors are taken, offer only "No color for this project" and "Other".

### Directory matching

A `directories` entry is the **working directory's path**, written with `~` for the home folder and forward slashes, as in `~/Desktop/Work/ClientA-Migration`, on a Mac and on Windows alike. `~` is the user's home folder: `/Users/<name>` on a Mac, `%USERPROFILE%` (usually `C:\Users\<name>`) on Windows. Paths survive being installed anywhere and on anyone's machine; bare folder names do not.

- **A repo** matches when its absolute path equals the entry's, after expanding `~`. On Windows, compare without regard to case or to which slash is used.
- **A transcript folder** matches when its name equals the entry's **encoded** form. Claude Code names each folder after the working directory's absolute path, drive letter included, with every character that is not a letter or a digit replaced by a hyphen. Derive that name from the expanded path at match time; never store it.

| Working directory | Transcript folder |
| --- | --- |
| `/Users/name/Desktop/Work/Client_A` | `-Users-name-Desktop-Work-Client-A` |
| `/Users/name/Desktop/Salesforce Projects/Client A` | `-Users-name-Desktop-Salesforce-Projects-Client-A` |
| `C:\Users\name\Code\Client_A` | `C--Users-name-Code-Client-A` |
| `C:\Users\First Last\Code\Client A` | `C--Users-First-Last-Code-Client-A` |

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

- A folder with evidence in scope is unmapped. Ask which home it gets, with the profile's project labels, "Serves several projects" (`shared_directories`, asked about on every run), and "Personal, leave it out" (`exclude_directories`) as the options, the likeliest first. Never guess. If it belongs to a client the profile does not know ("Other"), run the *active project* query for that client right there, offer the matches, and add the project (see *Color for a new project*).
- A Slack channel the user posted in during scope is unmapped. Verify it live (the *Channel matching* rule), show it, and ask which home it gets, with the profile's project labels, Internal, and "Not work, ignore it" (`slack.exclude_channels`) as the options. Never guess.
- A time record in scope is on a project the profile does not know. Ask whether to add it; on a yes, see *Color for a new project*.

### Re-verification (every 30 days)

When `verified_on` is more than 30 days old, re-run Setup step 3's project inference and show it as the same multi-select, with the projects already in the profile listed first, re-resolve every task with the *live task rule*, and ask about any channel the user posted in during the last 90 days that is neither mapped nor excluded, one pop-up as in *Evidence drift*. Re-resolve every mapped channel Id at the same time and show any whose name changed or which no longer resolves. Do not re-ask already-mapped folders or channels, or the workday hours, unless the user wants to. Projects added here get a color question (*Color for a new project*). Check how the user works, too. Skip all of this when the profile has no `work` key (*New questions* asks everything instead). A connected recorder that is marked as read and is in neither `work.recorders` nor `work.not_used` gets the Setup step 8 questions for that tool; never list a tool's recordings to decide this. A recorder saved with `work_only` null that is now marked as read gets its work-only question. Then run the *work pattern* query: unless `work.main_work` is empty, when the Activity Type with the most hours (Meeting and Travel aside) matches none of the main work and differs from `work.type_checked`, ask "What fills most of your week?" again, set `work.unclear_activity_type` again from the answer, and save that type as `work.type_checked`. Then set `verified_on` to today. The profile is saved once, at the end of Step 0, whatever combination of drift and re-verification ran.

## Step 1: Find the boundary

Run the *last records* query from the reference for the profile's username.

An explicit scope from the user wins outright; when they name a date or range, that is the scope and this section only supplies the reconciliation. The rest applies to the default.

**The boundary is the most recent date before today that has a record. The default scope runs from the boundary through today inclusive; today is part of the default scope even when it already has records.** People log in three rhythms: nothing for several days, two or three times within one day, and a quick stand-up logged for today before the previous days were touched. Anchoring on the last date *before today* is what survives all three; anchoring on the newest date collapses the scope to today and silently skips every unlogged day before it. Records dated after today (PTO booked ahead) are ignored for the boundary.

If the default is in play and the user has no records at all, ask for a start date and offer the Monday of the current week as the default. With an explicit scope, ask nothing.

If the default is in play and the boundary is more than 14 days ago (someone back from leave, or new to logging this way), ask before building months of days: "Your last time record is <date>. Where should I start?" Options: the Monday of the current week (Recommended), the boundary itself, and "Other" for a date.

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

When projects have a `color_id`, an event's `colorId` attributes it to that project if the title doesn't already, and a title wins when the two disagree.

Merge overlapping events, then find gaps of 25 minutes or more inside the workday. Skip `OUT_OF_OFFICE` events. Note any events that **overlap each other**: those are double-bookings the user must resolve, and they inflate the day if left alone.

### Meeting recordings

Skip this section when `work.recorders` is missing or empty, or when none of its tools is marked as read in [reference/meetings.md](reference/meetings.md). Check which tools are connected on each run; the saved `connected` is only what was true at setup, so update it when it differs. If a tool that was connected isn't now, say so in one line. Recordings make the notes specific; the run never depends on them.

- **The calendar stays in charge of hours.** A recording never adds, lengthens or shortens a booked meeting. Tools often report the scheduled time, not the recorded one. Someone else's recording shows what was discussed; it doesn't show that the user attended.
- **Read the list for times and matching only.** Never repeat a title or excerpt of a recording that isn't matched, and never write it anywhere, except as the *Unmatched* rule allows.
- **Match to a work meeting:** an event with attendees that belongs to a profile project or Internal. Declined events never match, and neither do personal ones. From a tool with `work_only` true, a recording matches on the same title the same day, or on a start within 15 minutes of the event's. From any other tool it needs **both** a start within 15 minutes **and** the same title or a shared attendee. When two events fit equally well, it isn't a match. A recording stopped and restarted counts as one. When two tools recorded one meeting, use the one with the same title, then the first in `work.recorders`.
- **Open only a matched recording**, and read the summary, not the transcript. Open the transcript only when there is no summary and the meeting's project or subject is unclear.
- **Use** the topics, the decisions and the user's own follow-ups: to add a topic phrase to the meeting's note (Step 6), to settle which project a meeting served, and to suggest what an unexplained block nearby might have been (ask; a follow-up is not evidence that it was done). Nothing about anyone's health, family, pay or performance goes into an event or a note.
- **Unmatched recordings** count only from tools with `work_only` true. Never list one that someone else recorded. List the user's own of 5 minutes or longer, or of unknown length, under *Needs your call*, by time only ("A recorded call around 3:00 pm isn't on your calendar. Was it work?"). They are never booked without an answer, and not opened until the user says it was work; then ask its project and how long it took, and add it as a new event. From every other tool, unmatched recordings are never shown or mentioned, titles included.

## Step 3: Reconstruct the gaps

Evidence sources, in order. Use whichever exist on this machine; say which ones you used. When `work.claude_use` is `rarely`, a day without session transcripts is normal and isn't remarked on. When it is `most`, a workday without any is worth a line beside that day's unaccounted time, because the work may have been somewhere else.

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

The proposal is approved in **two stages: calendar events first, then time records.** The user sees their calendar filled in and checks it before any time record is proposed, so no record is written from a plan they never looked at.

**Use these templates exactly.** Same headings, same order, same table columns, a blank line between sections, and one day per block. Everyone's proposal should look the same, so it reads at a glance. Use 12-hour times with am/pm, project labels from the profile, and hours to two decimals at most. Leave out a section only when it would be empty, and say so in one line ("No unaccounted time.").

### Stage 1: calendar events

One message, laid out like this:

```
## Proposed calendar events · Mon 11/16 to Thu 11/19

### Mon 11/16 · 6.5h on the calendar (2.0h new)

| Time | Event | Length | Why |
| --- | --- | --- | --- |
| 9:00 to 10:00 am | ClientA: Sprint planning | 1.0h | already on calendar |
| 10:00 to 11:30 am | ClientA: Built intake flow | 1.5h | new · Slack thread with the team |
| 1:00 to 1:30 pm | Internal: Status report | 0.5h | new · Slack thread on the report |

### Tue 11/17 · 7.0h on the calendar (1.5h new)

(same table)

---

**Needs your call (2)**

1. Tue 2:00 pm, the client sync ran long. ClientA or ClientB?
2. Wed 7:00 am, emails before work. Log them or skip?

**Unaccounted, 3.5h across 2 days**

Mon 11/16   1.0h    2:00 to 3:00 pm (1.0)
Wed 11/18   2.5h    9:00 to 10:00 am (1.0)  ·  3:30 to 5:00 pm (1.5)

---

Answer the questions above, then: write these events to your calendar?
```

- **The day tables** list every event in the day, existing and new, in time order, so the day reads whole. *Why* says "already on calendar" for existing events. For new ones it gives the evidence in a few words, and notes an overlap under the *Overlapping sources* rule. The day heading gives calendar hours and how much of that is new.
- **Needs your call** lists the ambiguous calls, numbered: overlapping meetings, heavy work during an invited meeting on another project, DMs with unclear attribution, work that spans midnight, internal versus billable, anything with thin evidence. Ask them through the option pop-up (*Asking questions*) right after the message.
- **Unaccounted** lists gaps with no evidence at all, one line per day with a per-day subtotal and a grand total, duration in parentheses. Never pad it with sub-25-minute gaps. When the profile has `rhythm.uses_google_tasks`, add one line under it: "Were any of these a Google Task you worked on? Tell me which, or paste a screenshot of your calendar with your tasks showing, and I'll add them as events." Read each task's title, day and time from the screenshot, match it to a gap, and add it to that day's table as a new event, asking how long it took when the screenshot doesn't show it. Never take a screenshot yourself. When the profile has `work.no_trace`, offer up to three of those as the options when asking about a gap ("Salesforce work by hand", "Planning and Jira boards"), plus "Not work"; "Other" takes anything else. Then ask which project it was for, what was done, and how long it took if it didn't fill the gap. Salesforce work by hand is Coding and Configuration, documents and slides is Documentation, planning and calls are Communications.

What the user says about a gap becomes a new event in this same Stage 1 proposal: add it to its day's table, show the changed days again, and ask once more. Gap answers that come after Stage 2 is approved go through both stages again, for those events and records only.

Then stop and wait. The approval writes the calendar events (Step 5) and nothing else. The user can skip the calendar ("records only"): then go straight to Stage 2.

### Stage 2: time records

Propose the records only after the calendar events are written (or skipped). First say: "Your calendar is updated. Have a look, and tell me if anything should move." Wait until they have checked their calendar and say it looks right, applying any changes they ask for to the calendar first. On the records-only path, skip that and say: "Skipping the calendar. Here are the time records." Then re-run the Step 3 deduplication over the calendar as it now stands. Events created in this run keep the rank of the evidence they came from under the *Overlapping sources* order; they don't count as events the user created themselves. Show one message, laid out like this:

```
## Proposed time records · 9 records, 24.5h

| Date | Project | Activity Type | Hours | Notes | Record |
| --- | --- | --- | --- | --- | --- |
| Mon 11/16 | ClientA | Meeting | 1.0 | ClientA: Sprint planning (cutover scope, test data) | New |
| Mon 11/16 | ClientA | Coding and Configuration | 1.5 | ClientA: Built intake flow | New |
| Mon 11/16 | Internal | Documentation | 0.5 | Internal: Status report | Adds to TT-01234 (now 1.5h) |

**By project**

| Project | This run | Week to date | Allocation |
| --- | --- | --- | --- |
| ClientA | 18.0 | 22.0 | 30 |
| Internal | 6.5 | 8.0 | 10 |

**Day totals:** Mon 8.0 · Tue 7.5 · Wed 9.0 · Thu 0 (nothing new)

This skill only changes a record on the day it was written, so check them now.

These are exactly what will be written. Write them?
```

- One row per date, per project, per Activity Type, with hours from the deduplicated timeline. *Record* is "New", or for a same-day merge (Step 1) "Adds to <record name> (now <total>h)", where Hours is only what this run adds. The Activity Type is its own column so it can be corrected before anything is written. Notes are what Step 6 will write.
- When calendar hours exceed record hours because of overlap, put both in the day totals ("Mon 8.0 (9.5 on the calendar)").
- For a date that already had records, show the reconciliation from Step 1 under the table: booked, supported, proposed.
- There is no row with zero or blank hours, and no row missing a project, a live task, an Activity Type or notes. A difference of zero is not a row. An event with no length, or a row with a missing value, goes back to the user as a question before this table is shown; hours are never padded to reach the 0.25h floor.
- *Week to date* includes this run. Leave *Allocation* blank for a project with none.

Then stop and wait. If the user changes a row, show the whole table again before writing. If a calendar write in Stage 1 failed partway, say which events landed before showing this stage.

## Step 5: Write the calendar events

Title format: `<project label>: <what they did>`, using the profile's `label`. Describe the work itself in the description and mark after-hours or weekend blocks as such. When the project has a `color_id`, pass it as the event's `colorId` so new events match the user's own color-coding.

**Wording rule, important.** These records are read by other people. Never reference how the work was reconstructed. No mention of Claude, an LLM, AI tooling, prompts, sessions, transcripts, recordings, chat, or commits, and never the word "reconstructed." Describe what the user decided, built, or reviewed, in their voice, as ordinary work notes. The same rule applies to time record notes. Naming Slack as the medium is fine when the conversation was the work ("worked through cutover questions with the team in Slack"); saying that Slack, or anything else, was searched is not. Set `availability: AVAILABILITY_FREE` so historical availability is untouched. Create only where the calendar has nothing for that activity already; an event may overlap an existing one under the *Overlapping sources* rule, and never duplicates one.

**Never put the time worked in the description.** No start and end times, no duration. The event's own start and end are the sole record of time spent, so the user can drag or resize the event without a description that then contradicts it. Keep the after-hours or weekend marker, just without the clock.

## Step 6: Write the time records

Write exactly the rows the user approved in Stage 2: same dates, projects, Activity Types, hours, and notes. Never recompute hours, never combine or split approved rows, and never adjust anything between the approval and the insert. A row marked "Adds to" is a same-day merge: its PATCH sets the record's hours to the booked hours plus the approved hours, the total shown in the row. If something has to change (a picklist value is rejected, a record turns out to exist already), stop, show the changed rows and ask again before writing them.

One record per date, per project, per Activity Type, using the project and task Ids from the profile and the payload in the reference. Hours for each row are the hours approved in Stage 2. Write each payload to a temporary file, run `check_record.py <payload file>` from this folder on it (`--update` for a same-day merge), and go on only when it prints OK. **Never insert or update a record that doesn't pass**, and never invent a value or edit the hours to make it pass: say which row stopped and what is missing, get the value from the user, show the changed row, and go on with the others. Run Python as in Step 8; if Python isn't available, check the fields by hand against *Required values* in the reference. Insert one at a time so the org's flows fire the way they do from the UI. Each insert takes several seconds, so keep the user informed: after every few records, print one line such as "12 of <total> written", and finish with "All <total> written." A same-day merge (Step 1) is a PATCH of hours and both notes fields on the existing record, using the *update* call in the reference; nothing else on the record is touched. Notes are the calendar event titles as written, label prefix included, comma-joined. A meeting with a matched recording (Step 2) has a short topic phrase after its title, in parentheses: `ClientA: Sprint planning (cutover scope, test data)`. The calendar event itself isn't changed.

### Choosing the Activity Type

`Activity_Type__c` is a restricted picklist **scoped by record type**. Use only values in the profile's `picklists` for that record type; the tables below are the defaults. If a table names a value the profile doesn't have, say so and ask which allowed value to use. If an insert is rejected for a picklist value, read the allowed values again and update `picklists` before retrying. Pick from the evidence, not by habit. Collapsing everything into Coding and Configuration and Meeting misreports the work.

| What the block produced | Activity Type |
| --- | --- |
| A written deliverable: register updates, guides, reports, internal notes, plan CSVs, doc revisions | **Documentation** |
| Client or team correspondence: Slack threads, email drafting, Notion pushes, chasing answers | **Communications** |
| Solo work producing config, metadata, scripts, queries, workbooks | **Coding and Configuration** |
| The calendar event has attendees | **Meeting** |
| Ambiguous client work, or genuinely mixed | `work.unclear_activity_type`, or **Coding and Configuration** when the profile has none |

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

Run the *created today* query from the reference and confirm the automation-populated fields match the user's existing records. Internal records legitimately have no Monthly Billing Summary; client records should have one. Confirm none of the records written has zero or blank hours, or a blank standard field (*Required values* in the reference). If one does, say so and name it; fixing it is the user's call.

Report record names, day totals, and anything still unaccounted for.

## Step 8: Refresh the dashboards

Run this right after Step 7, on every run that wrote at least one time record. It never waits for the user to ask for a report. time-report is installed beside this skill; its script is `../time-report/time_report.py` from this folder. Run Python as python3 on a Mac, and as py -3 on Windows (or python if that is the one that prints a Python 3 version).

- **Local dashboard, inline.** Run `time_report.py week --dashboard`, then open the file it wrote in the system browser, not a browser inside the agent app: `open "<path>"` on a Mac; on Windows, `Start-Process "<path>"` in PowerShell, or `start "" "<path>"` in cmd or Git Bash. Also give the `file://` link the script prints, in case the browser didn't open. It takes seconds.
- **Salesforce dashboard, as a link.** Look up *My Hours - Dashboard 2.0* with the *time dashboard* query in the reference, and give the link built from the org's `instanceUrl` (from `sf org display -o <alias> --json`): `<instanceUrl>/lightning/r/Dashboard/<Id>/view`. Say it's the company's own view of the same records, and that its Refresh button updates it. If the query finds nothing, leave the link out without comment.
- **Published dashboard, in the background.** Only when the profile has `dashboard.artifact_url`. Launch one background agent (the Agent tool) on a small, fast model, passing the model explicitly; the work is mechanical. Brief it with the artifact URL, the user's name, and the *Published dashboard* procedure in time-report's `SKILL.md`, which it follows step by step. Do not wait for it: finish the Step 7 report, and pass on its one-line result when it arrives. If it fails, say so, with what failed; the time records are already written and correct either way.

If either refresh lists *Forecast left out* or *Pipeline staffing*, mention each in one line. If the Artifact tools are not available in the session, skip the published refresh and say so.

## Standing conventions

These hold for everyone. Per-user rules live in the profile's `conventions` list and are read at the start of every run.

- Recurring stand-ups log at their true length, usually **0.25h**.
- Meetings with attendees are **Meeting**; solo client blocks whose evidence doesn't settle it take `work.unclear_activity_type` (**Coding and Configuration** when there is none), but check the Activity Type tables first.
- Work spanning midnight is split at midnight and lands on the day it happened.
- When meetings overlap, ask which one they attended. The other is trimmed or dropped.
- Overlapping events on the calendar are fine. On time records no minute is booked twice; the *Overlapping sources* order decides who gets it.
- Client-facing work is billable even when it is tooling or enablement, if it was built for a client deliverable.
- Meetings titled `[Internal]` are still billable to the client project they serve. Internal does not mean non-billable.
- **The org rejects time records dated in a previous month.** Check this before proposing a backfill that crosses a month boundary. If work is stranded in a closed month, ask where it should land. Never silently move hours across dates, and never move an hour that a closed record already bills, or it gets billed twice.

If a convention here ever conflicts with what the user says in the moment, they win. If they state a rule that should persist, add it to their profile's `conventions` and say you did.
