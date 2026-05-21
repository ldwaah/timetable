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
    if kind == "reset" or label == "Reset":
        return "slot reset"
    if kind == "checks" or "Checks" in label:
        return "slot checks"
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


def compare_cell_html(row: dict, stage: str, *, show_staff: bool = True) -> str:
    label = row[stage]
    staff = row.get(f"staff_{stage}") if show_staff else None
    cls = cell_class(label, row.get("kind", ""))
    label_html = esc(label)
    if staff:
        label_html = f'{esc(label)}<span class="slot-staff">{esc(staff)}</span>'
    return f'<td class="{cls}"><span class="slot-label">{label_html}</span></td>'


def day_arrival_hint(day: dict) -> str:
    arrival = f'from {day["arrival_from"]}'
    if day.get("arrival_latest"):
        arrival += f', latest {day["arrival_latest"]}'
    return arrival


def break_hints(week: dict, stage: str) -> str:
    parts = []
    for key in DAY_ORDER:
        day = week["days"][key]
        slots = [
            f'{r["start"]}–{r["end"]}'
            for r in day["rows"]
            if r[stage] == "Break"
        ]
        if slots:
            parts.append(f'{day["label"][:3]}: {" & ".join(slots)}')
    return " · ".join(parts)


def render_day_tab_inputs(default_key: str = "monday") -> str:
    parts = []
    for key in DAY_ORDER:
        checked = " checked" if key == default_key else ""
        parts.append(
            f'<input type="radio" name="day-tab" id="tab-{key}" class="tab-input"{checked}>'
        )
    return "\n    ".join(parts)


def render_day_tab_bar() -> str:
    labels = []
    for key in DAY_ORDER:
        short = key[:3].capitalize()
        labels.append(
            f'<label for="tab-{key}" class="day-tab-btn" role="tab">{short}</label>'
        )
    return f'<div class="tab-bar" role="tablist">{"".join(labels)}</div>'


def render_student_day_panel(week: dict, day_key: str) -> str:
    day = week["days"][day_key]
    rows_html = []
    for i, row in enumerate(day["rows"], 1):
        rows_html.append(
            "<tr>"
            f'<td class="period-col">{i}</td>'
            f'<td class="time-col">{esc(row["start"])}–{esc(row["end"])}</td>'
            f"{compare_cell_html(row, 'ks3')}"
            f"{compare_cell_html(row, 'ks4')}"
            "</tr>"
        )
    arrival = day_arrival_hint(day)
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel" aria-labelledby="tab-{day_key}">
        <p class="day-meta">Students {esc(arrival)} · finish <strong>{esc(day["finish"])}</strong></p>
        <div class="table-wrap">
          <table class="day-grid">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Time</th>
                <th scope="col">KS3</th>
                <th scope="col">KS4</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
      </section>"""


def render_student_day_views(week: dict) -> str:
    panels = [render_student_day_panel(week, key) for key in DAY_ORDER]
    panel_css = "\n    ".join(
        f"#tab-{key}:checked ~ .tab-panels #panel-{key} {{ display: block; }}"
        for key in DAY_ORDER
    )
    return f"""
  <style>
    {panel_css}
  </style>
  <div class="day-tabs">
    {render_day_tab_inputs()}
    {render_day_tab_bar()}
    <div class="tab-panels">
      {''.join(panels)}
    </div>
  </div>"""


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


def group_sessions_by_day(sessions: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {key: [] for key in DAY_ORDER}
    for s in sessions:
        grouped[s["day_key"]].append(s)
    return grouped


def render_person_day_panel(day_key: str, day_label: str, sessions: list[dict]) -> str:
    if sessions:
        rows_html = []
        for s in sessions:
            rows_html.append(
                "<tr>"
                f'<td class="time-col">{esc(s["time"])}</td>'
                f'<td>{esc(s["stage"])}</td>'
                f'<td class="subject-col">{esc(s["subject"])}</td>'
                "</tr>"
            )
        body = "".join(rows_html)
    else:
        body = '<tr><td colspan="3" class="muted">No sessions</td></tr>'
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel">
        <p class="day-meta">{esc(day_label)}</p>
        <div class="table-wrap">
          <table class="person-grid">
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">Group</th>
                <th scope="col">Subject</th>
              </tr>
            </thead>
            <tbody>{body}</tbody>
          </table>
        </div>
      </section>"""


def render_person_day_tabs(week: dict, sessions: list[dict]) -> str:
    grouped = group_sessions_by_day(sessions)
    panels = []
    for key in DAY_ORDER:
        day_label = week["days"][key]["label"]
        panels.append(render_person_day_panel(key, day_label, grouped[key]))
    panel_css = "\n    ".join(
        f"#tab-{key}:checked ~ .tab-panels #panel-{key} {{ display: block; }}"
        for key in DAY_ORDER
    )
    return f"""
  <style>
    {panel_css}
  </style>
  <div class="day-tabs">
    {render_day_tab_inputs()}
    {render_day_tab_bar()}
    <div class="tab-panels">
      {''.join(panels)}
    </div>
  </div>"""


def render_staff_person_page(week: dict, name: str, sessions: list[dict]) -> str:
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
  <p class="hints">On site from {esc(staff["start"])}. Teaching assignments by day.</p>
  {render_person_day_tabs(week, sessions)}
</body>
</html>
"""


def render_staff_day_panel(week: dict, day_key: str) -> str:
    meta = week["meta"]
    day = week["days"][day_key]
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
    arrival = day_arrival_hint(day)
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel">
        <p class="day-meta">Students {esc(arrival)} · finish <strong>{esc(day["finish"])}</strong></p>
        <div class="table-wrap">
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
        </div>
      </section>"""


def render_staff_day_tabs(week: dict) -> str:
    panels = [render_staff_day_panel(week, key) for key in DAY_ORDER]
    panel_css = "\n    ".join(
        f"#tab-{key}:checked ~ .tab-panels #panel-{key} {{ display: block; }}"
        for key in DAY_ORDER
    )
    return f"""
  <style>
    {panel_css}
  </style>
  <div class="day-tabs">
    {render_day_tab_inputs()}
    {render_day_tab_bar()}
    <div class="tab-panels">
      {''.join(panels)}
    </div>
  </div>"""


DAY_TAB_CSS = """
    .tab-input { position: absolute; opacity: 0; pointer-events: none; width: 0; height: 0; }

    .day-tabs { margin-top: 0.5rem; }

    .tab-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin-bottom: 1rem;
    }

    .day-tab-btn {
      cursor: pointer;
      padding: 0.45rem 0.9rem;
      font-size: 0.9rem;
      font-weight: 500;
      color: #8b949e;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      transition: background 0.15s, color 0.15s, border-color 0.15s;
    }

    .day-tab-btn:hover { color: #e6edf3; background: #21262d; }

    #tab-monday:checked ~ .tab-bar label[for="tab-monday"],
    #tab-tuesday:checked ~ .tab-bar label[for="tab-tuesday"],
    #tab-wednesday:checked ~ .tab-bar label[for="tab-wednesday"],
    #tab-thursday:checked ~ .tab-bar label[for="tab-thursday"],
    #tab-friday:checked ~ .tab-bar label[for="tab-friday"] {
      color: #f0f6fc;
      background: #1f3a5f;
      border-color: #58a6ff;
    }

    .tab-panels { position: relative; }

    .day-panel { display: none; }

    .day-meta {
      font-size: 0.85rem;
      color: #8b949e;
      margin-bottom: 0.75rem;
    }

    .day-meta strong { color: #58a6ff; font-weight: 600; }
"""

SHARED_STUDENT_CSS = """
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

    .hints {
      margin-bottom: 1.25rem;
      font-size: 0.88rem;
      color: #8b949e;
      line-height: 1.55;
    }

    .hints strong { color: #c9d1d9; font-weight: 500; }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.25rem;
      margin-bottom: 1.25rem;
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
    .legend .l-reset::before { background: #79c0ff; }
    .legend .l-arrival::before { background: #58a6ff; }
    .legend .l-pe::before { background: #238636; }

    .table-wrap {
      overflow-x: auto;
      border: 1px solid #30363d;
      border-radius: 12px;
      background: #161b22;
    }

    .day-grid {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }

    .day-grid th,
    .day-grid td {
      border: 1px solid #21262d;
      padding: 0.55rem 0.65rem;
      vertical-align: top;
      text-align: left;
    }

    .day-grid th {
      background: #1c2128;
      color: #f0f6fc;
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .period-col {
      color: #484f58;
      font-size: 0.75rem;
      text-align: center;
      width: 2rem;
    }

    .time-col {
      color: #8b949e;
      white-space: nowrap;
      width: 7.5rem;
      font-size: 0.8rem;
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
    .slot.reset { background: #1c2d4a; }
    .slot.reset .slot-label { color: #79c0ff; font-weight: 600; }
    .slot.checks { background: #21262d; }
    .slot.checks .slot-label { color: #8b949e; font-style: italic; }
    .slot.arrival { background: #1f3a5f44; }
    .slot.arrival .slot-label { color: #58a6ff; }
    .slot.pe { background: #132d1b; }
    .slot.pe .slot-label { color: #3fb950; font-weight: 600; }
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

    .hints {
      margin-bottom: 1.25rem;
      font-size: 0.88rem;
      color: #8b949e;
      line-height: 1.55;
    }

    .hints strong { color: #c9d1d9; font-weight: 500; }

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

    .table-wrap {
      overflow-x: auto;
      border: 1px solid #30363d;
      border-radius: 12px;
      background: #161b22;
    }

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
    .slot.reset { color: #79c0ff; font-weight: 600; }
    .slot.checks { color: #8b949e; font-style: italic; }
    .slot.arrival { color: #58a6ff; }
    .slot.lesson { color: #c9d1d9; }
    .slot.core.maths { color: #79c0ff; font-weight: 600; }
    .slot.core.english { color: #e3b341; font-weight: 600; }
    .slot.pe { color: #3fb950; font-weight: 600; }
"""

STAFF_PERSON_CSS = (
    DAY_TAB_CSS
    + """
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
)


def build_student_html(week: dict) -> str:
    meta = week["meta"]
    ks3_breaks = break_hints(week, "ks3")
    ks4_breaks = break_hints(week, "ks4")
    lunch_line = meta.get("lunch_time", "12:15–12:30")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Student timetable</title>
  <style>{DAY_TAB_CSS}{SHARED_STUDENT_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">← Back</a>
    <h1>Student timetable</h1>
  </div>

  <p class="hints">
    Pick a day below — <strong>KS3 and KS4 side by side</strong> for that day only.
    Mon/Tue/Thu/Fri from <strong>08:50</strong> (latest <strong>09:05</strong>); Wed from <strong>10:00</strong>.
    Finish Mon–Wed <strong>15:00</strong>; Thu–Fri <strong>14:00</strong>.
    Checks <strong>{esc(meta["checks_window"])}</strong>, then Reset ({meta["reset_minutes"]} min).
    Tue: Reset → Assembly ({meta["assembly_minutes"]} min) → English.
    Lunch <strong>{esc(lunch_line)}</strong> (both KS3 &amp; KS4). Breaks staggered between key stages.
  </p>

  <div class="legend" aria-hidden="true">
    <span class="l-english">English</span>
    <span class="l-maths">Maths</span>
    <span class="l-pe">PE</span>
    <span class="l-lesson">Other lessons</span>
    <span class="l-break">Break / Lunch</span>
    <span class="l-assembly">Assembly</span>
    <span class="l-reset">Reset</span>
    <span class="l-arrival">Arrival</span>
  </div>

  <p class="legend" style="margin-top:-0.75rem">
    <strong style="color:#f0f6fc">Example breaks — KS3:</strong> {esc(ks3_breaks)}.
    <strong style="color:#f0f6fc">KS4:</strong> {esc(ks4_breaks)}.
    <strong style="color:#f0f6fc">Breaks — KS3:</strong> {esc(ks3_breaks)}.
    <strong style="color:#f0f6fc">KS4:</strong> {esc(ks4_breaks)}.
  </p>

  {render_student_day_views(week)}
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
        staff_note = ""
        if key == "wednesday" and d.get("staff_meeting"):
            staff_note = f'<br><span class="muted">Staff meeting {esc(d["staff_meeting"])} (students from {esc(d["arrival_from"])})</span>'
        overview_rows.append(
            f"<tr><td>{esc(d['label'])}</td>"
            f'<td class="staff-start">{esc(staff["start"])}{staff_note}</td>'
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
  <style>{DAY_TAB_CSS}{STAFF_CSS}
    .assign-list {{ margin: 0.35rem 0 0 1.1rem; font-size: 0.85rem; color: #8b949e; }}
    .assign-list li {{ margin: 0.2rem 0; }}
  </style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">← Back</a>
    <h1>Staff timetable</h1>
  </div>

  <p class="hints">
    Pick a day — KS3 / KS4 timeline with staff in parentheses.
    Staff from <strong>{esc(staff["start"])}</strong>.
    Students Mon/Tue/Thu/Fri <strong>08:50–09:05</strong>; Wed <strong>10:00</strong>.
    Finish Mon–Wed <strong>15:00</strong>; Thu–Fri <strong>14:00</strong>.
    Checks {esc(meta["checks_window"])}, Reset {meta["reset_minutes"]} min; Tue assembly {meta["assembly_minutes"]} min.
    Leads: {", ".join(f"{esc(s)} ({esc(', '.join(f'{k.upper()}: {v}' for k, v in stages.items()))})" for s, stages in assign.items())}.
  </p>

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
  {render_staff_day_tabs(week)}
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
