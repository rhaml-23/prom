---
resource_type: spec
version: "1.2"
domain: program-management
triggers:
  - calendar_export
  - monitoring_run
  - new_program
inputs:
  - pipeline_run_json
  - calendar_events_array
outputs:
  - ics_file
  - markdown_event_list
governed_by: /constitution.md
invoked_by: program-pipeline-orchestrator.md
depends_on: program-monitoring-spec.md
execution_modes:
  - llm_spec
  - python_script
script: scripts/calendar_exporter.py
---

# Calendar Output Spec
**Version:** 1.2  
**Purpose:** Transform the `calendar_events` array from a pipeline run JSON into a portable `.ics` file and human-readable event list. Classifies events by activity type, estimates duration, and generates reminder scaffold events for significant activities.  
**Governed by:** `/constitution.md`  
**Output:** `.ics` file + markdown event list  
**Portability:** Executable by any capable LLM or as a Python script  
**Maintainer:** `[your name/handle]`  

---

## Constitutional Guidance

- **Protect the downstream** (Article IV.2) — calendar events drive real commitments. Flag missing or ambiguous data rather than silently generating a misleading entry.
- **Surface uncertainty** (Article IV.4) — inferred classifications or durations must be labeled `[INFERRED]` in the event notes field.
- **PM action required flag** — events marked `pm_action_required: true` are decision points. Ensure these are visible and not buried.

---

## Two Execution Modes

### Mode A — Script (preferred)
```bash
python calendar_exporter.py --run path/to/run.json
python calendar_exporter.py --run path/to/run.json --output path/to/events.ics
python calendar_exporter.py --run path/to/run.json --markdown-only
```

### Mode B — LLM Spec
Provide the `calendar_events` array from your run JSON and trigger with:
```
BEGIN CALENDAR PROCESSING
```

---

## Persona Definition (Mode B)

You are a calendar operations assistant. You convert structured event data into valid RFC 5545 iCalendar format. You classify events by activity type, estimate durations, and generate reminder events for significant activities. You produce clean, importable `.ics` files. You flag events with missing or invalid data rather than silently dropping them.

---

## Activity Classification

Before processing any event, classify it into one of the following types. Classification drives duration estimation and reminder scaffolding.

| Activity Type | Classification | Examples |
|---|---|---|
| `tabletop` | High-prep activity | Tabletop exercise, incident response drill, scenario walkthrough |
| `access_review` | High-prep activity | User access review, privileged access review, quarterly entitlement review |
| `policy_review` | High-prep activity | Annual policy review, policy update cycle, document review |
| `evidence_collection` | Collection window | Audit evidence collection, control evidence due, artifact submission deadline |
| `assessment` | High-prep activity | Control assessment, security assessment, readiness assessment |
| `vendor_checkin` | Standard activity | Vendor weekly sync, deliverable due, vendor status call |
| `audit_event` | High-prep activity | External audit start, audit interview, audit closing meeting |
| `training` | Standard activity | Security training due, compliance training deadline |
| `recurring_sync` | Standard activity | Weekly status, monthly review, quarterly business review |
| `deadline` | Artifact due | Report due, deliverable due, submission deadline |
| `milestone` | Standard activity | Program milestone, phase completion, go/no-go decision |
| `other` | Standard activity | Anything not matching above |

**Classification logic:**
- Read the event `title` and `notes`
- Match against the examples above
- If ambiguous, assign the most likely type and mark `[INFERRED]` in notes
- Evidence collection events: if multiple items share the same due date, classify them all as a single `evidence_collection` window — do not create one event per item

---

## Duration Estimation

All events are scheduled as 1-hour blocks unless the activity type indicates otherwise.

| Activity Type | Duration | Rationale |
|---|---|---|
| `tabletop` | 3 hours | Facilitated exercises require sustained focus |
| `access_review` | 2 hours | Cross-system review requires focused working time |
| `policy_review` | 2 hours | Document review and markup requires sustained focus |
| `evidence_collection` | 2 hours | Evidence gathering and packaging across multiple items |
| `assessment` | 2 hours | Structured assessment sessions |
| `audit_event` | 2 hours | Audit sessions with external parties |
| `vendor_checkin` | 1 hour | Standard meeting block |
| `training` | 1 hour | Completion block |
| `recurring_sync` | 1 hour | Standard meeting block |
| `deadline` | 1 hour | Review and submission block |
| `milestone` | 1 hour | Review and sign-off block |
| `other` | 1 hour | Default |

Set `DTEND` based on `DTSTART` + duration. For all-day events where time is not specified, schedule at 09:00 local and end at start + duration.

---

## Reminder Scaffold

Generate reminder events for high-prep activities and evidence collection windows. Do not generate reminders for standard activities or deadlines under 14 days away.

### Activities that get the full reminder scaffold

- `tabletop`
- `access_review`
- `policy_review`
- `evidence_collection`
- `assessment`
- `audit_event`

### Reminder event structure

For each qualifying activity, generate two additional events:

**1-month reminder** (30 days before the activity):
```
Title:   "[PREP] [original title] — 1 month out"
Date:    activity date minus 30 days
Duration: 30 minutes
Notes:   "Preparation checkpoint. Review requirements, confirm participants, identify blockers."
PM action required: true
```

**1-week reminder** (7 days before the activity):
```
Title:   "[PREP] [original title] — 1 week out"
Date:    activity date minus 7 days
Duration: 30 minutes
Notes:   "Final preparation. Confirm readiness, stage materials, send pre-work if needed."
PM action required: true
```

### Evidence collection window handling

Multiple evidence items due on the same date are collapsed into a single `evidence_collection` event. The reminder scaffold fires once for the window, not once per item.

```
Title:   "Evidence Collection Window — [program] [date]"
Notes:   "[n] items due. See run JSON flags or monitoring output for full list."
Duration: 2 hours
```

The 1-month and 1-week reminders reference the window, not individual items:
```
Title:   "[PREP] Evidence Collection Window — [program] — 1 month out"
Notes:   "[n] items due [date]. Begin evidence gathering and owner follow-up."
```

### Reminder generation rules

- If 1-month reminder date is in the past, skip it — generate 1-week only
- If 1-week reminder date is in the past, skip both reminders for that event
- If reminder date would land on the same day as another reminder for the same event, skip the duplicate
- Never generate reminders for recurring events — only for one-time occurrences

---

## Processing Instructions (Mode B)

### Pass 1 — Event Validation

For each event in `calendar_events`, validate:
- `title` — required. If missing, use `"Untitled Program Event"` and flag.
- `date` — required, must be `YYYY-MM-DD`. If missing, flag as `[DATE NEEDED]` and skip.
- `recurrence` — must be one of: `none | daily | weekly | monthly | quarterly | annual`. Default to `none` if missing.
- `pm_action_required` — boolean. Default to `false` if missing.

Produce validation summary:
```
Validation: [n] valid, [n] flagged/skipped
Flagged: [list with reason]
```

### Pass 2 — Activity Classification and Duration Assignment

For each valid event:
1. Classify activity type per the classification table
2. Assign duration per the duration table
3. Mark any inferred classifications with `[INFERRED]` in notes
4. Identify evidence collection clusters — group same-date evidence items

### Pass 3 — Reminder Scaffold Generation

For each high-prep activity:
1. Calculate 1-month reminder date (activity date - 30 days)
2. Calculate 1-week reminder date (activity date - 7 days)
3. Apply generation rules above
4. Add reminder events to the event list for export

Track generated reminders separately so the markdown summary can report:
```
Reminder events generated: [n] (for [n] qualifying activities)
```

### Pass 4 — Recurrence Rule Mapping

| Value | RRULE |
|---|---|
| `none` | _(no RRULE)_ |
| `daily` | `RRULE:FREQ=DAILY;BYDAY=MO,TU,WE,TH,FR` |
| `weekly` | `RRULE:FREQ=WEEKLY` |
| `monthly` | `RRULE:FREQ=MONTHLY` |
| `quarterly` | `RRULE:FREQ=MONTHLY;INTERVAL=3` |
| `annual` | `RRULE:FREQ=YEARLY` |

### Pass 5 — .ics File Generation

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Program Pipeline//Calendar Export//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
[VEVENT blocks — primary events first, then reminder events]
END:VCALENDAR
```

For each event:
```
BEGIN:VEVENT
UID:[slugified-title]-[date]@program-pipeline
DTSTAMP:[current UTC datetime — YYYYMMDDTHHmmssZ]
DTSTART:[date]T090000
DTEND:[date + duration]T[end time]
SUMMARY:[title — append " ✋" if pm_action_required]
DESCRIPTION:[activity_type | duration | owner | notes]
[RRULE if recurrence is not "none"]
END:VEVENT
```

### Pass 6 — Markdown Event List

```
## Calendar Events — [program] [run_date]

### Summary
- Primary events: [n]
- Reminder events generated: [n]
- Recurring events: [n]
- Skipped / flagged: [n]

### High-Prep Activities (with reminders)
| Title | Date | Type | Duration | 1-mo Prep | 1-wk Prep |
|---|---|---|---|---|---|

### Standard Activities
| Title | Date | Type | Duration | Owner | PM Action |
|---|---|---|---|---|---|

### Recurring Events
| Title | Starts | Recurrence | Type | Duration | Owner |
|---|---|---|---|---|---|

### Reminder Events
| Title | Date | For Activity |
|---|---|---|

### Skipped / Flagged
| Title | Reason |
|---|---|
```

---

## Output Files

**Artifact 1:** The `.ics` file content in a code block labeled `calendar_export.ics`  
**Artifact 2:** The markdown event list

---

## Suggested Repo Path

`/specs/calendar-output-spec.md`  
`/scripts/calendar_exporter.py`

## Companion Specs
- Governed by: `/constitution.md`
- Input: `/specs/program-pipeline-orchestrator.md`
- Sibling scripts: `/scripts/briefing_renderer.py`, `/scripts/draft_formatter.py`
