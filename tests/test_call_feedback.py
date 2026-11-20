"""Pins the changes that came out of the first two teammate setups (1.19.0)."""
import html
import json
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
LOG = "skills/log-time/SKILL.md"
REPORT = "skills/time-report/SKILL.md"


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def section(text, start, end):
    """Text from the heading `start` up to the heading `end`."""
    i = text.index(start)
    return text[i:text.index(end, i + len(start))]


def test_version_is_1_19_0():
    for p in (LOG, REPORT):
        assert re.search(r"^version: 1\.19\.0$", read(p), re.M), p
    assert "## 1.19.0 (" in read("CHANGELOG.md")


# Approval in two stages, calendar events first

def test_propose_has_two_stages_calendar_first():
    s = section(read(LOG), "## Step 4", "## Step 5")
    cal = s.index("### Stage 1: calendar events")
    rec = s.index("### Stage 2: time records")
    assert cal < rec
    assert "One approval covers both" not in s


def test_time_records_wait_for_the_calendar_check():
    s = section(read(LOG), "### Stage 2: time records", "## Step 5")
    assert "after the calendar events are written" in s
    assert "checked their calendar" in s


def test_proposal_templates_are_fixed():
    s = section(read(LOG), "## Step 4", "## Step 5")
    for line in ("## Proposed calendar events", "## Proposed time records",
                 "**Needs your call", "**Unaccounted,", "**By project**",
                 "These are exactly what will be written. Write them?"):
        assert line in s, line
    assert "Use these templates exactly" in s


def test_same_day_edit_rule_is_explained_before_writing():
    s = section(read(LOG), "### Stage 2: time records", "## Step 5")
    assert "changed later only on the day they were written" in s


# Writes

def test_records_written_are_exactly_the_approved_rows():
    s = section(read(LOG), "## Step 6", "### Choosing the Activity Type")
    assert "exactly the rows the user approved" in s
    assert "show the changed rows and ask again" in s


def test_progress_is_shown_while_records_are_written():
    s = section(read(LOG), "## Step 6", "### Choosing the Activity Type")
    assert "of <total> written" in s


def test_calendar_events_carry_the_project_color():
    s = section(read(LOG), "## Step 5", "## Step 6")
    assert "colorId" in s
    assert "color_id" in s


def test_old_last_record_asks_for_a_range():
    s = section(read(LOG), "## Step 1", "## Step 2")
    assert "more than 14 days" in s


# Setup questions

def test_setup_asks_for_timezone_from_the_computer():
    s = section(read(LOG), "### Setup (first run)", "### Directory matching")
    assert "What timezone do you work in?" in s
    assert "the computer's timezone" in s


def test_setup_asks_about_google_tasks_and_names_the_limit():
    s = section(read(LOG), "### Setup (first run)", "### Directory matching")
    assert "Google Tasks" in s
    assert "can't see Google Tasks" in s


def test_setup_asks_about_color_coding():
    s = section(read(LOG), "### Setup (first run)", "### Directory matching")
    assert "Do you color-code projects on your calendar?" in s


def test_profile_example_has_the_new_fields():
    p = json.loads(read("skills/log-time/profile.example.json"))
    assert "uses_google_tasks" in p["rhythm"]
    assert all("color_id" in proj for proj in p["projects"])


def test_setup_questions_say_why():
    s = section(read(LOG), "### Setup (first run)", "### Directory matching")
    assert "Labels go at the front of every calendar event" in s
    assert "Every user logs internal time" in s


# Dashboards

def test_log_time_opens_the_dashboard_in_the_system_browser():
    s = section(read(LOG), "## Step 8", "## Standing conventions")
    assert "Do not open the browser" not in s
    assert "system browser" in s
    assert 'Start-Process "<path>"' in s


def test_salesforce_dashboard_is_looked_up_by_name():
    for p, start, end in ((LOG, "## Step 8", "## Standing conventions"),
                          (REPORT, "# ", "\n## ")):
        t = read(p) if p == REPORT else section(read(p), start, end)
        assert "My Hours - Dashboard 2.0" in t, p
    assert "Title = 'My Hours - Dashboard 2.0'" in read("skills/log-time/reference/taskray.md")


# Setup and docs

def test_setup_signs_in_on_the_kicksaw_domain():
    t = read("SETUP.md")
    assert "--instance-url https://kicksaw.my.salesforce.com" in t
    assert "login.salesforce.com" not in t
    assert "the tab that opens" in t


def test_readme_sends_an_agent_to_setup_first():
    top = "\n".join(read("README.md").splitlines()[:8])
    assert "raw.githubusercontent.com/bbold-bb/kicksaw-time-skills/main/SETUP.md" in top


def test_guide_has_how_a_run_goes_and_the_code_tab():
    g = html.unescape(read("docs/time-skills-guide.html"))
    assert "How a run goes" in g
    assert "Code tab" in g
    assert "My Hours - Dashboard 2.0" in g
