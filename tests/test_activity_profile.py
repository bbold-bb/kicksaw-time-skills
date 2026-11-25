"""Pins the activity profile (1.20.0): how the user works, and where meetings are recorded."""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
LOG = "skills/log-time/SKILL.md"
MEET = "skills/log-time/reference/meetings.md"


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def section(text, start, end):
    i = text.index(start)
    return text[i:text.index(end, i + len(start))]


def setup():
    return section(read(LOG), "### Setup (first run)", "### New questions for existing profiles")


def how():
    return section(setup(), "8. **How you work.**", "9. **Workday, timezone, and save.**")


def recordings():
    return section(read(LOG), "### Meeting recordings", "## Step 3")


# Setup questions

def test_setup_asks_how_the_user_works():
    for q in ("What fills most of your week?", "What takes time but leaves no trace here?",
              "How much of your work goes through Claude?"):
        assert q in how(), q


def test_setup_asks_where_meetings_are_recorded_then_which_are_work_only():
    s = how()
    assert s.index("Where are your meetings recorded or transcribed?") < s.index("Does <tool> hold only work meetings?")
    assert "never list a tool's recordings during setup" in s
    assert '"Personal ones too"' in s
    for tool in ("Notion", "tl;dv", "Zoom", "Wispr Flow", "ZoomInfo (Chorus)", "Plaud", "I don't record"):
        assert tool in s, tool


def test_unconnected_recorder_is_saved_and_never_blocks():
    s = how()
    assert '"connected": false' in s
    assert "never asks for a password" in s


def test_recurring_meetings_without_a_label_are_asked_once():
    s = how()
    assert "3 or more times in the last 30 days" in s
    assert "conventions" in s
    assert "It varies, ask me" in s
    assert "up to two project labels" in s
    assert "`conventions` holds the recurring-meeting answers from step 8" in setup()


def test_workday_step_references_moved():
    log = read(LOG)
    assert "as in Setup step 8, with the profile's current `rhythm.timezone`" not in log
    assert "as in Setup step 9, with the profile's current `rhythm.timezone`" in log
    assert "the timezone is confirmed in step 9" in log
    assert "the summary in step 9 shows it" in log


# Unclear Activity Type

def test_unclear_type_mapping():
    s = how()
    for row in ("| Building and configuring | Coding and Configuration |",
                "| Testing and reviews | Coding and Configuration |",
                "| Documents and design | Documentation |",
                "| Managing projects and clients | Communications |"):
        assert row in s, row


def test_unclear_type_uses_the_profile_and_only_for_client_work():
    s = section(read(LOG), "### Choosing the Activity Type", "## Step 7")
    assert "Ambiguous client work" in s
    assert "`work.unclear_activity_type`" in s
    assert "| Ambiguous, or genuinely mixed | **Coding and Configuration** |" not in s
    conv = section(read(LOG), "## Standing conventions", "If a convention here")
    assert "`work.unclear_activity_type`" in conv


def test_missing_picklists_are_read_first():
    s = section(read(LOG), "### New questions for existing profiles", "### Color for a new project")
    assert "no `picklists`" in s


# Existing profiles

def test_existing_profiles_get_work_questions_once():
    s = section(read(LOG), "### New questions for existing profiles", "### Color for a new project")
    assert "no `work` key" in s
    assert "even with skipped answers, is what marks them as answered" in s
    assert "no `uses_google_tasks`" in s
    assert "Setup step 8" in s


def test_recheck_asks_only_about_new_recorders_or_a_changed_mix():
    s = section(read(LOG), "### Re-verification (every 30 days)", "## Step 1")
    assert "never list a tool's recordings to decide this" in s
    assert "`work.not_used`" in s
    assert "`work.main_work` is empty" in s
    assert "`work.type_checked`" in s
    assert "Skip all of this when the profile has no `work` key" in s


# Using recordings

def test_recordings_never_change_hours_or_prove_attendance():
    s = recordings()
    assert "never adds, lengthens or shortens" in s
    assert "doesn't show that the user attended" in s


def test_only_matched_recordings_are_opened_summary_first():
    s = recordings()
    assert "Open only a matched recording" in s
    assert "only when there is no summary" in s
    assert "Declined events never match" in s
    assert "**both** a start within 15 minutes **and** the same title or a shared attendee" in s
    assert "summary, not the transcript" in s


def test_personal_recordings_stay_out():
    s = recordings()
    assert "titles included" in s
    assert "health, family, pay or performance" in s
    assert "`work_only`" in s
    assert "Never repeat a title or excerpt" in s


def test_unmatched_work_only_recordings_are_asked_not_booked():
    s = recordings()
    assert "5 minutes" in s
    assert "Needs your call" in s
    assert "never booked" in s
    assert "of unknown length" in s
    assert "Never list one that someone else recorded" in s
    assert "ask its project and how long it took" in s


def test_no_recorder_is_fine():
    s = recordings()
    assert "Skip this section" in s
    assert "Check which tools are connected on each run" in s


def test_wording_rule_covers_recordings():
    s = section(read(LOG), "**Wording rule, important.**", "## Step 6")
    assert "recordings" in s


# Reference and profile

def test_meetings_reference_lists_every_tool_and_its_status():
    t = read(MEET)
    for tool in ("Notion", "Wispr Flow", "Plaud", "tl;dv", "Zoom", "ZoomInfo (Chorus)"):
        assert f"| {tool} |" in t, tool
    assert "Not read yet" in t
    assert "Never list Plaud" in t
    assert "reference/meetings.md" in read(LOG)


def test_profile_example_has_work():
    w = json.loads(read("skills/log-time/profile.example.json"))["work"]
    assert set(w) == {"main_work", "unclear_activity_type", "type_checked", "no_trace", "claude_use", "recorders", "not_used"}
    assert all(set(r) == {"tool", "connected", "work_only"} for r in w["recorders"])


def test_queries_are_in_the_reference():
    t = read("skills/log-time/reference/taskray.md")
    assert "**Work pattern**" in t
    assert "Owner_Role__c != null" in t


# Review fixes

def test_recordings_reach_the_notes():
    log = read(LOG)
    phrase = "ClientA: Sprint planning (cutover scope, test data)"
    assert phrase in section(log, "### Stage 2: time records", "## Step 5")
    s6 = section(log, "## Step 6", "### Choosing the Activity Type")
    assert "matched recording" in s6 and "in parentheses" in s6


def test_gap_choices_fit_the_popup_and_get_a_project():
    s = section(read(LOG), "### Stage 1: calendar events", "### Stage 2: time records")
    assert "up to three of those" in s
    assert "which project it was for" in s


def test_claude_use_changes_the_run():
    s = section(read(LOG), "## Step 3", "### Break the block on dead space")
    assert "`work.claude_use`" in s


def test_wording_and_read_only_rules_cover_recordings():
    assert "Meeting recorders are read-only" in section(read(LOG), "## Ground rules", "## Step 0")
    assert "recordings" in section(read("AGENTS.md"), "## Writing rules", "## Layout")


def test_reference_windows_and_shared_results():
    t = read(MEET)
    for s in ("next local midnight", "one day wider", "has started", "`shared`"):
        assert s in t, s


def test_guide_and_readmes_are_current():
    g = read("docs/time-skills-guide.html")
    version = [l for l in read(LOG).splitlines() if l.startswith("version:")][0].split()[1]
    assert g.count("1.19.4") == 1  # only its own What's new entry
    assert g.count(version) >= 3  # hero, footer, What's new
    assert "How you work" in g
    assert "never listed or opened" not in g
    assert "meetings.md" in read("README.md")
    assert "how you work" in read("README.md")
