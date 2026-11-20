# Guided setup

Date: 2026-11-20. Status: draft for approval.

## Intent

Most Kicksaw consultants who would use these skills are not technical, and some are on Windows. Today, getting started means running `npx` (which needs Node.js) or cloning the repo and running `install.sh` (which needs git and a Mac or Linux shell), then installing the Salesforce CLI and Python and logging in, all before log-time's own setup can run. That stops most people before the first click.

Guided setup removes that. A teammate who has only Claude desktop (Code tab) or Codex installed pastes one line, and the agent gets them from nothing to a saved profile, doing every step it can itself and talking them through the few clicks it can't.

**Success:** a non-technical teammate, on a Mac or a Windows laptop, gets to a saved profile without a call with the repo owner. When something fails, they see one plain instruction, never a raw error.

## Starting point

- Claude desktop or Codex, and nothing else: no Node.js, no Python, no Salesforce CLI, no git, no connectors.
- Kicksaw machines are not managed. Users install software themselves with no IT step. On a Mac an installer may ask for the user's own Mac password.
- The repo is public (`bbold-bb/kicksaw-time-skills`), so downloading it needs no GitHub account.
- In Claude Code on Windows without Git for Windows, the shell tool is PowerShell, not bash (Claude Code setup docs, verified 2026-11-20). Every step needs a PowerShell form.

## Goals

1. One pasted line starts setup in Claude Code (desktop or CLI) and in Codex.
2. The agent checks each requirement, fixes what is missing, and skips what is already fine. Running it again repairs or updates a setup.
3. Works on macOS (Apple Silicon and Intel) and Windows 10/11 (x64).
4. Ends by handing off to log-time's existing first-run setup.
5. The skills run on Windows as fully as on a Mac: the report script, the dashboard, log-time's refresh step, and log-time's matching of Claude session history and git folders to projects (the repo owner, 2026-11-20).
6. A non-technical user gets through the app's approval prompts without changing any setting (the repo owner chose coaching, 2026-11-20).

## Non-goals

- Replacing the Salesforce CLI with the Salesforce hosted MCP connector (see *Later*).
- Cowork or plain Claude chat. Guided setup targets the Code tab and Codex, where the agent has a shell.
- Linux desktops, managed or locked-down laptops, Windows on ARM.
- Changing log-time's first-run setup, which is already click-through.

## Anti-goals (a failure even if it works)

- Typing or asking for a password, or any credential, in chat. The user types their own password into the installer or browser.
- Installing anything without first saying what will be installed and from where, and getting one yes.
- Installing into more than the one agent folder the user is in (the `npx` pitfall with `--agent` left off).
- Touching `~/.claude/kicksaw-time/` (profile, dashboards). Setup never reads or replaces it except to hand off to log-time.
- Leaving the user at a stack trace. Every failed check ends with what to do next in one or two sentences.
- Any Slack write, now or as a setup "test".

## Approaches considered

1. **One pasted line plus a `SETUP.md` the agent follows (chosen).** The guide and README give a single line to paste; the agent fetches `SETUP.md` from the public repo and works through it, with a Mac and a Windows form of every step. log-time gets a short preflight that points back to the same steps if the CLI or login breaks later. Trade-off: it relies on the agent following written steps, which is how the skills already work.
2. **A third "time setup" skill in the zip.** Rejected: something must be installed before the setup can run, an uploaded zip may not reach Claude Code, and Codex has no upload.
3. **Setup scripts (`setup.sh`, `setup.ps1`).** Rejected: a script that fails halfway leaves a non-technical user with raw errors, the click-through parts (installers, browser login, connectors) still need the agent, and two scripts need testing on machines we don't have.

The repo owner chose approach 1 on 2026-11-20.

## Design

### The pasted line

Shown at the top of the README install section and the guide's install section, with a copy button:

> Download https://raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/main/SETUP.md with your shell, read all of it, and follow it to set up the Kicksaw time skills.

The same line updates or repairs an existing setup. It says "with your shell" on purpose: a web-fetch tool may hand the agent a summarized page, and a summary can drop steps. *(Builder's call, after the builder check.)*

**Trial runs from a branch.** `SETUP.md` downloads the skills archive from the same branch it was fetched from, so swapping `main` for a branch name in the line runs the whole setup from that branch. That is how the trial runs happen before merge. *(Builder's call.)*

### `SETUP.md` (repo root)

Written for the agent, in the repo's plain style, with short user-facing lines the agent says as it goes. Steps run in order; each is **check, then fix if needed, then re-check**. Every step that installs software is gathered into one confirmation up front (step 2) so the user answers once.

**Approval prompts.** Claude desktop asks the user to approve each command and download. Setup coaches them through it rather than changing any setting: its first message says they will see approval prompts and that Allow is right for these steps, and just before each command it says in one plain line what the next prompt will be for ("Next you'll be asked to allow a download of the Salesforce CLI installer from Salesforce"). It never writes permission rules or switches modes. In Codex, the same coaching covers its sandbox prompts for network access and folders outside the project.

1. **Detect.** OS and CPU (macOS arm64 or x64, Windows x64), which agent this is (Claude Code or Codex), and which shell the agent has (bash/zsh or PowerShell). Tell the user in one line what was found.
2. **Check everything, then ask once.** Run every check below without changing anything. Show a short table of what's ready and what's missing, then one question (option pop-up in Claude Code, numbered list in Codex): "I'll install <missing items> from <official source each>. OK?" Nothing is downloaded before the yes. If nothing is missing, skip to step 7.
3. **Skills.** Check: `~/.claude/skills/log-time/SKILL.md` and `~/.claude/skills/time-report/SKILL.md` (Claude Code) or `~/.agents/skills/...` (Codex) exist and their `version:` matches the repo's latest. Fix: download the repo archive from GitHub (`https://github.com/bbold-bb/kicksaw-time-skills/archive/refs/heads/main.zip`) to a new temp folder, extract it (`unzip` on Mac, `Expand-Archive` on Windows), and replace each skill folder whole (remove then copy, so it never nests). Install only into the current agent's folder. Never touch `~/.claude/kicksaw-time/`.
4. **Salesforce CLI.** Check: `sf --version` runs. Fix: download Salesforce's official installer for the platform and launch it: on a Mac the `.pkg` opened with `open`, where the user clicks through and enters their own Mac password; on Windows the official `.exe` (or `winget`, whichever the builder verifies is cleaner). Then re-check. If the agent's shell doesn't see `sf` yet because PATH was read before the install, use the installer's known path for the rest of the session and tell the user a new session picks it up normally.
5. **Python 3.** Only time-report and the dashboard refresh need it, so a failure here doesn't block logging time; say so. Check: on a Mac `python3 --version` (the built-in stub may offer Apple's Command Line Tools; accepting that is fine); on Windows `py -3 --version`, then `python --version`, ignoring the Microsoft Store alias that opens the Store instead of running. Fix: python.org's official installer for the platform (Windows: per-user install with "Add to PATH"), or `winget` on Windows if verified cleaner.
6. **Org login.** Which alias: the profile's `org_alias` if a profile exists (setup reads only that field), otherwise `Kicksaw-Prod`; if that fails but other orgs are logged in, offer them as options, as log-time's setup already does. *(Builder's call.)* Check: `sf org display user -o <alias> --json` succeeds. Fix: run `sf org login web -a Kicksaw-Prod --instance-url https://login.salesforce.com`, which opens the browser; tell the user to sign in with their Kicksaw Salesforce login and come back. Re-check. If they use SSO or a My Domain, the builder confirms the right instance URL from the org.
7. **Connectors.** Calendar is required, Slack recommended. Check by calling each connector (list one day of the calendar; one Slack search). Claude: if missing, give the exact clicks in Claude's settings to connect Google Calendar on their Kicksaw account and Slack on the Kicksaw workspace, then re-check when they say done. Codex: point to the README's Codex connector notes. Slack missing is a note, not a stop.
8. **Hand off.** Summarize what's ready in a short table. If a profile already exists, stop there and tell them to say "log my time" whenever they're ready; don't start a run. Otherwise start log-time's first-run setup. If the agent can't see a skill it installed this session, tell the user to start a new session and say "log my time".

Failure rule for every step: one retry where it makes sense, then stop with what failed, in plain words, and the one thing to do next. Never paste raw command output at the user unless they ask.

### log-time preflight

At the start of Step 0: if `sf` isn't found, or the org check (the profile's `org_alias`, or `Kicksaw-Prod` with no profile) fails with an auth error, stop and offer to run the matching `SETUP.md` steps (fetch it the same way) rather than printing a login command. Silent when everything is fine.

### Windows fixes in the skills

- **Python command.** time-report's SKILL.md and log-time's Step 8 say: on Windows run the script with `py -3` (or `python` if that's what setup found), on a Mac `python3`.
- **Calling `sf` from Python.** `time_report.py` resolves the CLI with `shutil.which("sf")` (which finds `sf.cmd` on Windows) and runs that path; if it's missing, it exits with one line pointing to `SETUP.md`.
- **Encoding.** `sf` output is read as UTF-8 (`encoding="utf-8"` on `subprocess.run`), and every file `time_report.py` opens is opened with `encoding="utf-8"`.
- **Dates.** `time_report.py` formats dates with `%-d` and `%-I`, which Windows Python rejects; build those parts without the `-` flag so both platforms print the same thing.
- **Python is found fresh each run** (`python3` on a Mac; `py -3`, then `python` on Windows), not saved in the profile. *(Builder's call.)*
- **Opening the dashboard.** SKILL.md gives `open "<path>"` on a Mac and `start "" "<path>"` on Windows.
- **Session history and git folders.** log-time's *Directory matching* and Setup step 5 expect Mac paths. On Windows, Claude Code names its session folders from a path with a drive letter. Matching, the map back to a real path, and repo discovery under the home folder all handle drive letters and backslashes, and the profile still saves paths in `~/...` form with forward slashes. The builder confirms the exact Windows folder naming on the Windows trial machine before writing the rule, and adds tests with Windows-shaped paths.
- **Paths.** Any `~` in SKILL.md or the profile is understood as the user's home folder on Windows too (`%USERPROFILE%`); the profile keeps `~` form.
- `install.sh` stays as the Mac and Linux path for technical users. Windows users use the pasted line.

### Docs

- README: the install section opens with the pasted line, under "Quick start (recommended)". `npx` and `install.sh` move under "For technical users".
- Guide: the "Before you install" requirements collapse into "Have Claude desktop or Codex. Setup installs the rest." The install section leads with the pasted line.
- AGENTS.md: add `SETUP.md` to the layout table.

### Testing

- pytest (fakes only, no Salesforce): `time_report.py` finds `sf` through `shutil.which`, exits with the `SETUP.md` pointer when it's missing, and reads UTF-8 output. `test_repo_hygiene.py` keeps passing.
- A test that the pasted line's URL and the archive URL in `SETUP.md` point at the public repo's `main`.
- **Manual trial runs, required before release, run from the PR branch:**
  - macOS: a new, empty user account on the repo owner's Mac, in the Claude desktop Code tab.
  - Windows: the repo owner's Windows virtual machine in Parallels, which has nothing installed (no Claude, no CLI), in the Claude desktop Code tab. Installing Claude desktop there is the trial's first step, done by hand.
  - Codex: one run on the Mac. Codex on Windows is not tested in this release, and the README says so.
  - Record what each step did, and every approval prompt the user saw, in the PR.

### Release

Skill files change (log-time Step 0 and Step 8, time-report SKILL.md and script), so this ships as **1.18.0**: every `SKILL.md` version line and a dated CHANGELOG entry, by PR against `main` on the public repo.

## Left to the builder

- Exact official download URLs for the Salesforce CLI and Python per platform, and whether `winget` is cleaner than the `.exe` on Windows. Verify against the vendors' current pages; don't guess.
- Whether Claude Code and Codex pick up a skill installed mid-session, which decides whether step 8 can start log-time directly.
- The exact connector-settings clicks for Claude desktop and Codex, checked against the current apps.
- Wording of the user-facing lines in `SETUP.md`, within the repo's writing rules.

## Later (backlog, not in this work)

- **Salesforce connector instead of the CLI.** Use Salesforce's hosted MCP server (SObject All) so logging needs nothing installed. Needs a Salesforce admin to turn it on in Kicksaw-Prod and an app for the connector's login, and a trial against TaskRay's objects.
- **Time from org activity, for admins.** Admins spend most of their time building in client orgs, with little communication or documentation to reconstruct from. Connect to the org they're building in, read its Setup Audit Trail for what they changed and when, and propose time blocks for that project from it.

## Change log

- 2026-11-20: First draft.
- 2026-11-20: After the builder check: pasted line downloads `SETUP.md` through the shell; trials run from a branch; org alias follows the profile; an existing profile ends setup without starting a run; Windows date formats added.
- 2026-11-20: The repo owner's answers: Windows trial on the owner's Parallels VM; coach users through approval prompts; Windows session history and git matching fixed in this release.
