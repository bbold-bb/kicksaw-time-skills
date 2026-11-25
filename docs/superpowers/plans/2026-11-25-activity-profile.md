# Activity Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (native, in one session). Final review: one Opus agent.

**Goal:** Setup learns how the user works and where meetings are recorded, and log-time uses the answers.

**Architecture:** Skill text only. A new Setup step 8 (the workday step becomes 9), a *Meeting recordings* section in Step 2, a changed ambiguous row in the Activity Type table, and `reference/meetings.md` for per-tool calls. No scripts.

**Spec:** docs/superpowers/specs/2026-11-25-activity-profile-design.md

## Global Constraints

- Version 1.20.0 in both SKILL.md files, changelog entry on top, guide What's new and footer.
- Public repo: no people, clients, real Ids or counts from a person's data.
- No em dashes. The wording rule stays intact. Recordings never change hours.

## Review Focus

- A user with no recorder, or only an unconnected one: no error, one line, and the run goes on.
- A personal recording in a mixed tool: never shown, titles included.
- A profile with `uses_google_tasks` but no `work`: asked only the new questions, once.
- A profile with no `picklists`: read and saved before the unclear type is chosen.
- A recording whose length is unknown: not dropped or opened on a guess.

## Tasks

- [ ] 1. Tests in `tests/test_activity_profile.py` pinning each rule below; loosen the two `1\.19` pins in `tests/test_call_feedback.py`. Run: they fail.
- [ ] 2. `SKILL.md` Setup step 8, renumbered step 9 and its references, *New questions* group, 30-day check.
- [ ] 3. `SKILL.md` Step 2 *Meeting recordings*, Step 4 bullets, Activity Type ambiguous row and the matching standing convention.
- [ ] 4. `reference/meetings.md`, `reference/taskray.md` queries, `profile.example.json`.
- [ ] 5. READMEs, guide, changelog, versions. Run the whole suite: green.

## Rulings made while planning

- Recurring meetings get their own follow-up pop-up (up to four), since each needs its own answer.
- The work-only question follows the recorder question, since it depends on the answer.
- Plaud is not listed at all in this release, because listing it exposes personal titles.
- Notion gives no reliable length. A note last edited under 5 minutes after it was created is dropped; otherwise an unmatched one is shown with no length and stays unopened until the user says it was work.
