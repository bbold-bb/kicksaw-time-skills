# Activity profile

Date: 2026-11-25. Status: approved 2026-11-25.

## Intent

log-time rebuilds a day from evidence, and what counts as evidence depends on how a person works. Setup never asks. It assumes work leaves session transcripts, commits or Slack messages, and it calls an unclear block Coding and Configuration. That fits a builder who uses Claude Code and misses a project manager, or anyone who works by hand.

Setup should learn three things: what fills the person's week, what work leaves no trace, and where their meetings are recorded.

**Success:** two people with different jobs get proposals that fit their jobs, and meeting notes are specific because the skill read the right recording.

## Goals

1. Learn how the user works in two short pop-ups, prefilled wherever possible.
2. Use each answer. A question that changes nothing isn't asked.
3. Find the user's meeting recordings and use them for better notes.
4. Ask existing users once.

## Non-goals

- Jira, Drive or email as evidence (Jira is designed separately and tabled).
- Recording anything, or changing a recorder's settings.
- Reading a recording to measure hours.

## Anti-goals

- Reading, listing or quoting a personal recording.
- Booking a meeting because a recording of it exists, when the user wasn't there.
- A long questionnaire.

## Approaches considered

1. **Infer, then confirm in two pop-ups (chosen).** Connectors and past time records prefill the answers.
2. **Ask for a job title and apply a preset.** Rejected: titles are inconsistent in the org, and people with one title work differently.
3. **Learn silently from corrections.** Rejected: the first weeks stay wrong, and nobody can see why a proposal looks as it does.

## Design

### The questions

All use the option pop-up, after setup's calendar step.

**How you work** (one pop-up)

| Question | Prefilled from | What it changes |
| --- | --- | --- |
| What fills most of your week? (building and configuring; documents and design; managing projects and clients; testing and reviews) Multi-select | The role on the user's time records and 90 days of Activity Types | The Activity Type for an unclear block |
| What takes time but leaves no trace here? (Salesforce work by hand; planning and Jira boards; documents and slides; calls and chats not on the calendar) Multi-select | Nothing | The choices offered for unaccounted time |
| How much of your work goes through Claude? (most; some; rarely) | How much session history there is | "Rarely": a day without transcripts is normal, and the run stops remarking on it |
| Which project do these recurring meetings belong to? Asked only when there are some | Events on the calendar 3 or more times in 30 days whose title names no project | Saved as a standing rule in `conventions` |

**Your meetings** (one pop-up)

| Question | Prefilled from | What it changes |
| --- | --- | --- |
| Where are your meetings recorded or transcribed? Multi-select, over two questions if needed | Connected tools with meetings in the last 30 days, each with its count; then Notion, tl;dv, Zoom, Wispr Flow, ZoomInfo (Chorus), Plaud, another tool, "I don't record" | Where the run looks |
| Which of those hold only work meetings? Multi-select | Nothing | Whether unmatched recordings may be shown |

A tool the user picks that isn't connected is saved as such. The skill says where to connect it, the user signs in themselves, and skipping is fine.

### Activity Type for unclear blocks

| Main work | Unclear blocks become |
| --- | --- |
| Building and configuring, or testing and reviews | Coding and Configuration |
| Documents and design | Documentation |
| Managing projects and clients | Communications |

With several picked, the one with the most hours in the last 90 days wins. Evidence still decides first; only the "ambiguous" row of the Activity Type table changes. Any value must be in the profile's `picklists`. A profile without `picklists` gets them read and saved at the same time, because profiles from before 1.17 never did.

### Using recordings

- **The calendar stays in charge of hours.** A recording never adds, lengthens or shortens a booked meeting. Tools often report the scheduled time, and note timestamps aren't a reliable end time.
- **Match first, then read.** List recordings for the scope dates and match each to a work meeting by time, and by title or attendees when there are several. Only a matched recording is opened.
- **Read the summary, not the transcript.** Open the transcript only when there is no summary and the meeting's project or subject is unclear.
- **Several recordings of one meeting:** use the tool that covered most of the user's meetings in the last 30 days.
- **Someone else's recording** shows what was discussed, not that the user attended.
- **Unmatched recordings** are shown only from tools marked work-only, only when 5 minutes or longer, under "Needs your call" ("A 25-minute recorded call at 3:00 PM isn't on your calendar"). Nothing from other tools is listed, titles included.
- **What is used:** topics, decisions and the user's own follow-ups, to write notes and to spot follow-up work to ask about. Nothing about a person's health, family, pay or performance goes into a note.
- The wording rule is unchanged: a note never says a recording was used.

### What each tool can give

| Tool | Connector | Checked |
| --- | --- | --- |
| Notion | Yes | Read: list, summary; transcript on request |
| Wispr Flow | Yes | Read: list, summary, transcript |
| Plaud | Yes | Read: list only. Holds personal recordings too |
| tl;dv | In the connector directory | Not connected, not tried |
| Zoom | In the connector directory | Not connected, not tried |
| ZoomInfo (Chorus) | ZoomInfo is in the directory and lists a conversation tool | Not connected; whether it returns Chorus calls is unknown |

The reference file covers the first two in full. Each of the rest is added once someone who uses it has tried it. Until then the skill saves the answer and says that tool isn't read yet.

### Profile

```json
"work": {
  "main_work": ["managing"],
  "unclear_activity_type": "Communications",
  "no_trace": ["planning", "calls"],
  "claude_use": "some",
  "recorders": [
    { "tool": "notion", "connected": true, "work_only": true },
    { "tool": "zoom", "connected": false, "work_only": true }
  ]
}
```

The presence of `work` marks the questions as answered. Existing users get both pop-ups once. The 30-day check asks again only about a connected recorder that has new meetings and isn't in the profile, or when the top Activity Type no longer fits `main_work`.

## Files

`skills/log-time/SKILL.md`, a new `skills/log-time/reference/meetings.md`, `profile.example.json`, tests, README, the guide (with What's new) and `CHANGELOG.md`. Release 1.20.0 for all skills.

## Not validated yet

tl;dv, Zoom and ZoomInfo, and the questions with someone who isn't a builder. A project manager's setup is the real test.

## Change Log

- 2026-11-25: first draft, after feedback that setup should ask how people work and where their meetings are transcribed.
