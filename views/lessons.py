"""Daily Lesson: a five-minute, Duolingo-style lesson on one investing concept, with a streak and XP."""

from datetime import date
from html import escape

import streamlit as st

import config
import progress as P
from lessons_content import BY_ID, LESSONS, UNITS
from theme import html

DAYS = ["M", "T", "W", "T", "F", "S", "S"]


# ---------- Session state for a running lesson ----------


def _plan(mode: str, lesson_id: str | None, review: list | None = None) -> list[tuple]:
    if mode == "review":
        return [("q", lid, qi) for lid, qi in review] + [("done",)]
    lesson = BY_ID[lesson_id]
    return (
        [("card", i) for i in range(len(lesson["cards"]))]
        + [("q", lesson_id, qi) for qi in range(len(lesson["questions"]))]
        + [("try",), ("done",)]
    )


def _start(mode: str, lesson_id: str | None = None) -> None:
    review = [tuple(r) for r in P.load()["review"]][:6] if mode == "review" else None
    st.session_state["lesson_run"] = {
        "mode": mode,
        "lesson_id": lesson_id,
        "plan": _plan(mode, lesson_id, review),
        "step": 0,
        "answers": {},
        "correct": 0,
        "missed": [],
        "cleared": [],
        "xp": None,
    }


def _next() -> None:
    st.session_state["lesson_run"]["step"] += 1


def _quit() -> None:
    st.session_state["lesson_run"] = None


def _answer(step: int, lid: str, qi: int, choice: int) -> None:
    run = st.session_state["lesson_run"]
    if str(step) in run["answers"]:
        return
    run["answers"][str(step)] = choice
    if choice == BY_ID[lid]["questions"][qi]["answer"]:
        run["correct"] += 1
        run["cleared"].append((lid, qi))
    else:
        run["missed"].append((lid, qi))


# ---------- Home: stats, today's lesson, the path ----------


def _next_lesson(p: dict) -> dict | None:
    return next((lesson for lesson in LESSONS if lesson["id"] not in p["completed"]), None)


def _home(p: dict, today: date) -> None:
    streak = P.current_streak(p, today)
    lvl, into = P.level(p["xp"])
    goal = min(P.today_xp(p, today) / P.DAILY_GOAL_XP, 1.0)
    done = len(p["completed"])
    week = "".join(
        f'<div class="day {"on" if active else ""} {"today" if d == today else ""}"><span>{DAYS[i]}</span></div>'
        for i, (d, active) in enumerate(P.week(p, today))
    )
    html(f"""
    <div class="lesson-stats">
      <div class="stat streak {"lit" if streak else ""}"><div class="big">{streak}</div><div class="k">day streak</div>
        <div class="d">Best: {p["best_streak"]}</div></div>
      <div class="stat"><div class="big">{p["xp"]}</div><div class="k">XP · level {lvl}</div>
        <div class="bar"><div style="width:{into}%"></div></div></div>
      <div class="stat"><div class="big">{done}<span>/{len(LESSONS)}</span></div><div class="k">lessons done</div>
        <div class="bar"><div style="width:{done / len(LESSONS) * 100:.0f}%"></div></div></div>
      <div class="stat"><div class="big">{"✓" if goal >= 1 else f"{goal * 100:.0f}%"}</div><div class="k">today's goal</div>
        <div class="bar goal"><div style="width:{goal * 100:.0f}%"></div></div></div>
      <div class="stat week"><div class="k">This week</div><div class="days">{week}</div></div>
    </div>
    """)

    nxt = _next_lesson(p)
    left, right = st.columns([1.6, 1], gap="large")
    with left:
        if nxt:
            met = goal >= 1
            html(f"""
            <div class="today-card">
              <div class="eyebrow">{"Goal met. Bonus lesson" if met else "Today's lesson"} · Unit {nxt["unit"] + 1}: {escape(nxt["unit_title"])}</div>
              <div class="today-title">{escape(nxt["title"])}</div>
              <p>{escape(nxt["takeaway"])}</p>
              <div class="meta">~5 minutes · {len(nxt["cards"])} cards · {len(nxt["questions"])} questions · up to
                {len(nxt["questions"]) * P.XP_PER_CORRECT + P.XP_LESSON_BONUS} XP</div>
            </div>""")
            st.button(
                "Keep going" if met else "Start lesson",
                key="start_lesson",
                type="primary",
                icon=":material/play_arrow:",
                on_click=_start,
                args=("lesson", nxt["id"]),
            )
        else:
            html(
                '<div class="today-card"><div class="eyebrow">Course complete</div><div class="today-title">'
                "You've finished all 28 lessons</div><p>Replay any lesson from the path, or clear your review "
                "queue to keep your streak going.</p></div>"
            )
    with right:
        n_review = len(p["review"])
        html(
            f'<div class="review-card"><div class="eyebrow">Practice</div><div class="big">{n_review}</div>'
            f"<p>{'question to review' if n_review == 1 else 'questions to review'}. Questions you miss come back "
            "here until you get them right.</p></div>"
        )
        st.button(
            "Review mistakes",
            key="start_review",
            icon=":material/replay:",
            disabled=not n_review,
            on_click=_start,
            args=("review",),
        )

    # The path
    current_id = nxt["id"] if nxt else None
    for u, unit in enumerate(UNITS):
        n_done = sum(lesson["id"] in p["completed"] for lesson in unit["lessons"])
        html(
            f'<div class="unit-head"><div><div class="eyebrow">Unit {u + 1}</div><div class="h2">{escape(unit["title"])}</div>'
            f'<p>{escape(unit["blurb"])}</p></div><div class="count">{n_done}/{len(unit["lessons"])}</div></div>'
        )
        cols = st.columns(len(unit["lessons"]))
        for i, (col, lesson) in enumerate(zip(cols, unit["lessons"], strict=True)):
            state = "done" if lesson["id"] in p["completed"] else "current" if lesson["id"] == current_id else "locked"
            with col:
                st.button(
                    "✓" if state == "done" else str(u * 4 + i + 1),
                    key=f"node_{state}_{lesson['id']}",
                    disabled=state == "locked",
                    on_click=_start,
                    args=("lesson", lesson["id"]),
                    help={
                        "done": "Replay this lesson",
                        "current": "Start this lesson",
                        "locked": "Finish the lessons before this one",
                    }[state],
                )
                html(f'<div class="node-label {state}">{escape(lesson["title"])}</div>')


# ---------- A running lesson ----------


def _run(run: dict, p: dict, today: date) -> None:
    plan, step = run["plan"], run["step"]
    kind = plan[step][0]
    _, mid, _ = st.columns([1, 2.4, 1])
    with mid:
        top_l, top_r = st.columns([6, 1])
        with top_l:
            st.progress(min(step / (len(plan) - 1), 1.0))
        with top_r:
            st.button("Quit", key="lesson_quit", type="tertiary", on_click=_quit, icon=":material/close:")

        lesson = BY_ID[run["lesson_id"]] if run["lesson_id"] else None
        eyebrow = (
            f"Unit {lesson['unit'] + 1} · {escape(lesson['title'])}" if lesson else "Practice · questions you missed"
        )

        if kind == "card":
            i = plan[step][1]
            html(
                f'<div class="lesson-step"><div class="eyebrow">{eyebrow} · {i + 1} of {len(lesson["cards"])}</div>'
                f'<div class="card-text">{escape(lesson["cards"][i])}</div></div>'
            )
            st.button("Continue", key=f"next_{step}", type="primary", on_click=_next, width="stretch")

        elif kind == "q":
            _, lid, qi = plan[step]
            q = BY_ID[lid]["questions"][qi]
            html(
                f'<div class="lesson-step"><div class="eyebrow">{eyebrow}</div><div class="q-text">{escape(q["q"])}</div></div>'
            )
            chosen = run["answers"].get(str(step))
            if chosen is None:
                for oi, opt in enumerate(q["options"]):
                    st.button(opt, key=f"opt_{step}_{oi}", on_click=_answer, args=(step, lid, qi, oi), width="stretch")
            else:
                right = chosen == q["answer"]
                opts = "".join(
                    f'<div class="opt {"right" if oi == q["answer"] else "wrong" if oi == chosen else ""}">{escape(opt)}</div>'
                    for oi, opt in enumerate(q["options"])
                )
                html(
                    f'<div class="opts">{opts}</div><div class="feedback {"right" if right else "wrong"}">'
                    f"<b>{'Correct!' if right else 'Not quite.'}</b> {escape(q['why'])}"
                    f"{'' if right else ' This one will come back in your review.'}</div>"
                )
                st.button("Continue", key=f"next_{step}", type="primary", on_click=_next, width="stretch")

        elif kind == "try":
            html(f"""
            <div class="lesson-step"><div class="eyebrow">{eyebrow} · use it</div>
              <div class="takeaway"><span>Remember</span>{escape(lesson["takeaway"])}</div>
              <div class="try"><span>Try it today</span>{escape(lesson["try"])}</div>
            </div>""")
            st.button("Finish lesson", key=f"next_{step}", type="primary", on_click=_next, width="stretch")

        else:  # done
            if run["xp"] is None:  # record exactly once
                streak_before = P.current_streak(p, today)
                run["xp"] = P.record_session(
                    p,
                    today,
                    run["correct"],
                    lesson_id=run["lesson_id"] if run["mode"] == "lesson" else None,
                    missed=run["missed"],
                    cleared=run["cleared"],
                )
                run["streak_up"] = P.current_streak(p, today) > streak_before
            total = sum(1 for s in plan if s[0] == "q")
            streak = P.current_streak(p, today)
            html(f"""
            <div class="lesson-done">
              <div class="eyebrow">{"Lesson complete" if run["mode"] == "lesson" else "Review complete"}</div>
              <div class="xp">+{run["xp"]} XP</div>
              <div class="row">
                <div><div class="big">{run["correct"]}/{total}</div><div class="k">correct</div></div>
                <div><div class="big">{streak}</div><div class="k">{"day streak" + (" · +1 today" if run.get("streak_up") else "")}</div></div>
                <div><div class="big">{len(p["review"])}</div><div class="k">left to review</div></div>
              </div>
            </div>""")
            nxt = _next_lesson(p)
            a, b = st.columns(2)
            with a:
                st.button("Back to your path", key="lesson_home", on_click=_quit, width="stretch")
            with b:
                if nxt:
                    st.button(
                        f"Next: {nxt['title']}",
                        key="lesson_next",
                        type="primary",
                        on_click=_start,
                        args=("lesson", nxt["id"]),
                        width="stretch",
                    )


def render() -> None:
    today = config.today_et()
    p = P.load()
    run = st.session_state.get("lesson_run")
    if run:
        _run(run, p, today)
    else:
        _home(p, today)
