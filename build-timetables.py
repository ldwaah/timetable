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
    if label == "Lesson":
        return "slot lesson"
    return "slot"


def period_time(week: dict, period_index: int, day_key: str) -> str | None:
    day = week["days"][day_key]
    overrides = day.get("time_overrides") or {}
    if str(period_index) in overrides:
        return overrides[str(period_index)]
    period = week["periods"][period_index]
    times = period["times"]
    if day_key in times:
        return times[day_key]
    if day_key == "wednesday" and "wednesday" in times:
        return times["wednesday"]
    return times.get("default")


def slot_index_for_day(day_key: str, period_index: int) -> int | None:
    if day_key == "wednesday" and period_index == 0:
        return None
    if day_key == "wednesday":
        return period_index - 1
    return period_index


def day_slot(week: dict, day_key: str, period_index: int) -> dict | None:
    slot_i = slot_index_for_day(day_key, period_index)
    if slot_i is None:
        return None
    slots = week["days"][day_key]["slots"]
    if slot_i >= len(slots):
        return None
    return slots[slot_i]


def render_stage_grid(week: dict, stage: str) -> str:
    periods = week["periods"]
    headers = "".join(
        f'<th scope="col">{esc(week["days"][key]["label"])}</th>' for key in DAY_ORDER
    )

    body_rows = []
    for pi, period in enumerate(periods):
        cells = []
        for day_key in DAY_ORDER:
            slot = day_slot(week, day_key, pi)
            if slot is None or period_time(week, pi, day_key) is None:
                cells.append('<td class="slot empty">—</td>')
                continue
            label = slot[stage]
            cls = cell_class(label, slot.get("kind", ""))
            cells.append(f'<td class="{cls}">{esc(label)}</td>')

        t = period["times"].get("default") or period["times"].get("wednesday") or "—"
        body_rows.append(
            "<tr>"
            f'<th scope="row" class="period-col">{esc(period["label"])}</th>'
            f'<td class="time-col">{esc(t)}</td>'
            + "".join(cells)
            + "</tr>"
        )

    caption = "Key Stage 3" if stage == "ks3" else "Key Stage 4"
    return f"""
    <section class="grid-section">
      <h2>{esc(caption)}</h2>
      <p class="grid-note">Times are Mon/Tue/Thu/Fri. Wednesday is one hour later (from 10:00).</p>
      <div class="table-wrap">
        <table class="week-grid">
          <thead>
            <tr>
              <th scope="col">Period</th>
              <th scope="col">Time</th>
              {headers}
            </tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
      </div>
    </section>"""


def render_staff_week_grid(week: dict) -> str:
    periods = week["periods"]
    headers = "".join(
        f'<th scope="col">{esc(week["days"][key]["label"])}</th>' for key in DAY_ORDER
    )

    body_rows = []
    for pi, period in enumerate(periods):
        pname = "Arrival" if period["label"] == "—" else period["label"]
        t = period["times"].get("default") or "—"
        cells = []
        for day_key in DAY_ORDER:
            slot = day_slot(week, day_key, pi)
            if not slot:
                cells.append('<td class="staff-cell muted">—</td>')
                continue
            k3, k4 = slot["ks3"], slot["ks4"]
            stagger = ""
            if (k3 in ("Break", "Lunch")) != (k4 in ("Break", "Lunch")):
                stagger = '<span class="stagger">≠</span>'
            cells.append(
                f'<td class="staff-cell">'
                f'<span class="ks3">{esc(k3)}</span> / <span class="ks4">{esc(k4)}</span>{stagger}</td>'
            )
        body_rows.append(
            "<tr>"
            f'<th scope="row">{esc(pname)}</th>'
            f'<td class="time-col">{esc(t)}</td>'
            + "".join(cells)
            + "</tr>"
        )

    staff = week["staff"]
    det = staff["detentions"]
    finish_row = "".join(
        f"<td>{esc(week['days'][k]['finish'])}</td>" for k in DAY_ORDER
    )
    det_cells = []
    for key in DAY_ORDER:
        if key == "monday":
            det_cells.append(f'<td class="detention">{esc(det["monday"])}</td>')
        elif key == "friday":
            det_cells.append(f'<td class="detention">{esc(det["friday"])}</td>')
        else:
            det_cells.append('<td class="muted">—</td>')

    return f"""
  <table class="week-grid staff-grid">
    <thead>
      <tr>
        <th scope="col">Period</th>
        <th scope="col">Time</th>
        {headers}
      </tr>
    </thead>
    <tbody>
      {''.join(body_rows)}
      <tr class="meta-row">
        <th scope="row">Finish</th>
        <td></td>
        {finish_row}
      </tr>
      <tr class="meta-row">
        <th scope="row">Detentions</th>
        <td></td>
        {''.join(det_cells)}
      </tr>
    </tbody>
  </table>
  <p class="grid-note">Staff on site from {esc(staff["start"])}. <span class="stagger">≠</span> staggered break.</p>"""


SHARED_STUDENT_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 1.5rem 1.25rem;
      max-width: 1100px;
      margin: 0 auto;
    }
    .top { margin-bottom: 1rem; }
    a.back { color: #58a6ff; text-decoration: none; font-size: 0.9rem; }
    a.back:hover { text-decoration: underline; }
    h1 { margin-top: 0.5rem; font-size: 1.35rem; font-weight: 600; color: #f0f6fc; }
    .hints { font-size: 0.8rem; color: #8b949e; margin-bottom: 1.25rem; line-height: 1.45; }
    .grid-section { margin-bottom: 2rem; }
    .grid-section h2 { font-size: 1.05rem; font-weight: 600; color: #f0f6fc; margin-bottom: 0.35rem; }
    .grid-note { font-size: 0.75rem; color: #8b949e; margin-bottom: 0.5rem; }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid #30363d;
      border-radius: 10px;
      background: #161b22;
    }
    .week-grid {
      width: 100%;
      border-collapse: collapse;
      min-width: 560px;
    }
    .week-grid th, .week-grid td {
      border: 1px solid #21262d;
      padding: 0.5rem 0.45rem;
      vertical-align: middle;
      font-size: 0.82rem;
      text-align: center;
    }
    .week-grid thead th { background: #1c2128; color: #f0f6fc; font-weight: 600; }
    .period-col, .time-col {
      text-align: left;
      font-weight: 500;
      color: #8b949e;
      background: #1c2128;
      white-space: nowrap;
    }
    .time-col { font-size: 0.75rem; }
    .slot.lesson { color: #c9d1d9; }
    .slot.core.maths { background: #1c2d4a; color: #79c0ff; font-weight: 600; }
    .slot.core.english { background: #3d2e12; color: #e3b341; font-weight: 600; }
    .slot.break { background: #132d1b; color: #3fb950; font-weight: 600; }
    .slot.assembly { background: #2d1f4a; color: #d2a8ff; font-weight: 600; }
    .slot.arrival { background: #1f3a5f33; color: #58a6ff; }
    .slot.empty { color: #484f58; }
"""

STAFF_CSS = """
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 1.5rem 1.25rem;
      max-width: 1100px;
      margin: 0 auto;
    }
    .top { margin-bottom: 1rem; }
    a.back { color: #58a6ff; text-decoration: none; font-size: 0.9rem; }
    h1 { margin-top: 0.5rem; font-size: 1.35rem; font-weight: 600; color: #f0f6fc; }
    .hints { font-size: 0.8rem; color: #8b949e; margin-bottom: 1rem; }
    .table-wrap {
      overflow-x: auto;
      border: 1px solid #30363d;
      border-radius: 10px;
      background: #161b22;
      margin-bottom: 0.75rem;
    }
    .staff-grid {
      width: 100%;
      border-collapse: collapse;
      min-width: 640px;
      font-size: 0.78rem;
    }
    .staff-grid th, .staff-grid td {
      border: 1px solid #21262d;
      padding: 0.45rem 0.4rem;
      text-align: center;
      vertical-align: middle;
    }
    .staff-grid thead th, .staff-grid .period-col, .staff-grid .time-col {
      background: #1c2128;
      color: #f0f6fc;
      text-align: left;
    }
    .staff-grid .time-col { color: #8b949e; font-size: 0.72rem; }
    .staff-cell .ks3 { color: #79c0ff; }
    .staff-cell .ks4 { color: #e3b341; }
    .stagger { color: #f85149; }
    .meta-row th { color: #8b949e; font-weight: 500; }
    .detention { color: #f85149; font-weight: 600; }
    .muted { color: #484f58; }
    .grid-note { font-size: 0.75rem; color: #8b949e; }
"""


def build_student_html(week: dict) -> str:
    meta = week["meta"]
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
    Lunch {esc(meta["lunch_time"])} daily.
    Wed from 10:00.
    Finish Mon–Wed 15:00, Thu–Fri 14:00.
    Assembly Tuesday P1.
  </p>
  {render_stage_grid(week, "ks3")}
  {render_stage_grid(week, "ks4")}
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
  <p class="hints">Staff from {esc(staff["start"])}. Students Mon/Tue/Thu/Fri 08:50 (latest 09:05), Wed 10:00.</p>
  <div class="table-wrap">
    {render_staff_week_grid(week)}
  </div>
</body>
</html>
"""


def main() -> None:
    week = load_week()
    if "periods" not in week:
        raise SystemExit("week.json must use periods + days.slots format")
    (ROOT / "student-timetable.html").write_text(build_student_html(week), encoding="utf-8")
    (ROOT / "staff-timetable.html").write_text(build_staff_html(week), encoding="utf-8")
    print("Wrote student-timetable.html and staff-timetable.html")


if __name__ == "__main__":
    main()
