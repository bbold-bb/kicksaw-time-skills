# Guided setup implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A teammate with only Claude desktop or Codex pastes one line and the agent installs the skills, the Salesforce CLI and Python, signs them in, checks connectors, and hands off to log-time's setup, on macOS and Windows.

**Architecture:** A new `SETUP.md` at the repo root is the agent-facing procedure, fetched raw from GitHub through the shell. The skills get Windows fixes: `time_report.py` resolves `sf` through `shutil.which`, reads UTF-8, formats dates without `%-`, and builds file links with `Path.as_uri()`; the SKILL.md files give per-OS commands and a Windows-aware directory matching rule; log-time gets a preflight that points to `SETUP.md`. Docs lead with the pasted line.

**Tech Stack:** Markdown skill text, Python 3 standard library, pytest (fakes only).

**Spec:** `docs/superpowers/specs/2026-11-20-guided-setup-design.md`

## Global Constraints

- The pasted line, verbatim everywhere it appears: `Download https://raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/main/SETUP.md with your shell, read all of it, and follow it to set up the Kicksaw time skills.`
- Skills archive: `https://github.com/bbold-bb/kicksaw-time-skills/archive/refs/heads/<branch>.zip`, where `<branch>` is the branch `SETUP.md` was fetched from (`main` normally).
- Skill folders: `~/.claude/skills/` for Claude Code, `~/.agents/skills/` for Codex. Install only into the current agent's folder. Never read or write `~/.claude/kicksaw-time/` except setup reading the profile's `org_alias`.
- No password or credential is ever typed or requested in chat. Nothing is downloaded before the user's one yes in setup step 2.
- Default org alias `Kicksaw-Prod`. Slack is read-only everywhere.
- Platforms: macOS arm64 and x64, Windows 10/11 x64. Codex tested on macOS only.
- No em dashes. Sentence-case headings. The *Wording rule* in log-time stays intact. No people, clients or record Ids (the repo is public; `tests/test_repo_hygiene.py` must pass).
- Release 1.18.0: every `SKILL.md` `version:` line plus a dated CHANGELOG entry. Ship by PR against `main` on `bbold-bb/kicksaw-time-skills`.
- Run tests with `python3 -m pytest -q tests`.

## Review Focus

1. **The shell can't find `sf` right after installing it**, because the agent's PATH was read before the install. Expected: setup uses the installer's known path for the rest of the session and still finishes. Pinned in Task 4 (`test_setup_names_sf_fallback_paths`).
2. **Windows `python` opens the Microsoft Store** instead of running. Expected: setup treats that as "Python missing", not "Python ready". Pinned in Task 4 (`test_setup_rejects_store_python`).
3. **A second run on a working machine.** Expected: no downloads, no install question, and it ends with "say log my time". Pinned in Task 4 (`test_setup_rerun_is_quiet`).
4. **Paths with spaces**, such as `~/Desktop/Salesforce Projects` or `C:\Users\First Last\...`. Expected: transcript folders still match and the dashboard link opens. Pinned in Task 1 (`test_file_link_handles_spaces`) and Task 3 (the encoding examples include a space).
5. **Non-ASCII project or client names in `sf` output on Windows**, where Python's default encoding is cp1252. Expected: the report prints them, no crash. Pinned in Task 1 (`test_sf_runs_with_utf8`).

---

### Task 1: Make `time_report.py` run on Windows

**Files:**
- Modify: `skills/time-report/time_report.py` (`fetch` at 121-138, `sf_query` at 148-156, date labels at 96, 99, 113, 347, 499, 560, file opens at 55, 356, 363, 421, link at 463)
- Create: `tests/time_report/conftest.py`, `tests/time_report/test_windows.py`

**Interfaces:**
- Produces, in `time_report.py`:
  - `SETUP_URL = "https://github.com/bbold-bb/kicksaw-time-skills#quick-start"`
  - `sf_path() -> str`: `shutil.which("sf")`; when it returns None, `sys.exit()` with: `The Salesforce CLI (sf) isn't installed or isn't on your PATH. To set it up, follow the quick start: ` + `SETUP_URL`.
  - `run_sf(args: list[str]) -> subprocess.CompletedProcess`: runs `[sf_path(), *args]` with `capture_output=True, text=True, encoding="utf-8"`. `fetch` and `sf_query` call it instead of `subprocess.run(["sf", ...])`.
  - `day_label(d: dt.date, weekday: bool = True) -> str`: `"Mon Nov 3"` with weekday, `"Nov 3"` without.
  - `clock(t: dt.datetime) -> str`: `"3:07 PM"`.
  - `file_link(path: str) -> str`: `pathlib.Path(path).resolve().as_uri()`.
- `conftest.py` puts `skills/time-report` on `sys.path` so tests `import time_report`.

- [ ] **Step 1: Write the failing tests** in `tests/time_report/test_windows.py`:

```python
def test_sf_resolved_through_which(monkeypatch):
    monkeypatch.setattr(time_report.shutil, "which", lambda name: r"C:\sf\bin\sf.cmd" if name == "sf" else None)
    assert time_report.sf_path() == r"C:\sf\bin\sf.cmd"

def test_missing_sf_points_to_setup(monkeypatch):
    monkeypatch.setattr(time_report.shutil, "which", lambda name: None)
    with pytest.raises(SystemExit) as e:
        time_report.sf_path()
    assert time_report.SETUP_URL in str(e.value)

def test_sf_runs_with_utf8(monkeypatch):
    seen = {}
    monkeypatch.setattr(time_report.shutil, "which", lambda name: "/usr/local/bin/sf")
    def fake_run(cmd, **kw):
        seen.update(kw, cmd=cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout='{"result":{"records":[{"Name":"Café Ñandú"}]}}', stderr="")
    monkeypatch.setattr(time_report.subprocess, "run", fake_run)
    assert time_report.sf_query({"org_alias": "Kicksaw-Prod"}, "SELECT Name FROM X") == [{"Name": "Café Ñandú"}]
    assert seen["encoding"] == "utf-8" and seen["cmd"][0] == "/usr/local/bin/sf"

def test_day_label_has_no_padding():
    assert time_report.day_label(dt.date(2026, 11, 3)) == "Tue Nov 3"
    assert time_report.day_label(dt.date(2026, 11, 3), weekday=False) == "Nov 3"

def test_clock_has_no_padding():
    assert time_report.clock(dt.datetime(2026, 11, 3, 15, 7)) == "3:07 PM"

def test_no_dash_flag_in_strftime():
    assert "%-" not in open(time_report.__file__, encoding="utf-8").read()

def test_every_open_names_utf8():
    # AST walk: every call to the builtin open() in time_report.py passes encoding="utf-8"

def test_file_link_handles_spaces(tmp_path):
    p = tmp_path / "Salesforce Projects" / "dash.html"
    p.parent.mkdir(); p.write_text("x")
    link = time_report.file_link(str(p))
    assert link.startswith("file:///") and "Salesforce%20Projects" in link
```

- [ ] **Step 2: Run them to see them fail.** Run: `python3 -m pytest -q tests/time_report`. Expected: failures on missing `sf_path`, `day_label`, `clock`, `file_link`, and the `%-` and `open()` checks.
- [ ] **Step 3: Implement the interfaces above** and switch every call site: date f-strings to `day_label`, the `generated` stamp to `f"{day_label(now)}, {now.year} at {clock(now)}"`, every `open()` to `encoding="utf-8"`, and the printed link at 463 to `file_link(out)`.
- [ ] **Step 4: Run the whole suite.** Run: `python3 -m pytest -q tests`. Expected: all pass.
- [ ] **Step 5: Smoke test against the real org (read-only).** Run: `python3 skills/time-report/time_report.py week --by-day`. Expected: the same report as before the change, dates printed as `Mon Nov 17`.
- [ ] **Step 6: Commit.** `git commit -m "time-report runs on Windows: sf through which, UTF-8, unpadded dates, file links"`

### Task 2: Per-OS commands in the skill text

**Files:**
- Modify: `skills/time-report/SKILL.md` (*Run it* at 19-23, *Dashboard* at 43), `skills/log-time/SKILL.md` (Step 8 at 267-273)
- Create: `tests/test_skill_text.py`

**Interfaces:**
- Produces: the sentence used in both files, verbatim: `Run Python as python3 on a Mac, and as py -3 on Windows (or python if that is the one that prints a Python 3 version).`

- [ ] **Step 1: Write the failing tests** in `tests/test_skill_text.py`:

```python
PY_LINE = "Run Python as python3 on a Mac, and as py -3 on Windows (or python if that is the one that prints a Python 3 version)."

def test_python_command_per_os():
    for p in ("skills/time-report/SKILL.md", "skills/log-time/SKILL.md"):
        assert PY_LINE in read(p), p

def test_dashboard_open_per_os():
    t = read("skills/time-report/SKILL.md")
    assert 'open "<path>"' in t and 'start "" "<path>"' in t
```

- [ ] **Step 2: Run it to see it fail.** Run: `python3 -m pytest -q tests/test_skill_text.py`. Expected: 2 failures.
- [ ] **Step 3: Edit the two SKILL.md files.** time-report: `PY_LINE` under *Run it*, and the *Dashboard* sentence becomes "Open it for the user in their browser (`open "<path>"` on a Mac, `start "" "<path>"` on Windows)". log-time Step 8: `PY_LINE` after the first paragraph.
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "Skill text gives the Python and open commands for Mac and Windows"`

### Task 3: Windows-aware directory matching in log-time

**Files:**
- Modify: `skills/log-time/SKILL.md` (*Directory matching* at 67-81, Setup step 5 at 55-56)
- Modify: `tests/test_skill_text.py`

**Interfaces:**
- Produces: a table in *Directory matching* headed `| Working directory | Transcript folder |`, with these four rows exactly:
  - `/Users/name/Desktop/Work/Client_A` → `-Users-name-Desktop-Work-Client-A`
  - `/Users/name/Desktop/Salesforce Projects/Client A` → `-Users-name-Desktop-Salesforce-Projects-Client-A`
  - `C:\Users\name\Code\Client_A` → `C--Users-name-Code-Client-A`
  - `C:\Users\First Last\Code\Client A` → `C--Users-First-Last-Code-Client-A`
- The rule text says: the encoded name comes from the absolute path, drive letter included, with every character that is not a letter or digit replaced by a hyphen; `~` means the home folder (`%USERPROFILE%` on Windows); entries are saved as `~/...` with forward slashes on both systems; a repo matches when its absolute path equals the expanded entry, comparing case-insensitively on Windows. Setup step 5 says repo discovery starts from the home folder on both systems and saves `~/...` paths.

- [ ] **Step 1: Write the failing test** in `tests/test_skill_text.py`. It holds the reference encoder and checks every row of the table against it:

```python
def encode(path):
    return re.sub(r"[^A-Za-z0-9]", "-", path)

def test_directory_examples_match_the_encoder():
    rows = table_rows(read("skills/log-time/SKILL.md"), "| Working directory | Transcript folder |")
    assert len(rows) == 4
    assert any(r[0].startswith("C:\\") for r in rows)
    for path, folder in rows:
        assert encode(path) == folder, path
```

- [ ] **Step 2: Run it to see it fail.** Expected: fails, table not found.
- [ ] **Step 3: Rewrite *Directory matching* and Setup step 5** as described in Interfaces. Keep the existing bare-name compatibility paragraph.
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "log-time matches session folders and repos on Windows"`

The Windows rows are a prediction until Task 7 confirms the real folder names on the Windows trial machine. If they differ, fix the rows and the rule in Task 7.

### Task 4: `SETUP.md`

**Files:**
- Create: `SETUP.md`
- Create: `tests/test_setup_doc.py`

**Interfaces:**
- Consumes: `SETUP_URL` anchor `#quick-start` (Task 6 creates the README heading).
- Produces: `SETUP.md` with these H2 headings in order: `## Before you start`, `## 1. Detect`, `## 2. Check everything, then ask once`, `## 3. Skills`, `## 4. Salesforce CLI`, `## 5. Python`, `## 6. Org login`, `## 7. Connectors`, `## 8. Hand off`, `## If a step fails`. Steps 3 to 6 each contain a `macOS` block and a `Windows (PowerShell)` block.

Content per the spec's *Design* section. Specifics the builder must include:
- *Before you start*: the user-facing opening line, verbatim: `I'll check what's already set up and install what's missing. You'll see prompts asking you to allow commands and downloads. Allow is right for these steps, and I'll say what each one is for just before it appears.` Then the coaching rule: before each command, one plain line naming what the next prompt is for. Never change permission settings or modes. The same applies to Codex's sandbox prompts.
- Step 2: one question listing each missing item with its official source; nothing downloaded before the yes; `If nothing is missing, skip to step 7.`
- Step 3: archive URL from the Global Constraints; extract to a new temp folder; find the single top-level folder inside rather than guessing its name; remove then copy each skill folder; never touch `~/.claude/kicksaw-time/`.
- Step 4: the Salesforce CLI's official installer per platform (`.pkg` launched with `open` on a Mac; the official Windows installer or `winget`). Before writing the URLs or the winget id, check each against Salesforce's current install page with `curl -sI` and use only what resolves. Name the installed `sf` paths to fall back on when the shell doesn't see it yet: `/usr/local/bin/sf` on a Mac and the Windows installer's `bin\sf.cmd`, confirmed on the trial machine.
- Step 5: `python3 --version` on a Mac; on Windows `py -3 --version`, then `python --version`. A result that doesn't print `Python 3.` (the Microsoft Store alias) counts as missing. Install from python.org (Windows per-user with Add to PATH) or a verified `winget` id. A failure here doesn't block logging time; say so.
- Step 6: alias order from the spec (profile `org_alias`, then `Kicksaw-Prod`, then offer logged-in aliases); login with `sf org login web -a Kicksaw-Prod --instance-url https://login.salesforce.com`; never ask for a password.
- Step 7: Calendar required, Slack recommended, checked by calling each connector; exact clicks for Claude desktop's connector settings, checked against the current app; Codex points to the README's *Codex* section.
- Step 8: summary table; with an existing profile, end with `say "log my time" whenever you're ready`; otherwise start log-time's setup; if the new skill isn't visible yet, tell them to start a new session and say "log my time".
- *If a step fails*: one retry where it makes sense, then one or two plain sentences on what to do next; no raw output unless asked.

- [ ] **Step 1: Write the failing tests** in `tests/test_setup_doc.py`:

```python
def test_headings_in_order(): ...           # the ten H2s above, in order
def test_install_steps_cover_both_systems(): # sections 3-6 each contain "macOS" and "Windows (PowerShell)"
def test_archive_url_follows_the_branch():   # contains "archive/refs/heads/" and tells the agent to use the branch it was fetched from
def test_asks_once_before_downloading():     # section 2 contains "If nothing is missing, skip to step 7."
def test_opening_line_verbatim(): ...
def test_setup_names_sf_fallback_paths():    # section 4 contains "/usr/local/bin/sf" and "sf.cmd"
def test_setup_rejects_store_python():       # section 5 contains "Python 3." and "Microsoft Store"
def test_setup_rerun_is_quiet():             # section 8 contains 'say "log my time" whenever you\'re ready'
def test_never_asks_for_a_password():        # no line matches r"(enter|type|paste|give me).{0,20}password" except "their own Mac password" in an installer
def test_no_em_dashes(): ...
```

- [ ] **Step 2: Run them to see them fail.** Expected: all fail, no file.
- [ ] **Step 3: Verify the vendor URLs.** Run `curl -sI` against each Salesforce CLI and Python download URL chosen. Expected: `200` or a redirect to a `200`. Record the URLs in the PR description.
- [ ] **Step 4: Write `SETUP.md`.**
- [ ] **Step 5: Run the suite.** Expected: all pass.
- [ ] **Step 6: Commit.** `git commit -m "SETUP.md: guided setup for Claude Code and Codex on Mac and Windows"`

### Task 5: log-time preflight

**Files:**
- Modify: `skills/log-time/SKILL.md` (Step 0 at 26-28)
- Modify: `tests/test_skill_text.py`

**Interfaces:**
- Consumes: `SETUP.md` raw URL from the Global Constraints.
- Produces: a `### Preflight` subsection at the start of Step 0: if `sf` isn't found, or `sf org display user -o <alias> --json` fails with an auth error (alias from the profile's `org_alias`, or `Kicksaw-Prod` with no profile), stop and offer to run the matching `SETUP.md` steps, fetched through the shell as the pasted line does. Silent when everything is fine.

- [ ] **Step 1: Write the failing test:** `test_log_time_preflight_points_to_setup` asserts Step 0 contains `### Preflight` and the raw `SETUP.md` URL.
- [ ] **Step 2: Run it to see it fail.**
- [ ] **Step 3: Add the subsection.** Setup step 1's "tell them to run `sf org login web`" becomes "run the *Org login* step of `SETUP.md`".
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `git commit -m "log-time preflight points to SETUP.md when the CLI or login is missing"`

### Task 6: Docs and release 1.18.0

**Files:**
- Modify: `README.md` (install section 89 onward), `docs/time-skills-guide.html` (*Before you install* 196-206, install 210-226, footer), `AGENTS.md` (layout block, add `SETUP.md`), `CHANGELOG.md`, `skills/log-time/SKILL.md` and `skills/time-report/SKILL.md` (`version: 1.18.0`)
- Modify: `tests/test_skill_text.py`

**Interfaces:**
- Produces: README heading `### Quick start` (anchor `#quick-start`) as the first item under `## Install`, holding the pasted line in a code block and one sentence: works in Claude desktop's Code tab and in Codex, on a Mac or Windows, and the same line updates or repairs a setup. `npx` and `install.sh` move under `### For technical users`. README's *Codex* section says Codex on Windows is untested.
- Guide: *Before you install* becomes one Required item, "Claude desktop or Codex. Setup installs the rest.", plus the Calendar and Slack items. The install section leads with the pasted line behind a copy button. Footer reads `Kicksaw Time Skills 1.18.0`.

- [ ] **Step 1: Write the failing test:** `test_pasted_line_is_identical_everywhere` asserts the Global Constraints line appears verbatim in `README.md` and `docs/time-skills-guide.html` (HTML-unescaped).
- [ ] **Step 2: Run it to see it fail.**
- [ ] **Step 3: Make the doc edits, the version bumps, and a `## 1.18.0 (<date>)` CHANGELOG entry** covering guided setup, Windows support, and the preflight.
- [ ] **Step 4: Run the suite.** Expected: all pass, including `test_skill_versions_match_the_changelog`.
- [ ] **Step 5: Commit, push the branch, and open the PR** against `main`. In the PR body, list the trial checklist from Task 7, unticked.

### Task 7: Trial runs, then merge

Manual. Each run uses the pasted line with `main` replaced by the branch name (`feature/guided-setup`). Record in the PR, per run: each step's result, every approval prompt shown, and anything confusing.

- [ ] **Step 1: macOS.** Create a new, empty standard user account on the Mac. Sign in to Claude desktop, open the Code tab, paste the line. Expected: it reaches log-time's setup with the CLI, Python and login done. Sign in with a real Kicksaw login. Don't save a profile or write records.
- [ ] **Step 2: Windows.** In the Parallels Windows VM: install Claude desktop by hand, open the Code tab, paste the line. Expected: same as Step 1. Also run a Claude session in a test folder such as `C:\Users\<you>\Code\Client A`, then compare the folder name under `%USERPROFILE%\.claude\projects` with Task 3's rows, and fix them if they differ. Run `time-report` once to check the Task 1 fixes.
- [ ] **Step 3: Codex, macOS.** In Codex, paste the line. Expected: it installs to `~/.agents/skills` and nowhere else.
- [ ] **Step 4: Second run.** On the Step 1 machine, paste the line again. Expected: nothing downloaded, no install question, ends with "say log my time".
- [ ] **Step 5: Fix what the trials found**, run the suite, push, and update the PR checklist.
- [ ] **Step 6: Merge the PR**, pull `main`, and reinstall on this Mac with the pasted line to confirm `main` works. Delete the trial user account afterwards.
