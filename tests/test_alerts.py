"""Alert rules, watchlist storage and notification formatting. Offline; nothing is sent."""

import numpy as np
import pandas as pd
import pytest

import alerts as AL
import journal as J
import notify


def _closes(**series):
    n = max(len(v) for v in series.values())
    idx = pd.bdate_range("2026-01-01", periods=n)
    return pd.DataFrame({k: pd.Series(v, index=idx[-len(v) :]) for k, v in series.items()})


def _calm(n=300, seed=1, drift=0.0):
    rng = np.random.default_rng(seed)
    return list(100 * np.cumprod(1 + rng.normal(drift, 0.01, n)))


def test_buy_zone_alert_fires_only_on_the_day_price_crosses_below():
    cfg = {"positions": [], "watchlist": [{"ticker": "NVDA", "buy_below": 180.0}]}
    crossed = AL.evaluate(cfg, _closes(NVDA=[185, 182, 178]))
    assert [a.kind for a in crossed] == ["buy_zone"]
    assert "$178.00" in crossed[0].detail and "$180.00" in crossed[0].detail
    still_below = AL.evaluate(cfg, _closes(NVDA=[185, 178, 175]))  # already in the zone yesterday: no repeat
    assert still_below == []


def test_target_and_stop_alerts_on_crossing():
    cfg = {"positions": [{"ticker": "PLD", "entry_price": 118, "target": 150, "stop": 105}], "watchlist": []}
    hit = AL.evaluate(cfg, _closes(PLD=[147, 149, 151]))
    assert [a.kind for a in hit] == ["target"] and "+28.0% from your entry" in hit[0].detail
    stopped = AL.evaluate(cfg, _closes(PLD=[110, 107, 104]))
    assert [a.kind for a in stopped] == ["stop"] and stopped[0].priority == 5


def test_no_alert_when_nothing_crossed():
    cfg = {
        "positions": [{"ticker": "PLD", "entry_price": 118, "target": 150, "stop": 105}],
        "watchlist": [{"ticker": "PLD", "buy_below": 100}],
    }
    assert AL.evaluate(cfg, _closes(PLD=[120, 121, 122])) == []


def test_big_move_alert_compares_against_the_market():
    stock, spy = _calm(seed=2), _calm(seed=3)
    stock[-1] = stock[-2] * 1.12  # +12% on a calm day for the market
    cfg = {"positions": [], "watchlist": [{"ticker": "AMD", "buy_below": 1}]}
    found = AL.evaluate(cfg, _closes(AMD=stock, SPY=spy))
    assert [a.kind for a in found] == ["big_move"] and "jumped 12.0%" in found[0].title


def test_moving_with_the_market_is_not_a_big_move():
    spy = _calm(seed=4)
    spy[-1] = spy[-2] * 0.94  # market −6%
    stock = [p * 1.5 for p in spy]  # stock moved exactly with it
    cfg = {"positions": [], "watchlist": [{"ticker": "XYZ", "buy_below": 1}]}
    assert AL.evaluate(cfg, _closes(XYZ=stock, SPY=spy)) == []


def test_alerts_are_ordered_by_urgency():
    cfg = {
        "positions": [{"ticker": "B", "entry_price": 100, "target": 200, "stop": 90}],
        "watchlist": [{"ticker": "A", "buy_below": 50}],
    }
    found = AL.evaluate(cfg, _closes(A=[55, 52, 49], B=[95, 92, 89]))
    assert [a.kind for a in found] == ["stop", "buy_zone"]


def test_zone_status_labels():
    assert AL.zone_status(95, 100) == ("In buy zone", "good")
    assert AL.zone_status(103, 100)[1] == "warn"
    assert AL.zone_status(130, 100) == ("30% above zone", "flat")


def test_summary_combines_alerts_and_uses_the_highest_priority():
    a = [AL.Alert("buy_zone", "A", "A entered", "d", 4), AL.Alert("stop", "B", "B fell", "d", 5)]
    title, body, prio = AL.summarize(a, pd.Timestamp("2026-10-06"))
    assert title == "Daily Market Brief · 2 alerts · Oct 06" and body.count("•") == 2 and prio == 5


# ---------- Watchlist storage ----------


@pytest.fixture
def jr(tmp_path, monkeypatch):
    monkeypatch.setattr(J, "PATH", tmp_path / "journal.json")
    return J.load()


def test_old_journal_files_gain_an_empty_watchlist(tmp_path, monkeypatch):
    path = tmp_path / "journal.json"
    path.write_text('{"positions": [], "notes": []}')
    monkeypatch.setattr(J, "PATH", path)
    assert J.load()["watchlist"] == []


def test_watching_twice_updates_the_buy_zone_instead_of_duplicating(jr):
    J.watch(jr, "nvda", 180, "wait for a pullback")
    J.watch(jr, "NVDA", 170, source="builder")
    saved = J.load()["watchlist"]
    assert len(saved) == 1 and saved[0]["buy_below"] == 170 and saved[0]["note"] == "wait for a pullback"


def test_unwatch(jr):
    item = J.watch(jr, "AMD", 150)
    J.unwatch(jr, item["id"])
    assert J.load()["watchlist"] == []


def test_automation_config_leaves_out_private_notes_and_closed_positions(jr):
    J.add_position(
        jr,
        ticker="PLD",
        shares=5,
        entry_price=118,
        entry_date="2026-01-02",
        target=150,
        stop=105,
        conviction=3,
        horizon="1–2 years",
        thesis="secret thesis",
        wrong_if="secret",
    )
    closed = J.add_position(
        jr,
        ticker="OLD",
        shares=1,
        entry_price=10,
        entry_date="2025-01-02",
        target=20,
        stop=5,
        conviction=1,
        horizon="< 6 months",
        thesis="x",
        wrong_if="y",
    )
    J.update_position(jr, closed["id"], status="closed")
    J.watch(jr, "NVDA", 180, "private note")
    cfg = J.automation_config(J.load())
    assert cfg == {
        "positions": [{"ticker": "PLD", "entry_price": 118, "target": 150, "stop": 105}],
        "watchlist": [{"ticker": "NVDA", "buy_below": 180.0}],
    }
    assert "secret" not in str(cfg) and "private" not in str(cfg)


# ---------- Notification settings ----------


def test_no_channels_without_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(notify, "SECRETS", tmp_path / "missing.toml")
    for k in ("NTFY_TOPIC", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "ALERT_EMAIL_TO"):
        monkeypatch.delenv(k, raising=False)
    assert notify.channels() == []


def test_ntfy_payload(monkeypatch):
    sent = {}
    monkeypatch.setenv("NTFY_TOPIC", "my-private-topic")
    monkeypatch.setattr(
        notify.requests,
        "post",
        lambda url, json, timeout: (
            sent.update(url=url, json=json) or type("R", (), {"raise_for_status": lambda self: None})()
        ),
    )
    notify.send_ntfy("Daily Market Brief · 1 alert", "• NVDA entered your buy zone", 4, click="https://example.com")
    assert sent["url"] == "https://ntfy.sh/"
    assert sent["json"]["topic"] == "my-private-topic" and sent["json"]["priority"] == 4
    assert sent["json"]["title"] == "Daily Market Brief · 1 alert" and sent["json"]["click"] == "https://example.com"
