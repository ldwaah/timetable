#!/usr/bin/env python3
"""Build validated data/week.json from period templates."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "week.json"

PE = "PE"

DURATIONS = {
    "English": 45,
    "Maths": 45,
    "Art": 40,
    "Citizenship": 40,
    "DofE": 40,
    "King's Trust": 60,
    "Food Technology": 50,
    PE: 85,
    "Reset": 35,
    "Assembly": 35,
    "Break": 15,
    "Lunch": 15,
    "Arrival": 15,
    "Checks / late arrivals": 10,
}


def t2m(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def m2t(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def row(start: str, end: str, ks3: str, ks4: str, **extra) -> dict:
    r = {"start": start, "end": end, "ks3": ks3, "ks4": ks4}
    r.update(extra)
    return r


def arrival_checks_reset() -> list[dict]:
    return [
        row("08:50", "09:05", "Arrival", "Arrival", kind="arrival"),
        row("09:05", "09:15", "Checks / late arrivals", "Checks / late arrivals", kind="checks"),
        row(
            "09:15",
            "09:50",
            "Reset",
            "Reset",
            kind="reset",
            staff_ks3="Lorelle",
            staff_ks4="Laurent",
        ),
    ]


def english_block(start: str = "09:50") -> dict:
    return row(
        start,
        m2t(t2m(start) + 45),
        "English",
        "English",
        kind="lesson",
        staff_ks3="Lorelle",
        staff_ks4="Laurent",
    )


def lunch_block() -> dict:
    return row("12:15", "12:30", "Lunch", "Lunch", kind="lesson")


def pe_block(start: str = "13:20", duration: int = 85) -> dict:
    return row(
        start,
        m2t(t2m(start) + duration),
        PE,
        PE,
        kind="pe",
        staff_ks3="Laurent",
        staff_ks4="Laurent",
    )


def build_monday() -> list[dict]:
    return [
        *arrival_checks_reset(),
        english_block(),
        row("10:35", "10:50", "Citizenship", "Break", kind="lesson", staff_ks3="Lloyd"),
        row(
            "10:50",
            "11:15",
            "Citizenship",
            "Maths",
            kind="lesson",
            staff_ks3="Lloyd",
            staff_ks4="Laurent",
        ),
        row("11:15", "11:35", "Break", "Maths", kind="lesson", staff_ks4="Laurent"),
        row(
            "11:35",
            "12:15",
            "Maths",
            "DofE",
            kind="lesson",
            staff_ks3="Lorelle",
            staff_ks4="Lloyd",
        ),
        lunch_block(),
        pe_block(),
        row("13:30", "13:45", "Break", "King's Trust", kind="lesson", staff_ks4="Lorelle"),
        row(
            "13:45",
            "14:30",
            "Lesson — TBC",
            "King's Trust",
            kind="lesson",
            staff_ks4="Lorelle",
        ),
        row("14:30", "14:45", "Lesson — TBC", "Break", kind="lesson"),
        row("14:45", "15:00", "Lesson — TBC", "Lesson — TBC", kind="lesson"),
    ]


def build_tuesday() -> list[dict]:
    return [
        *arrival_checks_reset(),
        row("09:50", "10:25", "Assembly", "Assembly", kind="assembly"),
        english_block("10:25"),
        row("11:10", "11:25", "Art", "Break", kind="lesson"),
        row("11:25", "12:05", "Art", "Maths", kind="lesson", staff_ks4="Laurent"),
        row(
            "12:05",
            "12:15",
            "Maths",
            "Maths",
            kind="lesson",
            staff_ks3="Lorelle",
            staff_ks4="Laurent",
        ),
        lunch_block(),
        pe_block(),
        row("13:30", "13:45", "Break", "Citizenship", kind="lesson", staff_ks4="Lloyd"),
        row(
            "13:45",
            "14:30",
            "Lesson — TBC",
            "Citizenship",
            kind="lesson",
            staff_ks4="Lloyd",
        ),
        row(
            "14:30",
            "15:00",
            "Lesson — TBC",
            "King's Trust",
            kind="lesson",
            staff_ks4="Lorelle",
        ),
    ]


def build_wednesday() -> list[dict]:
    return [
        row(
            "10:00",
            "10:35",
            "Reset",
            "Reset",
            kind="reset",
            staff_ks3="Lorelle",
            staff_ks4="Laurent",
        ),
        row(
            "10:35",
            "11:20",
            "English",
            "English",
            kind="lesson",
            staff_ks3="Lorelle",
            staff_ks4="Laurent",
        ),
        row("11:20", "11:35", "Art", "Break", kind="lesson"),
        row("11:35", "12:15", "Art", "Maths", kind="lesson", staff_ks4="Laurent"),
        row(
            "12:15",
            "12:30",
            "Maths",
            "Maths",
            kind="lesson",
            staff_ks3="Lorelle",
            staff_ks4="Laurent",
        ),
        lunch_block(),
        row("12:30", "13:10", "Art", "Citizenship", kind="lesson", staff_ks4="Lloyd"),
        row("13:10", "13:25", "Citizenship", "Break", kind="lesson", staff_ks3="Lloyd"),
        row(
            "13:25",
            "14:05",
            "Citizenship",
            "DofE",
            kind="lesson",
            staff_ks3="Lloyd",
            staff_ks4="Lloyd",
        ),
        row("14:05", "14:20", "Break", "DofE", kind="lesson", staff_ks4="Lloyd"),
        row("14:20", "15:00", "Lesson — TBC", "Lesson — TBC", kind="lesson"),
    ]


def build_thursday() -> list[dict]:
    return [
        *arrival_checks_reset(),
        english_block(),
        row("10:35", "10:50", "Citizenship", "Break", kind="lesson", staff_ks3="Lloyd"),
        row(
            "10:50",
            "11:30",
            "Citizenship",
            "Maths",
            kind="lesson",
            staff_ks3="Lloyd",
            staff_ks4="Laurent",
        ),
        row("11:30", "11:45", "Break", "Maths", kind="lesson", staff_ks4="Laurent"),
        row(
            "11:45",
            "12:15",
            "Maths",
            "DofE",
            kind="lesson",
            staff_ks3="Lorelle",
            staff_ks4="Lloyd",
        ),
        lunch_block(),
        pe_block(),
        row("13:30", "13:45", "Break", "King's Trust", kind="lesson", staff_ks4="Lorelle"),
        row(
            "13:45",
            "14:00",
            "Lesson — TBC",
            "King's Trust",
            kind="lesson",
            staff_ks4="Lorelle",
        ),
    ]


def build_friday() -> list[dict]:
    return [
        *arrival_checks_reset(),
        english_block(),
        row("10:35", "10:50", "Art", "Break", kind="lesson"),
        row("10:50", "11:30", "Art", "Maths", kind="lesson", staff_ks4="Laurent"),
        row("11:30", "11:45", "Break", "Maths", kind="lesson", staff_ks4="Laurent"),
        row(
            "11:45",
            "12:15",
            "Maths",
            "DofE",
            kind="lesson",
            staff_ks3="Lorelle",
            staff_ks4="Lloyd",
        ),
        lunch_block(),
        pe_block(),
        row("13:30", "13:45", "Break", "Citizenship", kind="lesson", staff_ks4="Lloyd"),
        row(
            "13:45",
            "14:00",
            "Lesson — TBC",
            "Citizenship",
            kind="lesson",
            staff_ks4="Lloyd",
        ),
    ]


def subject_total(rows: list[dict], stage: str, label: str) -> int:
    total = 0
    for r in rows:
        if r[stage] == label:
            total += t2m(r["end"]) - t2m(r["start"])
    return total


def validate(rows: list[dict], finish: str, day: str) -> list[str]:
    issues = []
    fin = t2m(finish)

    for stage in ("ks3", "ks4"):
        prev = None
        seen: dict[str, int] = {}
        for r in rows:
            s, e = t2m(r["start"]), t2m(r["end"])
            label = r[stage]
            if label not in ("Lesson — TBC", "Arrival", "Checks / late arrivals"):
                seen[label] = seen.get(label, 0) + (e - s)
            if prev is not None and s != prev:
                issues.append(f"{day} {stage}: gap {m2t(prev)}->{r['start']}")
            if label in ("Break", "Lunch", "Arrival", "Checks / late arrivals"):
                exp = DURATIONS.get(label)
                if exp and e - s != exp:
                    issues.append(
                        f"{day} {stage} {label}: {e-s}min not {exp} ({r['start']}-{r['end']})"
                    )
            prev = e
        if prev != fin:
            issues.append(f"{day} {stage}: ends {m2t(prev)} not {finish}")

        for label, total in seen.items():
            exp = DURATIONS.get(label)
            if exp and total != exp:
                issues.append(f"{day} {stage} {label}: total {total}min not {exp}")

    for r in rows:
        if r["ks3"] == "Lunch" or r["ks4"] == "Lunch":
            if r["ks3"] != "Lunch" or r["ks4"] != "Lunch":
                issues.append(f"{day}: lunch not aligned at {r['start']}")
            if r["start"] != "12:15" or r["end"] != "12:30":
                issues.append(f"{day}: lunch at {r['start']}-{r['end']} not 12:15-12:30")

    for i in range(len(rows) - 1):
        if rows[i]["end"] != rows[i + 1]["start"]:
            issues.append(f"{day}: row gap {rows[i]['end']}->{rows[i+1]['start']}")

    if day == "wednesday":
        if not any(r["ks3"] == "Break" and r["ks4"] != "Break" for r in rows) and not any(
            r["ks4"] == "Break" and r["ks3"] != "Break" for r in rows
        ):
            issues.append(f"{day}: breaks not staggered")

    if day in ("thursday", "friday"):
        if subject_total(rows, "ks4", "King's Trust") + subject_total(rows, "ks4", "Citizenship") < 40:
            pass

    return issues


def main() -> None:
    week = {
        "meta": {
            "assembly_day": "tuesday",
            "assembly_minutes": 35,
            "break_minutes": 15,
            "lunch_minutes": 15,
            "lunch_time": "12:15–12:30",
            "pe_label": PE,
            "pe_minutes_mon_tue": 85,
            "pe_minutes_thu_fri": 40,
            "reset_minutes": 35,
            "checks_window": "09:05–09:15",
            "core_placement": "Reset — first teaching block after checks; English then Maths; Tuesday: Reset → Assembly → English",
        },
        "days": {
            "monday": {
                "label": "Monday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "15:00",
                "rows": build_monday(),
            },
            "tuesday": {
                "label": "Tuesday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "15:00",
                "rows": build_tuesday(),
            },
            "wednesday": {
                "label": "Wednesday",
                "arrival_from": "10:00",
                "arrival_latest": None,
                "finish": "15:00",
                "staff_meeting": "09:00–10:00",
                "rows": build_wednesday(),
            },
            "thursday": {
                "label": "Thursday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "14:00",
                "rows": build_thursday(),
            },
            "friday": {
                "label": "Friday",
                "arrival_from": "08:50",
                "arrival_latest": "09:05",
                "finish": "14:00",
                "rows": build_friday(),
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
                "Food Technology": {"ks3": "Sacha", "ks4": "Sacha"},
            },
        },
    }

    all_issues = []
    for key, day in week["days"].items():
        all_issues.extend(validate(day["rows"], day["finish"], key))

    if all_issues:
        print("VALIDATION FAILED:")
        for i in all_issues:
            print(" -", i)
        raise SystemExit(1)

    OUT.write_text(json.dumps(week, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} — all days valid")


if __name__ == "__main__":
    main()
