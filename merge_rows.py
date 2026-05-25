#!/usr/bin/env python3
"""Merge consecutive timetable rows with the same subject + staff per KS group."""

from __future__ import annotations

SKIP_MERGE_LABELS = frozenset(
    {"Break", "Lunch", "Arrival", "Checks / Late Arrivals", "Assembly",
     "Student Searches", "Team Meeting", "Thrive"}
)


def _skip_merge(label: str) -> bool:
    if label in SKIP_MERGE_LABELS:
        return True
    if label.startswith("Break") or "Toilet Break" in label:
        return True
    return False


def stage_slot_key(row: dict, stage: str) -> tuple[str, str | None] | None:
    label = row[stage]
    if _skip_merge(label):
        return None
    return (label, row.get(f"staff_{stage}"))


def combine_labels(a: str, b: str) -> str:
    if a == b:
        return a
    return f"{a} · {b}"


def other_stage_compatible(prev: dict, curr: dict, merged_stage: str) -> bool:
    """Allow a lesson to span a break on the other key stage column."""
    other = "ks4" if merged_stage == "ks3" else "ks3"
    p, c = prev[other], curr[other]
    if p == c:
        return True
    if merged_stage == "ks4":
        return _skip_merge(p) or _skip_merge(c)
    if _skip_merge(p) or _skip_merge(c):
        return False
    return True


def try_merge_rows(prev: dict, curr: dict) -> dict | None:
    if prev["end"] != curr["start"]:
        return None

    merge_ks3 = (
        (k3 := stage_slot_key(prev, "ks3")) is not None
        and k3 == stage_slot_key(curr, "ks3")
        and other_stage_compatible(prev, curr, "ks3")
    )
    merge_ks4 = (
        (k4 := stage_slot_key(prev, "ks4")) is not None
        and k4 == stage_slot_key(curr, "ks4")
        and other_stage_compatible(prev, curr, "ks4")
    )
    if not merge_ks3 and not merge_ks4:
        return None

    merged = dict(prev)
    merged["end"] = curr["end"]

    if not merge_ks3:
        if prev["ks3"] != curr["ks3"]:
            merged["ks3"] = combine_labels(prev["ks3"], curr["ks3"])
        sk3 = "staff_ks3"
        if prev.get(sk3) != curr.get(sk3):
            merged.pop(sk3, None)
        elif curr.get(sk3):
            merged[sk3] = curr[sk3]

    if not merge_ks4:
        if prev["ks4"] != curr["ks4"]:
            merged["ks4"] = combine_labels(prev["ks4"], curr["ks4"])
        sk4 = "staff_ks4"
        if prev.get(sk4) != curr.get(sk4):
            merged.pop(sk4, None)
        elif curr.get(sk4):
            merged[sk4] = curr[sk4]

    if curr.get("kind") and not merged.get("kind"):
        merged["kind"] = curr["kind"]

    return merged


def merge_consecutive_rows(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    out: list[dict] = [dict(rows[0])]
    for row in rows[1:]:
        prev = out[-1]
        merged = try_merge_rows(prev, row)
        if merged is not None:
            out[-1] = merged
        else:
            out.append(dict(row))
    return out
