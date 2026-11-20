# Kicksaw time skills

Instructions for Codex and other coding agents working in this repo. Claude Code reads the same rules from the skills themselves; this file covers the repo.

## What this repo is

Agent skills that Kicksaw consultants use to log and review TaskRay time in the Kicksaw Salesforce org.

| Skill | What it does | Writes? |
| --- | --- | --- |
| `skills/log-time/` | Rebuilds unlogged work from the calendar, Slack, session transcripts and git, proposes calendar events and time records, and writes them after the user approves | Yes, after approval |
| `skills/time-report/` | Reports logged time by project and activity type, pace, and an HTML dashboard | No |

Each skill is a folder with a `SKILL.md` (frontmatter plus the process), reference files, and scripts. The user's profile lives at `~/.claude/kicksaw-time/profile.json` for every agent, Codex included, so one profile serves Claude Code and Codex. It is never in this repo.

## Using the skills from Codex

Install with `./install.sh --codex` (into `~/.agents/skills`) or `npx skills add bbold-bb/kicksaw-time-skills --agent codex --global --skill '*'`. Then say "log my time" or `$log-time`, and "how am I pacing" or `$time-report`. The README's *Codex* section lists what differs from Claude Code.

When a skill says to use the option pop-up (`AskUserQuestion`), ask the same question as a short numbered list and accept numbers as the answer.

## Working on the skills

- **One version for all skills.** A release changes the `version:` line in every `SKILL.md` to the same number and adds a dated entry at the top of `CHANGELOG.md`. A change to repo files only (README, install script, this file) needs a changelog note but no version change.
- **Run the tests** before committing: `python3 -m pytest -q tests`. They need nothing but Python and pytest; they never call Salesforce.
- **Ship by pull request** against `main`. Don't push to `main` directly.
- **Never commit user data**: `profile.json`, anything under `~/.claude/kicksaw-time/` (dashboards, exports), org record Ids from a real profile, or pay and cost figures. `.gitignore` covers `profile.json`; the rest lives outside the repo by design.
- **Salesforce safety.** The only org these skills write to is Kicksaw-Prod, and only the time record object. Never test against it with real writes; tests use fakes. Treat every other org as read-only.
- **Slack is read-only** in every skill. Never add a step that sends, schedules or drafts a message.

## Writing rules for skill text and docs

- Plain, direct language. Sentence-case headings. No em dashes; use commas, periods or parentheses.
- Time record notes and calendar events never mention Claude, Codex, AI, sessions, transcripts or how the work was reconstructed (the *Wording rule* in `skills/log-time/SKILL.md`). Keep that rule intact in any edit.
- Name things by what the user sees: "time record", "project", "Activity Type", matching the org's labels.
- Counts and breakdowns go in tables.

## Layout

```
SETUP.md                     guided setup the quick start line points to
skills/<name>/SKILL.md       the process an agent follows
skills/<name>/reference/     org queries, picklists, payloads
skills/<name>/*.py           scripts the skills run (time_report.py)
tests/                       pytest suite, fakes only
docs/time-skills-guide.html  one-page visual guide for consultants
install.sh                   offline installer; --codex for Codex
```
