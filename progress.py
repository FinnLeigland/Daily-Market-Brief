"""Daily Lesson progress: streak, XP, completed lessons and questions to review. Saved as JSON next to the app."""

import json
from datetime import date, timedelta
from pathlib import Path

PATH = Path(__file__).with_name("progress.json")
XP_PER_CORRECT = 5
XP_LESSON_BONUS = 10
DAILY_GOAL_XP = 20  # roughly one lesson


def load() -> dict:
    try:
        data = json.loads(PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return {
        "completed": data.get("completed", {}),  # lesson id -> date first completed
        "xp": data.get("xp", 0),
        "streak": data.get("streak", 0),
        "best_streak": data.get("best_streak", 0),
        "last_day": data.get("last_day"),  # last day with any activity (ISO date)
        "history": data.get("history", {}),  # ISO date -> XP earned that day
        "review": data.get("review", []),  # [lesson id, question index] pairs answered wrong
    }


def save(p: dict) -> None:
    PATH.write_text(json.dumps(p, indent=1))


def current_streak(p: dict, today: date) -> int:
    """The streak as of today: still alive if you were active today or yesterday, otherwise broken."""
    if not p["last_day"]:
        return 0
    last = date.fromisoformat(p["last_day"])
    return p["streak"] if (today - last).days <= 1 else 0


def _touch_streak(p: dict, today: date) -> None:
    last = date.fromisoformat(p["last_day"]) if p["last_day"] else None
    if last == today:
        return
    p["streak"] = p["streak"] + 1 if last == today - timedelta(days=1) else 1
    p["best_streak"] = max(p["best_streak"], p["streak"])
    p["last_day"] = today.isoformat()


def record_session(
    p: dict,
    today: date,
    correct: int,
    lesson_id: str | None = None,
    missed: list[tuple[str, int]] = (),
    cleared: list[tuple[str, int]] = (),
) -> int:
    """Record a finished lesson or review session. Returns the XP earned.

    The completion bonus is only paid the first time a lesson is finished, so replaying lessons
    still earns XP for correct answers but can't be farmed for bonuses.
    """
    xp = correct * XP_PER_CORRECT
    if lesson_id and lesson_id not in p["completed"]:
        p["completed"][lesson_id] = today.isoformat()
        xp += XP_LESSON_BONUS
    key = today.isoformat()
    p["history"][key] = p["history"].get(key, 0) + xp
    p["xp"] += xp
    review = [tuple(r) for r in p["review"]]
    for item in missed:
        if tuple(item) not in review:
            review.append(tuple(item))
    review = [r for r in review if r not in {tuple(c) for c in cleared}]
    p["review"] = [list(r) for r in review]
    _touch_streak(p, today)
    save(p)
    return xp


def today_xp(p: dict, today: date) -> int:
    return p["history"].get(today.isoformat(), 0)


def week(p: dict, today: date) -> list[tuple[date, bool]]:
    """Monday-to-Sunday of the current week, with whether each day had any activity."""
    monday = today - timedelta(days=today.weekday())
    return [(monday + timedelta(days=i), (monday + timedelta(days=i)).isoformat() in p["history"]) for i in range(7)]


def level(xp: int) -> tuple[int, int]:
    """(level, XP into the current level). Every 100 XP is a level."""
    return xp // 100 + 1, xp % 100
