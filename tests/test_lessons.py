"""Tests for Daily Lesson progress (streak, XP, review queue), the curriculum's integrity, and headline matching."""

from datetime import date, timedelta

import pytest

import config
import data
import progress as P
from lessons_content import BY_ID, LESSONS, UNITS

MON = date(2026, 10, 5)


@pytest.fixture
def p(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "PATH", tmp_path / "progress.json")
    return P.load()


# ---------- Streak and XP ----------


def test_new_learner_starts_at_zero(p):
    assert P.current_streak(p, MON) == 0
    assert p["xp"] == 0


def test_first_lesson_starts_a_streak_and_pays_the_bonus(p):
    xp = P.record_session(p, MON, correct=3, lesson_id="compounding")
    assert xp == 3 * P.XP_PER_CORRECT + P.XP_LESSON_BONUS
    assert P.current_streak(p, MON) == 1
    assert "compounding" in p["completed"]


def test_consecutive_days_grow_the_streak(p):
    for i, lid in enumerate(["compounding", "real-returns", "index-funds"]):
        P.record_session(p, MON + timedelta(days=i), correct=3, lesson_id=lid)
    assert P.current_streak(p, MON + timedelta(days=2)) == 3
    assert p["best_streak"] == 3


def test_two_lessons_on_one_day_count_once(p):
    P.record_session(p, MON, correct=3, lesson_id="compounding")
    P.record_session(p, MON, correct=3, lesson_id="real-returns")
    assert P.current_streak(p, MON) == 1


def test_streak_survives_until_the_end_of_the_next_day(p):
    P.record_session(p, MON, correct=2, lesson_id="compounding")
    assert P.current_streak(p, MON + timedelta(days=1)) == 1  # haven't done today's yet, still alive
    assert P.current_streak(p, MON + timedelta(days=2)) == 0  # missed a whole day


def test_missing_a_day_resets_the_streak_but_keeps_the_best(p):
    P.record_session(p, MON, correct=3, lesson_id="compounding")
    P.record_session(p, MON + timedelta(days=1), correct=3, lesson_id="real-returns")
    P.record_session(p, MON + timedelta(days=4), correct=3, lesson_id="index-funds")
    assert P.current_streak(p, MON + timedelta(days=4)) == 1
    assert p["best_streak"] == 2


def test_replaying_a_lesson_earns_answers_but_not_the_bonus_again(p):
    P.record_session(p, MON, correct=3, lesson_id="compounding")
    again = P.record_session(p, MON, correct=3, lesson_id="compounding")
    assert again == 3 * P.XP_PER_CORRECT


def test_missed_questions_enter_review_and_leave_when_answered(p):
    P.record_session(p, MON, correct=2, lesson_id="compounding", missed=[("compounding", 1)])
    assert p["review"] == [["compounding", 1]]
    P.record_session(p, MON, correct=1, cleared=[("compounding", 1)])
    assert p["review"] == []


def test_the_same_miss_is_only_queued_once(p):
    P.record_session(p, MON, correct=0, lesson_id="compounding", missed=[("compounding", 0)])
    P.record_session(p, MON, correct=0, missed=[("compounding", 0)])
    assert p["review"] == [["compounding", 0]]


def test_progress_is_saved_and_reloaded(p):
    P.record_session(p, MON, correct=3, lesson_id="compounding")
    reloaded = P.load()
    assert reloaded["xp"] == p["xp"] and reloaded["completed"] == p["completed"]


def test_week_runs_monday_to_sunday_and_marks_active_days(p):
    P.record_session(p, MON + timedelta(days=2), correct=1, lesson_id="compounding")  # Wednesday
    week = P.week(p, MON + timedelta(days=3))
    assert [d.weekday() for d, _ in week] == list(range(7))
    assert [active for _, active in week] == [False, False, True, False, False, False, False]


def test_levels_every_100_xp():
    assert P.level(0) == (1, 0)
    assert P.level(250) == (3, 50)


# ---------- Curriculum integrity ----------


def test_curriculum_has_seven_units_of_four_lessons():
    assert len(UNITS) == 7
    assert all(len(u["lessons"]) == 4 for u in UNITS)
    assert len(LESSONS) == 28


def test_lesson_ids_are_unique():
    assert len(BY_ID) == len(LESSONS)


@pytest.mark.parametrize("lesson", LESSONS, ids=lambda lesson: lesson["id"])
def test_every_lesson_is_complete(lesson):
    assert 2 <= len(lesson["cards"]) <= 4
    assert lesson["takeaway"] and lesson["try"]
    assert len(lesson["questions"]) == 3
    for q in lesson["questions"]:
        assert 2 <= len(q["options"]) <= 4
        assert 0 <= q["answer"] < len(q["options"])
        assert len(set(q["options"])) == len(q["options"]), "duplicate options"
        assert q["why"], "every question explains its answer"


# ---------- Headline keyword matching ----------


@pytest.mark.parametrize(
    "title, keywords, expected",
    [
        ("Nvidia says AI demand is strong", ["ai"], True),
        ("Fed official said rates stay high", ["ai"], False),  # "ai" inside "said"
        ("AMD shares rise", ["amd"], True),
        ("Diamond prices slump", ["amd"], False),
        ("Refinery margins jump", ["refin"], True),  # long keywords match as prefixes
        ("Federal Reserve holds rates", ["federal"], True),
    ],
)
def test_keyword_match(title, keywords, expected):
    assert data.keyword_match(title, keywords) is expected


def test_six_featured_sectors_including_ai_and_without_health_care():
    names = [s["name"] for s in config.FEATURED_SECTORS]
    assert len(names) == 6
    assert "Artificial Intelligence" in names
    assert "Health Care" not in names
