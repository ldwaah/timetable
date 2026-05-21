#!/usr/bin/env python3
"""Generate student and staff timetable HTML from data/week.json."""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "week.json"
STAFF_DIR = ROOT / "staff"
DAY_ORDER = ("monday", "tuesday", "wednesday", "thursday", "friday")


def load_week() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def esc(text: str | None) -> str:
    return html.escape(text or "", quote=True)


def cell_class(label: str, kind: str) -> str:
    if kind == "assembly" or label == "Assembly":
        return "slot assembly"
    if label in ("Break", "Lunch"):
        return "slot break"
    if label == "Arrival":
        return "slot arrival"
    if label == "Maths":
        return "slot core maths"
    if label == "English":
        return "slot core english"
    if kind == "pe" or label.startswith("PE"):
        return "slot pe"
    if "Lesson" in label:
        return "slot lesson"
    return "slot"


def student_cell_html(row: dict, stage: str) -> str:
    label = row[stage]
    staff = row.get(f"staff_{stage}")
    cls = cell_class(label, row.get("kind", ""))
    time_range = f'{row["start"]}–{row["end"]}'
    label_html = esc(label)
    if staff:
        label_html = f'{esc(label)}<span class="slot-staff">{esc(staff)}</span>'
    return (
        f'<td class="{cls}">'
        f'<span class="slot-time">{esc(time_range)}</span>'
        f'<span class="slot-label">{label_html}</span></td>'
    )


def render_stage_grid(week: dict, stage: str) -> str:
    days = week["days"]
    max_rows = max(len(days[key]["rows"]) for key in DAY_ORDER)
    headers = []
    for key in DAY_ORDER:
        d = days[key]
        finish = d["finish"]
        headers.append(
            f'<th scope="col">{esc(d["label"])}<span class="finish-hint"> → {esc(finish)}</span></th>'
        )

    body_rows = []
    for i in range(max_rows):
        cells = []
        for key in DAY_ORDER:
            rows = days[key]["rows"]
            if i < len(rows):
                cells.append(student_cell_html(rows[i], stage))
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
            <tr>
              {''.join(headers)}
            </tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
      </div>
    </section>"""


def collect_staff_sessions(week: dict) -> dict[str, list[dict]]:
    sessions: dict[str, list[dict]] = {}
    for day_key in DAY_ORDER:
        day = week["days"][day_key]
        for row in day["rows"]:
            for stage in ("ks3", "ks4"):
                staff = row.get(f"staff_{stage}")
                if not staff:
                    continue
                sessions.setdefault(staff, []).append(
                    {
                        "day": day["label"],
                        "day_key": day_key,
                        "time": f'{row["start"]}–{row["end"]}',
                        "stage": "KS3" if stage == "ks3" else "KS4",
                        "subject": row[stage],
                    }
                )
    return sessions


def render_staff_person_page(week: dict, name: str, sessions: list[dict]) -> str:
    rows_html = []
    for s in sessions:
        rows_html.append(
            "<tr>"
            f'<td>{esc(s["day"])}</td>'
            f'<td class="time-col">{esc(s["time"])}</td>'
            f'<td>{esc(s["stage"])}</td>'
            f'<td class="subject-col">{esc(s["subject"])}</td>'
            "</tr>"
        )
    staff = week["staff"]
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(name)} — staff timetable</title>
  <style>{STAFF_PERSON_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="../staff-timetable.html">← Staff timetable</a>
    <h1>{esc(name)}</h1>
  </div>
  <p class="hints">On site from {esc(staff["start"])}. Teaching assignments this week.</p>
  <div class="table-wrap">
    <table class="person-grid">
      <thead>
        <tr>
          <th scope="col">Day</th>
          <th scope="col">Time</th>
          <th scope="col">Group</th>
          <th scope="col">Subject</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html) if rows_html else '<tr><td colspan="4" class="muted">No assigned sessions</td></tr>'}
      </tbody>
    </table>
  </div>
</body>
</html>
"""


def render_staff_day_timeline(week: dict) -> str:
    sections = []
    meta = week["meta"]
    for key in DAY_ORDER:
        day = week["days"][key]
        rows_html = []
        for row in day["rows"]:
            ks3, ks4 = row["ks3"], row["ks4"]
            s3 = row.get("staff_ks3")
            s4 = row.get("staff_ks4")
            k3_disp = esc(ks3) + (f' <span class="lead">({esc(s3)})</span>' if s3 else "")
            k4_disp = esc(ks4) + (f' <span class="lead">({esc(s4)})</span>' if s4 else "")
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
                f'<td class="{cell_class(ks3, row.get("kind", ""))}">{k3_disp}</td>'
                f'<td class="{cell_class(ks4, row.get("kind", ""))}">{k4_disp}</td>'
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
      padding: 2rem 1.25rem;
      max-width: 1200px;
      margin: 0 auto;
    }

    .top { margin-bottom: 1.5rem; }

    a.back {
      color: #58a6ff;
      text-decoration: none;
      font-size: 0.9rem;
    }

    a.back:hover { text-decoration: underline; }

    h1 {
      margin-top: 1rem;
      font-size: 1.5rem;
      font-weight: 600;
      color: #f0f6fc;
    }

    .banner {
      margin-bottom: 1.5rem;
      padding: 1rem 1.25rem;
      background: linear-gradient(135deg, #1f3a5f 0%, #161b22 100%);
      border: 1px solid #30363d;
      border-left: 4px solid #58a6ff;
      border-radius: 12px;
      font-size: 0.95rem;
      color: #c9d1d9;
      line-height: 1.55;
    }

    .banner strong { color: #f0f6fc; }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.25rem;
      margin-bottom: 1.5rem;
      font-size: 0.85rem;
      color: #8b949e;
    }

    .legend span::before {
      content: "";
      display: inline-block;
      width: 0.65rem;
      height: 0.65rem;
      border-radius: 3px;
      margin-right: 0.35rem;
      vertical-align: middle;
    }

    .legend .l-lesson::before { background: #30363d; }
    .legend .l-maths::before { background: #1f6feb; }
    .legend .l-english::before { background: #9e6a03; }
    .legend .l-break::before { background: #238636; }
    .legend .l-assembly::before { background: #a371f7; }
    .legend .l-arrival::before { background: #58a6ff; }
    .legend .l-pe::before { background: #238636; }

    .grid-section { margin-bottom: 2.5rem; }

    .grid-section h2 {
      font-size: 1.15rem;
      font-weight: 600;
      color: #f0f6fc;
      margin-bottom: 0.75rem;
    }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid #30363d;
      border-radius: 12px;
      background: #161b22;
    }

    .week-grid {
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
    }

    .week-grid th,
    .week-grid td {
      border: 1px solid #21262d;
      padding: 0.55rem 0.5rem;
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
      font-size: 0.7rem;
      font-weight: 500;
      color: #58a6ff;
      margin-top: 0.15rem;
    }

    .slot-time {
      display: block;
      font-size: 0.68rem;
      color: #8b949e;
      margin-bottom: 0.2rem;
    }

    .slot-label { font-weight: 500; color: #e6edf3; display: block; }

    .slot-staff {
      display: block;
      font-size: 0.72rem;
      font-weight: 500;
      color: #8b949e;
      margin-top: 0.15rem;
    }

    .slot.core.maths .slot-staff { color: #58a6ff; }
    .slot.core.english .slot-staff { color: #d4a72c; }

    .slot.lesson .slot-label { color: #c9d1d9; }
    .slot.core.maths { background: #1c2d4a; }
    .slot.core.maths .slot-label { color: #79c0ff; font-weight: 600; }
    .slot.core.english { background: #3d2e12; }
    .slot.core.english .slot-label { color: #e3b341; font-weight: 600; }
    .slot.break { background: #132d1b; }
    .slot.break .slot-label { color: #3fb950; }
    .slot.assembly { background: #2d1f4a; }
    .slot.assembly .slot-label { color: #d2a8ff; }
    .slot.arrival { background: #1f3a5f44; }
    .slot.arrival .slot-label { color: #58a6ff; }
    .slot.pe { background: #132d1b; }
    .slot.pe .slot-label { color: #3fb950; font-weight: 600; }
    .slot.empty { color: #484f58; text-align: center; }
"""

STAFF_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 2rem 1.25rem;
      max-width: 900px;
      margin: 0 auto;
    }

    .top { margin-bottom: 1.5rem; }

    a.back {
      color: #58a6ff;
      text-decoration: none;
      font-size: 0.9rem;
    }

    a.back:hover { text-decoration: underline; }

    h1 {
      margin-top: 1rem;
      font-size: 1.5rem;
      font-weight: 600;
      color: #f0f6fc;
    }

    .banner {
      margin-bottom: 1.5rem;
      padding: 1rem 1.25rem;
      background: linear-gradient(135deg, #3d1f5f 0%, #161b22 100%);
      border: 1px solid #30363d;
      border-left: 4px solid #a371f7;
      border-radius: 12px;
      font-size: 0.95rem;
      color: #c9d1d9;
      line-height: 1.55;
    }

    .banner strong { color: #f0f6fc; display: block; margin-bottom: 0.35rem; }

    .banner .staff-time { color: #a371f7; font-weight: 600; }
    .banner .student-time { color: #58a6ff; font-weight: 600; }

    .staff-links {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem 1rem;
      margin-bottom: 1.5rem;
    }

    .staff-links a {
      color: #58a6ff;
      text-decoration: none;
      font-size: 0.9rem;
      padding: 0.35rem 0.75rem;
      border: 1px solid #30363d;
      border-radius: 8px;
      background: #161b22;
    }

    .staff-links a:hover { background: #21262d; text-decoration: underline; }

    .week-table {
      width: 100%;
      border-collapse: collapse;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      overflow: hidden;
      margin-bottom: 2rem;
    }

    .week-table caption {
      padding: 0.75rem 1rem;
      text-align: left;
      font-weight: 600;
      color: #f0f6fc;
      background: #1c2128;
      border-bottom: 1px solid #30363d;
    }

    .week-table th,
    .week-table td {
      padding: 0.85rem 1rem;
      text-align: left;
      border-bottom: 1px solid #21262d;
    }

    .week-table th {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #8b949e;
      background: #1c2128;
    }

    .week-table tr:last-child td { border-bottom: none; }

    .week-table td:first-child {
      font-weight: 500;
      color: #f0f6fc;
      width: 22%;
    }

    .week-table .staff-start { color: #a371f7; font-weight: 600; }
    .week-table .student-window { color: #8b949e; font-size: 0.9rem; }
    .week-table .student-window em {
      font-style: normal;
      color: #58a6ff;
      font-weight: 500;
    }
    .week-table .finish { color: #58a6ff; font-weight: 600; }
    .week-table .detention { color: #f85149; font-weight: 600; font-size: 0.9rem; }
    .muted { color: #484f58; }

    h2.section-title {
      font-size: 1.1rem;
      margin-bottom: 1rem;
      color: #f0f6fc;
    }

    .day-block {
      margin-bottom: 0.75rem;
      border: 1px solid #30363d;
      border-radius: 12px;
      background: #161b22;
      overflow: hidden;
    }

    .day-block summary {
      cursor: pointer;
      padding: 0.85rem 1rem;
      background: #1c2128;
      list-style: none;
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem 1rem;
      align-items: baseline;
    }

    .day-block summary::-webkit-details-marker { display: none; }

    .day-name { font-weight: 600; color: #f0f6fc; }

    .day-meta { font-size: 0.85rem; color: #8b949e; }

    .timeline-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }

    .timeline-table th,
    .timeline-table td {
      padding: 0.5rem 0.75rem;
      border-top: 1px solid #21262d;
      text-align: left;
    }

    .timeline-table th {
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #8b949e;
      background: #161b22;
    }

    .time-col { color: #8b949e; white-space: nowrap; width: 8.5rem; }
    .note-col { color: #8b949e; font-size: 0.8rem; }
    .lead { color: #a371f7; font-size: 0.8rem; font-weight: 500; }
    .slot.break { color: #3fb950; }
    .slot.assembly { color: #d2a8ff; }
    .slot.arrival { color: #58a6ff; }
    .slot.lesson { color: #c9d1d9; }
    .slot.core.maths { color: #79c0ff; font-weight: 600; }
    .slot.core.english { color: #e3b341; font-weight: 600; }
    .slot.pe { color: #3fb950; font-weight: 600; }
"""

STAFF_PERSON_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 2rem 1.25rem;
      max-width: 720px;
      margin: 0 auto;
    }
    .top { margin-bottom: 1rem; }
    a.back { color: #58a6ff; text-decoration: none; font-size: 0.9rem; }
    h1 { margin-top: 0.75rem; font-size: 1.4rem; color: #f0f6fc; }
    .hints { font-size: 0.85rem; color: #8b949e; margin-bottom: 1rem; }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid #30363d;
      border-radius: 12px;
      background: #161b22;
    }
    .person-grid {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }
    .person-grid th, .person-grid td {
      padding: 0.55rem 0.75rem;
      border-bottom: 1px solid #21262d;
      text-align: left;
    }
    .person-grid th {
      background: #1c2128;
      color: #8b949e;
      font-size: 0.72rem;
      text-transform: uppercase;
    }
    .time-col { color: #8b949e; white-space: nowrap; }
    .subject-col { color: #f0f6fc; font-weight: 500; }
    .muted { color: #484f58; text-align: center; }
"""


def build_student_html(week: dict) -> str:
    meta = week["meta"]
    ks3_breaks = "Mon: 10:40 & 12:45 · Tue: 11:15 & 13:20 · Wed: 11:35 & 13:40 · Thu/Fri: 10:30 & 12:25"
    ks4_breaks = "Mon: 09:45 & 13:40 · Tue: 10:20 & 14:15 · Wed: 10:40 & 14:35 · Thu/Fri: 09:40 & 13:15"
    ks3_lunch = "Mon–Fri: 11:50–12:05 (KS4 at 11:35–11:50)"
    ks4_lunch = "Mon–Fri: 11:35–11:50 (KS3 at 11:50–12:05)"

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

  <aside class="banner" role="status">
    <strong>Arrival &amp; finish</strong>
    Mon, Tue, Thu, Fri: from <strong>08:50</strong> (latest <strong>09:05</strong>). Wednesday: from <strong>10:00</strong>.
    Finish Mon–Wed <strong>15:00</strong>; Thu–Fri <strong>14:00</strong>.
    Assembly <strong>Tuesday 09:05–09:40</strong> ({meta["assembly_minutes"]} min, whole school).
    Two breaks and one lunch per day (15 min each); KS3 and KS4 staggered.
    <strong>Maths &amp; English:</strong> English in the first teaching block; Maths in the block after the first break (between-breaks window). Not scheduled post-lunch.
    Teacher names shown under assigned subjects.
  </aside>

  <div class="legend" aria-hidden="true">
    <span class="l-english">English</span>
    <span class="l-maths">Maths</span>
    <span class="l-pe">PE</span>
    <span class="l-lesson">Other lessons</span>
    <span class="l-break">Break / Lunch</span>
    <span class="l-assembly">Assembly</span>
    <span class="l-arrival">Arrival</span>
  </div>

  <p class="legend" style="margin-top:-0.75rem">
    <strong style="color:#f0f6fc">Example breaks — KS3:</strong> {esc(ks3_breaks)}.
    <strong style="color:#f0f6fc">KS4:</strong> {esc(ks4_breaks)}.
    <strong style="color:#f0f6fc">Lunch — KS3:</strong> {esc(ks3_lunch)}.
    <strong style="color:#f0f6fc">KS4:</strong> {esc(ks4_lunch)}.
  </p>

  {render_stage_grid(week, "ks3")}
  {render_stage_grid(week, "ks4")}
</body>
</html>
"""


def build_staff_html(week: dict) -> str:
    meta = week["meta"]
    staff = week["staff"]
    det = staff["detentions"]
    people = staff.get("people", [])

    overview_rows = []
    for key in DAY_ORDER:
        d = week["days"][key]
        arrival = f'from <em>{esc(d["arrival_from"])}</em>'
        if d.get("arrival_latest"):
            arrival += f', latest <em>{esc(d["arrival_latest"])}</em>'
        if key == "monday":
            det_cell = f'<td class="detention">Detentions {esc(det["monday"])}</td>'
        elif key == "friday":
            det_cell = f'<td class="detention">Detentions {esc(det["friday"])}</td>'
        else:
            det_cell = '<td class="muted">—</td>'
        overview_rows.append(
            f"<tr><td>{esc(d['label'])}</td>"
            f'<td class="staff-start">{esc(staff["start"])}</td>'
            f'<td class="student-window">{arrival}</td>'
            f'<td class="finish">{esc(d["finish"])}</td>'
            f"{det_cell}</tr>"
        )

    person_links = "".join(
        f'<a href="staff/{esc(name.lower())}.html">{esc(name)}</a>' for name in people
    )

    assign = staff.get("assignments", {})
    assign_lines = []
    for subject, stages in assign.items():
        parts = [f"{k.upper()}: {v}" for k, v in stages.items()]
        assign_lines.append(f"<li><strong>{esc(subject)}</strong> — {esc(', '.join(parts))}</li>")
    assign_list = "<ul class=\"assign-list\">" + "".join(assign_lines) + "</ul>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Staff timetable</title>
  <style>{STAFF_CSS}
    .assign-list {{ margin: 0.5rem 0 0 1.1rem; font-size: 0.9rem; color: #c9d1d9; }}
    .assign-list li {{ margin: 0.25rem 0; }}
  </style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">← Back</a>
    <h1>Staff timetable</h1>
  </div>

  <aside class="banner" role="status">
    <strong>Start &amp; finish — Monday to Friday</strong>
    Staff on site from <span class="staff-time">{esc(staff["start"])}</span> every day.
    Students Mon, Tue, Thu, Fri from <span class="student-time">08:50</span> (latest <span class="student-time">09:05</span>);
    Wednesday from <span class="student-time">10:00</span>.
    School finish Mon–Wed <span class="student-time">15:00</span>; Thu–Fri <span class="student-time">14:00</span>.
    Assembly <span class="student-time">Tuesday</span> ({meta["assembly_minutes"]} min).
    <strong>Lead teachers:</strong>
    {assign_list}
  </aside>

  <nav class="staff-links" aria-label="Individual staff timetables">
    {person_links}
  </nav>

  <table class="week-table">
    <caption>Weekly times</caption>
    <thead>
      <tr>
        <th scope="col">Day</th>
        <th scope="col">Staff start</th>
        <th scope="col">Students</th>
        <th scope="col">Finish</th>
        <th scope="col">Detentions</th>
      </tr>
    </thead>
    <tbody>
      {''.join(overview_rows)}
    </tbody>
  </table>

  <h2 class="section-title">Daily timeline (KS3 / KS4 — names in parentheses)</h2>
  {render_staff_day_timeline(week)}
</body>
</html>
"""


def main() -> None:
    week = load_week()
    if "rows" not in week["days"]["monday"]:
        raise SystemExit("week.json must use days.*.rows format")

    (ROOT / "student-timetable.html").write_text(build_student_html(week), encoding="utf-8")
    (ROOT / "staff-timetable.html").write_text(build_staff_html(week), encoding="utf-8")

    STAFF_DIR.mkdir(exist_ok=True)
    sessions = collect_staff_sessions(week)
    for name in week["staff"].get("people", []):
        slug = name.lower()
        page = render_staff_person_page(week, name, sessions.get(name, []))
        (STAFF_DIR / f"{slug}.html").write_text(page, encoding="utf-8")

    print("Wrote student-timetable.html, staff-timetable.html, and staff/*.html")


if __name__ == "__main__":
    main()
