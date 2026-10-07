import numpy as np
import pandas as pd
import pytest

import ideas as I

SECTOR = {"name": "Technology", "etf": "XLK"}


def _closes(paths: dict[str, float], n: int = 300) -> pd.DataFrame:
    """Daily closes that grow at a constant daily rate per ticker (e.g. 0.002 = steady climb)."""
    idx = pd.bdate_range(end="2026-10-02", periods=n)
    return pd.DataFrame({t: 100 * (1 + r) ** np.arange(n) for t, r in paths.items()}, index=idx)


def _infos(**overrides) -> dict:
    base = {"forwardPE": 20, "revenueGrowth": 0.10, "targetMeanPrice": None, "shortName": None}
    return {t: {**base, **o} for t, o in overrides.items()}


@pytest.fixture
def scored():
    closes = _closes({"WIN": 0.003, "MID": 0.0005, "LOSE": -0.002})
    infos = _infos(
        WIN={"forwardPE": 15, "revenueGrowth": 0.30, "targetMeanPrice": 9999},
        MID={},
        LOSE={"forwardPE": 40, "revenueGrowth": -0.05, "targetMeanPrice": 1},
    )
    return I.score(I.raw_signals(closes, infos))


def test_strong_stock_leans_up_and_weak_leans_down(scored):
    assert scored.loc["WIN", "lean"] == "up"
    assert scored.loc["LOSE", "lean"] == "down"
    assert scored.loc["WIN", "score"] > scored.loc["MID", "score"] > scored.loc["LOSE", "score"]


def test_contributions_add_up_to_score(scored):
    parts = scored[[f"c_{k}" for k, _, _ in I.SIGNALS]].sum(axis=1)
    assert np.allclose(parts, scored["score"])


def test_short_history_is_dropped():
    closes = _closes({"OLD": 0.001})
    closes["NEW"] = np.where(np.arange(len(closes)) < 100, np.nan, 50.0)
    raw = I.raw_signals(closes, {})
    assert list(raw.index) == ["OLD"]


def test_negative_pe_is_neutral_not_cheap():
    closes = _closes({"A": 0.001, "B": 0.001, "C": 0.001})
    raw = I.raw_signals(closes, _infos(A={"forwardPE": -5}, B={"forwardPE": 10}, C={"forwardPE": 30}))
    assert pd.isna(raw.loc["A", "fpe"])
    s = I.score(raw)
    assert s.loc["A", "c_value"] == 0
    assert s.loc["B", "c_value"] > 0 > s.loc["C", "c_value"]


def test_pick_takes_strongest_in_either_direction(scored):
    assert I.pick(scored, set(), {"days": {}}) in {"WIN", "LOSE"}
    strongest = scored["score"].abs().idxmax()
    assert I.pick(scored, set(), {"days": {}}) == strongest


def test_cooldown_gives_a_new_stock(scored):
    first = I.pick(scored, set(), {"days": {}})
    hist = {"days": {"2026-10-05": [{"ticker": first}]}}
    recent = I.recent_tickers(hist, "2026-10-06")
    assert recent == {first}
    assert I.pick(scored, recent, hist) != first


def test_cooldown_expires():
    hist = {"days": {"2026-09-01": [{"ticker": "OLD"}], "2026-10-01": [{"ticker": "NEW"}]}}
    assert I.recent_tickers(hist, "2026-10-06") == {"NEW"}
    assert I.recent_tickers(hist, "2026-10-01") == set()  # today's own picks don't count


def test_all_excluded_falls_back_to_least_recent(scored):
    hist = {"days": {"2026-10-01": [{"ticker": "WIN"}], "2026-10-03": [{"ticker": "LOSE"}, {"ticker": "MID"}]}}
    assert I.pick(scored, {"WIN", "MID", "LOSE"}, hist) == "WIN"


def test_reasons_support_the_lean(scored):
    reasons, risk, inv = I.explain(scored.loc["WIN"], scored)
    assert reasons and any(r.startswith("Leading") for r in reasons)
    assert risk and inv.startswith("A close below $")
    _, _, inv_down = I.explain(scored.loc["LOSE"], scored)
    assert inv_down.startswith("A close above $")


def _row(lean, price, ma200, vol_m=0.08):
    return pd.Series({"lean": lean, "price": price, "ma200": ma200, "vol_m": vol_m})


def test_invalidation_uses_200_day_only_when_it_is_on_the_right_side_and_near():
    assert "200-day" in I.invalidation_level(_row("up", 100, 95))  # just below: a real level
    assert "typical monthly moves" in I.invalidation_level(_row("up", 100, 60))  # too far away to be useful
    assert "typical monthly moves" in I.invalidation_level(_row("up", 100, 105))  # already broken
    assert "200-day" in I.invalidation_level(_row("down", 100, 104))
    down_wrong_side = I.invalidation_level(_row("down", 100, 97))  # already above the average: can't use it
    assert "typical monthly moves" in down_wrong_side and "above $112.00" in down_wrong_side


def test_make_idea_is_json_safe(scored):
    import json

    idea = I.make_idea(SECTOR, "WIN", scored, 250.0, "2026-10-06")
    json.dumps(idea)
    assert idea["lean"] == "up" and idea["price"] > 0 and idea["etf_price"] == 250.0


def _hist(lean: str, price: float, day: str = "2026-09-01") -> dict:
    return {
        "days": {
            day: [
                {"ticker": "AAA", "etf": "XLK", "sector": "Technology", "lean": lean, "price": price, "etf_price": 100}
            ]
        }
    }


def test_track_grades_calls():
    idx = pd.bdate_range("2026-09-01", periods=30)
    closes = pd.DataFrame({"AAA": np.linspace(100, 110, 30), "XLK": np.linspace(100, 105, 30)}, index=idx)
    up = I.track(_hist("up", 100), closes, "2026-10-20").iloc[0]
    assert up["right"] and up["ret"] == pytest.approx(10) and up["vs_sector"] == pytest.approx(5)
    assert up["status"] == "Final" and up["held"] == 29
    down = I.track(_hist("down", 100), closes, "2026-10-20").iloc[0]
    assert not down["right"]


def test_track_skips_todays_ideas_and_open_status():
    idx = pd.bdate_range("2026-09-28", periods=5)
    closes = pd.DataFrame({"AAA": [100, 99, 98, 97, 96.0], "XLK": [100.0] * 5}, index=idx)
    assert I.track(_hist("down", 100, "2026-10-02"), closes, "2026-10-02").empty
    row = I.track(_hist("down", 100, "2026-09-28"), closes, "2026-10-02").iloc[0]
    assert row["status"] == "Open" and row["right"]


def test_record_summary():
    tr = pd.DataFrame(
        {
            "lean": ["up", "up", "down"],
            "ret": [5.0, -1.0, -3.0],
            "right": [True, False, True],
            "status": ["Final", "Open", "Final"],
        }
    )
    s = I.record_summary(tr)
    assert s["ideas"] == 3 and s["final"] == 2 and s["hit_final"] == 100
    assert s["up_avg"] == pytest.approx(2.0) and s["down_avg"] == pytest.approx(-3.0)
    assert I.record_summary(pd.DataFrame())["ideas"] == 0


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(I, "PATH", tmp_path / "ideas.json")
    assert I.load() == {"days": {}}
    I.save({"days": {"2026-10-06": [{"ticker": "AAA"}]}})
    assert I.load()["days"]["2026-10-06"][0]["ticker"] == "AAA"
    (tmp_path / "ideas.json").write_text("{broken")
    assert I.load() == {"days": {}}


def test_backtest_uses_only_past_prices():
    """A shock in the month after a month-end must not change that month-end's picks."""
    idx = pd.bdate_range("2020-01-01", periods=600)
    rng = np.random.default_rng(0)
    base = pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0, 0.01, (600, 6)), axis=0)), index=idx, columns=list("ABCDEF")
    )
    groups = {"S": list("ABCDEF")}
    bt = I.backtest_price_screen(groups, base)
    day = bt["date"].iloc[5]
    shocked = base.copy()
    shocked.loc[shocked.index > day, "A"] *= 3  # A soars only after `day`
    bt2 = I.backtest_price_screen(groups, shocked)
    before = bt[bt["date"] <= day][["up", "down"]].reset_index(drop=True)
    before2 = bt2[bt2["date"] <= day][["up", "down"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(before, before2)


def test_backtest_rewards_persistent_momentum():
    """When winners keep winning, up calls beat their group and down calls lag it."""
    idx = pd.bdate_range("2018-01-01", periods=900)
    drifts = {"A": 0.002, "B": 0.001, "C": 0.0, "D": -0.001, "E": -0.002}
    rng = np.random.default_rng(1)
    closes = pd.DataFrame(
        {t: 100 * np.exp(np.cumsum(d + rng.normal(0, 0.002, len(idx)))) for t, d in drifts.items()}, index=idx
    )
    s = I.backtest_summary(I.backtest_price_screen({"S": list(drifts)}, closes))
    assert s["up_avg"] > 0 > s["down_avg"] and s["spread"] > 0 and s["t"] > 2
    assert s["up_hit"] > 50 and s["down_hit"] > 50


def test_backtest_summary_empty():
    assert I.backtest_summary(pd.DataFrame()) is None


def test_warnings_toggle(monkeypatch):
    import streamlit as st

    import theme

    state = {}
    monkeypatch.setattr(st, "session_state", state)
    assert theme.show_warnings() is True
    assert 'class="warn-note"' in theme.warning_note("careful")
    theme.toggle_warnings()
    assert theme.show_warnings() is False and theme.show_help() is True  # independent of explanations
    theme.toggle_warnings()
    assert theme.show_warnings() is True
