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


def test_version_is_at_least_1_19():
    for p in (LOG, REPORT):
        assert re.search(r"^version: 1\.(19|[2-9]\d)\.\d+$", read(p), re.M), p
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
    assert "only changes a record on the day it was written" in s


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
    assert "Google Tasks" in s


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


# Review fixes

def test_same_day_merge_adds_to_the_booked_hours():
    log = read(LOG)
    s2 = section(log, "### Stage 2: time records", "## Step 5")
    assert "Adds to" in s2
    s6 = section(log, "## Step 6", "### Choosing the Activity Type")
    assert "booked hours plus the approved hours" in s6
    assert "never combine or split approved rows" in s6


def test_stage_two_reruns_the_dedup_and_keeps_evidence_rank():
    s2 = section(read(LOG), "### Stage 2: time records", "## Step 5")
    assert "re-run the Step 3 deduplication" in s2
    assert "keep the rank of the evidence they came from" in s2
    s6 = section(read(LOG), "## Step 6", "### Choosing the Activity Type")
    assert "the hours approved in Stage 2" in s6


def test_color_question_fits_the_popup():
    s = section(read(LOG), "### Setup (first run)", "### Directory matching")
    assert "No color for this project" in s
    assert "four projects per pop-up" in s
    assert "share a color" in s


def test_unaccounted_answers_go_through_the_stages():
    s1 = section(read(LOG), "### Stage 1: calendar events", "### Stage 2: time records")
    assert "What the user says about a gap becomes a new event" in s1


def test_windows_timezone_has_a_converter_and_a_table():
    s = section(read(LOG), "### Setup (first run)", "### Directory matching")
    assert "TryConvertWindowsIdToIanaId" in s
    assert "Pacific Standard Time" in s


def test_records_only_path_has_its_own_opening():
    s2 = section(read(LOG), "### Stage 2: time records", "## Step 5")
    assert "On the records-only path" in s2


def test_dashboard_query_is_not_a_blind_limit_one():
    t = read("skills/log-time/reference/taskray.md")
    assert "ORDER BY LastModifiedDate DESC" in t
    assert "sf org display -o <alias> --json" in read(REPORT)


# 1.19.1: existing profiles answer the new questions once

def test_existing_profiles_get_the_new_questions_once():
    log = read(LOG)
    s = section(log, "### New questions for existing profiles", "### Directory matching")
    assert "no `uses_google_tasks`" in s
    for q in ("Do you color-code projects on your calendar?",
              "Do you track work as Google Tasks?",
              "What timezone do you work in?"):
        assert q in s, q
    assert "asked once" in s
    i = log.index("If it exists, run the **org drift check**")
    assert "new questions" in log[i:i + 400]
    assert re.search(r"^version: 1\.(19|[2-9]\d)\.\d+$", log, re.M)


# Guide tabs: Get started and What's new

def test_guide_has_two_tabs_and_whats_new():
    g = html.unescape(read("docs/time-skills-guide.html"))
    assert 'id="tab-start"' in g and 'id="tab-new"' in g
    assert 'id="whats-new"' in g
    new = g[g.index('id="whats-new"'):]
    version = re.search(r"^version: (\S+)$", read(LOG), re.M).group(1)
    assert version in new
    for s in ("From team feedback", "Coming next", "Comment on this page"):
        assert s in new, s


def test_readme_points_the_team_to_whats_new():
    assert "What's new" in read("README.md")


# 1.19.2: color for projects added later, softer Tasks wording

def test_new_project_is_asked_for_an_unused_color():
    log = read(LOG)
    s = section(log, "### Color for a new project", "### Directory matching")
    assert "rhythm.color_codes" in s
    assert "not already used by another project" in s
    for where in ("Re-verification", "Evidence drift"):
        assert "Color for a new project" in section(log, f"### {where}", "\n### " if where == "Evidence drift" else "## Step 1"), where
    assert "color_codes" in json.loads(read("skills/log-time/profile.example.json"))["rhythm"]


def test_tasks_are_not_described_as_unreadable():
    log = read(LOG)
    assert "can't see Google Tasks" not in log
    assert "Were any of these a Google Task you worked on?" in log
    assert "connector can't see" not in html.unescape(read("docs/time-skills-guide.html"))


# 1.19.3: Tasks from a calendar screenshot; prominent guide header

def test_tasks_can_come_from_a_calendar_screenshot():
    log = read(LOG)
    assert "screenshot of your calendar" in log
    assert "Read each task's title, day and time from the screenshot" in log


def test_guide_has_a_branded_header_with_the_tabs():
    g = html.unescape(read("docs/time-skills-guide.html"))
    top = g[g.index('<nav class="tabs"'):g.index("</nav>")]
    assert "Kicksaw Time Skills" in top
    assert 'id="tab-start"' in top and 'id="tab-new"' in top
