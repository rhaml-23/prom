#!/usr/bin/env python3
"""
portfolio_renderer.py

Purpose: Read data/portfolio/latest.json and render ui/portfolio.html —
         a cross-program portfolio dashboard showing health, decisions,
         blockers, escalations, and cross-program signals.

Usage:
  python scripts/portfolio_renderer.py
  python scripts/portfolio_renderer.py --portfolio data/portfolio/latest.json
  python scripts/portfolio_renderer.py --output ui/portfolio.html
  python scripts/portfolio_renderer.py --open

Dependencies: None beyond Python standard library
Repo path: /scripts/portfolio_renderer.py
Standards: PEP 8, type hints, argparse, standard library only
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# ── Constants ────────────────────────────────────────────────────────────────

DEFAULT_PORTFOLIO = "data/portfolio/latest.json"
DEFAULT_OUTPUT = "ui/portfolio.html"

HEALTH_CONFIG = {
    "red":    {"icon": "🔴", "label": "Red",    "color": "#c0392b", "bg": "#fdf2f2"},
    "yellow": {"icon": "🟡", "label": "Yellow", "color": "#d68910", "bg": "#fefdf0"},
    "green":  {"icon": "🟢", "label": "Green",  "color": "#1e8449", "bg": "#f2fdf4"},
}

URGENCY_COLOR = {
    "high":   "#c0392b",
    "medium": "#d68910",
    "low":    "#555555",
}

SEVERITY_COLOR = {
    "critical": "#c0392b",
    "high":     "#e67e22",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def load_portfolio(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        print(f"[ERROR] Portfolio file not found: {path}", file=sys.stderr)
        print("Run 'BEGIN PORTFOLIO RUN' in your LLM interface first.", file=sys.stderr)
        sys.exit(1)
    with open(p) as f:
        return json.load(f)


def days_label(days: int) -> str:
    return f"{days}d" if days != 1 else "1d"


def escape(text: str) -> str:
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def badge(text: str, color: str, bg: str = "#f0f0f0") -> str:
    return (f'<span style="background:{bg};color:{color};padding:2px 8px;'
            f'border-radius:4px;font-size:0.78em;font-weight:600">'
            f'{escape(text)}</span>')


def section_header(title: str) -> str:
    return (f'<div style="font-size:0.7em;font-weight:700;letter-spacing:0.08em;'
            f'color:#888;text-transform:uppercase;margin:24px 0 8px">{title}</div>')


# ── Per-program card ─────────────────────────────────────────────────────────

def render_program_card(prog: dict[str, Any]) -> str:
    health = prog.get("health", "green")
    cfg = HEALTH_CONFIG.get(health, HEALTH_CONFIG["green"])
    slug = escape(prog.get("slug", "unknown"))
    display = escape(prog.get("display_name", slug))
    reason = escape(prog.get("health_reason", ""))
    phase = escape(prog.get("phase", "—"))
    framework = escape(prog.get("framework", "—"))
    last_run = escape(prog.get("last_run", "—"))
    next_due = escape(prog.get("next_run_due", "—"))
    staleness = prog.get("run_staleness_days", 0)
    top_risk = escape(prog.get("top_risk", "—"))
    drafts = prog.get("drafts_staged", 0)
    intel = prog.get("intel_items_pending", 0)
    nearest_dl = escape(prog.get("nearest_deadline", ""))
    nearest_dl_item = escape(prog.get("nearest_deadline_item", ""))

    # card border color
    border = cfg["color"]
    is_expanded = health == "red"

    html = f"""
<div style="border-left:4px solid {border};background:{cfg['bg']};
     border-radius:6px;padding:16px 20px;margin-bottom:12px">

  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
    <div>
      <span style="font-size:1.05em;font-weight:700;color:#1a1a1a">{cfg['icon']} {display}</span>
      <span style="font-size:0.8em;color:#666;margin-left:10px">{slug}</span>
    </div>
    {badge(cfg['label'], cfg['color'])}
  </div>
"""

    if reason:
        html += f'<div style="font-size:0.85em;color:{border};margin-bottom:8px">{reason}</div>\n'

    # meta row
    meta_items = [f"Phase: {phase}", f"Framework: {framework}",
                  f"Last run: {last_run}", f"Next due: {next_due}"]
    if staleness > 0:
        meta_items.append(badge(f"Stale {days_label(staleness)}", "#c0392b", "#fdf2f2"))
    html += ('<div style="font-size:0.78em;color:#555;margin-bottom:10px">'
             + " &nbsp;|&nbsp; ".join(meta_items) + "</div>\n")

    if is_expanded:
        # Decision queue
        decisions = prog.get("decision_queue", [])
        if decisions:
            html += section_header(f"Decisions Needed ({len(decisions)})")
            for d in decisions:
                urgency = d.get("urgency", "medium")
                color = URGENCY_COLOR.get(urgency, "#555")
                age = days_label(d.get("age_days", 0))
                html += (f'<div style="padding:4px 0;font-size:0.85em">'
                         f'<span style="color:{color}">→</span> '
                         f'{escape(d.get("item",""))} '
                         f'<span style="color:#aaa;font-size:0.85em">{age}</span></div>\n')

        # Blockers
        blockers = prog.get("blockers", [])
        if blockers:
            html += section_header(f"Blockers ({len(blockers)})")
            for b in blockers:
                owner = escape(b.get("owner", "OWNER NEEDED"))
                owner_color = "#c0392b" if "NEEDED" in owner else "#333"
                age = days_label(b.get("age_days", 0))
                html += (f'<div style="padding:4px 0;font-size:0.85em">'
                         f'<span style="color:#c0392b">→</span> '
                         f'{escape(b.get("item",""))} '
                         f'— <span style="color:{owner_color};font-weight:600">{owner}</span> '
                         f'<span style="color:#aaa;font-size:0.85em">{age}</span></div>\n')

        # Escalations
        escalations = prog.get("escalations", [])
        if escalations:
            html += section_header(f"Escalations ({len(escalations)})")
            for e in escalations:
                sev = e.get("severity", "high")
                color = SEVERITY_COLOR.get(sev, "#c0392b")
                age = days_label(e.get("age_days", 0))
                html += (f'<div style="padding:4px 0;font-size:0.85em">'
                         f'<span style="color:{color};font-weight:700">⚠ </span>'
                         f'{escape(e.get("item",""))} '
                         f'{badge(sev, color)} '
                         f'<span style="color:#aaa;font-size:0.85em">{age}</span></div>\n')
    else:
        # Yellow/green: compact summary
        decisions = prog.get("decision_queue", [])
        blockers = prog.get("blockers", [])
        if decisions:
            top = decisions[0]
            age = days_label(top.get("age_days", 0))
            html += (f'<div style="font-size:0.82em;color:#555;margin-bottom:4px">'
                     f'Top decision: {escape(top.get("item",""))} '
                     f'<span style="color:#aaa">{age}</span></div>\n')
        if blockers:
            top = blockers[0]
            html += (f'<div style="font-size:0.82em;color:#555;margin-bottom:4px">'
                     f'Blocker: {escape(top.get("item",""))}</div>\n')

    # Footer row — always shown
    footer_parts = []
    if top_risk and top_risk != "—":
        footer_parts.append(f'<span style="color:#555">Risk: {top_risk}</span>')
    if nearest_dl:
        footer_parts.append(f'<span style="color:#c0392b">Deadline: {nearest_dl_item} — {nearest_dl}</span>')
    if drafts:
        footer_parts.append(badge(f"{drafts} draft{'s' if drafts > 1 else ''} staged", "#1a6e9e"))
    if intel:
        footer_parts.append(badge(f"{intel} intel pending", "#6c3483"))

    if footer_parts:
        html += ('<div style="margin-top:10px;font-size:0.78em;border-top:1px solid #ddd;'
                 f'padding-top:8px">' + " &nbsp;·&nbsp; ".join(footer_parts) + "</div>\n")

    html += "</div>\n"
    return html


# ── Cross-program signals ────────────────────────────────────────────────────

def render_cross_program(cp: dict[str, Any]) -> str:
    html = ""

    def signal_rows(items: list, label_key: str, detail_key: str, color: str) -> str:
        if not items:
            return ""
        rows = ""
        for item in items:
            label = escape(item.get(label_key, ""))
            detail = escape(item.get(detail_key, ""))
            rows += (f'<div style="padding:4px 0;font-size:0.85em">'
                     f'<span style="color:{color}">→</span> '
                     f'<strong>{label}</strong> — {detail}</div>\n')
        return rows

    deadlines = cp.get("near_term_deadlines", [])
    if deadlines:
        html += section_header("Near-term Deadlines (14 days)")
        for d in deadlines:
            html += (f'<div style="padding:4px 0;font-size:0.85em">'
                     f'<span style="color:#c0392b">→</span> '
                     f'{escape(d.get("date",""))} — {escape(d.get("item",""))} '
                     f'— <em>{escape(d.get("program",""))}</em></div>\n')

    vendors = cp.get("shared_vendors_at_risk", [])
    if vendors:
        html += section_header("Shared Vendor Risk")
        for v in vendors:
            programs = ", ".join(v.get("programs", []))
            html += (f'<div style="padding:4px 0;font-size:0.85em">'
                     f'<span style="color:#e67e22">→</span> '
                     f'<strong>{escape(v.get("vendor",""))}</strong> — {escape(programs)}</div>\n')

    contention = cp.get("resource_contention", [])
    if contention:
        html += section_header("Resource Contention")
        for c in contention:
            programs = ", ".join(c.get("programs", []))
            html += (f'<div style="padding:4px 0;font-size:0.85em">'
                     f'<span style="color:#d68910">→</span> '
                     f'<strong>{escape(c.get("owner",""))}</strong> — open items in: {escape(programs)}</div>\n')

    intel = cp.get("intel_overlap", [])
    if intel:
        html += section_header("Intel Overlap")
        for i in intel:
            programs = ", ".join(i.get("programs", []))
            html += (f'<div style="padding:4px 0;font-size:0.85em">'
                     f'<span style="color:#6c3483">→</span> '
                     f'{escape(i.get("finding",""))} — {escape(programs)}</div>\n')

    return html


# ── Suggested actions ────────────────────────────────────────────────────────

def render_suggested_actions(portfolio: dict[str, Any]) -> str:
    actions = []
    for prog in portfolio.get("programs", []):
        if prog.get("health") == "red":
            for esc in prog.get("escalations", []):
                actions.append({
                    "text": f'[{prog["slug"]}] Resolve escalation: {esc.get("item","")}',
                    "age": esc.get("age_days", 0),
                    "priority": 0
                })
            for dec in prog.get("decision_queue", []):
                if dec.get("urgency") == "high":
                    actions.append({
                        "text": f'[{prog["slug"]}] Decision needed: {dec.get("item","")}',
                        "age": dec.get("age_days", 0),
                        "priority": 1
                    })

    actions.sort(key=lambda x: (x["priority"], -x["age"]))
    actions = actions[:3]

    if not actions:
        return ""

    html = section_header("Suggested First Actions")
    for i, action in enumerate(actions, 1):
        html += (f'<div style="padding:6px 0;font-size:0.88em">'
                 f'<strong>{i}.</strong> {escape(action["text"])}</div>\n')
    return html


# ── Full page ────────────────────────────────────────────────────────────────

def render_html(portfolio: dict[str, Any]) -> str:
    summary = portfolio.get("summary", {})
    generated = escape(portfolio.get("generated", str(date.today())))
    total = summary.get("total_programs", 0)
    red = summary.get("red", 0)
    yellow = summary.get("yellow", 0)
    green = summary.get("green", 0)
    total_decisions = summary.get("total_decisions_pending", 0)
    total_blockers = summary.get("total_blockers", 0)
    total_escalations = summary.get("total_escalations", 0)
    nearest_dl = escape(summary.get("nearest_deadline", ""))
    nearest_dl_prog = escape(summary.get("nearest_deadline_program", ""))

    programs_html = "".join(render_program_card(p) for p in portfolio.get("programs", []))
    cross_html = render_cross_program(portfolio.get("cross_program", {}))
    actions_html = render_suggested_actions(portfolio)

    stat_box = lambda label, value, color="#1a1a1a": (
        f'<div style="text-align:center;padding:12px 20px">'
        f'<div style="font-size:1.8em;font-weight:700;color:{color}">{value}</div>'
        f'<div style="font-size:0.72em;color:#888;text-transform:uppercase;letter-spacing:0.05em">{label}</div>'
        f'</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Portfolio Briefing — {generated}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
         background: #f5f5f5; color: #1a1a1a; line-height: 1.5; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 24px 16px; }}
  .card {{ background: #fff; border-radius: 8px; padding: 20px;
           box-shadow: 0 1px 4px rgba(0,0,0,0.08); margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="container">

  <!-- Header -->
  <div style="margin-bottom:20px">
    <div style="font-size:1.4em;font-weight:700;color:#1a1a1a">Portfolio Briefing</div>
    <div style="font-size:0.82em;color:#888">{generated} &nbsp;·&nbsp; {total} programs</div>
  </div>

  <!-- Summary stats -->
  <div class="card" style="margin-bottom:20px">
    <div style="display:flex;flex-wrap:wrap;justify-content:space-around;border-bottom:1px solid #eee;margin-bottom:12px;padding-bottom:12px">
      {stat_box("Red", red, "#c0392b")}
      {stat_box("Yellow", yellow, "#d68910")}
      {stat_box("Green", green, "#1e8449")}
      {stat_box("Decisions", total_decisions, "#1a6e9e")}
      {stat_box("Blockers", total_blockers, "#e67e22")}
      {stat_box("Escalations", total_escalations, "#c0392b")}
    </div>
    {"<div style='font-size:0.82em;color:#c0392b'>⚑ Nearest deadline: " + nearest_dl_prog + " — " + nearest_dl + "</div>" if nearest_dl else ""}
  </div>

  <!-- Suggested actions -->
  {"<div class='card'>" + actions_html + "</div>" if actions_html else ""}

  <!-- Programs -->
  <div class="card">
    <div style="font-size:0.7em;font-weight:700;letter-spacing:0.08em;color:#888;
         text-transform:uppercase;margin-bottom:16px">Programs</div>
    {programs_html}
  </div>

  <!-- Cross-program signals -->
  {"<div class='card'><div style='font-size:0.7em;font-weight:700;letter-spacing:0.08em;color:#888;text-transform:uppercase;margin-bottom:8px'>Cross-Program Signals</div>" + cross_html + "</div>" if cross_html.strip() else ""}

  <div style="font-size:0.72em;color:#aaa;text-align:center;margin-top:16px">
    Generated by portfolio-orchestrator v1.0 · {generated}
  </div>

</div>
</body>
</html>"""


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render portfolio state JSON to HTML dashboard"
    )
    parser.add_argument("--portfolio", default=DEFAULT_PORTFOLIO,
                        help=f"Path to portfolio JSON (default: {DEFAULT_PORTFOLIO})")
    parser.add_argument("--output", default=DEFAULT_OUTPUT,
                        help=f"Output HTML path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--open", action="store_true",
                        help="Open dashboard in browser after rendering")
    args = parser.parse_args()

    portfolio = load_portfolio(args.portfolio)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    html = render_html(portfolio)
    output_path.write_text(html, encoding="utf-8")

    print(f"Portfolio dashboard written to: {output_path}")

    summary = portfolio.get("summary", {})
    print(f"  {summary.get('total_programs', 0)} programs | "
          f"🔴 {summary.get('red', 0)} | "
          f"🟡 {summary.get('yellow', 0)} | "
          f"🟢 {summary.get('green', 0)}")

    if args.open:
        try:
            import webbrowser
            webbrowser.open(output_path.resolve().as_uri())
        except Exception as e:
            print(f"Could not open browser: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
