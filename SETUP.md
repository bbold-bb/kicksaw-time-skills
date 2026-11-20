# Set up the Kicksaw time skills

For the agent (Claude Code or Codex) helping someone set up `log-time` and `time-report`. They may not be technical and may have nothing installed but you. Work through the steps in order. Each step is **check, then fix if needed, then check again**. Say short, plain lines to the user as you go; the lines in quotes are what to say. Never paste raw command output at them unless they ask.

Two rules hold throughout:

- **No passwords in chat.** Never ask for, type, or handle a password or any credential. Installers and the browser ask the user directly, and they type their own password there.
- **Never touch `~/.claude/kicksaw-time/`.** That folder holds the user's profile and dashboards. The only thing setup reads from it is `org_alias` in `profile.json`, in step 6.

Install only into the folder for the agent you are: `~/.claude/skills/` for Claude Code, `~/.agents/skills/` for Codex. Never into both, never anywhere else.

**Which branch.** You fetched this file from `https://raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/<branch>/SETUP.md`. Note `<branch>` (normally `main`) and use the same one wherever `<branch>` appears below.

## Before you start

Say this first, as written:

"I'll check what's already set up and install what's missing. You'll see prompts asking you to allow commands and downloads. Allow is right for these steps, and I'll say what each one is for just before it appears."

Then, before every command or download that will raise an approval prompt, say in one plain line what the next prompt is for, such as "Next you'll be asked to allow a download of the Salesforce CLI installer from Salesforce." Never change the user's permission settings or modes, and never write permission rules. In Codex, the same goes for its sandbox prompts for network access and for folders outside the project.

## 1. Detect

Find the system and the processor:

- macOS: `uname -sm` (`Darwin arm64` is Apple Silicon, `Darwin x86_64` is Intel).
- Windows (PowerShell): `$env:PROCESSOR_ARCHITECTURE` (`AMD64` is x64).

Windows on ARM and Linux desktops aren't supported yet: say so plainly and stop.

On Windows, run the PowerShell forms below. If your shell tool is bash (Git Bash), run each block through `powershell.exe -NoProfile -Command`.

Tell the user in one line what you found, for example "You're on a Mac with Apple Silicon, using Claude Code."

## 2. Check everything, then ask once

Run every check in steps 3 to 7 without changing anything. Show a short table: each item (skills, Salesforce CLI, Python, Kicksaw org sign-in, Google Calendar, Slack) and whether it's ready or missing.

If anything in steps 3 to 5 is missing, ask one question (the option pop-up in Claude Code, a numbered list in Codex): "I'll install <the missing items> from <each one's official source: GitHub for the skills, Salesforce for the CLI, python.org for Python>. Each installer's standard license terms apply. OK to go ahead?" Download nothing before a yes. On a no, stop and say they can paste the setup line again any time.

If nothing is missing, skip to step 7.

## 3. Skills

**Check.** Both `<skills folder>/log-time/SKILL.md` and `<skills folder>/time-report/SKILL.md` exist, and the `version:` line of each matches the one in `https://raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/<branch>/skills/log-time/SKILL.md`.

**Fix.** Download the repo archive for the same branch into a new, empty temporary folder, extract it there, find the single top-level folder it created (don't guess its name), and replace each skill folder whole: remove it, then copy the new one in, so it can never end up nested inside the old one. Each block below stops before removing anything if the download or extract failed, so a failed update never deletes a working install. Run each block as one command: your shell doesn't keep variables between commands.

Replace `<skills folder>` with exactly one of these, for the agent you are:

| Agent | macOS | Windows (PowerShell) |
| --- | --- | --- |
| Claude Code | `~/.claude/skills` | `$HOME\.claude\skills` |
| Codex | `~/.agents/skills` | `$HOME\.agents\skills` |

macOS:

```
T=$(mktemp -d) &&
curl -fsSL -o "$T/skills.zip" "https://github.com/bbold-bb/kicksaw-time-skills/archive/refs/heads/<branch>.zip" &&
unzip -q "$T/skills.zip" -d "$T/x" &&
SRC=$(find "$T/x" -mindepth 1 -maxdepth 1 -type d) &&
[ -f "$SRC/skills/log-time/SKILL.md" ] && [ -f "$SRC/skills/time-report/SKILL.md" ] &&
D=<skills folder> && mkdir -p "$D" &&
for s in log-time time-report; do rm -rf "${D:?}/${s:?}" && cp -R "$SRC/skills/$s" "$D/$s"; done
rm -rf "${T:?}"
```

Windows (PowerShell):

```
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'Stop'
$T = Join-Path $env:TEMP ("kts-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $T | Out-Null
try {
  Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/bbold-bb/kicksaw-time-skills/archive/refs/heads/<branch>.zip" -OutFile "$T\skills.zip"
  Expand-Archive -Path "$T\skills.zip" -DestinationPath "$T\x"
  $Src = (Get-ChildItem "$T\x" -Directory | Select-Object -First 1).FullName
  foreach ($s in "log-time", "time-report") {
    if (-not (Test-Path (Join-Path $Src "skills\$s\SKILL.md"))) { throw "The download didn't contain $s." }
  }
  $D = "<skills folder>"
  New-Item -ItemType Directory -Force -Path $D | Out-Null
  foreach ($s in "log-time", "time-report") {
    Remove-Item -Recurse -Force (Join-Path $D $s) -ErrorAction SilentlyContinue
    Copy-Item -Recurse (Join-Path $Src "skills\$s") (Join-Path $D $s)
  }
} finally {
  Remove-Item -Recurse -Force $T -ErrorAction SilentlyContinue
}
```

Check again.

## 4. Salesforce CLI

**Check.** `sf --version` prints a version.

**Fix.** Download Salesforce's official installer and start it. Don't use `winget` for this one: its Salesforce package is an old, retired version.

macOS: say "The Salesforce installer will open. Click through it; it will ask for your own Mac password, which you type into the installer, not here." Then:

```
curl -fsSL -o "$TMPDIR/sf.pkg" "https://developer.salesforce.com/media/salesforce-cli/sf/channels/stable/sf-arm64.pkg"
open "$TMPDIR/sf.pkg"
```

Use `sf-x64.pkg` instead on an Intel Mac. Wait until the user says the installer finished.

Windows (PowerShell): say "The Salesforce installer will open. Click Yes when Windows asks whether it can make changes, then click through it." Then run this with a 10-minute timeout, since it waits for the installer to close:

```
$ProgressPreference = 'SilentlyContinue'
$Exe = Join-Path $env:TEMP "sf-x64.exe"
Invoke-WebRequest -UseBasicParsing -Uri "https://developer.salesforce.com/media/salesforce-cli/sf/channels/stable/sf-x64.exe" -OutFile $Exe
Start-Process -FilePath $Exe -Wait
```

**Check again.** Your shell may have read its PATH before the install, so `sf` can still be "not found" even though it installed. If so, use the full path for the rest of this session:

- macOS: `/usr/local/bin/sf --version`
- Windows (PowerShell): `& "C:\Program Files\sf\bin\sf.cmd" --version`

The time report finds those paths on its own. On a Mac, a new session finds `sf` normally. On Windows, tell the user: "When we're done, quit Claude and open it again, so it picks up the new install. Starting a new session isn't enough."

## 5. Python

Only the time report and the dashboard need Python. Logging time doesn't, so if this step fails, say so and carry on.

**Check.** The command must print `Python 3.` and a version.

- macOS: `python3 --version`. If macOS offers to install Apple's command line developer tools instead, that's fine: the user can accept it, and it provides Python 3.
- Windows (PowerShell): `py -3 --version`, then `python --version`. On a new Windows machine, `python` may be the Microsoft Store shortcut, which opens the Store or prints nothing instead of a version. That counts as missing.

**Fix.**

macOS: find the current Python 3 installer on python.org and open it:

```
PKG=$(curl -fsSL https://www.python.org/downloads/macos/ | grep -o 'python-3\.[0-9]*\.[0-9]*-macos11\.pkg' | head -1)
V=$(echo "$PKG" | sed -E 's/python-([0-9.]+)-macos11\.pkg/\1/')
curl -fsSL -o "$TMPDIR/$PKG" "https://www.python.org/ftp/python/$V/$PKG"
open "$TMPDIR/$PKG"
```

Say "The Python installer will open. Click through it; it may ask for your own Mac password, which you type into the installer."

Windows (PowerShell): install for this user only, so no extra Windows prompt is needed:

```
winget install --id Python.Python.3.14 -e --scope user --accept-package-agreements --accept-source-agreements
```

If `winget` isn't available, download `python-<version>-amd64.exe` from `https://www.python.org/downloads/windows/`, run it, and tell the user to tick "Add python.exe to PATH" before clicking Install.

**Check again.** If the shell can't find it yet, use the full path for this session:

- macOS: `/usr/local/bin/python3 --version`
- Windows (PowerShell): `& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" --version`

## 6. Org login

**Which org alias.** If `~/.claude/kicksaw-time/profile.json` exists, read only its `org_alias`. Otherwise use `Kicksaw-Prod`.

**Check.**

- macOS and Windows (PowerShell) alike: `sf org display user -o <alias> --json` succeeds.

If it fails and there is no profile yet, run `sf org list --json`. If other orgs are signed in, offer them as options ("Is one of these your Kicksaw login?"), with "Sign in fresh" as the first option. Use the one they pick as `<alias>` for the rest of this step; log-time's setup saves it to the profile. With a profile, keep its `org_alias`.

**Fix.** Say "Your browser will open to Kicksaw's Salesforce sign-in page. Sign in on the tab that opens, with your Kicksaw login, then come back here. If no tab opens, or you closed it, tell me and I'll open it again." Then run this with a 10-minute timeout, since it waits until the browser sign-in finishes (the same command on macOS and Windows (PowerShell); use the full `sf` path from step 4 if needed):

```
sf org login web -a <alias> --instance-url https://kicksaw.my.salesforce.com
```

**Check again** with `sf org display user -o <alias> --json`.

## 7. Connectors

Google Calendar is required. Slack is recommended: without it, logging still works, and every run notes that Slack is off.

**Check** by using each one: list one day of the user's calendar, then run one Slack search for the user's own recent messages. Read only; never send, schedule, or draft anything in Slack.

**Fix.**

- Claude: say "In Claude, open Settings, then Connectors. Connect Google Calendar with your Kicksaw Google account, and Slack with the Kicksaw workspace. Tell me when that's done." Check again when they say so. If a connector still doesn't show up, ask them to start a new session, since connectors load when a session starts.
- Codex: point them to the *Codex* section of the README at `https://github.com/bbold-bb/kicksaw-time-skills#codex`, which covers connecting Calendar and Slack in Codex.

## 8. Hand off

Show the final table: each item and whether it's ready.

- **A profile already exists** (`~/.claude/kicksaw-time/profile.json`): don't start a run. Say: "You're all set. When you want to log time, say "log my time"." If anything above was missing, add one line on what you fixed. End with: say "log my time" whenever you're ready.
- **No profile yet:** start log-time's first-run setup now, which reads the org and asks with clicks. If you can't see the `log-time` skill you just installed, say: "Start a new session, then say "log my time", and setup will begin."

## If a step fails

Try once more where that makes sense (a download that timed out, a sign-in window closed by accident). If it still fails, stop that step and tell the user, in one or two plain sentences, what didn't work and the one thing to do next. Then carry on with any steps that don't depend on it, and list what's still missing in the step 8 table. Paste the setup line again later to pick up where this left off.
