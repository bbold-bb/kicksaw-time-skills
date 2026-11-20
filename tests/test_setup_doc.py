"""SETUP.md is followed by an agent on someone else's machine. These pin what it must say."""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
HEADINGS = [
    "## Before you start", "## 1. Detect", "## 2. Check everything, then ask once", "## 3. Skills",
    "## 4. Salesforce CLI", "## 5. Python", "## 6. Org login", "## 7. Connectors", "## 8. Hand off",
    "## If a step fails",
]
OPENING = ("I'll check what's already set up and install what's missing. You'll see prompts asking you to "
           "allow commands and downloads. Allow is right for these steps, and I'll say what each one is for "
           "just before it appears.")


def text():
    with open(os.path.join(ROOT, "SETUP.md"), encoding="utf-8") as fh:
        return fh.read()


def section(heading):
    t = text()
    start = t.index(heading + "\n")
    nxt = t.find("\n## ", start + len(heading))
    return t[start:] if nxt == -1 else t[start:nxt]


def test_headings_in_order():
    found = [line for line in text().splitlines() if line.startswith("## ")]
    assert found == HEADINGS


def test_install_steps_cover_both_systems():
    for h in HEADINGS[3:7]:
        s = section(h)
        assert "macOS" in s and "Windows (PowerShell)" in s, h


def test_archive_url_follows_the_branch():
    s = section("## 3. Skills")
    assert "https://github.com/bbold-bb/kicksaw-time-skills/archive/refs/heads/" in s
    assert "branch" in s


def test_asks_once_before_downloading():
    assert "If nothing is missing, skip to step 7." in section("## 2. Check everything, then ask once")


def test_opening_line_verbatim():
    assert OPENING in section("## Before you start")


def test_setup_names_sf_fallback_paths():
    s = section("## 4. Salesforce CLI")
    assert "/usr/local/bin/sf" in s and "sf.cmd" in s


def test_setup_rejects_store_python():
    s = section("## 5. Python")
    assert "Python 3." in s and "Microsoft Store" in s


def test_setup_rerun_is_quiet():
    assert 'say "log my time" whenever you\'re ready' in section("## 8. Hand off")


def test_never_asks_for_a_password():
    for line in text().splitlines():
        if re.search(r"(enter|type|paste|give me).{0,20}password", line, re.I):
            assert "their own" in line or "your own" in line, line


def test_never_touches_profile_folder_except_alias():
    t = text()
    assert "Never touch `~/.claude/kicksaw-time/`" in t or "never touch `~/.claude/kicksaw-time/`" in t


def test_no_em_dashes():
    assert "—" not in text()


def code_blocks(s):
    return re.findall(r"```\n(.*?)```", s, re.S)


def test_login_uses_the_chosen_alias():
    s = section("## 6. Org login")
    assert "sf org login web -a <alias>" in s
    assert "sf org login web -a Kicksaw-Prod" not in s


def test_download_failure_keeps_the_old_skills():
    blocks = code_blocks(section("## 3. Skills"))
    mac, win = blocks[0], blocks[1]
    assert mac.index('[ -f "$SRC/skills/log-time/SKILL.md" ]') < mac.index("rm -rf")
    assert win.index("throw") < win.index("Remove-Item -Recurse -Force (Join-Path")
    assert 'rm -rf "${T:?}"' in mac and "Remove-Item -Recurse -Force $T" in win


def test_skills_folder_is_a_placeholder():
    for b in code_blocks(section("## 3. Skills")):
        assert "<skills folder>" in b
        assert ".claude/skills" not in b and ".claude\\skills" not in b


def test_full_paths_are_runnable_in_powershell():
    assert '& "C:\\Program Files\\sf\\bin\\sf.cmd" --version' in section("## 4. Salesforce CLI")
    assert '& "$env:LOCALAPPDATA\\Programs\\Python\\Python314\\python.exe" --version' in section("## 5. Python")


def test_windows_downloads_hide_the_progress_bar():
    for h in ("## 3. Skills", "## 4. Salesforce CLI"):
        win = [b for b in code_blocks(section(h)) if "Invoke-WebRequest" in b]
        assert win and all(b.startswith("$ProgressPreference = 'SilentlyContinue'") for b in win), h


def test_long_steps_get_a_long_timeout():
    for h in ("## 4. Salesforce CLI", "## 6. Org login"):
        assert "10-minute timeout" in section(h), h


def test_windows_says_to_reopen_claude():
    assert "quit Claude and open it again" in section("## 4. Salesforce CLI")
