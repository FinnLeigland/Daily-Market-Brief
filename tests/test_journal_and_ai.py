"""Tests for journal storage, the AI explanation parsing/caching, and small data helpers."""

import json
import types

import pandas as pd
import pytest

import ai
import data
import journal as J

# ---------- Journal ----------


@pytest.fixture
def jr(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "PATH", tmp_path / "journal.json")
    return J.load()


def _add(jr, ticker="NVDA", **kw):
    fields = dict(
        ticker=ticker,
        shares=10,
        entry_price=100.0,
        entry_date="2026-01-02",
        target=150.0,
        stop=85.0,
        conviction=4,
        horizon="1–2 years",
        thesis="Demand keeps compounding.",
        wrong_if="Margins fall below 60%.",
    )
    return J.add_position(jr, **{**fields, **kw})


def test_empty_journal_when_no_file(jr):
    assert jr == {"positions": [], "notes": [], "watchlist": []}


def test_corrupt_file_falls_back_to_empty(tmp_path, monkeypatch):
    path = tmp_path / "journal.json"
    path.write_text("{not json")
    monkeypatch.setattr(J, "PATH", path)
    assert J.load() == {"positions": [], "notes": [], "watchlist": []}


def test_adding_a_position_saves_it_with_an_opening_note(jr):
    pos = _add(jr)
    saved = J.load()
    assert saved["positions"][0]["id"] == pos["id"]
    assert saved["positions"][0]["status"] == "open"
    assert saved["notes"][0]["kind"] == "open"
    assert "Demand keeps compounding." in saved["notes"][0]["text"]


def test_update_changes_only_the_named_position(jr):
    a, b = _add(jr, "NVDA"), _add(jr, "PLD")
    J.update_position(jr, a["id"], target=180.0)
    saved = {p["ticker"]: p for p in J.load()["positions"]}
    assert saved["NVDA"]["target"] == 180.0
    assert saved["PLD"]["target"] == 150.0
    assert b["id"] != a["id"]


def test_deleting_the_last_position_in_a_ticker_removes_its_notes(jr):
    a = _add(jr, "NVDA")
    _add(jr, "PLD")
    J.delete_position(jr, a["id"])
    saved = J.load()
    assert [p["ticker"] for p in saved["positions"]] == ["PLD"]
    assert {n["ticker"] for n in saved["notes"]} == {"PLD"}


# ---------- AI explanations ----------

EVENT = {
    "day": "2026-08-27",
    "ret": 8.7,
    "bench": 0.7,
    "earnings": {"Reported EPS": 2.22, "EPS Estimate": 2.09},
    "news": [{"title": "Nvidia jumps after earnings", "source": "Reuters", "published": pd.Timestamp("2026-08-27")}],
}


@pytest.fixture
def ai_env(tmp_path, monkeypatch):
    """A fake API key, an isolated cache file, and a stub client that records requests."""
    monkeypatch.setattr(ai, "CACHE", tmp_path / "explanations.json")
    monkeypatch.setattr(ai, "_api_key", lambda: "sk-test")
    monkeypatch.setattr(ai.st, "session_state", {})
    calls = []

    def respond(text, stop_reason="end_turn"):
        reply = types.SimpleNamespace(stop_reason=stop_reason, content=[types.SimpleNamespace(type="text", text=text)])

        def create(**kwargs):
            calls.append(kwargs)
            return reply

        stub = types.SimpleNamespace(beta=types.SimpleNamespace(messages=types.SimpleNamespace(create=create)))
        monkeypatch.setattr(ai, "_client", lambda key: stub)

    return types.SimpleNamespace(calls=calls, respond=respond)


def test_explanations_are_parsed_and_cached(ai_env):
    ai_env.respond(
        json.dumps({"events": [{"day": "2026-08-27", "tag": "Earnings Beat", "summary": "Beat on AI demand."}]})
    )
    out = ai.explain_moves("NVDA", "NVIDIA Corporation", [EVENT])
    assert out == {"2026-08-27": {"tag": "Earnings Beat", "summary": "Beat on AI demand."}}
    assert json.loads(ai.CACHE.read_text())["NVDA:2026-08-27"]["tag"] == "Earnings Beat"


def test_cached_moves_are_not_sent_to_the_api_again(ai_env):
    ai_env.respond(json.dumps({"events": [{"day": "2026-08-27", "tag": "Earnings Beat", "summary": "x"}]}))
    ai.explain_moves("NVDA", "NVIDIA", [EVENT])
    ai.explain_moves("NVDA", "NVIDIA", [EVENT])
    assert len(ai_env.calls) == 1


def test_request_uses_structured_output_and_fallbacks(ai_env):
    ai_env.respond(json.dumps({"events": []}))
    ai.explain_moves("NVDA", "NVIDIA", [EVENT])
    req = ai_env.calls[0]
    assert req["model"] == ai.MODEL
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert req["fallbacks"] == "default"
    assert "Nvidia jumps after earnings" in req["messages"][0]["content"]


def test_refusal_falls_back_to_keyword_labels(ai_env):
    ai_env.respond("", stop_reason="refusal")
    assert ai.explain_moves("NVDA", "NVIDIA", [EVENT]) == {}


def test_malformed_json_falls_back_to_keyword_labels(ai_env):
    ai_env.respond("not json")
    assert ai.explain_moves("NVDA", "NVIDIA", [EVENT]) == {}


def test_long_tags_are_trimmed_for_the_chart(ai_env):
    ai_env.respond(json.dumps({"events": [{"day": "2026-08-27", "tag": "A" * 60, "summary": "s"}]}))
    assert len(ai.explain_moves("NVDA", "NVIDIA", [EVENT])["2026-08-27"]["tag"]) == 28


def test_no_api_call_without_a_key(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "CACHE", tmp_path / "explanations.json")
    monkeypatch.setattr(ai, "_api_key", lambda: None)
    monkeypatch.setattr(ai, "_client", lambda key: pytest.fail("should not create a client"))
    assert ai.explain_moves("NVDA", "NVIDIA", [EVENT]) == {}
    assert ai.disabled_reason() == "no_key"


# ---------- Data helpers ----------


@pytest.mark.parametrize(
    "name, short",
    [
        ("NVIDIA Corporation", "NVIDIA"),
        ("Apple Inc.", "Apple"),
        ("JPMorgan Chase & Co.", "JPMorgan Chase"),
        ("Prologis, Inc.", "Prologis"),
        ("Costco Wholesale Corporation", "Costco Wholesale"),
    ],
)
def test_short_company_names_for_news_search(name, short):
    assert data.short_name(name) == short


def test_duplicate_headlines_are_removed_newest_first():
    t = pd.Timestamp
    items = [
        {"title": "Fed holds rates steady", "published": t("2026-10-01", tz="UTC")},
        {"title": "Fed Holds Rates Steady!", "published": t("2026-10-02", tz="UTC")},
        {"title": "Oil jumps", "published": t("2026-09-30", tz="UTC")},
    ]
    out = data._dedupe(items)
    assert [i["title"] for i in out] == ["Fed Holds Rates Steady!", "Oil jumps"]


def test_wrong_pins_are_limited_across_sessions(monkeypatch):
    """Refreshing the page starts a new session; the server-wide guard still locks the gate."""
    import streamlit as st

    from views import desk

    monkeypatch.setattr(desk, "_guard", {"fails": 0, "until": 0.0})
    for _ in range(desk.GLOBAL_MAX_FAILS):
        fresh = {"desk_pin_input": "0000"}  # a brand-new session for every guess
        monkeypatch.setattr(st, "session_state", fresh)
        desk._try_unlock()
    assert desk._guard["until"] > 0
    right = {"desk_pin_input": "2222"}
    monkeypatch.setattr(st, "session_state", right)
    desk._try_unlock()
    assert not right.get("desk_unlocked")  # even the right PIN waits out the lockout
    monkeypatch.setattr(desk, "_guard", {"fails": 0, "until": 0.0})
    right = {"desk_pin_input": "2222"}
    monkeypatch.setattr(st, "session_state", right)
    desk._try_unlock()
    assert right.get("desk_unlocked")
