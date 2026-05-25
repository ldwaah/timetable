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

INITIALS_TO_NAME: dict[str, str] = {
    "LG": "Lorelle",
    "LD": "Lloyd",
    "LI": "Laurent",
    "SA": "Sacha",
    "JC": "Jeff",
    "JM": "Janet",
    "HK": "Hisham",
}

SLT_MEMBERS = {"SA", "LD"}

STAFF_WORKING_HOURS: dict[str, dict[str, tuple[str, str]]] = {
    "LD": {
        "monday": ("08:30", "15:30"), "tuesday": ("08:30", "15:30"),
        "wednesday": ("08:30", "15:00"), "thursday": ("08:30", "15:00"),
        "friday": ("08:30", "15:00"),
    },
    "LG": {
        "monday": ("08:30", "15:00"), "tuesday": ("08:30", "15:00"),
        "wednesday": ("08:30", "15:00"), "thursday": ("08:30", "15:00"),
        "friday": ("08:30", "15:00"),
    },
    "LI": {
        "monday": ("08:30", "15:30"), "tuesday": ("08:30", "15:30"),
        "wednesday": ("08:30", "15:00"), "thursday": ("08:30", "15:00"),
        "friday": ("08:30", "15:00"),
    },
    "SA": {
        "tuesday": ("08:30", "15:30"),
        "wednesday": ("08:30", "15:00"), "thursday": ("08:30", "15:00"),
        "friday": ("08:30", "15:00"),
    },
    "JC": {
        "monday": ("11:00", "15:30"), "tuesday": ("11:00", "15:00"),
        "thursday": ("11:00", "15:00"),
    },
    "JM": {
        "monday": ("09:00", "14:00"), "tuesday": ("09:00", "14:00"),
        "wednesday": ("09:00", "14:00"), "thursday": ("09:00", "14:00"),
        "friday": ("09:00", "14:00"),
    },
    "HK": {
        "monday": ("09:00", "13:00"), "tuesday": ("09:00", "13:00"),
        "wednesday": ("09:00", "13:00"), "thursday": ("09:00", "13:00"),
        "friday": ("09:00", "13:00"),
    },
}


def _minutes_to_time(mins: int) -> str:
    return f"{mins // 60:02d}:{mins % 60:02d}"


def _time_minutes(t: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _staff_working_at(person: str, day_key: str, start: str) -> bool:
    """Return True if person is working during the given slot."""
    day_hours = STAFF_WORKING_HOURS.get(person, {}).get(day_key)
    if not day_hours:
        return True
    p_start = _time_minutes(day_hours[0])
    p_end = _time_minutes(day_hours[1])
    slot_start = _time_minutes(start)
    return p_start <= slot_start < p_end


def _parse_staff(staff_str: str | None) -> set[str]:
    if not staff_str:
        return set()
    return {s.strip() for s in staff_str.split("/")}


def _is_break_or_lunch(label: str) -> bool:
    if label == "Lunch":
        return True
    if label.startswith("Break") or "Toilet Break" in label:
        return True
    return False


def _row_ks_identical(row: dict) -> bool:
    """True when KS3 and KS4 carry the same label, staff, and supervision."""
    if (row.get("ks3", "—") or "—").lower() != (row.get("ks4", "—") or "—").lower():
        return False
    if row.get("staff_ks3") != row.get("staff_ks4"):
        return False
    if row.get("supervision_ks3") != row.get("supervision_ks4"):
        return False
    return True


def _row_flz_matches_ks(row: dict) -> bool:
    """True when FLZ label and staff match KS3 (for spanning all three columns)."""
    flz = row.get("flz")
    ks3 = row.get("ks3", "—")
    if not flz or flz == "—":
        return ks3 == "—"
    if flz.lower() != ks3.lower():
        return False
    if row.get("staff_flz") != row.get("staff_ks3"):
        return False
    return True


def _rota_key_for_row(row: dict) -> str:
    """Determine the supervision_rota lookup key for a break/lunch row."""
    ks3 = row.get("ks3", "")
    ks4 = row.get("ks4", "")
    if ks3 == "Lunch" and ks4 == "Lunch":
        return "lunch"
    if "Toilet Break" in ks3:
        return "toilet_break"
    ks3_brk = _is_break_or_lunch(ks3)
    ks4_brk = _is_break_or_lunch(ks4)
    if ks3_brk and ks4_brk:
        return "break"
    if ks3_brk:
        return "ks3_break"
    return "ks4_break"


def add_supervision(week: dict) -> None:
    """Tag every break/lunch row with the rostered supervision staff."""
    rota = week["staff"].get("supervision_rota", {})
    for day_key in DAY_ORDER:
        day = week["days"].get(day_key)
        if not day:
            continue
        day_rota = rota.get(day_key, {})
        for row in day["rows"]:
            ks3_is_break = _is_break_or_lunch(row.get("ks3", ""))
            ks4_is_break = _is_break_or_lunch(row.get("ks4", ""))
            if not ks3_is_break and not ks4_is_break:
                continue
            if ks3_is_break and ks4_is_break and row.get("ks3") != row.get("ks4"):
                row["supervision_ks3"] = day_rota.get("ks3_break", [])
                row["supervision_ks4"] = day_rota.get("ks4_break", [])
            else:
                key = _rota_key_for_row(row)
                if key == "lunch" and ("lunch_ks3" in day_rota or "lunch_ks4" in day_rota):
                    if ks3_is_break:
                        row["supervision_ks3"] = day_rota.get("lunch_ks3", day_rota.get("lunch", []))
                    if ks4_is_break:
                        row["supervision_ks4"] = day_rota.get("lunch_ks4", day_rota.get("lunch", []))
                else:
                    assigned = day_rota.get(key, [])
                    if ks3_is_break:
                        row["supervision_ks3"] = assigned
                    if ks4_is_break:
                        row["supervision_ks4"] = assigned


def _supervision_text(free: list[str], all_staff: list[str]) -> str:
    if len(free) == len(all_staff):
        return "All staff"
    parts = []
    for person in free:
        if person in SLT_MEMBERS:
            parts.append(f"{person} (Main Foyer)")
        else:
            parts.append(person)
    return ", ".join(parts)


def load_week() -> dict:
    with DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def esc(text: str | None) -> str:
    return html.escape(text or "", quote=True)


def cell_class(label: str, kind: str) -> str:
    if label == "—":
        return "slot"
    if kind == "searches" or "Student Searches" in label:
        return "slot searches"
    if kind == "assembly" or label == "Assembly":
        return "slot assembly"
    if kind == "reset" or label == "Reset":
        return "slot reset"
    if kind == "checks" or "Checks" in label:
        return "slot checks"
    if label == "Lunch" or label.startswith("Break") or "Toilet Break" in label:
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
    if kind == "briefing" or "Staff Briefing" in label:
        return "slot briefing"
    if kind == "meeting" or label == "Team Meeting":
        return "slot meeting"
    if kind == "staff_development" or label == "Thrive":
        return "slot staff-dev"
    if "Lesson" in label:
        return "slot lesson"
    return "slot"


def compare_cell_html(
    row: dict,
    stage: str,
    *,
    show_staff: bool = True,
    all_staff: list[str] | None = None,
    colspan: int = 1,
) -> str:
    label = row.get(stage, "—")
    staff = row.get(f"staff_{stage}") if show_staff else None
    supervision = row.get(f"supervision_{stage}")
    note = row.get("note")
    cls = cell_class(label, row.get("kind", ""))
    label_html = esc(label)
    if staff:
        label_html = f'{esc(label)}<span class="slot-staff">{esc(staff)}</span>'
    elif supervision and all_staff:
        sup = _supervision_text(supervision, all_staff)
        label_html = f'{esc(label)}<span class="slot-staff">{esc(sup)}</span>'
    if note and label != "—":
        label_html += f'<span class="slot-note">{esc(note)}</span>'
    cs = f' colspan="{colspan}"' if colspan > 1 else ""
    return f'<td{cs} class="{cls}"><span class="slot-label">{label_html}</span></td>'


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


def display_rows(day: dict, *, include_staff_only: bool = True) -> list[dict]:
    rows = day["rows"]
    if not include_staff_only:
        rows = [r for r in rows if not r.get("staff_only")]
    return merge_consecutive_rows(rows)


def render_student_day_panel(week: dict, day_key: str) -> str:
    day = week["days"][day_key]
    all_staff = week["staff"].get("people", [])
    rows = display_rows(day, include_staff_only=False)
    rows = [r for r in rows if r.get("kind") != "searches"]
    has_flz = any(row.get("flz") for row in rows)
    hint_html = render_searches_hint(day)
    rows_html = []
    for row in rows:
        time_cell = f'<td class="time-col">{esc(row["start"])}\u2013{esc(row["end"])}</td>'
        merge_ks = _row_ks_identical(row)
        merge_flz = merge_ks and has_flz and _row_flz_matches_ks(row)
        if merge_flz:
            rows_html.append(
                f"<tr>{time_cell}"
                f"{compare_cell_html(row, 'ks3', all_staff=all_staff, colspan=3)}"
                "</tr>"
            )
        elif merge_ks:
            flz_cell = compare_cell_html(row, "flz", all_staff=all_staff) if has_flz else ""
            rows_html.append(
                f"<tr>{time_cell}"
                f"{compare_cell_html(row, 'ks3', all_staff=all_staff, colspan=2)}"
                f"{flz_cell}</tr>"
            )
        else:
            flz_cell = compare_cell_html(row, "flz", all_staff=all_staff) if has_flz else ""
            rows_html.append(
                f"<tr>{time_cell}"
                f"{compare_cell_html(row, 'ks3', all_staff=all_staff)}"
                f"{compare_cell_html(row, 'ks4', all_staff=all_staff)}"
                f"{flz_cell}</tr>"
            )
    flz_th = '<th scope="col">FLZ</th>' if has_flz else ""
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel" aria-labelledby="tab-{day_key}">
        {hint_html}
        <div class="table-wrap">
          <table class="day-grid">
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">KS3</th>
                <th scope="col">KS4</th>
                {flz_th}
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


def compute_ppa_sessions(week: dict) -> dict[str, list[dict]]:
    """Return one designated PPA session per staff member per working day."""
    all_staff = week["staff"].get("people", [])
    ppa_map: dict[str, dict] = week["staff"].get("ppa", {})
    day_labels = {k: v["label"] for k, v in week["days"].items()}
    ppa: dict[str, list[dict]] = {s: [] for s in all_staff}

    for person in all_staff:
        person_ppa = ppa_map.get(person, {})
        for day_key in DAY_ORDER:
            slot = person_ppa.get(day_key)
            if not slot:
                continue
            ppa[person].append({
                "day": day_labels.get(day_key, day_key.capitalize()),
                "day_key": day_key,
                "time": f'{slot["start"]}\u2013{slot["end"]}',
                "stage": "\u2014",
                "subject": "PPA",
            })

    return ppa


def fill_ppa_gaps(
    sessions: list[dict], initials: str, day_labels: dict[str, str],
    *, min_gap: int = 10,
) -> list[dict]:
    """Create PPA sessions for every gap within a staff member's working hours.

    Gaps shorter than *min_gap* minutes (e.g. arrival buffer) are skipped.
    """
    hours = STAFF_WORKING_HOURS.get(initials, {})
    grouped = group_sessions_by_day(sessions)
    ppa_sessions: list[dict] = []

    for day_key in DAY_ORDER:
        day_hours = hours.get(day_key)
        if not day_hours:
            continue

        work_start = _time_minutes(day_hours[0])
        work_end = _time_minutes(day_hours[1])

        intervals: list[tuple[int, int]] = []
        for s in grouped.get(day_key, []):
            parts = s["time"].split("\u2013")
            intervals.append((_time_minutes(parts[0]), _time_minutes(parts[1])))

        intervals.sort()
        merged_intervals: list[tuple[int, int]] = []
        for start, end in intervals:
            if merged_intervals and start <= merged_intervals[-1][1]:
                merged_intervals[-1] = (merged_intervals[-1][0], max(merged_intervals[-1][1], end))
            else:
                merged_intervals.append((start, end))

        cursor = work_start
        for s_start, s_end in merged_intervals:
            if s_end <= work_start or s_start >= work_end:
                continue
            clamped_start = max(s_start, work_start)
            gap = clamped_start - cursor
            if gap >= min_gap:
                ppa_sessions.append({
                    "day": day_labels.get(day_key, day_key.capitalize()),
                    "day_key": day_key,
                    "time": f"{_minutes_to_time(cursor)}\u2013{_minutes_to_time(clamped_start)}",
                    "stage": "\u2014",
                    "subject": "PPA",
                })
            cursor = max(cursor, min(s_end, work_end))

        trailing = work_end - cursor
        if trailing >= min_gap:
            ppa_sessions.append({
                "day": day_labels.get(day_key, day_key.capitalize()),
                "day_key": day_key,
                "time": f"{_minutes_to_time(cursor)}\u2013{_minutes_to_time(work_end)}",
                "stage": "\u2014",
                "subject": "PPA",
            })

    return ppa_sessions


def group_sessions_by_day(sessions: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {key: [] for key in DAY_ORDER}
    for s in sessions:
        grouped[s["day_key"]].append(s)
    return grouped


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
    all_people = week["staff"].get("people", [])
    off_days: dict[str, list[str]] = week["staff"].get("off_days", {})
    for day_key in DAY_ORDER:
        day = week["days"][day_key]
        for row in display_rows(day):
            if row.get("all_staff"):
                label = row.get("ks3", row.get("ks4", ""))
                for person in all_people:
                    if day_key in off_days.get(person, []):
                        continue
                    sessions.setdefault(person, []).append(
                        {
                            "day": day["label"],
                            "day_key": day_key,
                            "time": f'{row["start"]}–{row["end"]}',
                            "stage": "All",
                            "subject": label,
                        }
                    )
                continue
            for stage in ("ks3", "ks4"):
                staff = row.get(f"staff_{stage}")
                if staff:
                    for initials in (s.strip() for s in staff.split("/")):
                        sessions.setdefault(initials, []).append(
                            {
                                "day": day["label"],
                                "day_key": day_key,
                                "time": f'{row["start"]}–{row["end"]}',
                                "stage": "KS3" if stage == "ks3" else "KS4",
                                "subject": row[stage],
                            }
                        )
                supervision = row.get(f"supervision_{stage}")
                if supervision:
                    stage_label = "KS3" if stage == "ks3" else "KS4"
                    break_label = row.get(stage, "")
                    if "\u2014" in break_label:
                        sup_subject = f"Supervision ({break_label.split('\u2014')[1].strip()})"
                    else:
                        sup_subject = "Supervision"
                    for person in supervision:
                        if day_key in off_days.get(person, []):
                            continue
                        person_subject = (
                            "Supervision (Main Foyer)"
                            if person in SLT_MEMBERS
                            else sup_subject
                        )
                        sessions.setdefault(person, []).append(
                            {
                                "day": day["label"],
                                "day_key": day_key,
                                "time": f'{row["start"]}\u2013{row["end"]}',
                                "stage": stage_label,
                                "subject": person_subject,
                            }
                        )
            flz_staff = row.get("staff_flz")
            flz_label = row.get("flz")
            if flz_staff and flz_label:
                for initials in (s.strip() for s in flz_staff.split("/")):
                    sessions.setdefault(initials, []).append(
                        {
                            "day": day["label"],
                            "day_key": day_key,
                            "time": f'{row["start"]}–{row["end"]}',
                            "stage": "FLZ",
                            "subject": flz_label,
                        }
                    )
    for name in sessions:
        sessions[name] = merge_staff_sessions(sessions[name])
    return sessions


def dedup_person_sessions(sessions: list[dict]) -> list[dict]:
    """Merge KS3+KS4 rows that share the same time and subject into a single 'All' row,
    and drop exact duplicates. Must be called on a sorted session list."""
    if not sessions:
        return []
    out: list[dict] = []
    i = 0
    while i < len(sessions):
        curr = sessions[i]
        if i + 1 < len(sessions):
            nxt = sessions[i + 1]
            same_slot = (
                curr["day_key"] == nxt["day_key"]
                and curr["time"] == nxt["time"]
                and curr["subject"] == nxt["subject"]
            )
            if same_slot:
                stages = {curr["stage"], nxt["stage"]}
                if stages == {"KS3", "KS4"}:
                    merged = dict(curr)
                    merged["stage"] = "All"
                    out.append(merged)
                    i += 2
                    continue
                if curr["stage"] == nxt["stage"]:
                    out.append(dict(curr))
                    i += 2
                    continue
        out.append(dict(curr))
        i += 1
    return out


def render_person_day_panel(day_key: str, sessions: list[dict], *, is_off_day: bool = False) -> str:
    if sessions:
        rows_html = []
        for s in sessions:
            is_ppa = s["subject"].startswith("PPA")
            subj_cls = "subject-col ppa" if is_ppa else "subject-col"
            rows_html.append(
                "<tr>"
                f'<td class="time-col">{esc(s["time"])}</td>'
                f'<td>{esc(s["stage"])}</td>'
                f'<td class="{subj_cls}">{esc(s["subject"])}</td>'
                "</tr>"
            )
        body = "".join(rows_html)
    else:
        msg = "Not working" if is_off_day else "No sessions"
        body = f'<tr><td colspan="3" class="muted">{msg}</td></tr>'
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


def render_person_day_tabs(week: dict, sessions: list[dict], *, off_days: list[str] | None = None) -> str:
    _off = off_days or []
    grouped = group_sessions_by_day(sessions)
    panels = []
    for key in DAY_ORDER:
        panels.append(render_person_day_panel(key, grouped[key], is_off_day=key in _off))
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


def render_staff_person_page(week: dict, initials: str, sessions: list[dict]) -> str:
    full_name = INITIALS_TO_NAME.get(initials, initials)
    display = f"{initials} ({full_name})"
    off = week["staff"].get("off_days", {}).get(initials, [])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(display)} — staff timetable</title>
  <style>{STAFF_PERSON_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="../staff-timetable.html">← Staff timetable</a>
    <h1>{esc(display)}</h1>
  </div>
  {render_person_day_tabs(week, sessions, off_days=off)}
</body>
</html>
"""


def render_staff_day_panel(week: dict, day_key: str) -> str:
    day = week["days"][day_key]
    all_staff = week["staff"].get("people", [])
    rows = display_rows(day, include_staff_only=True)
    rows = [r for r in rows if r.get("kind") != "searches"]
    has_flz = any(row.get("flz") for row in rows)
    hint_html = render_searches_hint(day)
    rows_html = []
    for row in rows:
        ks3, ks4 = row["ks3"], row["ks4"]
        s3 = row.get("staff_ks3")
        s4 = row.get("staff_ks4")
        sup3 = row.get("supervision_ks3")
        sup4 = row.get("supervision_ks4")
        note = row.get("note")
        if row.get("all_staff"):
            k3_disp = esc(ks3) + ' <span class="lead">(All staff)</span>'
            k4_disp = esc(ks4) + ' <span class="lead">(All staff)</span>'
        else:
            k3_disp = esc(ks3) + (f' <span class="lead">({esc(s3)})</span>' if s3 else "")
            k4_disp = esc(ks4) + (f' <span class="lead">({esc(s4)})</span>' if s4 else "")
            if not s3 and sup3:
                k3_disp = esc(ks3) + f' <span class="lead">({esc(_supervision_text(sup3, all_staff))})</span>'
            if not s4 and sup4:
                k4_disp = esc(ks4) + f' <span class="lead">({esc(_supervision_text(sup4, all_staff))})</span>'
        if note:
            note_html = f'<span class="slot-note">{esc(note)}</span>'
            k3_disp += note_html
        flz_html = ""
        if has_flz:
            flz = row.get("flz", "—")
            sf = row.get("staff_flz")
            flz_disp = esc(flz) + (f' <span class="lead">({esc(sf)})</span>' if sf else "")
            flz_html = f'<td class="{cell_class(flz, row.get("kind", ""))}">{flz_disp}</td>'
        merge_ks = _row_ks_identical(row)
        merge_all = merge_ks and has_flz and _row_flz_matches_ks(row)
        time_cell = f'<td class="time-col">{esc(row["start"])}–{esc(row["end"])}</td>'
        ks3_cls = cell_class(ks3, row.get("kind", ""))
        if merge_all:
            rows_html.append(
                f"<tr>{time_cell}"
                f'<td colspan="3" class="{ks3_cls}">{k3_disp}</td>'
                f"</tr>"
            )
        elif merge_ks:
            rows_html.append(
                f"<tr>{time_cell}"
                f'<td colspan="2" class="{ks3_cls}">{k3_disp}</td>'
                f"{flz_html}</tr>"
            )
        else:
            rows_html.append(
                f"<tr>{time_cell}"
                f'<td class="{ks3_cls}">{k3_disp}</td>'
                f'<td class="{cell_class(ks4, row.get("kind", ""))}">{k4_disp}</td>'
                f"{flz_html}</tr>"
            )
    flz_th = '<th scope="col">FLZ</th>' if has_flz else ""
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel">
        {hint_html}
        <div class="table-wrap">
          <table class="timeline-table">
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">KS3</th>
                <th scope="col">KS4</th>
                {flz_th}
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

    .slot-note {
      display: block;
      font-size: 0.65rem;
      font-style: italic;
      color: #6e7681;
      margin-top: 0.2rem;
    }

    .day-grid td[colspan] { text-align: center; }

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
    .slot.searches { background: #2d1f1f; }
    .slot.searches .slot-label { color: #f78166; font-weight: 600; }
    .slot.searches .slot-staff { color: #f0883e; }
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
    .slot.searches { color: #f78166; font-weight: 600; }
    .slot.searches .lead { color: #f0883e; }
    .slot.checks { color: #8b949e; font-style: italic; }
    .slot.arrival { color: #58a6ff; }
    .slot.lesson { color: #c9d1d9; }
    .slot.core.maths { color: #79c0ff; font-weight: 600; }
    .slot.core.english { color: #e3b341; font-weight: 600; }
    .slot.pe { color: #3fb950; font-weight: 600; }
    .slot.briefing { color: #f0883e; font-weight: 600; }
    .slot.meeting { color: #d2a8ff; font-weight: 600; }
    .slot.staff-dev { color: #56d364; font-weight: 600; }
    .slot-note { display: block; font-size: 0.65rem; font-style: italic; color: #6e7681; margin-top: 0.15rem; font-weight: 400; }
    .timeline-table td[colspan] { text-align: center; }
"""

SEARCHES_HINT_CSS = """
    .searches-hint {
      position: relative;
      display: inline-block;
      margin-bottom: 0.5rem;
    }
    .searches-hint-btn {
      background: #1c2128;
      border: 1px solid #30363d;
      color: #f78166;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.75rem;
      font-family: inherit;
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      transition: background 0.15s, border-color 0.15s;
    }
    .searches-hint-btn:hover {
      background: #2d1f1f;
      border-color: #f78166;
    }
    .searches-hint-icon {
      font-size: 0.85rem;
      line-height: 1;
    }
    .searches-hint-popup {
      display: none;
      position: absolute;
      top: 100%;
      left: 0;
      margin-top: 0.35rem;
      background: #1c2128;
      border: 1px solid #f78166;
      border-radius: 8px;
      padding: 0.6rem 0.85rem;
      min-width: 15rem;
      z-index: 10;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    .searches-hint.open .searches-hint-popup {
      display: block;
    }
    .searches-hint-title {
      font-size: 0.78rem;
      font-weight: 600;
      color: #f78166;
      margin-bottom: 0.25rem;
    }
    .searches-hint-staff {
      font-size: 0.78rem;
      color: #e6edf3;
    }
    .searches-hint-note {
      font-size: 0.68rem;
      color: #8b949e;
      font-style: italic;
      margin-top: 0.2rem;
    }
"""

SEARCHES_HINT_JS = """
<script>
document.addEventListener('click', function(e) {
  var btn = e.target.closest('.searches-hint-btn');
  if (btn) {
    e.stopPropagation();
    btn.parentElement.classList.toggle('open');
    return;
  }
  document.querySelectorAll('.searches-hint.open').forEach(function(el) {
    el.classList.remove('open');
  });
});
</script>
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
    .subject-col.ppa { color: #d2a8ff; font-style: italic; }
    .muted { color: #484f58; text-align: center; }
"""
)


def extract_searches(day: dict) -> dict | None:
    for row in day["rows"]:
        if row.get("kind") == "searches":
            return row
    return None


def render_searches_hint(day: dict) -> str:
    row = extract_searches(day)
    if not row:
        return ""
    time_range = f'{row["start"]}\u2013{row["end"]}'
    staff = row.get("staff_ks3", "")
    note = row.get("note", "")
    note_html = f'<div class="searches-hint-note">{esc(note)}</div>' if note else ""
    return (
        f'<div class="searches-hint">'
        f'<button class="searches-hint-btn" aria-label="Student searches info">'
        f'<span class="searches-hint-icon">\u2139\uFE0F</span> Searches</button>'
        f'<div class="searches-hint-popup">'
        f'<div class="searches-hint-title">Student Searches {esc(time_range)}</div>'
        f'<div class="searches-hint-staff">{esc(staff)}</div>'
        f'{note_html}'
        f'</div></div>'
    )


def build_student_html(week: dict) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Student timetable</title>
  <style>{DAY_TAB_CSS}{SHARED_STUDENT_CSS}{SEARCHES_HINT_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">\u2190 Back</a>
    <h1>Student timetable</h1>
  </div>

  {render_student_day_views(week)}
  {SEARCHES_HINT_JS}
</body>
</html>
"""


def staff_slug(initials: str) -> str:
    return INITIALS_TO_NAME.get(initials, initials).lower()


STAFF_CARDS_CSS = """
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

    .top { margin-bottom: 2rem; }

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

    .staff-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 1.25rem;
    }

    .staff-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
      padding: 2rem 1rem;
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      text-decoration: none;
      color: inherit;
      transition: border-color 0.2s, background 0.2s, transform 0.15s;
    }

    .staff-card:hover {
      border-color: #a371f7;
      background: #1c2128;
      transform: translateY(-2px);
    }

    .staff-card:focus-visible {
      outline: 2px solid #a371f7;
      outline-offset: 2px;
    }

    .staff-avatar {
      width: 64px;
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      background: linear-gradient(135deg, #3d1f5f 0%, #a371f733 100%);
      font-size: 1.4rem;
      font-weight: 700;
      color: #d2a8ff;
      letter-spacing: 0.02em;
    }

    .staff-name {
      font-size: 0.9rem;
      font-weight: 500;
      color: #f0f6fc;
    }
"""


def build_staff_html(week: dict) -> str:
    people = week["staff"].get("people", [])
    cards = []
    for initials in people:
        slug = staff_slug(initials)
        full_name = INITIALS_TO_NAME.get(initials, initials)
        cards.append(
            f'<a class="staff-card" href="staff/{esc(slug)}.html">'
            f'<span class="staff-avatar">{esc(initials)}</span>'
            f'<span class="staff-name">{esc(full_name)}</span>'
            f'</a>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Staff timetable</title>
  <style>{STAFF_CARDS_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">\u2190 Back</a>
    <h1>Staff timetable</h1>
  </div>

  <nav class="staff-grid" aria-label="Staff members">
    {''.join(cards)}
  </nav>
</body>
</html>
"""


def filter_by_working_hours(sessions: list[dict], initials: str) -> list[dict]:
    """Remove sessions outside a staff member's working hours."""
    person_hours = STAFF_WORKING_HOURS.get(initials)
    if not person_hours:
        return sessions
    filtered = []
    for s in sessions:
        day_hours = person_hours.get(s["day_key"])
        if not day_hours:
            filtered.append(s)
            continue
        slot_start = _time_minutes(s["time"].split("\u2013")[0])
        p_start = _time_minutes(day_hours[0])
        p_end = _time_minutes(day_hours[1])
        if p_start <= slot_start < p_end:
            filtered.append(s)
    return filtered


def main() -> None:
    week = load_week()
    if "rows" not in week["days"]["monday"]:
        raise SystemExit("week.json must use days.*.rows format")
    add_supervision(week)

    (ROOT / "student-timetable.html").write_text(build_student_html(week), encoding="utf-8")
    (ROOT / "staff-timetable.html").write_text(build_staff_html(week), encoding="utf-8")

    STAFF_DIR.mkdir(exist_ok=True)
    sessions = collect_staff_sessions(week)
    day_labels = {k: v["label"] for k, v in week["days"].items()}
    for initials in week["staff"].get("people", []):
        person_sessions = sessions.get(initials, [])
        person_sessions = filter_by_working_hours(person_sessions, initials)
        sorted_sessions = sorted(
            person_sessions,
            key=lambda s: (DAY_ORDER.index(s["day_key"]), s["time"]),
        )
        deduped = dedup_person_sessions(sorted_sessions)
        merged = merge_staff_sessions(deduped)
        ppa_gaps = fill_ppa_gaps(merged, initials, day_labels)
        combined = sorted(
            merged + ppa_gaps,
            key=lambda s: (DAY_ORDER.index(s["day_key"]), s["time"]),
        )
        combined = merge_staff_sessions(combined)
        if initials in ("SA", "LD"):
            for s in combined:
                if s["subject"] == "PPA":
                    s["subject"] = "PPA / On-call / Centre Duties"
        slug = staff_slug(initials)
        page = render_staff_person_page(week, initials, combined)
        (STAFF_DIR / f"{slug}.html").write_text(page, encoding="utf-8")

    print("Wrote student-timetable.html, staff-timetable.html, and staff/*.html")


if __name__ == "__main__":
    main()
