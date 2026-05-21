#!/usr/bin/env python3
"""Generate student and staff timetable HTML from data/week.json."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "week.json"
DAY_ORDER = ("monday", "tuesday", "wednesday", "thursday", "friday")


def load_week() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def esc(text: str | None) -> str:
    return html.escape(text or "", quote=True)


def uses_rows(week: dict) -> bool:
    return "rows" in week["days"][DAY_ORDER[0]]


def cell_class(label: str, kind: str) -> str:
    if kind == "assembly" or label == "Assembly":
        return "slot assembly"
    if kind == "pe" or label.startswith("PE"):
        return "slot pe"
    if label in ("Break", "Lunch"):
        return "slot break"
    if label == "Arrival":
        return "slot arrival"
    if label == "Maths":
        return "slot core maths"
    if label == "English":
        return "slot core english"
    if "Lesson" in label:
        return "slot lesson"
    return "slot"


def render_stage_grid_rows(week: dict, stage: str) -> str:
    days = week["days"]
    max_rows = max(len(days[key]["rows"]) for key in DAY_ORDER)
    headers = []
    for key in DAY_ORDER:
        d = days[key]
        headers.append(
            f'<th scope="col">{esc(d["label"])}'
            f'<span class="finish-hint"> → {esc(d["finish"])}</span></th>'
        )

    body_rows = []
    for i in range(max_rows):
        cells = []
        for key in DAY_ORDER:
            rows = days[key]["rows"]
            if i < len(rows):
                row = rows[i]
                label = row[stage]
                time_range = f'{row["start"]}–{row["end"]}'
                cls = cell_class(label, row.get("kind", ""))
                cells.append(
                    f'<td class="{cls}">'
                    f'<span class="slot-time">{esc(time_range)}</span>'
                    f'<span class="slot-label">{esc(label)}</span></td>'
                )
            else:
                cells.append('<td class="slot empty">—</td>')
        body_rows.append("<tr>" + "".join(cells) + "</tr>")

    caption = "Key Stage 3" if stage == "ks3" else "Key Stage 4"
    return f"""
    <section class="grid-section">
      <h2>{esc(caption)}</h2>
      <div class="table-wrap">
        <table class="week-grid">
          <thead>
            <tr>{''.join(headers)}</tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
      </div>
    </section>"""


def render_staff_timeline_rows(week: dict) -> str:
    sections = []
    meta = week["meta"]
    for key in DAY_ORDER:
        day = week["days"][key]
        rows_html = []
        for row in day["rows"]:
            ks3, ks4 = row["ks3"], row["ks4"]
            note = ""
            if ks3 in ("Break", "Lunch") and ks4 not in ("Break", "Lunch"):
                note = "KS3 break / KS4 in lesson"
            elif ks4 in ("Break", "Lunch") and ks3 not in ("Break", "Lunch"):
                note = "KS4 break / KS3 in lesson"
            elif ks3 == ks4 == "Assembly":
                note = f"Assembly ({meta['assembly_minutes']} min)"
            rows_html.append(
                f"<tr>"
                f'<td class="time-col">{esc(row["start"])}–{esc(row["end"])}</td>'
                f'<td class="{cell_class(ks3, row.get("kind", ""))}">{esc(ks3)}</td>'
                f'<td class="{cell_class(ks4, row.get("kind", ""))}">{esc(ks4)}</td>'
                f'<td class="note-col">{esc(note) if note else "<span class=\"muted\">—</span>"}</td>'
                f"</tr>"
            )
        arrival = f'from {day["arrival_from"]}'
        if day.get("arrival_latest"):
            arrival += f', latest {day["arrival_latest"]}'
        sections.append(
            f"""
    <details class="day-block" {"open" if key == "monday" else ""}>
      <summary>
        <span class="day-name">{esc(day["label"])}</span>
        <span class="day-meta">Students {esc(arrival)} · finish {esc(day["finish"])}</span>
      </summary>
      <table class="timeline-table">
        <thead>
          <tr>
            <th scope="col">Time</th>
            <th scope="col">KS3</th>
            <th scope="col">KS4</th>
            <th scope="col">Stagger</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </details>"""
        )
    return "\n".join(sections)


SHARED_STUDENT_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 1.5rem 1.25rem;
      max-width: 1200px;
      margin: 0 auto;
    }
    .top { margin-bottom: 1rem; }
    a.back { color: #58a6ff; text-decoration: none; font-size: 0.9rem; }
    a.back:hover { text-decoration: underline; }
    h1 { margin-top: 0.5rem; font-size: 1.35rem; font-weight: 600; color: #f0f6fc; }
    .hints {
      font-size: 0.85rem;
      color: #8b949e;
      margin-bottom: 1.25rem;
      line-height: 1.5;
      padding: 0.85rem 1rem;
      background: #161b22;
      border: 1px solid #30363d;
      border-left: 3px solid #58a6ff;
      border-radius: 8px;
    }
    .hints strong { color: #f0f6fc; }
    .grid-section { margin-bottom: 2rem; }
    .grid-section h2 { font-size: 1.05rem; font-weight: 600; color: #f0f6fc; margin-bottom: 0.5rem; }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid #30363d;
      border-radius: 10px;
      background: #161b22;
    }
    .week-grid {
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
    }
    .week-grid th, .week-grid td {
      border: 1px solid #21262d;
      padding: 0.5rem 0.45rem;
      vertical-align: top;
      font-size: 0.8rem;
    }
    .week-grid th {
      background: #1c2128;
      color: #f0f6fc;
      font-weight: 600;
      text-align: center;
    }
    .finish-hint {
      display: block;
      font-size: 0.68rem;
      font-weight: 500;
      color: #58a6ff;
      margin-top: 0.1rem;
    }
    .slot-time {
      display: block;
      font-size: 0.68rem;
      color: #8b949e;
      margin-bottom: 0.15rem;
    }
    .slot-label { font-weight: 500; color: #e6edf3; }
    .slot.lesson .slot-label { color: #c9d1d9; }
    .slot.core.maths { background: #1c2d4a; }
    .slot.core.maths .slot-label { color: #79c0ff; font-weight: 600; }
    .slot.core.english { background: #3d2e12; }
    .slot.core.english .slot-label { color: #e3b341; font-weight: 600; }
    .slot.pe { background: #1a3d2e; }
    .slot.pe .slot-label { color: #56d364; font-weight: 600; }
    .slot.break { background: #132d1b; }
    .slot.break .slot-label { color: #3fb950; }
    .slot.assembly { background: #2d1f4a; }
    .slot.assembly .slot-label { color: #d2a8ff; }
    .slot.arrival { background: #1f3a5f33; }
    .slot.arrival .slot-label { color: #58a6ff; }
    .slot.empty { color: #484f58; text-align: center; }
"""

STAFF_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 1.5rem 1.25rem;
      max-width: 900px;
      margin: 0 auto;
    }
    .top { margin-bottom: 1rem; }
    a.back { color: #58a6ff; text-decoration: none; font-size: 0.9rem; }
    h1 { margin-top: 0.5rem; font-size: 1.35rem; font-weight: 600; color: #f0f6fc; }
    .hints { font-size: 0.85rem; color: #8b949e; margin-bottom: 1rem; line-height: 1.45; }
    .day-block {
      margin-bottom: 0.75rem;
      border: 1px solid #30363d;
      border-radius: 10px;
      background: #161b22;
      overflow: hidden;
    }
    .day-block summary {
      cursor: pointer;
      padding: 0.75rem 1rem;
      background: #1c2128;
      list-style: none;
    }
    .day-block summary::-webkit-details-marker { display: none; }
    .day-name { font-weight: 600; color: #f0f6fc; }
    .day-meta { font-size: 0.82rem; color: #8b949e; margin-left: 0.5rem; }
    .timeline-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }
    .timeline-table th, .timeline-table td {
      padding: 0.45rem 0.65rem;
      border-top: 1px solid #21262d;
      text-align: left;
    }
    .timeline-table th {
      font-size: 0.68rem;
      text-transform: uppercase;
      color: #8b949e;
      background: #161b22;
    }
    .time-col { color: #8b949e; white-space: nowrap; }
    .note-col { color: #8b949e; font-size: 0.78rem; }
    .slot.break { color: #3fb950; }
    .slot.pe { color: #56d364; font-weight: 600; }
    .slot.assembly { color: #d2a8ff; }
    .slot.core.maths { color: #79c0ff; font-weight: 600; }
    .slot.core.english { color: #e3b341; font-weight: 600; }
    .muted { color: #484f58; }
"""


def build_student_html(week: dict) -> str:
    meta = week["meta"]
    pe_note = (
        f'<strong>PE:</strong> {esc(meta["pe_label"])} ({meta["pe_minutes"]} min) '
        "Mon, Tue, Thu, Fri — same time for KS3 and KS4. No PE on Wednesday."
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Student timetable</title>
  <style>{SHARED_STUDENT_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">← Back</a>
    <h1>Student timetable</h1>
  </div>
  <p class="hints">
    <strong>Arrival &amp; finish:</strong> Mon, Tue, Thu, Fri from 08:50 (latest 09:05); Wed from 10:00.
    Finish Mon–Wed 15:00; Thu–Fri 14:00. Assembly Tuesday morning ({meta["assembly_minutes"]} min).
    Staggered breaks; lunch {esc(meta["lunch_time"])} where shown.
    {pe_note}
  </p>
  {render_stage_grid_rows(week, "ks3")}
  {render_stage_grid_rows(week, "ks4")}
</body>
</html>
"""


def build_staff_html(week: dict) -> str:
    staff = week["staff"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Staff timetable</title>
  <style>{STAFF_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">← Back</a>
    <h1>Staff timetable</h1>
  </div>
  <p class="hints">
    Staff from {esc(staff["start"])}. Students Mon/Tue/Thu/Fri 08:50 (latest 09:05), Wed 10:00.
    Detentions: Mon {esc(staff["detentions"]["monday"])}, Fri {esc(staff["detentions"]["friday"])}.
  </p>
  {render_staff_timeline_rows(week)}
</body>
</html>
"""


def main() -> None:
    week = load_week()
    if not uses_rows(week):
        raise SystemExit("week.json must use days.*.rows format")
    (ROOT / "student-timetable.html").write_text(build_student_html(week), encoding="utf-8")
    (ROOT / "staff-timetable.html").write_text(build_staff_html(week), encoding="utf-8")
    print("Wrote student-timetable.html and staff-timetable.html")


if __name__ == "__main__":
    main()
