# Meeting recordings reference

Which meeting tools the skill reads, and how. Everything here is read-only. Never create, edit, share or delete a note or recording. The rules for using what is read are in `SKILL.md`, *Meeting recordings*.

Connector tool names carry a different prefix on each machine, so find a tool by the name below, not by its prefix. A tool that can't be found or refuses access counts as not connected for that run.

| Tool | Saved as | Status |
| --- | --- | --- |
| Notion | `notion` | Read |
| Wispr Flow | `wispr_flow` | Read |
| Plaud | `plaud` | Not read yet. Never list Plaud recordings: people use it for personal ones, and a list shows their titles |
| tl;dv | `tldv` | Not read yet |
| Zoom | `zoom` | Not read yet |
| ZoomInfo (Chorus) | `zoominfo` | Not read yet |
| Anything else | its name in lower case | Not read yet |

For a tool that isn't read yet, save the answer and say so. Don't try its connector.

## Notion

- **List:** `notion-query-meeting-notes` with a `created_time` filter from the first scope day through the last, one day wider on each side, then keep the scope by the actual time in the profile timezone. It returns notes where the user is an attendee or the creator, up to 50; when it returns 50, ask again in shorter ranges. A note with a different creator is someone else's recording.
- **Match:** the title ends with a date mark; ignore it. `Created time` (UTC) is close to when the recording started, and can be a little early.
- **Read:** `notion-fetch` with the matched note's URL. The summary is in the result. The transcript is left out unless asked for with `include_transcript: true`.
- **Length is not reliable.** The note's Date is the scheduled time, and it can be edited days later. A note last edited less than 5 minutes after it was created is too short to list. Otherwise an unmatched note is of unknown length.

## Wispr Flow

- **List:** `search_meetings` with `since`, `until`, `sort: "start"` and `limit: 200`. `until` is not included, so pass the next local midnight after the last scope day. Keep only meetings that have a transcript or a summary and whose start time has passed (the meeting has started). If `has_more` is true, use shorter ranges.
- **Match:** title, then start time (UTC), then attendees. Its start and end can be the calendar's, so they don't measure the recording. With no end time, its length is unknown.
- **Read:** `get_meeting` with the matched meeting's id and no `view_transcript`; the summary is in the result. Ask for the transcript in `view_transcript` only under the rule in `SKILL.md`.
- A result marked `shared` is someone else's recording: what it lists as their tasks are not the user's.
- A list result carries a short excerpt of each meeting. Ignore the excerpt of any meeting that isn't matched.
