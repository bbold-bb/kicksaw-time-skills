"""Staffing on an Opportunity is pipeline, not allocation.

Resource Hero lets an assignment point at an Opportunity before a deal is won.
Those hours are not part of what a person is staffed on, so the report lists
them on their own line and keeps them out of allocation, pace and the export.
"""
import json

import time_report

PROFILE = {
    "org_alias": "Test",
    "projects": [{"name": "Acme Phase 1", "label": "Acme", "rh_assignment_id": "a78PROJ"}],
    "resource_hero": {"use_for_allocations": True, "resource_id": "a7BRES"},
}

ASSIGNMENTS = [
    {"Id": "a78PROJ", "Name": "ARN1", "ResourceHeroApp__RH_Project__r": {"Name": "Acme Phase 1"},
     "ResourceHeroApp__Start_Date__c": "2026-11-16", "ResourceHeroApp__End_Date__c": "2027-01-01",
     "ResourceHeroApp__Is_Holiday_Time__c": False, "ResourceHeroApp__Is_Time_Off_PTO__c": False,
     "ResourceHeroApp__Related_Record_Type__c": "RH Project",
     "ResourceHeroApp__Related_Record__c": '<a href="/a77X" target="_top">Acme Phase 1</a>'},
    {"Id": "a78OPP", "Name": "ARN2", "ResourceHeroApp__RH_Project__r": None,
     "ResourceHeroApp__Start_Date__c": "2026-11-09", "ResourceHeroApp__End_Date__c": "2027-03-31",
     "ResourceHeroApp__Is_Holiday_Time__c": False, "ResourceHeroApp__Is_Time_Off_PTO__c": False,
     "ResourceHeroApp__Related_Record_Type__c": "Opportunity",
     "ResourceHeroApp__Related_Record__c": '<a href="/006X" target="_top">Acme - Phase 2 &amp; Support</a>'},
]


def forecast(assignment, day, hours):
    return {"ResourceHeroApp__Resource_Assignment__c": assignment, "ResourceHeroApp__ForecastDate__c": day, "fc": hours}


FORECAST = [
    forecast("a78PROJ", "2026-11-16", 4), forecast("a78PROJ", "2026-11-17", 4),
    forecast("a78OPP", "2026-11-16", 4), forecast("a78OPP", "2026-11-17", 4),
    # Dated before the Opportunity assignment starts: still pipeline, not "forecast left out".
    forecast("a78OPP", "2026-10-15", 4),
]


def fake_query(monkeypatch):
    def sf_query(profile, soql):
        return ASSIGNMENTS if "FROM ResourceHeroApp__Resource_Assignment__c" in soql else FORECAST
    monkeypatch.setattr(time_report, "sf_query", sf_query)


def test_assignment_query_reads_the_related_record_type(monkeypatch):
    seen = []
    monkeypatch.setattr(time_report, "sf_query", lambda profile, soql: seen.append(soql) or [])
    time_report.fetch_assignments(PROFILE, {})
    assert "ResourceHeroApp__Related_Record_Type__c" in seen[0]
    assert "ResourceHeroApp__Related_Record__c" in seen[0]


def test_opportunity_staffing_is_not_allocation(monkeypatch):
    fake_query(monkeypatch)
    days = time_report.fetch_allocation_days(PROFILE, "2026-10-01", "2026-11-30")
    assert days == {"Acme": {"2026-11-16": 4, "2026-11-17": 4}}


def test_opportunity_staffing_is_reported_as_pipeline(monkeypatch):
    fake_query(monkeypatch)
    ignored, pipeline = [], []
    time_report.fetch_allocation_days(PROFILE, "2026-10-01", "2026-11-30", ignored, pipeline)
    assert ignored == []
    assert len(pipeline) == 1
    p = pipeline[0]
    assert p["label"] == "Acme - Phase 2 & Support"
    assert p["hours"] == 12
    assert (p["first"], p["last"]) == ("2026-10-15", "2026-11-17")


def test_pipeline_line_says_it_is_not_counted(capsys):
    time_report.print_pipeline([{"label": "Acme - Phase 2", "hours": 8.0, "first": "2026-11-16",
                                 "last": "2026-11-17", "start": "2026-11-09", "end": "2027-03-31"}])
    out = capsys.readouterr().out
    assert "Pipeline staffing" in out
    assert "not counted" in out
    assert "Acme - Phase 2: 8h" in out


def test_export_keeps_pipeline_out_of_allocation(monkeypatch, tmp_path):
    fake_query(monkeypatch)
    monkeypatch.setattr(time_report, "fetch", lambda profile, start, end: [])
    import datetime as dt
    out_dir, _, _ = time_report.write_data(str(tmp_path), PROFILE, {}, dt.date(2026, 11, 21))
    alloc = json.loads((tmp_path / "allocation.json").read_text())
    assert {r["project"] for r in alloc} == {"Acme"}
    info = json.loads((tmp_path / "run-info.json").read_text())[0]
    assert info["forecast_left_out"] == []
    assert info["pipeline_left_out"] == [{"project": "Acme - Phase 2 & Support", "hours": 12,
                                          "from": "2026-10-15", "to": "2026-11-17",
                                          "assignment_start": "2026-11-09", "assignment_end": "2027-03-31"}]
