#!/usr/bin/env python3
"""Find workouts by two users that likely happened together."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


def activity_ids(workout: dict[str, Any]) -> set[str]:
    exercises = workout.get("exercises") or []
    return {str(e["exercise_template_id"]) for e in exercises if e.get("exercise_template_id")}


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def local_time(workout: dict[str, Any], timezone: ZoneInfo) -> datetime:
    timestamp = workout.get("start_time") or workout.get("end_time")
    if timestamp is None:
        raise ValueError(f"Workout {workout.get('id', '<unknown>')} has no timestamp")
    return datetime.fromtimestamp(float(timestamp), tz=timezone)


def workout_summary(workout: dict[str, Any], when: datetime) -> dict[str, Any]:
    return {
        "id": workout.get("id"),
        "short_id": workout.get("short_id"),
        "username": workout.get("username"),
        "name": workout.get("name"),
        "start_time": when.isoformat(),
        "activity_ids": sorted(activity_ids(workout)),
    }


def find_matches(
    left: list[dict[str, Any]],
    right: list[dict[str, Any]],
    timezone: ZoneInfo,
    max_hours: float,
    min_activity: float,
) -> list[dict[str, Any]]:
    candidates: list[tuple[float, int, int, dict[str, Any]]] = []
    max_seconds = max_hours * 3600

    for left_index, left_workout in enumerate(left):
        left_time = local_time(left_workout, timezone)
        for right_index, right_workout in enumerate(right):
            right_time = local_time(right_workout, timezone)
            if left_time.date() != right_time.date():
                continue
            seconds = abs((left_time - right_time).total_seconds())
            if seconds > max_seconds:
                continue
            left_ids = activity_ids(left_workout)
            right_ids = activity_ids(right_workout)
            similarity = jaccard(left_ids, right_ids)
            if similarity < min_activity:
                continue
            time_score = 1.0 - seconds / max_seconds
            score = 0.65 * similarity + 0.35 * time_score
            common_ids = left_ids & right_ids
            result = {
                "score": round(score, 4),
                "time_difference_minutes": round(seconds / 60, 1),
                "activity_id_similarity": round(similarity, 4),
                "common_activity_ids": sorted(common_ids),
                "left": workout_summary(left_workout, left_time),
                "right": workout_summary(right_workout, right_time),
            }
            candidates.append((score, left_index, right_index, result))

    matches: list[dict[str, Any]] = []
    used_left: set[int] = set()
    used_right: set[int] = set()
    for _, left_index, right_index, result in sorted(candidates, reverse=True):
        if left_index not in used_left and right_index not in used_right:
            used_left.add(left_index)
            used_right.add(right_index)
            matches.append(result)
    return sorted(matches, key=lambda item: item["left"]["start_time"], reverse=True)


def load_workouts(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path, help="First user's workout JSON")
    parser.add_argument("right", type=Path, help="Second user's workout JSON")
    parser.add_argument("-o", "--output", type=Path, default=Path("workout_matches.json"))
    parser.add_argument("--timezone", default="Europe/Zurich")
    parser.add_argument("--max-hours", type=float, default=4.0)
    parser.add_argument("--min-activity", type=float, default=0.25)
    args = parser.parse_args()

    if args.max_hours <= 0:
        parser.error("--max-hours must be greater than zero")
    if not 0 <= args.min_activity <= 1:
        parser.error("--min-activity must be between zero and one")

    matches = find_matches(
        load_workouts(args.left), load_workouts(args.right), ZoneInfo(args.timezone),
        args.max_hours, args.min_activity,
    )
    report = {
        "match_count": len(matches),
        "settings": {
            "timezone": args.timezone,
            "max_hours": args.max_hours,
            "min_activity_similarity": args.min_activity,
        },
        "matches": matches,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Found {len(matches)} matches; wrote {args.output}")


if __name__ == "__main__":
    main()
