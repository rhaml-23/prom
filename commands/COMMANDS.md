# Command Reference
**Compliance Agent System — Slash Commands**
`.cursor/commands/` — invoke with `/command-name` in the Cursor Agent composer

---

## Quick Reference

| Command | What it does | Required args |
|---|---|---|
| `/daily-brief` | Morning portfolio health + what's due today | none |
| `/program-status` | One-page status for a single program | program |
| `/due-this-week` | Cross-program digest of everything due in 7 days | none |
| `/meeting-prep` | 1:1 briefing scoped to a person's responsibilities | person, program |
| `/draft-status-update` | Draft a stakeholder communication | program, audience |
| `/evidence-due` | Upcoming evidence collection windows | program |
| `/log-decision` | Capture a decision to program memory | program, decision |
| `/update-item` | Update status, owner, or notes on a GRC item | program, ID |
| `/intel-scan` | External source monitoring and risk deltas | scope |
| `/auditor-view` | Generate read-only auditor compliance dashboard | program |
| `/provenance-query` | What has the system produced for a program | program |
| `/meeting-debrief` | Ingest a meeting transcript and update program state | program |

---

## Commands

### `/daily-brief`
Morning orientation across all active programs. Reads portfolio state, all program run JSONs, and provenance log. Surfaces health, what's due today, pending decisions, and open blockers in a single view under 40 lines.

No arguments. Run first thing.

---

### `/program-status [program]`
One-page status summary for a single program. Covers health, scope, control coverage, open risks, decisions, blockers, upcoming deadlines, and next pipeline run recommendation.

```
/program-status fedramp-high
```

Arguments:
- `program` — program slug matching the `runs/` directory name

---

### `/due-this-week`
Cross-program digest of everything due or overdue in the next 7 days. Covers evidence windows, POA&M target dates, high-urgency decisions, overdue pipeline runs, and active escalations.

No arguments. Use at the start of the week or any time you need a deadline view.

---

### `/meeting-prep [person] [program] [days]`
Prepares a focused briefing for a 1:1 or team meeting. Filters all program items by owner field match, scoped to the specified date range. Surfaces open items, completed work (shows progress), evidence windows, blockers, and three suggested talking points.

```
/meeting-prep "Jordan Kim" fedramp-high 30
/meeting-prep "Jordan" iso-42001
```

Arguments:
- `person` — name or partial match of the owner field value
- `program` — program slug
- `days` — lookback/lookahead window in days (default: 30)

Note: talking points are data-derived, not performance commentary.

---

### `/draft-status-update [program] [audience]`
Drafts a stakeholder status communication calibrated to the specified audience. Reads current program state and memory. Routes through the comms spec. Output is always flagged as a draft requiring review — never sent automatically.

```
/draft-status-update fedramp-high executive
/draft-status-update iso-42001 auditor
```

Arguments:
- `program` — program slug
- `audience` — one of: `executive` `technical` `auditor` `vendor` `all-hands`

Audience calibration:
- `executive` — 3 paragraphs, health + one metric + one ask
- `technical` — coverage metrics, GRC IDs, evidence gaps
- `auditor` — monitoring cadence, coverage %, closure rate
- `vendor` — their systems only, open items, what you need and by when
- `all-hands` — plain language, no jargon

---

### `/evidence-due [program] [days]`
Shows upcoming evidence collection windows for a program within a specified number of days. Also surfaces overdue windows regardless of date.

```
/evidence-due fedramp-high 30
/evidence-due iso-42001 60
```

Arguments:
- `program` — program slug
- `days` — how far ahead to look (default: 30)

---

### `/log-decision [program]`
Captures a decision made outside a pipeline run. Appends to the Decision Log in the program's memory file. Optionally links to a GRC item by ID. Logs provenance.

```
/log-decision fedramp-high
```

Arguments:
- `program` — program slug

The command will prompt for: decision summary, GRC ID (optional), rationale (optional), revisit condition (optional).

Use whenever a decision is made in a meeting, email, or conversation that should be on record. Keeps the memory file accurate between pipeline runs.

---

### `/update-item [program] [id]`
Updates status, owner, or notes on a specific POA&M item, control gap, or action item identified by GRC ID. Displays current state before making any change. Requires confirmation before writing. Logs provenance.

```
/update-item fedramp-high ID-18
/update-item iso-42001 ID-7
```

Arguments:
- `program` — program slug
- `id` — GRC ID as it appears in the run JSON (e.g. ID-18)

Update types: `status` `owner` `note` — command prompts for the new value.

Closing an item during an active audit window is treated as a one-way door and requires explicit confirmation.

---

### `/intel-scan [scope]`
Runs external intelligence monitoring against one or all active programs. Scans CISA KEV, NVD, MITRE ATT&CK, AI Incident Database, NIST, research feeds, and threat intel. Scores relevance against framework and tech stack. Generates risk deltas for Critical and High findings.

```
/intel-scan all
/intel-scan fedramp-high
```

Arguments:
- `scope` — program slug or `all`
- lookback window defaults to 14 days, prompted if needed

Critical and High findings generate stakeholder draft communications written to `drafts/` for review. All findings are staged as weekly session agenda items.

---

### `/auditor-view [program]`
Generates a read-only auditor compliance posture dashboard as a static HTML file. Covers monitoring activity log (full provenance), control coverage status, risk register summary, and evidence collection calendar. Suitable for third-party auditor submission — print to PDF from browser.

```
/auditor-view fedramp-high
/auditor-view iso-42001
```

Arguments:
- `program` — program slug
- lookback window defaults to 90 days, prompted if needed

Output: `ui/[program]-auditor-[date].html`

---

### `/provenance-query [program]`
Shows what the system has produced for a program. Queries the provenance log with optional filters by output type and date range. Surfaces reusable artifacts.

```
/provenance-query fedramp-high
/provenance-query fedramp-high run_json
```

Arguments:
- `program` — program slug
- output type filter (optional) — `run_json` `status_report` `auditor_dashboard` `intel_report` `decision_log` `item_update`

---

### `/meeting-debrief [program]`
Ingests a meeting transcript from `data/[program]/materials/meeting-debrief.md` and extracts all compliance-relevant signal. Decisions and session notes write automatically to the memory file. Action items, control updates, new risks, and date commitments are staged and confirmed before touching the run JSON.

```
/meeting-debrief fedramp-high
```

Arguments:
- `program` — program slug

Extracts: decisions, action items with owners, control implementation commitments, new risks and blockers, date commitments. Assigns provisional GRC IDs (`DEBRIEF-[date]-[n]`) to new items pending next pipeline run.

Confirmation behavior: decisions and memory notes write immediately. All run JSON changes are grouped and confirmed before writing.

Suggested file naming:
- `data/[program]/materials/meeting-debrief.md` — active file, overwrite each time
- `data/[program]/materials/meeting-[YYYY-MM-DD].md` — if keeping a history

---

## Notes

**All commands are governed by `config/constitution.md`.** One-way door actions (closing items during audit windows, sending external communications) require explicit confirmation regardless of command.

**Arguments are optional at invocation.** If not provided, the command asks for them before proceeding. You can type `/meeting-prep` with no arguments and supply them interactively.

**Commands write to the repo.** `log-decision` and `update-item` modify files. All writes are logged to `logs/provenance.jsonl`. Nothing is sent externally.

**Draft communications are always staged, never sent.** `/draft-status-update` writes to `drafts/` and flags the output for review. Sending is always a manual step.

---

## File Locations

```
.cursor/commands/daily-brief.md
.cursor/commands/program-status.md
.cursor/commands/due-this-week.md
.cursor/commands/meeting-prep.md
.cursor/commands/draft-status-update.md
.cursor/commands/evidence-due.md
.cursor/commands/log-decision.md
.cursor/commands/update-item.md
.cursor/commands/intel-scan.md
.cursor/commands/auditor-view.md
.cursor/commands/provenance-query.md
.cursor/commands/meeting-debrief.md
```
