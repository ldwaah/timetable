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
        "monday": ("11:00", "15:00"), "tuesday": ("11:00", "15:00"),
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
    if label == "Lunch Break":
        return True
    if label.startswith("Break") or "Toilet Break" in label:
        return True
    return False


def _period_suffix_for_row(row: dict) -> str:
    """Return suffix for a whole-row period label, e.g. ' (Break)'."""
    ks3 = row.get("ks3", "") or ""
    ks4 = row.get("ks4", "") or ""
    if ks3 == "Lunch" or ks4 == "Lunch":
        return " (Lunch)"
    if _is_break_or_lunch(ks3) or _is_break_or_lunch(ks4):
        return " (Break)"
    return ""


def _period_suffix_for_label(label: str) -> str:
    if label == "Lunch":
        return " (Lunch)"
    if _is_break_or_lunch(label):
        return " (Break)"
    return ""


def _period_label(n: int, *, suffix: str = "") -> str:
    return f"Period {n}{suffix}"


def get_location(label: str, stage: str, day_key: str, kind: str) -> str:
    """Determine the room/location for a given activity."""
    if not label or label == "—":
        return ""
    low = label.lower()

    # Wednesday: Foyer does not exist — redirect to available rooms
    if day_key == "wednesday":
        if kind == "searches" or "student searches" in low:
            return "Main Room"
        if kind == "arrival" or "arrival" in low:
            return "Main Room"
        if kind == "checks" or "checks" in low:
            return "Main Room"
        if kind == "transition" or "transition" in low:
            return "Main Room"
        if "pause" in low and "progress" in low:
            return "Main Room"
        if "line management" in low:
            return "Main Room"
        if "slt meeting" in low:
            return "Main Room"
        if kind == "assembly" or low == "assembly":
            return "Main Room"
        if kind == "pe" or low == "gym":
            return "Gym"
        if "flz" in low or stage == "flz":
            return "Gym"
        if "sports leaders" in low or "vocational" in low:
            return "Gym"
        if low in ("lunch", "lunch break"):
            if stage == "ks3":
                return "Main Room"
            return "Computer Suite"
        if low.startswith("break"):
            if stage == "ks3":
                return "Main Room"
            return "Computer Suite"
        if stage == "ks3":
            return "Main Room"
        if stage == "ks4":
            return "Computer Suite"
        return "Main Room"

    if kind == "searches" or "student searches" in low:
        return "Foyer"
    if kind == "arrival" or "arrival" in low:
        return "Foyer"
    if kind == "checks" or "checks" in low:
        return "Foyer"
    if kind == "transition" or "transition" in low:
        return "Foyer"
    if "pause" in low and "progress" in low:
        return "Foyer"
    if "line management" in low:
        return "Foyer"
    if "slt meeting" in low:
        return "Foyer"

    if kind == "assembly" or low == "assembly":
        return "Foyer"
    if kind == "pe":
        if low == "gym":
            return "Gym"
        return "Sports Hall"
    if "art" in low and "art" == low:
        return "Art Room"
    if low == "food technology":
        return "Cooking Room"
    if "flz" in low or stage == "flz":
        return "Sports Hall"
    if low in ("lunch", "lunch break"):
        if stage == "ks3":
            return "Boardroom"
        return "URFUTURE"
    if low.startswith("break"):
        if "main room" in low:
            return "Boardroom"
        if "computer room" in low:
            return "Computer Room"
        return "Outside"
    if "sports leaders" in low or "vocational" in low:
        return "Sports Hall"
    if stage == "ks3":
        return "Boardroom"
    if stage == "ks4":
        return "URFUTURE"
    return ""


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


def _supervision_text(free: list[str], all_staff: list[str], *, day_key: str = "") -> str:
    if len(free) == len(all_staff):
        return "All staff"
    parts = []
    for person in free:
        if person in SLT_MEMBERS and day_key != "wednesday":
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
    if label in ("Lunch", "Lunch Break") or label.startswith("Break") or "Toilet Break" in label:
        return "slot break"
    if label == "Arrival":
        return "slot arrival"
    if label == "Maths":
        return "slot core maths"
    if label == "English":
        return "slot core english"
    low = label.lower()
    if kind == "pe" or low in ("pe", "sports", "semh sports", "gym"):
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
    day_key: str = "",
) -> str:
    label = row.get(stage, "—")
    staff = row.get(f"staff_{stage}") if show_staff else None
    supervision = row.get(f"supervision_{stage}")
    note = row.get("note")
    cls = cell_class(label, row.get("kind", ""))
    display_label = label
    if colspan == 1 and stage in ("ks3", "ks4") and _is_break_or_lunch(label):
        prefix = "KS3" if stage == "ks3" else "KS4"
        if label == "Lunch":
            display_label = f"{prefix} Lunch"
        elif "\u2014" in label:
            room = label.split("\u2014")[1].strip()
            display_label = f"{prefix} Break ({room})"
        elif label.startswith("Break"):
            if day_key and day_key != "wednesday":
                display_label = f"{prefix} Break (Outside)"
            else:
                display_label = f"{prefix} Break"
    label_html = esc(display_label)
    if staff:
        label_html = f'{esc(display_label)}<span class="slot-staff">{esc(staff)}</span>'
    elif supervision and all_staff:
        sup = _supervision_text(supervision, all_staff, day_key=day_key)
        label_html = f'{esc(display_label)}<span class="slot-staff">{esc(sup)}</span>'
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


def render_student_ks_day_panel(week: dict, day_key: str, stage: str) -> str:
    """Render a single day panel for one key stage (ks3 or ks4)."""
    day = week["days"][day_key]
    all_staff = week["staff"].get("people", [])
    rows = display_rows(day, include_staff_only=False)
    rows = [r for r in rows if r.get("kind") != "searches"]
    hint_html = render_searches_hint(day)
    rows_html = []
    period_n = 1
    for row in rows:
        label = row.get(stage, "—")
        if not label or label == "—":
            continue
        time_str = f'{row["start"]}\u2013{row["end"]}'
        staff = row.get(f"staff_{stage}", "")
        supervision = row.get(f"supervision_{stage}")
        if not staff and supervision:
            staff = _supervision_text(supervision, all_staff, day_key=day_key)
        location = get_location(label, stage, day_key, row.get("kind", ""))
        cls = cell_class(label, row.get("kind", ""))
        period = _period_label(period_n, suffix=_period_suffix_for_label(label))
        period_n += 1
        rows_html.append(
            f'<tr class="{cls}">'
            f'<td class="period-col">{esc(period)}</td>'
            f'<td class="time-col">{esc(time_str)}</td>'
            f'<td class="activity-col"><span class="slot-label">{esc(label)}</span></td>'
            f'<td class="staff-col">{esc(staff)}</td>'
            f'<td class="location-col">{esc(location)}</td>'
            f"</tr>"
        )
    prefix = "ks3" if stage == "ks3" else "ks4"
    return f"""
      <section class="day-panel" id="panel-{prefix}-{day_key}" role="tabpanel">
        {hint_html}
        <div class="table-wrap">
          <table class="ks-grid">
            <thead>
              <tr>
                <th scope="col">Period</th>
                <th scope="col">Time</th>
                <th scope="col">Activity</th>
                <th scope="col">Staff</th>
                <th scope="col">Location</th>
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
      </section>"""


def render_student_ks_view(week: dict, stage: str) -> str:
    """Render the full day-tabbed view for one key stage."""
    prefix = "ks3" if stage == "ks3" else "ks4"
    panels = [render_student_ks_day_panel(week, key, stage) for key in DAY_ORDER]
    tab_inputs = []
    for key in DAY_ORDER:
        checked = " checked" if key == "monday" else ""
        tab_inputs.append(
            f'<input type="radio" name="{prefix}-day-tab" id="tab-{prefix}-{key}" class="tab-input"{checked}>'
        )
    tab_labels = []
    for key in DAY_ORDER:
        short = key[:3].capitalize()
        tab_labels.append(
            f'<label for="tab-{prefix}-{key}" class="day-tab-btn" role="tab">{short}</label>'
        )
    panel_css = "\n    ".join(
        f"#tab-{prefix}-{key}:checked ~ .tab-panels #panel-{prefix}-{key} {{ display: block; }}"
        for key in DAY_ORDER
    )
    tab_bar = f'<div class="tab-bar" role="tablist">{"".join(tab_labels)}</div>'
    return f"""
  <style>
    {panel_css}
  </style>
  <div class="day-tabs">
    {"".join(tab_inputs)}
    {tab_bar}
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


ARRIVAL_WINDOW = (8 * 60 + 50, 9 * 60 + 15)  # 08:50–09:15


def relabel_arrival_ppa(ppa_sessions: list[dict]) -> list[dict]:
    """Replace PPA with 'Whole School Support' during the 08:50–09:15 arrival window."""
    arrival_start, arrival_end = ARRIVAL_WINDOW
    result: list[dict] = []
    for s in ppa_sessions:
        if s["subject"] != "PPA":
            result.append(s)
            continue
        parts = s["time"].split("\u2013")
        s_start = _time_minutes(parts[0])
        s_end = _time_minutes(parts[1])
        if s_end <= arrival_start or s_start >= arrival_end:
            result.append(s)
            continue
        if s_start < arrival_start:
            result.append({**s, "time": f"{_minutes_to_time(s_start)}\u2013{_minutes_to_time(arrival_start)}"})
        overlap_start = max(s_start, arrival_start)
        overlap_end = min(s_end, arrival_end)
        result.append({
            **s,
            "time": f"{_minutes_to_time(overlap_start)}\u2013{_minutes_to_time(overlap_end)}",
            "subject": "Whole School Support",
        })
        if s_end > arrival_end:
            result.append({**s, "time": f"{_minutes_to_time(arrival_end)}\u2013{_minutes_to_time(s_end)}"})
    return result


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
        # Some staff-wide blocks (e.g. CPD) must remain split so that
        # part-time staff only see their actual overlap after working-hours filtering.
        if prev.get("subject") == "CPD" and s.get("subject") == "CPD":
            out.append(dict(s))
            continue
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
                    sup_type = "Lunch" if break_label == "Lunch" else "Break"
                    sup_subject = f"{stage_label} {sup_type} Supervision"
                    location = ""
                    if "\u2014" in break_label:
                        location = break_label.split("\u2014")[1].strip()
                        sup_subject = f"{sup_subject} ({location})"
                    for person in supervision:
                        if day_key in off_days.get(person, []):
                            continue
                        if person in SLT_MEMBERS and day_key != "wednesday" and not location:
                            person_subject = f"Break Supervision (Main Foyer)"
                        elif person not in SLT_MEMBERS and day_key != "wednesday" and not location and sup_type == "Break":
                            if person == supervision[0]:
                                person_subject = sup_subject
                            else:
                                person_subject = f"{sup_subject} (Outside)"
                        else:
                            person_subject = sup_subject
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


def get_staff_location(subject: str, stage: str, day_key: str) -> str:
    """Derive a room/location for a staff timetable entry."""
    low = subject.lower()

    if low == "student support":
        return ""
    if low == "ppa" or low == "ppa / lunch":
        return ""

    # Wednesday: Foyer does not exist — redirect to available rooms
    if day_key == "wednesday":
        if "student searches" in low:
            return "Main Room"
        if "on-call" in low or "centre duties" in low:
            return "Main Room"
        if low == "supporting assembly":
            return "Main Room"
        if "whole school support" in low:
            return "Main Room"
        if "ks3 support" in low:
            return "Main Room"
        if "arrival" in low:
            return "Main Room"
        if "checks" in low:
            return "Main Room"
        if "transition" in low:
            return "Main Room"
        if "staff briefing" in low or "set up" in low:
            return "Main Room"
        if "pause" in low and "progress" in low:
            return "Main Room"
        if "line management" in low:
            return "Main Room"
        if "slt meeting" in low:
            return "Main Room"
        if "assembly" in low:
            return "Main Room"
        if "break supervision" in low or ("break" in low and "supervision" in low):
            if "ks3" in low or stage == "KS3":
                return "Main Room"
            if "ks4" in low or stage == "KS4":
                return "Computer Suite"
            return "Main Room"
        if "lunch supervision" in low or ("lunch" in low and "supervision" in low):
            if "ks3" in low or stage == "KS3":
                return "Main Room"
            if "ks4" in low or stage == "KS4":
                return "Computer Suite"
            return "Main Room"
        if low in ("lunch", "lunch break"):
            if stage == "KS3":
                return "Main Room"
            if stage == "KS4":
                return "Computer Suite"
            return "Main Room"
        if low.startswith("break"):
            if stage == "KS3":
                return "Main Room"
            return "Computer Suite"
        if low in ("gym", "pe", "sports", "semh sports") or low.startswith("pe"):
            return "Gym"
        if "sports leaders" in low or "vocational" in low:
            return "Gym"
        if stage == "FLZ" or "flz" in low:
            return "Gym"
        if "reset" in low:
            if stage == "KS3" or stage == "All":
                return "Main Room"
            if stage == "KS4":
                return "Computer Suite"
            return "Main Room"
        if "team meeting" in low or "thrive" in low:
            return "Main Room"
        if stage in ("KS3", "All"):
            return "Main Room"
        if stage == "KS4":
            return "Computer Suite"
        return "Main Room"

    # Non-Wednesday days
    if "student searches" in low:
        return "Foyer"
    if "on-call" in low or "centre duties" in low:
        return "Foyer"
    if low == "supporting assembly":
        return "Foyer"
    if "whole school support" in low:
        return "Foyer"
    if "ks3 support" in low:
        return "Foyer"
    if "arrival" in low:
        return "Foyer"
    if "checks" in low:
        return "Foyer"
    if "transition" in low:
        return "Foyer"
    if "staff briefing" in low or "set up" in low:
        return "Foyer"
    if "pause" in low and "progress" in low:
        return "Foyer"
    if "line management" in low:
        return "Foyer"
    if "slt meeting" in low:
        return "Foyer"

    if "assembly" in low:
        return "Foyer"

    if "break supervision" in low or ("break" in low and "supervision" in low):
        if "main foyer" in low or "foyer" in low:
            return "Foyer"
        if "outside" in low:
            return "Outside"
        if "main room" in low:
            return "Boardroom"
        if "computer room" in low:
            return "Computer Room"
        if "ks3" in low or stage == "KS3":
            return "Boardroom"
        if "ks4" in low or stage == "KS4":
            return "URFUTURE"
        return "Outside"

    if "lunch supervision" in low or ("lunch" in low and "supervision" in low):
        if "ks3" in low or stage == "KS3":
            return "Boardroom"
        if "ks4" in low or stage == "KS4":
            return "URFUTURE"
        return ""

    if low in ("lunch", "lunch break"):
        if stage == "KS3":
            return "Boardroom"
        if stage == "KS4":
            return "URFUTURE"
        return ""

    if low.startswith("break"):
        return "Outside"

    if low == "gym":
        return "Gym"
    if low in ("pe", "sports", "semh sports"):
        return "Sports Hall"
    if low == "art":
        return "Art Room"
    if low == "food technology":
        return "Cooking Room"
    if "beauty" in low or "enrichment" in low:
        return "Foyer / Beauty Room"
    if "sports leaders" in low or "vocational" in low:
        return "Sports Hall"

    if stage == "FLZ" or "flz" in low:
        return "Sports Hall"

    if "reset" in low:
        if stage == "KS3" or stage == "All":
            return "Boardroom"
        if stage == "KS4":
            return "URFUTURE"
        return ""

    if "team meeting" in low or "thrive" in low:
        return "Boardroom"

    if stage in ("KS3", "All"):
        return "Boardroom"
    if stage == "KS4":
        return "URFUTURE"
    return ""


def render_person_day_panel(day_key: str, sessions: list[dict], *, is_off_day: bool = False) -> str:
    if sessions:
        rows_html = []
        period_n = 1
        for s in sessions:
            is_ppa = s["subject"].startswith("PPA")
            subj_cls = "subject-col ppa" if is_ppa else "subject-col"
            location = s["location"] if "location" in s else get_staff_location(s["subject"], s["stage"], day_key)
            period = _period_label(period_n)
            period_n += 1
            rows_html.append(
                "<tr>"
                f'<td class="period-col">{esc(period)}</td>'
                f'<td class="time-col">{esc(s["time"])}</td>'
                f'<td>{esc(s["stage"])}</td>'
                f'<td class="{subj_cls}">{esc(s["subject"])}</td>'
                f'<td class="location-col">{esc(location)}</td>'
                "</tr>"
            )
        body = "".join(rows_html)
    else:
        msg = "Not working" if is_off_day else "No sessions"
        body = f'<tr><td colspan="5" class="muted">{msg}</td></tr>'
    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel">
        <div class="table-wrap">
          <table class="person-grid">
            <thead>
              <tr>
                <th scope="col">Period</th>
                <th scope="col">Time</th>
                <th scope="col">Group</th>
                <th scope="col">Activity</th>
                <th scope="col">Location</th>
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
    <a class="back" href="../staff-timetable.html">\u2190 Staff timetable</a>
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
    period_n = 1
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
                k3_disp = esc(ks3) + f' <span class="lead">({esc(_supervision_text(sup3, all_staff, day_key=day_key))})</span>'
            if not s4 and sup4:
                k4_disp = esc(ks4) + f' <span class="lead">({esc(_supervision_text(sup4, all_staff, day_key=day_key))})</span>'
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
        period = _period_label(period_n, suffix=_period_suffix_for_row(row))
        period_n += 1
        period_cell = f'<td class="period-col">{esc(period)}</td>'
        time_cell = f'<td class="time-col">{esc(row["start"])}–{esc(row["end"])}</td>'
        ks3_cls = cell_class(ks3, row.get("kind", ""))
        if merge_all:
            rows_html.append(
                f"<tr>{period_cell}{time_cell}"
                f'<td colspan="3" class="{ks3_cls}">{k3_disp}</td>'
                f"</tr>"
            )
        elif merge_ks:
            rows_html.append(
                f"<tr>{period_cell}{time_cell}"
                f'<td colspan="2" class="{ks3_cls}">{k3_disp}</td>'
                f"{flz_html}</tr>"
            )
        else:
            rows_html.append(
                f"<tr>{period_cell}{time_cell}"
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
                <th scope="col">Period</th>
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
    #tab-friday:checked ~ .tab-bar label[for="tab-friday"],
    #tab-ks3-monday:checked ~ .tab-bar label[for="tab-ks3-monday"],
    #tab-ks3-tuesday:checked ~ .tab-bar label[for="tab-ks3-tuesday"],
    #tab-ks3-wednesday:checked ~ .tab-bar label[for="tab-ks3-wednesday"],
    #tab-ks3-thursday:checked ~ .tab-bar label[for="tab-ks3-thursday"],
    #tab-ks3-friday:checked ~ .tab-bar label[for="tab-ks3-friday"],
    #tab-ks4-monday:checked ~ .tab-bar label[for="tab-ks4-monday"],
    #tab-ks4-tuesday:checked ~ .tab-bar label[for="tab-ks4-tuesday"],
    #tab-ks4-wednesday:checked ~ .tab-bar label[for="tab-ks4-wednesday"],
    #tab-ks4-thursday:checked ~ .tab-bar label[for="tab-ks4-thursday"],
    #tab-ks4-friday:checked ~ .tab-bar label[for="tab-ks4-friday"] {
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

    .period-col {
      color: #8b949e;
      white-space: nowrap;
      width: 6.75rem;
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
    .period-col { color: #8b949e; white-space: nowrap; width: 7rem; }
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

FAQ_CSS = """
    .faq-section {
      margin-top: 2rem;
      border-top: 1px solid #21262d;
      padding-top: 1.5rem;
    }
    .faq-title {
      font-size: 1rem;
      font-weight: 600;
      color: #8b949e;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.75rem;
    }
    .faq-section details {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      margin-bottom: 0.5rem;
      transition: border-color 0.15s;
    }
    .faq-section details[open] {
      border-color: #58a6ff;
    }
    .faq-section summary {
      cursor: pointer;
      padding: 0.65rem 0.85rem;
      font-size: 0.85rem;
      font-weight: 500;
      color: #e6edf3;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .faq-section summary::-webkit-details-marker { display: none; }
    .faq-section summary::before {
      content: '▸';
      color: #8b949e;
      font-size: 0.75rem;
      transition: transform 0.15s;
    }
    .faq-section details[open] summary::before {
      transform: rotate(90deg);
    }
    .faq-section .faq-answer {
      padding: 0 0.85rem 0.75rem 1.6rem;
      font-size: 0.82rem;
      color: #8b949e;
      line-height: 1.5;
    }
"""

FAQ_ITEMS: dict[str, dict[str, str]] = {
    "student_support": {
        "q": "What is Student Support?",
        "a": "Student Support is in the form of mentoring, in-class or out-of-class support of students. This is assigned to you by SLT.",
    },
    "whole_school_support": {
        "q": "What is Whole School Support?",
        "a": "Whole School Support is essentially supporting all staff and all students during unstructured times. To supervise students.",
    },
    "centre_duties": {
        "q": "What are Centre Duties?",
        "a": "Centre Duties means being available on-call for incidents, overseeing general centre operations from the Main Foyer (including supporting unstructured times), and assigning staff for student support allocations (Supervision / monitoring of students).",
    },
    "lesson_observations": {
        "q": "What is the lesson observation expectation?",
        "a": "At least two lesson observations per staff member per week as part of SLT Centre Duties.",
    },
}

def render_faq_section_all() -> str:
    """Render glossary with ALL FAQ items for the main staff page."""
    items_html = []
    for key in ("student_support", "whole_school_support", "centre_duties", "lesson_observations"):
        item = FAQ_ITEMS[key]
        items_html.append(
            f'<details><summary>{esc(item["q"])}</summary>'
            f'<div class="faq-answer">{esc(item["a"])}</div></details>'
        )
    return f"""
  <section class="faq-section">
    <h2 class="faq-title">Glossary / FAQ</h2>
    {''.join(items_html)}
  </section>"""


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
    .period-col { color: #8b949e; white-space: nowrap; width: 7rem; }
    .subject-col { color: #f0f6fc; font-weight: 500; }
    .subject-col.ppa { color: #d2a8ff; font-style: italic; }
    .location-col { color: #a371f7; font-size: 0.8rem; font-weight: 500; }
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


STUDENT_KS_SPLIT_CSS = """
    .ks-selector {
      display: flex;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .ks-btn {
      flex: 1;
      padding: 1rem 1.5rem;
      font-size: 1.1rem;
      font-weight: 600;
      text-align: center;
      cursor: pointer;
      border: 2px solid #30363d;
      border-radius: 12px;
      background: #161b22;
      color: #8b949e;
      transition: all 0.2s;
    }

    .ks-btn:hover {
      background: #21262d;
      color: #e6edf3;
      border-color: #58a6ff;
    }

    .ks-btn.active {
      background: #1f3a5f;
      color: #f0f6fc;
      border-color: #58a6ff;
    }

    .ks-view { display: none; }
    .ks-view.active { display: block; }

    .ks-grid {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }

    .ks-grid th,
    .ks-grid td {
      border: 1px solid #21262d;
      padding: 0.55rem 0.65rem;
      vertical-align: top;
      text-align: left;
    }

    .ks-grid th {
      background: #1c2128;
      color: #f0f6fc;
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }

    .activity-col .slot-label { font-weight: 500; color: #e6edf3; }
    .staff-col { color: #8b949e; font-size: 0.8rem; }
    .location-col { color: #a371f7; font-size: 0.8rem; font-weight: 500; }

    .ks-grid tr.break .activity-col .slot-label { color: #3fb950; }
    .ks-grid tr.break .location-col { color: #3fb950; }
    .ks-grid tr.core.maths .activity-col .slot-label { color: #79c0ff; font-weight: 600; }
    .ks-grid tr.core.english .activity-col .slot-label { color: #e3b341; font-weight: 600; }
    .ks-grid tr.assembly .activity-col .slot-label { color: #d2a8ff; }
    .ks-grid tr.reset .activity-col .slot-label { color: #79c0ff; font-weight: 600; }
    .ks-grid tr.pe .activity-col .slot-label { color: #3fb950; font-weight: 600; }
    .ks-grid tr.arrival .activity-col .slot-label { color: #58a6ff; }
    .ks-grid tr.checks .activity-col .slot-label { color: #8b949e; font-style: italic; }
    .ks-grid tr.transition .activity-col .slot-label { color: #8b949e; font-style: italic; }
"""

STUDENT_KS_SPLIT_JS = """
<script>
document.addEventListener('DOMContentLoaded', function() {
  var btns = document.querySelectorAll('.ks-btn');
  var views = document.querySelectorAll('.ks-view');
  btns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      btns.forEach(function(b) { b.classList.remove('active'); });
      views.forEach(function(v) { v.classList.remove('active'); });
      btn.classList.add('active');
      var target = btn.getAttribute('data-target');
      document.getElementById(target).classList.add('active');
    });
  });
});
</script>
"""


def build_student_html(week: dict) -> str:
    ks3_view = render_student_ks_view(week, "ks3")
    ks4_view = render_student_ks_view(week, "ks4")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Student timetable</title>
  <style>{DAY_TAB_CSS}{SHARED_STUDENT_CSS}{STUDENT_KS_SPLIT_CSS}{SEARCHES_HINT_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">\u2190 Back</a>
    <h1>Student timetable</h1>
  </div>

  <div class="ks-selector">
    <button class="ks-btn active" data-target="ks3-view">KS3 Timetable</button>
    <button class="ks-btn" data-target="ks4-view">KS4 Timetable</button>
  </div>

  <div id="ks3-view" class="ks-view active">
    {ks3_view}
  </div>

  <div id="ks4-view" class="ks-view">
    {ks4_view}
  </div>

  {SEARCHES_HINT_JS}
  {STUDENT_KS_SPLIT_JS}
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


OVERVIEW_CSS = DAY_TAB_CSS + """
    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
      background: #0d1117;
      color: #e6edf3;
      min-height: 100vh;
      padding: 2rem 1rem;
      margin: 0 auto;
    }

    .top { margin-bottom: 1.5rem; max-width: 900px; margin-left: auto; margin-right: auto; }

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

    .overview-grid {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.78rem;
      min-width: 900px;
    }

    .overview-grid th,
    .overview-grid td {
      border: 1px solid #21262d;
      padding: 0.4rem 0.5rem;
      vertical-align: top;
      text-align: left;
    }

    .overview-grid th {
      background: #1c2128;
      color: #f0f6fc;
      font-weight: 600;
      font-size: 0.7rem;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      white-space: nowrap;
      position: sticky;
      top: 0;
      z-index: 2;
    }

    .overview-grid .time-col {
      color: #8b949e;
      white-space: nowrap;
      width: 6.5rem;
      font-size: 0.72rem;
    }

    .overview-grid .period-col {
      color: #8b949e;
      white-space: nowrap;
      width: 6.75rem;
      font-size: 0.72rem;
    }

    .ov-cell { min-width: 90px; }
    .ov-cell .ov-activity { font-weight: 500; color: #e6edf3; display: block; line-height: 1.3; }
    .ov-cell .ov-location { font-size: 0.65rem; color: #a371f7; display: block; margin-top: 0.1rem; }
    .ov-cell .ov-off { color: #484f58; font-style: italic; }

    .ov-cell.cat-break .ov-activity { color: #3fb950; }
    .ov-cell.cat-supervision .ov-activity { color: #f0883e; }
    .ov-cell.cat-teaching .ov-activity { color: #79c0ff; }
    .ov-cell.cat-assembly .ov-activity { color: #d2a8ff; }
    .ov-cell.cat-admin .ov-activity { color: #8b949e; font-style: italic; }
    .ov-cell.cat-pe .ov-activity { color: #3fb950; font-weight: 600; }
    .ov-cell.cat-reset .ov-activity { color: #79c0ff; font-weight: 600; }
    .ov-cell.cat-searches .ov-activity { color: #f78166; font-weight: 600; }

    #tab-monday:checked ~ .tab-bar label[for="tab-monday"],
    #tab-tuesday:checked ~ .tab-bar label[for="tab-tuesday"],
    #tab-wednesday:checked ~ .tab-bar label[for="tab-wednesday"],
    #tab-thursday:checked ~ .tab-bar label[for="tab-thursday"],
    #tab-friday:checked ~ .tab-bar label[for="tab-friday"] {
      color: #f0f6fc;
      background: #1f3a5f;
      border-color: #58a6ff;
    }
"""


def _overview_category(label: str, kind: str) -> str:
    """Return a CSS category class for colour-coding overview cells."""
    if not label or label == "—":
        return ""
    low = label.lower()
    if kind == "searches" or "searches" in low:
        return "cat-searches"
    if kind == "pe" or low in ("pe", "sports", "semh sports", "gym"):
        return "cat-pe"
    if kind == "assembly" or low == "assembly":
        return "cat-assembly"
    if kind == "reset" or low == "reset":
        return "cat-reset"
    if "break" in low or low == "lunch":
        return "cat-break"
    if "supervision" in low:
        return "cat-supervision"
    if kind in ("checks", "transition", "briefing") or "checks" in low or "transition" in low or "briefing" in low:
        return "cat-admin"
    if kind == "lesson" or "maths" in low or "english" in low or "mentoring" in low:
        return "cat-teaching"
    return ""


def _overview_staff_activity(person: str, row: dict, day_key: str, all_staff: list[str]) -> tuple[str, str]:
    """Determine what a staff member is doing in a given row.

    Returns (activity_label, location).
    """
    if row.get("all_staff"):
        label = row.get("ks3", row.get("ks4", ""))
        loc = get_location(label, "ks3", day_key, row.get("kind", ""))
        return label, loc

    for stage in ("ks3", "ks4", "flz"):
        staff_field = row.get(f"staff_{stage}", "")
        if person in {s.strip() for s in staff_field.split("/")} if staff_field else False:
            label = row.get(stage, "—")
            loc = get_location(label, stage, day_key, row.get("kind", ""))
            stage_prefix = {"ks3": "KS3", "ks4": "KS4", "flz": "FLZ"}.get(stage, "")
            if stage_prefix and row.get("kind") == "lesson":
                label = f"{label} ({stage_prefix})"
            return label, loc

    for stage in ("ks3", "ks4"):
        supervision = row.get(f"supervision_{stage}", [])
        if person in supervision:
            break_label = row.get(stage, "")
            stage_label = "KS3" if stage == "ks3" else "KS4"
            sup_type = "Lunch" if break_label == "Lunch" else "Break"
            activity = f"{stage_label} {sup_type} Sup."
            loc = get_location(break_label, stage, day_key, row.get("kind", ""))
            return activity, loc

    # SLT expectation: during break/lunch, SLT are based in the Main Foyer
    # unless they are teaching (handled above).
    if (
        day_key != "wednesday"
        and person in SLT_MEMBERS
        and (_is_break_or_lunch(row.get("ks3", "")) or _is_break_or_lunch(row.get("ks4", "")))
    ):
        return "Centre Duties", "Foyer"

    return "", ""


def render_overview_day_panel(week: dict, day_key: str) -> str:
    """Render one day panel for the overview page."""
    day = week["days"][day_key]
    all_staff = week["staff"].get("people", [])
    off_days = week["staff"].get("off_days", {})
    rows = display_rows(day, include_staff_only=True)

    rows_html = []
    period_n = 1
    for row in rows:
        period = _period_label(period_n, suffix=_period_suffix_for_row(row))
        period_n += 1
        period_cell = f'<td class="period-col">{esc(period)}</td>'
        time_cell = f'<td class="time-col">{esc(row["start"])}–{esc(row["end"])}</td>'

        ks3_label = row.get("ks3", "—")
        ks4_label = row.get("ks4", "—")
        ks3_loc = get_location(ks3_label, "ks3", day_key, row.get("kind", ""))
        ks4_loc = get_location(ks4_label, "ks4", day_key, row.get("kind", ""))
        ks3_cat = _overview_category(ks3_label, row.get("kind", ""))
        ks4_cat = _overview_category(ks4_label, row.get("kind", ""))
        sup3 = row.get("supervision_ks3")
        sup4 = row.get("supervision_ks4")
        ks3_support = ""
        ks4_support = ""
        if _is_break_or_lunch(ks3_label) and sup3:
            ks3_support = _supervision_text(sup3, all_staff, day_key=day_key)
        if _is_break_or_lunch(ks4_label) and sup4:
            ks4_support = _supervision_text(sup4, all_staff, day_key=day_key)

        ks3_cell = (
            f'<td class="ov-cell {ks3_cat}">'
            f'<span class="ov-activity">{esc(ks3_label)}</span>'
            + (f'<span class="ov-location">{esc(ks3_support)}</span>' if ks3_support else "")
            + (f'<span class="ov-location">{esc(ks3_loc)}</span>' if ks3_loc else "")
            + "</td>"
        )
        ks4_cell = (
            f'<td class="ov-cell {ks4_cat}">'
            f'<span class="ov-activity">{esc(ks4_label)}</span>'
            + (f'<span class="ov-location">{esc(ks4_support)}</span>' if ks4_support else "")
            + (f'<span class="ov-location">{esc(ks4_loc)}</span>' if ks4_loc else "")
            + "</td>"
        )

        staff_cells = []
        for person in all_staff:
            is_off = day_key in off_days.get(person, [])
            working = _staff_working_at(person, day_key, row["start"])
            if is_off or not working:
                staff_cells.append('<td class="ov-cell"><span class="ov-off">—</span></td>')
                continue
            activity, loc = _overview_staff_activity(person, row, day_key, all_staff)
            if not activity:
                staff_cells.append('<td class="ov-cell"><span class="ov-off">—</span></td>')
                continue
            cat = _overview_category(activity, row.get("kind", ""))
            cell = (
                f'<td class="ov-cell {cat}">'
                f'<span class="ov-activity">{esc(activity)}</span>'
                + (f'<span class="ov-location">{esc(loc)}</span>' if loc else "")
                + "</td>"
            )
            staff_cells.append(cell)

        rows_html.append(
            f"<tr>{period_cell}{time_cell}{ks3_cell}{ks4_cell}{''.join(staff_cells)}</tr>"
        )

    staff_headers = "".join(f'<th scope="col">{esc(p)}</th>' for p in all_staff)

    return f"""
      <section class="day-panel" id="panel-{day_key}" role="tabpanel">
        <div class="table-wrap">
          <table class="overview-grid">
            <thead>
              <tr>
                <th scope="col">Period</th>
                <th scope="col">Time</th>
                <th scope="col">KS3</th>
                <th scope="col">KS4</th>
                {staff_headers}
              </tr>
            </thead>
            <tbody>
              {''.join(rows_html)}
            </tbody>
          </table>
        </div>
      </section>"""


def build_overview_html(week: dict) -> str:
    """Generate the full overview page with all staff + students side by side."""
    panels = [render_overview_day_panel(week, key) for key in DAY_ORDER]
    panel_css = "\n    ".join(
        f"#tab-{key}:checked ~ .tab-panels #panel-{key} {{ display: block; }}"
        for key in DAY_ORDER
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Overview — All Timetables</title>
  <style>
    {OVERVIEW_CSS}
    {panel_css}
  </style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">\u2190 Back</a>
    <h1>Weekly Overview</h1>
  </div>

  <div class="day-tabs">
    {render_day_tab_inputs()}
    {render_day_tab_bar()}
    <div class="tab-panels">
      {''.join(panels)}
    </div>
  </div>
</body>
</html>
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
  <style>{STAFF_CARDS_CSS}{FAQ_CSS}</style>
</head>
<body>
  <div class="top">
    <a class="back" href="index.html">\u2190 Back</a>
    <h1>Staff timetable</h1>
  </div>

  <nav class="staff-grid" aria-label="Staff members">
    {''.join(cards)}
  </nav>

  {render_faq_section_all()}
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


def apply_staff_period_overrides(combined: list[dict], initials: str) -> None:
    """Apply staff-only Activity overrides by (day_key, period_number).

    These overrides must not alter the underlying student timetable (week.json rows).
    Period numbers are the rendered numbering within each staff day panel.
    """
    overrides: dict[str, dict[str, dict[int, str]]] = {
        "LG": {
            "monday": {7: "Student Support", 10: "Lunch Break"},
            "tuesday": {7: "Lunch Break", 10: "Student Support"},
            "thursday": {7: "Lunch Break"},
            "wednesday": {13: "Lunch Break"},
        },
        "LI": {
            "wednesday": {13: "Lunch Break"},
        },
    }

    def _apply_label(s: dict, label: str) -> None:
        s["subject"] = label
        if label.lower() in ("lunch", "lunch break"):
            s["stage"] = ""
            s["location"] = ""
        elif label.lower() == "student support":
            s["location"] = ""
            if not s.get("stage"):
                s["stage"] = "—"

    per_person = overrides.get(initials, {})
    if not per_person:
        return

    grouped = group_sessions_by_day(combined)
    for day_key, day_sessions in grouped.items():
        if not day_sessions:
            continue
        day_sessions.sort(key=lambda s: s["time"])
        day_override = per_person.get(day_key, {})
        for idx, sess in enumerate(day_sessions, start=1):
            new_label = day_override.get(idx)
            if new_label:
                _apply_label(sess, new_label)


def split_blank_sessions_for_period_alignment(combined: list[dict], initials: str) -> None:
    """Split specific blank sessions so period numbering matches expected rows."""
    if initials != "LI":
        return
    split_at = _time_minutes("14:30")
    new: list[dict] = []
    for s in combined:
        if s.get("day_key") != "wednesday" or s.get("subject") != "":
            new.append(s)
            continue
        start_s, end_s = s["time"].split("–")
        a, b = _time_minutes(start_s), _time_minutes(end_s)
        if not (a < split_at < b):
            new.append(s)
            continue
        left = dict(s)
        left["time"] = f"{_minutes_to_time(a)}–{_minutes_to_time(split_at)}"
        right = dict(s)
        right["time"] = f"{_minutes_to_time(split_at)}–{_minutes_to_time(b)}"
        new.extend([left, right])
    combined[:] = new


def main() -> None:
    week = load_week()
    if "rows" not in week["days"]["monday"]:
        raise SystemExit("week.json must use days.*.rows format")
    add_supervision(week)

    (ROOT / "student-timetable.html").write_text(build_student_html(week), encoding="utf-8")
    (ROOT / "staff-timetable.html").write_text(build_staff_html(week), encoding="utf-8")
    (ROOT / "overview.html").write_text(build_overview_html(week), encoding="utf-8")

    STAFF_DIR.mkdir(exist_ok=True)
    sessions = collect_staff_sessions(week)
    day_labels = {k: v["label"] for k, v in week["days"].items()}
    for initials in week["staff"].get("people", []):
        person_sessions = sessions.get(initials, [])
        person_sessions = filter_by_working_hours(person_sessions, initials)
        for ovr in week["staff"].get("slot_overrides", {}).get(initials, []):
            for day_key in ovr["days"]:
                person_sessions.append({
                    "day": day_labels.get(day_key, day_key.capitalize()),
                    "day_key": day_key,
                    "time": f'{ovr["start"]}\u2013{ovr["end"]}',
                    "stage": ovr.get("stage", "\u2014"),
                    "subject": ovr["subject"],
                })
        sorted_sessions = sorted(
            person_sessions,
            key=lambda s: (DAY_ORDER.index(s["day_key"]), s["time"]),
        )
        deduped = dedup_person_sessions(sorted_sessions)
        merged = merge_staff_sessions(deduped)
        ppa_gaps = fill_ppa_gaps(merged, initials, day_labels)
        ppa_gaps = relabel_arrival_ppa(ppa_gaps)
        combined = sorted(
            merged + ppa_gaps,
            key=lambda s: (DAY_ORDER.index(s["day_key"]), s["time"]),
        )
        combined = merge_staff_sessions(combined)
        if initials in ("SA", "LD"):
            for s in combined:
                if s["subject"] == "PPA":
                    s["subject"] = "On-call / Centre Duties"
            # During break/lunch, SLT are based in the Main Foyer unless teaching.
            existing_slots = {(s["day_key"], s["time"]) for s in combined}
            for day_key in DAY_ORDER:
                if day_key == "wednesday":
                    continue
                day = week["days"].get(day_key)
                if not day:
                    continue
                for row in day.get("rows", []):
                    if not (_is_break_or_lunch(row.get("ks3", "")) or _is_break_or_lunch(row.get("ks4", ""))):
                        continue
                    slot_time = f'{row["start"]}–{row["end"]}'
                    if (day_key, slot_time) in existing_slots:
                        continue
                    combined.append(
                        {
                            "day": day_labels.get(day_key, day_key.capitalize()),
                            "day_key": day_key,
                            "time": slot_time,
                            "stage": "All",
                            "subject": "Centre Duties",
                            "location": "Foyer",
                        }
                    )
                    existing_slots.add((day_key, slot_time))
        if initials == "SA":
            for s in combined:
                if s["subject"] == "Break Supervision (Main Foyer)":
                    s["subject"] = "Supervision"
                    s["location"] = "Foyer"
        if initials == "LG":
            for s in combined:
                if s["subject"] == "PPA" and (
                    s["time"] == "11:35\u201312:15"
                    or (s["time"] == "12:30\u201313:20" and s["day_key"] == "monday")
                ):
                    s["subject"] = "PPA / Lunch"
        if initials == "LI":
            _li_overrides: dict[tuple[str, str], str] = {
                ("monday", "11:05\u201311:20"): "Student Support",
                ("monday", "11:35\u201312:15"): "PPA / Lunch",
                ("monday", "14:45\u201315:00"): "Student Support",
                ("tuesday", "11:05\u201311:20"): "Student Support",
                ("tuesday", "11:35\u201312:15"): "PPA / Lunch",
                ("tuesday", "13:00\u201313:10"): "Student Support",
                ("tuesday", "14:45\u201315:30"): "Student Support",
                ("wednesday", "14:30\u201315:00"): "PPA / Lunch",
                ("wednesday", "14:45\u201315:00"): "Student Support",
                ("thursday", "11:05\u201311:20"): "Student Support",
                ("thursday", "11:35\u201312:15"): "PPA / Lunch",
                ("friday", "11:35\u201312:15"): "PPA / Lunch",
            }
            for s in combined:
                if s["subject"] == "PPA":
                    new_label = _li_overrides.get((s["day_key"], s["time"]))
                    if new_label:
                        s["subject"] = new_label
            # Ensure LI's lunch slot is always labelled "Lunch" (Mon/Tue/Thu/Fri only).
            for s in combined:
                if (
                    s["day_key"] in ("monday", "tuesday", "thursday", "friday")
                    and s["time"] == "12:15\u201312:30"
                ):
                    s["subject"] = "Lunch"
                    s["stage"] = ""
                    s["location"] = ""
        if initials in ("HK", "JM", "JC"):
            for s in combined:
                if s["subject"] == "PPA":
                    s["subject"] = "Student Support"
                    if initials == "JC":
                        s["location"] = "Foyer"
        if initials == "JC":
            # JC has a few fixed-role blocks that should appear explicitly (not as generic support),
            # and one slot that needs a label variant without changing the student-facing timetable.
            def _upsert_slot(day_key: str, time: str, *, stage: str, subject: str) -> None:
                # Prefer replacing generic filler (e.g. Student Support) rather than duplicating slots.
                for s in combined:
                    if s["day_key"] == day_key and s["time"] == time:
                        if s.get("subject") in ("", "Student Support"):
                            s["stage"] = stage
                            s["subject"] = subject
                            s.pop("location", None)
                            return
                combined.append(
                    {
                        "day": day_labels.get(day_key, day_key.capitalize()),
                        "day_key": day_key,
                        "time": time,
                        "stage": stage,
                        "subject": subject,
                    }
                )

            def _subtract_fixed_support(day_key: str, *, fixed: list[tuple[str, str]]) -> None:
                """Remove/trim generic Student Support that overlaps fixed slots."""
                fixed_mins = [(_time_minutes(s), _time_minutes(e)) for s, e in fixed]
                fixed_mins.sort()

                new_combined: list[dict] = []
                for s in combined:
                    if s["day_key"] != day_key or s.get("subject") != "Student Support":
                        new_combined.append(s)
                        continue

                    start_s, end_s = s["time"].split("–")
                    a, b = _time_minutes(start_s), _time_minutes(end_s)
                    remaining: list[tuple[int, int]] = [(a, b)]
                    for fs, fe in fixed_mins:
                        next_remaining: list[tuple[int, int]] = []
                        for rs, re in remaining:
                            if fe <= rs or fs >= re:
                                next_remaining.append((rs, re))
                                continue
                            if rs < fs:
                                next_remaining.append((rs, fs))
                            if fe < re:
                                next_remaining.append((fe, re))
                        remaining = next_remaining

                    for rs, re in remaining:
                        if re <= rs:
                            continue
                        new_combined.append(
                            {
                                **s,
                                "time": f"{_minutes_to_time(rs)}–{_minutes_to_time(re)}",
                            }
                        )

                combined[:] = new_combined

            # Tue: keep staffing unchanged, but show explicit KS3 label variant for JC.
            for s in combined:
                if (
                    s["day_key"] == "tuesday"
                    and s["time"] == "12:30–13:10"
                    and s["stage"] == "KS3"
                    and s["subject"] == "SEMH / AQA"
                ):
                    s["subject"] = "SEMH / AQA (KS3)"

            _subtract_fixed_support(
                "tuesday",
                fixed=[("11:20", "11:35"), ("11:35", "12:15"), ("12:15", "12:30")],
            )
            _upsert_slot("tuesday", "11:20–11:35", stage="KS4", subject="KS4 Break Support")
            _upsert_slot("tuesday", "11:35–12:15", stage="KS4", subject="1-2-1 Mentoring")
            _upsert_slot("tuesday", "12:15–12:30", stage="KS4", subject="Lunch Support")

            _subtract_fixed_support(
                "thursday",
                fixed=[("11:20", "11:35"), ("11:35", "12:15"), ("12:15", "12:30"), ("12:30", "13:10")],
            )
            _upsert_slot("thursday", "11:20–11:35", stage="KS4", subject="KS4 Break Support")
            _upsert_slot("thursday", "11:35–12:15", stage="KS4", subject="1-2-1 Mentoring")
            _upsert_slot("thursday", "12:15–12:30", stage="KS4", subject="Lunch Support")
            _upsert_slot("thursday", "12:30–13:10", stage="KS4", subject="SEMH / AQA (KS4)")

            # Hard guard: ensure no long "Student Support" block masks the fixed pattern.
            combined[:] = [
                s
                for s in combined
                if not (
                    s.get("subject") == "Student Support"
                    and (
                        (s["day_key"] == "tuesday" and s["time"] == "11:20–12:30")
                        or (s["day_key"] == "thursday" and s["time"] == "11:20–13:10")
                    )
                )
            ]

            combined.sort(key=lambda s: (DAY_ORDER.index(s["day_key"]), s["time"]))
            combined[:] = merge_staff_sessions(dedup_person_sessions(combined))
        if initials == "HK":
            for s in combined:
                if "reset" in s["subject"].lower():
                    s["location"] = "Main Room" if s["day_key"] == "wednesday" else "Boardroom"
        if initials == "JM":
            for s in combined:
                if "reset" in s["subject"].lower():
                    s["location"] = "Computer Suite" if s["day_key"] == "wednesday" else "URFUTURE"
        if initials in ("JM", "HK"):
            for s in combined:
                low = s.get("subject", "").lower()
                if "lunch" in low:
                    continue
                is_break_support = ("break" in low) and ("support" in low or "supervision" in low)
                if not is_break_support:
                    continue
                # Non-Wednesday: break support should display Outside / Foyer for JM/HK.
                # Wednesday has no foyer; keep the standard Wednesday room rules.
                if s.get("day_key") != "wednesday":
                    s["location"] = "Outside / Foyer"

        combined.sort(key=lambda s: (DAY_ORDER.index(s["day_key"]), s["time"]))
        combined[:] = merge_staff_sessions(dedup_person_sessions(combined))

        for s in combined:
            if s["subject"] == "PPA" or s["subject"].startswith("PPA"):
                s["subject"] = ""
                s["stage"] = ""
                s["location"] = ""

        split_blank_sessions_for_period_alignment(combined, initials)
        apply_staff_period_overrides(combined, initials)

        if initials == "LG":
            # Friday: fill any blank/unassigned gaps with Student Support (LG only).
            for s in combined:
                if s.get("day_key") != "friday":
                    continue
                if s.get("subject", "") != "":
                    continue
                s["subject"] = "Student Support"
                s["location"] = ""
                if not s.get("stage"):
                    s["stage"] = "—"
        slug = staff_slug(initials)
        page = render_staff_person_page(week, initials, combined)
        (STAFF_DIR / f"{slug}.html").write_text(page, encoding="utf-8")

    print("Wrote student-timetable.html, staff-timetable.html, overview.html, and staff/*.html")


if __name__ == "__main__":
    main()
