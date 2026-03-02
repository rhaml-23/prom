#!/usr/bin/env python3
"""
Program Dashboard Generator
============================
Reads all runs/*/latest.json files and generates a single static
HTML dashboard showing program health, decision queues, and flags.

Usage:
    python dashboard.py
    python dashboard.py --runs path/to/runs/ --output dashboard.html
    python dashboard.py --open    # auto-open in browser after generation

Dependencies:
    Standard library only

Repo path: /scripts/dashboard.py
"""

import json
import argparse
import sys
import webbrowser
from datetime import date, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_programs(runs_dir: Path) -> list[dict]:
    programs = []
    for latest in sorted(runs_dir.glob("*/latest.json")):
        try:
            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["_source"] = str(latest)
                data["_program_slug"] = latest.parent.name
                programs.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"WARNING: Could not load {latest}: {e}", file=sys.stderr)
    return programs


def safe_get(d, *keys, default=""):
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
    return d if d is not None else default


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def get_health(program: dict) -> str:
    return safe_get(program, "program_state", "overall_health", default="unknown").lower()


def get_health_color(health: str) -> str:
    return {"green": "#22c55e", "yellow": "#f59e0b", "red": "#ef4444"}.get(health, "#94a3b8")


def get_health_label(health: str) -> str:
    return {"green": "🟢 GREEN", "yellow": "🟡 YELLOW", "red": "🔴 RED"}.get(health, "⚪ UNKNOWN")


def days_until(date_str: str) -> int | None:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (d - date.today()).days
    except (ValueError, TypeError):
        return None


def due_label(date_str: str) -> str:
    delta = days_until(date_str)
    if delta is None:
        return date_str or "TBD"
    if delta < 0:
        return f"{date_str} <span class='badge badge-red'>{abs(delta)}d overdue</span>"
    if delta == 0:
        return f"{date_str} <span class='badge badge-red'>TODAY</span>"
    if delta <= 3:
        return f"{date_str} <span class='badge badge-yellow'>in {delta}d</span>"
    return date_str


def priority_badge(priority: str) -> str:
    p = priority.lower()
    cls = {"high": "badge-red", "medium": "badge-yellow", "low": "badge-green"}.get(p, "badge-gray")
    return f"<span class='badge {cls}'>{priority.upper()}</span>"


def count_flags(program: dict) -> int:
    flags = program.get("flags", {})
    return sum(
        len(v) for k, v in flags.items()
        if isinstance(v, list) and k != "inferred"
    )


def collect_all_decisions(programs: list[dict]) -> list[dict]:
    all_decisions = []
    for p in programs:
        program_name = safe_get(p, "run_manifest", "program_name", default=p.get("_program_slug", "Unknown"))
        queue = safe_get(p, "monitoring_output", "decision_queue", default=[])
        for item in queue:
            all_decisions.append({**item, "_program": program_name})
    all_decisions.sort(key=lambda x: (
        {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "low").lower(), 3),
        x.get("due", "9999-99-99")
    ))
    return all_decisions


def collect_all_flags(programs: list[dict]) -> list[dict]:
    all_flags = []
    flag_labels = {
        "owner_needed": "OWNER NEEDED",
        "date_needed": "DATE NEEDED",
        "escalation_path_needed": "ESCALATION PATH NEEDED",
        "conflicts": "CONFLICT — VERIFY",
        "insufficient_data": "INSUFFICIENT DATA",
        "unresolved_from_prior_run": "UNRESOLVED FROM PRIOR RUN",
    }
    for p in programs:
        program_name = safe_get(p, "run_manifest", "program_name", default=p.get("_program_slug", "Unknown"))
        flags = p.get("flags", {})
        for key, label in flag_labels.items():
            for item in flags.get(key, []):
                all_flags.append({
                    "program": program_name,
                    "type": label,
                    "item": item,
                })
    return all_flags


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    min-height: 100vh;
    padding: 2rem;
}
h1 { font-size: 1.5rem; font-weight: 700; color: #f8fafc; margin-bottom: 0.25rem; }
h2 { font-size: 1.1rem; font-weight: 600; color: #94a3b8; text-transform: uppercase;
     letter-spacing: 0.05em; margin-bottom: 1rem; }
h3 { font-size: 0.95rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.5rem; }

.header { margin-bottom: 2rem; }
.header .meta { font-size: 0.8rem; color: #64748b; margin-top: 0.25rem; }

.grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }

.card {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 0.75rem;
    padding: 1.25rem;
}
.card.red-border { border-color: #ef4444; }
.card.yellow-border { border-color: #f59e0b; }
.card.green-border { border-color: #22c55e; }

.program-card { position: relative; overflow: hidden; }
.program-card .health-bar {
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.program-name { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.25rem; margin-top: 0.25rem; }
.program-status { font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem; }
.program-meta { display: flex; gap: 1rem; font-size: 0.75rem; color: #64748b; }
.program-meta span { display: flex; align-items: center; gap: 0.25rem; }

.section { margin-bottom: 2rem; }
.section-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e293b;
}
.count-badge {
    background: #334155; color: #94a3b8;
    font-size: 0.75rem; font-weight: 600;
    padding: 0.15rem 0.5rem; border-radius: 999px;
}
.count-badge.urgent { background: #450a0a; color: #fca5a5; }

table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th {
    text-align: left; padding: 0.5rem 0.75rem;
    color: #64748b; font-weight: 500; font-size: 0.75rem;
    text-transform: uppercase; letter-spacing: 0.04em;
    border-bottom: 1px solid #334155;
}
td { padding: 0.6rem 0.75rem; border-bottom: 1px solid #1e293b; vertical-align: top; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #243044; }

.badge {
    display: inline-block; font-size: 0.7rem; font-weight: 600;
    padding: 0.1rem 0.4rem; border-radius: 0.25rem; vertical-align: middle;
}
.badge-red { background: #450a0a; color: #fca5a5; }
.badge-yellow { background: #431407; color: #fcd34d; }
.badge-green { background: #052e16; color: #86efac; }
.badge-gray { background: #1e293b; color: #94a3b8; }

.flag-type {
    font-size: 0.7rem; font-weight: 600; font-family: monospace;
    background: #0f172a; color: #94a3b8;
    padding: 0.1rem 0.4rem; border-radius: 0.2rem;
    white-space: nowrap;
}
.empty { color: #475569; font-size: 0.85rem; font-style: italic; padding: 1rem 0; text-align: center; }

.run-date { font-size: 0.75rem; color: #475569; }
footer { margin-top: 3rem; text-align: center; font-size: 0.75rem; color: #334155; }
"""


def render_program_cards(programs: list[dict]) -> str:
    if not programs:
        return '<p class="empty">No programs found.</p>'

    cards = []
    for p in programs:
        name = safe_get(p, "run_manifest", "program_name", default=p.get("_program_slug", "Unknown"))
        health = get_health(p)
        color = get_health_color(health)
        health_label = get_health_label(health)
        status = safe_get(p, "program_state", "one_line_status", default="No status available")
        run_date = safe_get(p, "run_manifest", "run_date", default="Unknown")
        decision_count = len(safe_get(p, "monitoring_output", "decision_queue", default=[]))
        flag_count = count_flags(p)
        next_run = safe_get(p, "next_run_recommendation", "suggested_date", default="")

        border_class = {"green": "green-border", "yellow": "yellow-border", "red": "red-border"}.get(health, "")

        cards.append(f"""
        <div class="card program-card {border_class}">
            <div class="health-bar" style="background:{color}"></div>
            <div class="program-name">{name}</div>
            <div class="program-status">{health_label} — {status}</div>
            <div class="program-meta">
                <span>🎯 {decision_count} decision{'s' if decision_count != 1 else ''}</span>
                <span>🚩 {flag_count} flag{'s' if flag_count != 1 else ''}</span>
                {"<span>🔁 " + next_run + "</span>" if next_run else ""}
            </div>
            <div class="run-date" style="margin-top:0.5rem">Last run: {run_date}</div>
        </div>""")

    return "\n".join(cards)


def render_decision_table(decisions: list[dict]) -> str:
    if not decisions:
        return '<p class="empty">No decisions required. ✓</p>'

    rows = []
    for d in decisions:
        rows.append(f"""
        <tr>
            <td><strong>{d.get('_program', '—')}</strong></td>
            <td>{d.get('item', '—')}</td>
            <td>{d.get('action_needed', '—')}</td>
            <td>{d.get('owner', '—')}</td>
            <td>{due_label(d.get('due', ''))}</td>
            <td>{priority_badge(d.get('priority', 'medium'))}</td>
        </tr>""")

    urgent = sum(1 for d in decisions if d.get("priority", "").lower() == "high")
    badge_class = "urgent" if urgent > 0 else ""

    return f"""
    <div class="section-header">
        <h2>🎯 Decision Queue</h2>
        <span class="count-badge {badge_class}">{len(decisions)} item{'s' if len(decisions) != 1 else ''}</span>
    </div>
    <table>
        <thead><tr>
            <th>Program</th><th>Item</th><th>Action Needed</th>
            <th>Owner</th><th>Due</th><th>Priority</th>
        </tr></thead>
        <tbody>{"".join(rows)}</tbody>
    </table>"""


def render_flags_table(flags: list[dict]) -> str:
    if not flags:
        return '<p class="empty">No open flags. ✓</p>'

    rows = []
    for f in flags:
        rows.append(f"""
        <tr>
            <td><strong>{f.get('program', '—')}</strong></td>
            <td><span class="flag-type">[{f.get('type', '—')}]</span></td>
            <td>{f.get('item', '—')}</td>
        </tr>""")

    return f"""
    <div class="section-header">
        <h2>🚩 Open Flags</h2>
        <span class="count-badge">{len(flags)}</span>
    </div>
    <table>
        <thead><tr><th>Program</th><th>Type</th><th>Item</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
    </table>"""


def generate_html(programs: list[dict]) -> str:
    now = datetime.now().strftime("%A, %B %d %Y — %I:%M %p")
    today = date.today().isoformat()

    all_decisions = collect_all_decisions(programs)
    all_flags = collect_all_flags(programs)

    red_count = sum(1 for p in programs if get_health(p) == "red")
    yellow_count = sum(1 for p in programs if get_health(p) == "yellow")
    green_count = sum(1 for p in programs if get_health(p) == "green")

    summary_line = f"{len(programs)} program{'s' if len(programs) != 1 else ''}"
    if red_count:
        summary_line += f" &nbsp;·&nbsp; <span style='color:#ef4444'>{red_count} red</span>"
    if yellow_count:
        summary_line += f" &nbsp;·&nbsp; <span style='color:#f59e0b'>{yellow_count} yellow</span>"
    if green_count:
        summary_line += f" &nbsp;·&nbsp; <span style='color:#22c55e'>{green_count} green</span>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Program Dashboard — {today}</title>
<style>{CSS}</style>
</head>
<body>

<div class="header">
    <h1>Program Dashboard</h1>
    <div class="meta">{now} &nbsp;·&nbsp; {summary_line}</div>
</div>

<div class="grid-3">
{render_program_cards(programs)}
</div>

<div class="section card">
{render_decision_table(all_decisions)}
</div>

<div class="section card">
{render_flags_table(all_flags)}
</div>

<footer>Generated by program-pipeline · {today} · {len(programs)} program(s) loaded</footer>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate a static HTML program dashboard from pipeline run JSON files.")
    parser.add_argument("--runs", default="runs", help="Path to runs directory (default: ./runs)")
    parser.add_argument("--output", default="dashboard.html", help="Output HTML file (default: dashboard.html)")
    parser.add_argument("--open", action="store_true", help="Open dashboard in browser after generation")
    args = parser.parse_args()

    runs_dir = Path(args.runs)
    if not runs_dir.exists():
        print(f"ERROR: Runs directory not found: {args.runs}", file=sys.stderr)
        print("Run the pipeline for at least one program first.", file=sys.stderr)
        sys.exit(1)

    programs = load_programs(runs_dir)

    if not programs:
        print(f"No latest.json files found in {args.runs}/*/", file=sys.stderr)
        print("Run the pipeline for at least one program first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(programs)} program(s):")
    for p in programs:
        name = safe_get(p, "run_manifest", "program_name", default=p.get("_program_slug", "Unknown"))
        health = get_health(p)
        decisions = len(safe_get(p, "monitoring_output", "decision_queue", default=[]))
        flags = count_flags(p)
        print(f"  · {name} — {health.upper()} — {decisions} decisions, {flags} flags")

    html = generate_html(programs)
    out_path = Path(args.output)
    out_path.write_text(html, encoding="utf-8")
    print(f"\nDashboard written to: {out_path}")

    if args.open:
        webbrowser.open(out_path.resolve().as_uri())
        print("Opening in browser...")


if __name__ == "__main__":
    main()
