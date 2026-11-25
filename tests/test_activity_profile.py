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
    assert s.index("Where are your meetings recorded or transcribed?") < s.index("Which of these hold only work meetings?")
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
    assert "no `uses_google_tasks`" in s
    assert "Setup step 8" in s


def test_recheck_asks_only_about_new_recorders_or_a_changed_mix():
    s = section(read(LOG), "### Re-verification (every 30 days)", "## Step 1")
    assert "`work.recorders`" in s
    assert "`work.main_work`" in s


# Using recordings

def test_recordings_never_change_hours_or_prove_attendance():
    s = recordings()
    assert "never adds, lengthens or shortens" in s
    assert "doesn't show that the user attended" in s


def test_only_matched_recordings_are_opened_summary_first():
    s = recordings()
    assert "Open only a matched recording" in s
    assert "summary, not the transcript" in s


def test_personal_recordings_stay_out():
    s = recordings()
    assert "titles included" in s
    assert "health, family, pay or performance" in s
    assert "`work_only`" in s


def test_unmatched_work_only_recordings_are_asked_not_booked():
    s = recordings()
    assert "5 minutes" in s
    assert "Needs your call" in s
    assert "never booked" in s


def test_no_recorder_is_fine():
    assert "Skip this section" in recordings()


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
    assert set(w) == {"main_work", "unclear_activity_type", "no_trace", "claude_use", "recorders"}
    assert all(set(r) == {"tool", "connected", "work_only"} for r in w["recorders"])


def test_queries_are_in_the_reference():
    t = read("skills/log-time/reference/taskray.md")
    assert "**Work pattern**" in t
    assert "Owner_Role__c != null" in t


def test_guide_mentions_the_questions():
    assert "How you work" in read("docs/time-skills-guide.html")
