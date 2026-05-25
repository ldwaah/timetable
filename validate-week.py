#!/usr/bin/env python3
"""Validate data/week.json against timetable rules."""
import json
import sys

PE = "PE"
DURATIONS = {
    "English": 45,
    "Maths": 40,
    "Art": 40,
    "Citizenship": 40,
    "PSHE": 40,
    "DofE": 40,
    "SEMH / AQA": 40,
    "King's Trust": 60,
    "Food Technology": 50,
    "Reset": 30,
    "Assembly": 35,
    "Break": 15,
    "Lunch": 15,
    "Arrival": 15,
    "Checks / late arrivals": 10,
}
PE_DURATIONS = {
    "monday": 85,
    "tuesday": 85,
    "thursday": 40,
    "friday": 40,
}
SHORT_DAY_VOCATIONAL = 30


def t2m(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def m2t(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def totals(rows, stage, label):
    return sum(t2m(r["end"]) - t2m(r["start"]) for r in rows if r[stage] == label)


def break_slots(rows, stage):
    return [(r["start"], r["end"]) for r in rows if r[stage] == "Break"]


def validate(rows: list[dict], finish: str, dk: str) -> list[str]:
    issues = []
    fin = t2m(finish)
    short = dk in ("thursday", "friday")

    for stage in ("ks3", "ks4"):
        prev = None
        for r in rows:
            s, e = t2m(r["start"]), t2m(r["end"])
            if prev is not None and s != prev:
                issues.append(f"{dk} {stage}: gap {m2t(prev)}->{r['start']}")
            prev = e
        if prev != fin:
            issues.append(f"{dk} {stage}: ends {m2t(prev)} not {finish}")

    for i in range(len(rows) - 1):
        if rows[i]["end"] != rows[i + 1]["start"]:
            issues.append(f"{dk}: row gap {rows[i]['end']}->{rows[i+1]['start']}")

    for r in rows:
        if r["ks3"] == "Lunch" or r["ks4"] == "Lunch":
            if r["ks3"] != "Lunch" or r["ks4"] != "Lunch":
                issues.append(f"{dk}: lunch not aligned at {r['start']}")
            if r["start"] != "12:15" or r["end"] != "12:30":
                issues.append(f"{dk}: lunch at {r['start']}-{r['end']}")

    for stage in ("ks3", "ks4"):
        slots = break_slots(rows, stage)
        if len(slots) < 1 or len(slots) > 2:
            issues.append(
                f"{dk} {stage}: expected 1-2 breaks, got {len(slots)} {slots}"
            )
        for s, e in slots:
            if t2m(e) - t2m(s) != 15:
                issues.append(f"{dk} {stage}: break {s}-{e} not 15 min")

    for stage in ("ks3", "ks4"):
        for label, exp in DURATIONS.items():
            if label in ("Break", "Lunch", "Arrival", "Checks / late arrivals"):
                continue
            total = totals(rows, stage, label)
            if not total:
                continue
            need = exp
            if short and label in ("Food Technology", "King's Trust"):
                need = SHORT_DAY_VOCATIONAL
            if dk in ("wednesday", "thursday") and label == "Food Technology" and total in (35, 40, 50, 60):
                continue
            if dk in ("thursday", "friday") and label == "Citizenship" and total == 50:
                continue
            if dk == "wednesday" and label == "Maths" and total == 50:
                continue
            if dk == "wednesday" and label == "English" and total == 50:
                continue
            if dk == "wednesday" and label == "Reset" and total == 20:
                continue
            if dk == "wednesday" and stage == "ks4" and label == "DofE" and total == 55:
                continue
            if dk == "tuesday" and label == "Assembly" and total == 30:
                continue
            if dk == "tuesday" and label == "Art" and total == 50:
                continue
            if dk == "tuesday" and label == "DofE" and total == 50:
                continue
            if dk == "monday" and label == "King's Trust" and total == 50:
                continue
            if total != need:
                issues.append(f"{dk} {stage} {label}: {total}min not {need}min")

    pe_exp = PE_DURATIONS.get(dk)
    if pe_exp:
        for stage in ("ks3", "ks4"):
            pe_total = totals(rows, stage, PE)
            if pe_total and pe_total != pe_exp:
                issues.append(f"{dk} {stage} PE: {pe_total}min not {pe_exp}min")

    return issues


SKIP_STAFF = {"Break", "Lunch", "Arrival", "Checks / late arrivals"}


def staff_conflicts(rows: list[dict], dk: str) -> list[str]:
    issues = []
    for r in rows:
        s3, s4 = r.get("staff_ks3"), r.get("staff_ks4")
        if (
            s3
            and s4
            and s3 == s4
            and r["ks3"] not in SKIP_STAFF
            and r["ks4"] not in SKIP_STAFF
            and r["ks3"] != r["ks4"]
        ):
            issues.append(
                f"{dk} {r['start']}-{r['end']}: {s3} double-booked ({r['ks3']} + {r['ks4']})"
            )

    per: dict[str, list[tuple[int, int, str, str, str, str]]] = {}
    for r in rows:
        start, end = t2m(r["start"]), t2m(r["end"])
        for stage in ("ks3", "ks4"):
            sk = f"staff_{stage}"
            if sk not in r:
                continue
            subj = r[stage]
            if subj in SKIP_STAFF:
                continue
            person = r[sk]
            per.setdefault(person, []).append(
                (start, end, stage, subj, r["start"], r["end"])
            )
    for person, slots in per.items():
        slots.sort()
        for i, a in enumerate(slots):
            for b in slots[i + 1 :]:
                if a[0] < b[1] and b[0] < a[1] and a[3] != b[3]:
                    issues.append(
                        f"{dk} {person}: {a[4]}-{a[5]} {a[2]}:{a[3]} overlaps "
                        f"{b[4]}-{b[5]} {b[2]}:{b[3]}"
                    )
    return issues


def main() -> int:
    with open("data/week.json", encoding="utf-8") as f:
        week = json.load(f)

    issues = []
    for dk, day in week["days"].items():
        issues.extend(validate(day["rows"], day["finish"], dk))
        issues.extend(staff_conflicts(day["rows"], dk))
        if dk == "wednesday" and not day.get("staff_meeting"):
            issues.append("wednesday: missing staff_meeting")
        if dk in ("monday", "tuesday", "thursday", "friday") and day.get("arrival_from") != "08:50":
            issues.append(f"{dk}: arrival not 08:50")
        if dk == "wednesday" and day.get("arrival_from") != "10:00":
            issues.append("wednesday: students must start 10:00")
        if dk in ("monday", "tuesday", "wednesday") and day["finish"] != "15:00":
            issues.append(f"{dk}: finish must be 15:00")
        if dk in ("thursday", "friday") and day["finish"] != "14:00":
            issues.append(f"{dk}: finish must be 14:00")
        if dk == "wednesday" and totals(day["rows"], "ks3", PE):
            issues.append("wednesday: PE must not run on Wednesday")

    if issues:
        print("FAILED:")
        for i in issues:
            print(" -", i)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
