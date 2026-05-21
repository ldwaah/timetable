#!/usr/bin/env python3
"""Generate a validated week.json."""

from __future__ import annotations

import json
from pathlib import Path

PE = "PE (50 min + 10 min change)"
OUT = Path(__file__).parent / "data" / "week.json"


def t2m(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def m2t(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def row(start: str, end: str, ks3: str, ks4: str, **kw) -> dict:
    d = {"start": start, "end": end, "ks3": ks3, "ks4": ks4}
    d.update(kw)
    return d


def acr() -> list[dict]:
    return [
        row("08:50", "09:05", "Arrival", "Arrival", kind="arrival"),
        row("09:05", "09:15", "Checks / late arrivals", "Checks / late arrivals", kind="checks"),
        row("09:15", "09:50", "Reset", "Reset", kind="reset", staff_ks3="Lorelle", staff_ks4="Laurent"),
    ]


def eng(s: str = "09:50") -> dict:
    return row(s, m2t(t2m(s) + 45), "English", "English", kind="lesson", staff_ks3="Lorelle", staff_ks4="Laurent")


def lunch() -> dict:
    return row("12:15", "12:30", "Lunch", "Lunch", kind="lesson")


def pe(s: str = "12:30") -> dict:
    return row(s, m2t(t2m(s) + 60), PE, PE, kind="pe", staff_ks3="Laurent", staff_ks4="Laurent")


def am_pshe_block() -> list[dict]:
    return [
        row("10:35", "11:15", "PSHE", "PSHE", kind="lesson", staff_ks3="Sacha", staff_ks4="Sacha"),
        row("11:15", "11:30", "Break", "Break", kind="lesson"),
        row("11:30", "12:15", "Maths", "Maths", kind="lesson", staff_ks3="Lorelle", staff_ks4="Laurent"),
    ]


def am_core_block() -> list[dict]:
    """After English: staggered citizenship/art pattern + maths (Thu template)."""
    return [
        row("10:35", "10:50", "Citizenship", "Break", kind="lesson", staff_ks3="Lloyd"),
        row("10:50", "11:15", "Citizenship", "Maths", kind="lesson", staff_ks3="Lloyd", staff_ks4="Laurent"),
        row("11:15", "11:30", "Break", "Maths", kind="lesson", staff_ks4="Laurent"),
        row("11:30", "11:35", "Maths", "Maths", kind="lesson", staff_ks3="Lorelle", staff_ks4="Laurent"),
        row("11:35", "12:15", "Maths", "DofE", kind="lesson", staff_ks3="Lorelle", staff_ks4="Lloyd"),
    ]


def am_art_block() -> list[dict]:
    return [
        row("10:35", "10:50", "Art", "Break", kind="lesson"),
        row("10:50", "11:15", "Art", "Maths", kind="lesson", staff_ks4="Laurent"),
        row("11:15", "11:30", "Break", "Maths", kind="lesson", staff_ks4="Laurent"),
        row("11:30", "11:35", "Maths", "Maths", kind="lesson", staff_ks3="Lorelle", staff_ks4="Laurent"),
        row(
            "11:35",
            "12:15",
            "Maths",
            "Citizenship",
            kind="lesson",
            staff_ks3="Lorelle",
            staff_ks4="Lloyd",
        ),
    ]


def pm_long_mon() -> list[dict]:
    return [
        row("13:30", "13:45", "Break", "King's Trust", kind="lesson", staff_ks4="Lorelle"),
        row("13:45", "14:30", "Food Technology", "King's Trust", kind="lesson", staff_ks4="Lorelle"),
        row("14:30", "14:45", "Food Technology", "Break", kind="lesson"),
        row("14:45", "15:00", "Lesson — TBC", "Lesson — TBC", kind="lesson"),
    ]


def pm_long_tue() -> list[dict]:
    return [
        row(
            "13:30",
            "14:30",
            "Food Technology",
            "King's Trust",
            kind="lesson",
            staff_ks4="Lorelle",
        ),
        row("14:30", "14:45", "Break", "Break", kind="lesson"),
        row("14:45", "15:00", "Lesson — TBC", "Lesson — TBC", kind="lesson"),
    ]


def pm_short_vocational() -> list[dict]:
    return [
        row(
            "13:30",
            "14:00",
            "Food Technology",
            "King's Trust",
            kind="lesson",
            staff_ks4="Lorelle",
        ),
    ]


def pm_short_fri() -> list[dict]:
    return [
        row("13:30", "14:00", "Food Technology", "Lesson — TBC", kind="lesson"),
    ]


def build() -> dict:
    return {
        "meta": {
            "assembly_day": "tuesday",
            "assembly_minutes": 35,
            "break_minutes": 15,
            "lunch_minutes": 15,
            "lunch_time": "12:15–12:30",
            "pe_label": PE,
            "pe_minutes": 60,
            "reset_minutes": 35,
            "checks_window": "09:05–09:15",
            "core_placement": "Reset — first teaching block after checks; English then Maths; Tuesday: Reset → Assembly → English",
            "short_day_note": "Thu/Fri: Food Technology and King's Trust are 30-minute sessions after PE (14:00 finish)",
        },
        "days": {
            "monday": {
                "label": "Monday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "15:00",
                "rows": [*acr(), eng(), *am_pshe_block(), lunch(), pe(), *pm_long_mon()],
            },
            "tuesday": {
                "label": "Tuesday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "15:00",
                "rows": [
                    *acr(),
                    row("09:50", "10:25", "Assembly", "Assembly", kind="assembly"),
                    eng("10:25"),
                    row("11:10", "11:25", "Maths", "Break", kind="lesson", staff_ks3="Lorelle"),
                    row("11:25", "11:55", "Maths", "Maths", kind="lesson", staff_ks3="Lorelle", staff_ks4="Laurent"),
                    row("11:55", "12:10", "Break", "Maths", kind="lesson", staff_ks4="Laurent"),
                    row("12:10", "12:15", "Lesson — TBC", "Lesson — TBC", kind="lesson"),
                    lunch(),
                    pe(),
                    *pm_long_tue(),
                ],
            },
            "wednesday": {
                "label": "Wednesday",
                "arrival_from": "10:00",
                "arrival_latest": None,
                "finish": "15:00",
                "staff_meeting": "09:00–10:00",
                "rows": [
                    row("10:00", "10:35", "Reset", "Reset", kind="reset", staff_ks3="Lorelle", staff_ks4="Laurent"),
                    eng("10:35"),
                    row("11:20", "11:35", "Lesson — TBC", "Break", kind="lesson"),
                    row("11:35", "12:15", "Art", "Maths", kind="lesson", staff_ks4="Laurent"),
                    lunch(),
                    row("12:30", "13:10", "Maths", "Citizenship", kind="lesson", staff_ks3="Lorelle", staff_ks4="Lloyd"),
                    row("13:10", "13:15", "Maths", "Lesson — TBC", kind="lesson", staff_ks3="Lorelle"),
                    row("13:15", "13:30", "Break", "Break", kind="lesson"),
                    row("13:30", "14:10", "Lesson — TBC", "DofE", kind="lesson", staff_ks4="Lloyd"),
                    row("14:10", "14:25", "Break", "DofE", kind="lesson", staff_ks4="Lloyd"),
                    row("14:25", "15:00", "Food Technology", "Food Technology", kind="lesson"),
                ],
            },
            "thursday": {
                "label": "Thursday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "14:00",
                "rows": [*acr(), eng(), *am_core_block(), lunch(), pe(), *pm_short_vocational()],
            },
            "friday": {
                "label": "Friday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "14:00",
                "rows": [
                    *acr(),
                    eng(),
                    *am_art_block(),
                    lunch(),
                    pe(),
                    *pm_short_fri(),
                ],
            },
        },
        "staff": {
            "start": "08:30",
            "detentions": {"monday": "15:00–15:30", "friday": "14:00–15:00"},
            "people": ["Lorelle", "Lloyd", "Laurent", "Sacha"],
            "assignments": {
                "Reset": {"ks3": "Lorelle", "ks4": "Laurent"},
                "King's Trust": {"ks4": "Lorelle"},
                "DofE": {"ks4": "Lloyd"},
                "Citizenship": {"ks3": "Lloyd", "ks4": "Lloyd"},
                "Maths": {"ks3": "Lorelle", "ks4": "Laurent"},
                "English": {"ks3": "Lorelle", "ks4": "Laurent"},
                "PE": {"ks3": "Laurent", "ks4": "Laurent"},
                "Art": {"ks3": "Sacha"},
                "Food Technology": {"ks3": "Sacha"},
                "PSHE": {"ks3": "Sacha", "ks4": "Sacha"},
            },
        },
    }


def validate(week: dict) -> list[str]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("vw", Path(__file__).parent / "validate-week.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    issues = []
    for dk, day in week["days"].items():
        issues.extend(mod.validate(day["rows"], day["finish"], dk))  # type: ignore[attr-defined]
    return issues


if __name__ == "__main__":
    week = build()
    issues = validate(week)
    if issues:
        print("FAILED:")
        for i in issues:
            print(" -", i)
        raise SystemExit(1)
    OUT.write_text(json.dumps(week, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
