#!/usr/bin/env python3
"""Generate student and staff timetable HTML from data/week.json."""

from __future__ import annotations

import html
import json
from pathlib import Path

from merge_rows import merge_consecutive_rows

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
    if kind == "transition" or label == "Transition":
        return "slot transition"
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


def display_rows(day: dict) -> list[dict]:
    return merge_consecutive_rows(day["rows"])


def render_student_day_panel(week: dict, day_key: str) -> str:
    day = week["days"][day_key]
    rows_html = []
    for row in display_rows(day):
        rows_html.append(
            "<tr>"
            f'<td class="time-col">{esc(row["start"])}–{esc(row["end"])}</td>'
            f"{compare_cell_html(row, 'ks3')}"
            f"{compare_cell_html(row, 'ks4')}"
            "</tr>"
        )
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel" aria-labelledby="tab-{day_key}">
        <div class="table-wrap">
          <table class="day-grid">
            <thead>
              <tr>
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


def merge_staff_sessions(sessions: list[dict]) -> list[dict]:
    if not sessions:
        return []
    out = [dict(sessions[0])]
    for s in sessions[1:]:
        prev = out[-1]
        if (
            prev["day_key"] == s["day_key"]
            and prev["stage"] == s["stage"]
            and prev["subject"] == s["subject"]
            and prev["time"].split("–")[1] == s["time"].split("–")[0]
        ):
            prev["time"] = f'{prev["time"].split("–")[0]}–{s["time"].split("–")[1]}'
        else:
            out.append(dict(s))
    return out


def collect_staff_sessions(week: dict) -> dict[str, list[dict]]:
    sessions: dict[str, list[dict]] = {}
    for day_key in DAY_ORDER:
        day = week["days"][day_key]
        for row in display_rows(day):
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
    for name in sessions:
        sessions[name] = merge_staff_sessions(sessions[name])
    return sessions


def group_sessions_by_day(sessions: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {key: [] for key in DAY_ORDER}
    for s in sessions:
        grouped[s["day_key"]].append(s)
    return grouped


def render_person_day_panel(day_key: str, sessions: list[dict]) -> str:
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
        panels.append(render_person_day_panel(key, grouped[key]))
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
  {render_person_day_tabs(week, sessions)}
</body>
</html>
"""


def render_staff_day_panel(week: dict, day_key: str) -> str:
    day = week["days"][day_key]
    rows_html = []
    for row in display_rows(day):
        ks3, ks4 = row["ks3"], row["ks4"]
        s3 = row.get("staff_ks3")
        s4 = row.get("staff_ks4")
        k3_disp = esc(ks3) + (f' <span class="lead">({esc(s3)})</span>' if s3 else "")
        k4_disp = esc(ks4) + (f' <span class="lead">({esc(s4)})</span>' if s4 else "")
        rows_html.append(
            f"<tr>"
            f'<td class="time-col">{esc(row["start"])}–{esc(row["end"])}</td>'
            f'<td class="{cell_class(ks3, row.get("kind", ""))}">{k3_disp}</td>'
            f'<td class="{cell_class(ks4, row.get("kind", ""))}">{k4_disp}</td>'
            f"</tr>"
        )
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel">
        <div class="table-wrap">
          <table class="timeline-table">
            <thead>
              <tr>
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
    .slot.transition { background: #21262d; }
    .slot.transition .slot-label { color: #8b949e; font-style: italic; }
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

    .muted { color: #484f58; }

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

  {render_student_day_views(week)}
</body>
</html>
"""


def build_staff_html(week: dict) -> str:
    people = week["staff"].get("people", [])
    person_links = "".join(
        f'<a href="staff/{esc(name.lower())}.html">{esc(name)}</a>' for name in people
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Staff timetable</title>
  <style>{DAY_TAB_CSS}{STAFF_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">← Back</a>
    <h1>Staff timetable</h1>
  </div>

  <nav class="staff-links" aria-label="Individual staff timetables">
    {person_links}
  </nav>

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
