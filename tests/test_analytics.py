"""Tests for the finance math in analytics.py. All offline, on synthetic data."""

import numpy as np
import pandas as pd
import pytest

import analytics as A

# ---------- Valuation ----------


def test_dcf_with_no_growth_is_a_perpetuity():
    # $100 a year forever at a 10% required return is worth exactly $1,000.
    assert A.dcf_per_share(fcf=100, growth=0, discount=0.10, terminal=0, shares=1) == pytest.approx(1000)


def test_dcf_adds_cash_and_subtracts_debt_per_share():
    base = A.dcf_per_share(fcf=100, growth=0, discount=0.10, terminal=0, shares=10)
    with_balance_sheet = A.dcf_per_share(fcf=100, growth=0, discount=0.10, terminal=0, shares=10, cash=50, debt=20)
    assert with_balance_sheet - base == pytest.approx(3.0)  # (50 - 20) / 10 shares


def test_dcf_rises_with_growth_and_falls_with_required_return():
    kw = dict(fcf=100, terminal=0.025, shares=1)
    assert A.dcf_per_share(growth=0.10, discount=0.09, **kw) > A.dcf_per_share(growth=0.05, discount=0.09, **kw)
    assert A.dcf_per_share(growth=0.05, discount=0.11, **kw) < A.dcf_per_share(growth=0.05, discount=0.09, **kw)


def test_reverse_dcf_recovers_the_growth_rate_behind_a_price():
    kw = dict(fcf=5e9, discount=0.09, terminal=0.025, shares=1e9, cash=2e9, debt=1e9)
    price = A.dcf_per_share(growth=0.12, **kw)
    assert A.implied_growth(price, **kw) == pytest.approx(0.12, abs=1e-6)


@pytest.mark.parametrize("fcf, shares", [(-1e9, 1e9), (0, 1e9), (1e9, 0)])
def test_reverse_dcf_returns_none_when_cash_flow_model_does_not_apply(fcf, shares):
    assert A.implied_growth(100, fcf, 0.09, 0.025, shares) is None


def test_reverse_dcf_returns_none_for_prices_no_growth_rate_can_explain():
    assert A.implied_growth(1e12, fcf=1e9, discount=0.09, terminal=0.025, shares=1e9) is None


# ---------- Risk ----------


def test_drawdown_measures_fall_from_running_peak():
    prices = pd.Series([100, 120, 90, 130, 117.0])
    assert A.drawdown(prices).round(2).tolist() == [0, 0, -25, 0, -10]


def test_identical_series_have_beta_and_correlation_of_one():
    rng = np.random.default_rng(0)
    p = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 300)))
    stats = A.risk_stats(p, p)
    assert stats["beta"] == pytest.approx(1)
    assert stats["corr"] == pytest.approx(1)


def test_leveraged_series_has_double_beta():
    rng = np.random.default_rng(1)
    r = rng.normal(0, 0.01, 300)
    market = pd.Series(100 * np.cumprod(1 + r))
    levered = pd.Series(100 * np.cumprod(1 + 2 * r))
    assert A.risk_stats(levered, market)["beta"] == pytest.approx(2, rel=1e-6)


def _monthly_prices(seed=2, n=120):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2015-01-01", periods=n, freq="MS")
    rets = pd.DataFrame(
        {"A": rng.normal(0.01, 0.06, n), "B": rng.normal(0.005, 0.02, n), "C": rng.normal(0.007, 0.04, n)}, index=idx
    )
    return 100 * (1 + rets).cumprod()


def test_risk_contributions_sum_to_100_percent():
    rc = A.risk_contributions(_monthly_prices(), {"A": 50, "B": 30, "C": 20})
    assert rc.sum() == pytest.approx(100)


def test_volatile_asset_dominates_risk_contribution():
    rc = A.risk_contributions(_monthly_prices(), {"A": 50, "B": 50})
    assert rc["A"] > 80  # 6% monthly vol vs. 2%: the volatile half drives nearly all the risk


def test_cvar_is_never_better_than_var():
    r = A.portfolio_returns(_monthly_prices(), {"A": 60, "B": 40})
    stats = A.portfolio_stats(r)
    assert stats["cvar95"] <= stats["var95"]
    assert stats["max_dd"] <= 0


# ---------- Notable moves ----------


def _calm_market(n=250, seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2025-01-01", periods=n)
    market_r = rng.normal(0, 0.008, n)
    stock_r = market_r + rng.normal(0, 0.01, n)
    return idx, market_r, stock_r


def _to_prices(idx, r):
    return pd.Series(100 * np.cumprod(1 + r), index=idx)


def test_find_moves_flags_a_company_specific_jump():
    idx, m, s = _calm_market()
    s[150] += 0.12  # a +12% day the market didn't share
    moves = A.find_moves(_to_prices(idx, s), _to_prices(idx, m))
    assert idx[150] in moves.index
    assert moves.loc[idx[150], "ret"] > 10


def test_find_moves_ignores_moves_the_whole_market_made():
    idx, m, s = _calm_market()
    m[100] -= 0.06
    s[100] -= 0.06  # stock fell with the market, not because of its own news
    moves = A.find_moves(_to_prices(idx, s), _to_prices(idx, m))
    assert idx[100] not in moves.index


def test_find_moves_keeps_only_the_biggest_of_nearby_days():
    idx, m, s = _calm_market()
    s[120] += 0.10
    s[123] += 0.15
    moves = A.find_moves(_to_prices(idx, s), _to_prices(idx, m), min_gap=10)
    assert idx[123] in moves.index
    assert idx[120] not in moves.index


def test_earnings_after_the_close_count_for_the_next_trading_day():
    earnings = pd.DataFrame({"Reported EPS": [2.22]}, index=pd.DatetimeIndex(["2026-08-26 16:00"]))  # Wednesday
    assert A.earnings_day(earnings, pd.Timestamp("2026-08-27")) is not None
    assert A.earnings_day(earnings, pd.Timestamp("2026-08-28")) is None


def test_earnings_before_the_open_count_for_the_same_day():
    earnings = pd.DataFrame({"Reported EPS": [1.0]}, index=pd.DatetimeIndex(["2026-07-21 07:00"]))
    assert A.earnings_day(earnings, pd.Timestamp("2026-07-21")) is not None


@pytest.mark.parametrize(
    "ret, bench, headlines, earnings, expected",
    [
        (8.0, 0.5, ["Shares jump after results"], True, "Earnings"),
        (-3.0, -2.5, ["Stocks slide"], False, "Market selloff"),
        (3.0, 2.0, ["Wall Street rallies"], False, "Market rally"),
        (-6.0, 0.2, ["Company cuts full-year guidance"], False, "Guidance"),
        (5.0, 0.1, ["Analyst upgrade lifts shares"], False, "Upgrade"),
        (4.0, 0.0, [], False, "Unexplained"),
    ],
)
def test_tag_move(ret, bench, headlines, earnings, expected):
    assert A.tag_move(ret, bench, headlines, earnings) == expected


# ---------- Sector rotation ----------


@pytest.mark.parametrize(
    "x, y, quadrant",
    [(101, 101, "Leading"), (101, 99, "Weakening"), (99, 99, "Lagging"), (99, 101, "Improving")],
)
def test_rrg_quadrants(x, y, quadrant):
    assert A.rrg_quadrant(x, y) == quadrant


# ---------- Macro regimes ----------


def _panel(growth, inflation):
    idx = pd.date_range("2020-01-01", periods=len(growth), freq="MS")
    return pd.DataFrame({"growth_mom": growth, "infl_mom": inflation}, index=idx)


def test_regime_quadrants():
    panel = _panel([1, 1, -1, -1], [-1, 1, 1, -1])
    assert A.classify_regimes(panel, confirm=1).tolist() == ["Goldilocks", "Reflation", "Stagflation", "Slowdown"]


def test_one_month_blip_does_not_switch_the_regime():
    # Goldilocks, one Stagflation reading, back to Goldilocks: with 2-month confirmation the blip is ignored.
    panel = _panel([1, 1, -1, 1, 1], [-1, -1, 1, -1, -1])
    assert set(A.classify_regimes(panel, confirm=2)) == {"Goldilocks"}


def test_regime_switches_once_the_new_reading_holds_two_months():
    panel = _panel([1, 1, -1, -1, -1], [-1, -1, 1, 1, 1])
    assert A.classify_regimes(panel, confirm=2).tolist() == [
        "Goldilocks",
        "Goldilocks",
        "Goldilocks",
        "Stagflation",
        "Stagflation",
    ]


def test_longer_confirmation_waits_longer_to_switch():
    panel = _panel([1, -1, -1, -1, -1], [-1, 1, 1, 1, 1])
    assert A.classify_regimes(panel, confirm=3).tolist() == [
        "Goldilocks",
        "Goldilocks",
        "Goldilocks",
        "Stagflation",
        "Stagflation",
    ]


def test_regime_returns_are_lagged_to_avoid_look_ahead():
    idx = pd.date_range("2020-01-01", periods=6, freq="MS")
    regimes = pd.Series(["Reflation"] * 6, index=idx)
    prices = pd.DataFrame({"SPY": [100] * 6, "XLE": [100, 110, 121, 133.1, 146.41, 161.05]}, index=idx)
    table, counts = A.regime_sector_returns(regimes, prices, "SPY", lag=2)
    # Returns exist for months 2-6, but a 2-month lag means only months 3-6 get a regime label.
    assert counts.loc["Reflation", "XLE"] == 4
    assert table.loc["Reflation", "XLE"] == pytest.approx(120, rel=1e-3)  # +10%/month vs. flat SPY, annualized


# ---------- Recession model ----------


def test_recession_model_learns_that_inverted_curves_precede_recessions():
    idx = pd.date_range("1980-01-01", "2024-12-01", freq="MS")
    rng = np.random.default_rng(4)
    usrec = pd.Series(0.0, index=idx)
    for start in ["1990-07-01", "2001-03-01", "2008-01-01", "2014-06-01", "2020-03-01"]:
        usrec[start : pd.Timestamp(start) + pd.DateOffset(months=8)] = 1
    soon = usrec.shift(-12).rolling(12).max().fillna(0)  # recession within 12 months
    panel = pd.DataFrame(
        {
            "spread_avg12": 1.5 - 2.5 * soon + rng.normal(0, 0.4, len(idx)),
            "sahm": 0.4 * soon + rng.normal(0, 0.1, len(idx)),
            "indpro_yoy": 2 - 3 * soon + rng.normal(0, 1, len(idx)),
            "usrec": usrec,
        },
        index=idx,
    )
    model = A.recession_model(panel)
    assert model["auc_oos"] > 0.8
    assert model["odds_per_unit"]["spread_avg12"] < 1  # a higher spread lowers recession odds
    assert model["prob"].between(0, 100).all()


# ---------- Industry structure ----------


def test_monopoly_has_maximum_hhi():
    c = A.concentration([1.0])
    assert c["hhi"] == pytest.approx(10_000)
    assert c["label"] == "Highly concentrated"


def test_ten_equal_firms_are_unconcentrated():
    c = A.concentration([0.1] * 10)
    assert c["hhi"] == pytest.approx(1000)
    assert c["label"] == "Moderately concentrated"  # exactly at the 1,000 threshold
    assert A.concentration([0.05] * 20)["label"] == "Unconcentrated"


def test_concentration_ratios_use_the_largest_firms_in_any_order():
    c = A.concentration([0.1, 0.4, 0.2, 0.3])
    assert c["leader"] == pytest.approx(40)
    assert c["cr3"] == pytest.approx(90)
    assert c["coverage"] == pytest.approx(100)


def test_regime_runs_collapse_consecutive_months():
    idx = pd.date_range("2024-01-01", periods=7, freq="MS")
    regimes = pd.Series(
        ["Slowdown", "Slowdown", "Reflation", "Reflation", "Reflation", "Slowdown", "Goldilocks"], index=idx
    )
    runs = A.regime_runs(regimes)
    assert runs["regime"].tolist() == ["Slowdown", "Reflation", "Slowdown", "Goldilocks"]
    assert runs["months"].tolist() == [2, 3, 1, 1]
    assert runs.loc[1, "start"] == pd.Timestamp("2024-03-01") and runs.loc[1, "end"] == pd.Timestamp("2024-05-01")
    assert runs["months"].sum() == len(regimes)


# ---------- Signal scorecard ----------


def _walk(n=600, seed=7, cols=("A", "B", "C")):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-01", periods=n)
    return pd.DataFrame({c: 100 * np.cumprod(1 + rng.normal(0.0004, 0.012, n)) for c in cols}, index=idx)


def test_vectorized_trend_labels_match_the_digest_labels():
    from data import trend_state

    px = _walk()
    labels = A.trend_labels(px)
    for day in px.index[250::37]:
        for col in px.columns:
            assert labels.at[day, col] == trend_state(px.loc[:day, col])["label"]


def test_trend_labels_are_blank_before_200_days_of_history():
    labels = A.trend_labels(_walk())
    assert labels.iloc[:199].isna().all().all()
    assert labels.iloc[199:].notna().all().all()


def test_label_scorecard_averages_and_hit_rates():
    idx = pd.date_range("2020-01-31", periods=4, freq="ME")
    labels = pd.DataFrame({"X": ["Up"] * 4, "Y": ["Down"] * 4}, index=idx)
    excess = pd.DataFrame({"X": [1.0, 2.0, 1.0, 2.0], "Y": [-1.0, -1.0, -3.0, -3.0]}, index=idx)
    sc = A.label_scorecard(labels, excess, ["Up", "Down"])
    assert sc.loc["Up", "avg"] == pytest.approx(1.5) and sc.loc["Up", "hit"] == 100
    assert sc.loc["Down", "avg"] == pytest.approx(-2.0) and sc.loc["Down", "hit"] == 0
    assert sc.loc["Up", "t"] > 0 > sc.loc["Down", "t"]


def test_selection_backtest_earns_selected_returns_net_of_costs_and_falls_back():
    idx = pd.date_range("2020-01-31", periods=3, freq="ME")
    nxt = pd.DataFrame({"X": [0.10, 0.10, 0.10], "Y": [0.0, 0.0, 0.0]}, index=idx)
    sel = pd.DataFrame({"X": [True, True, False], "Y": [False, False, False]}, index=idx)
    spy = pd.Series([0.02, 0.02, 0.02], index=idx)
    r = A.selection_backtest(sel, nxt, spy, cost_bps=100)
    assert r.iloc[0] == pytest.approx(0.10 - 0.01)  # buy in: 100% turnover × 1%
    assert r.iloc[1] == pytest.approx(0.10)  # hold: no trading
    assert r.iloc[2] == pytest.approx(0.02 - 0.02)  # nothing selected: sell X, buy fallback = 200% turnover


def test_regime_walkforward_never_uses_future_returns():
    idx = pd.date_range("2000-01-01", periods=120, freq="MS")
    rng = np.random.default_rng(3)
    prices = pd.DataFrame(
        100 * np.cumprod(1 + rng.normal(0.005, 0.04, (120, 4)), axis=0), index=idx, columns=["SPY", "AAA", "BBB", "CCC"]
    )
    regimes = pd.Series(np.where(np.arange(120) % 6 < 3, "Reflation", "Slowdown"), index=idx)
    _, picks = A.regime_walkforward(regimes, prices, "SPY", start="2004-01-01", min_obs=6)
    shocked = prices.copy()
    shocked.loc["2008-01-01":, "CCC"] *= 50  # a huge future jump in one sector
    _, picks2 = A.regime_walkforward(regimes, shocked, "SPY", start="2004-01-01", min_obs=6)
    # Decisions made up to and including the shocked month can't know about it (the month's own return
    # is only known at its end).
    upto = picks.index <= "2008-01-01"
    assert (picks[upto] == picks2[upto]).all()


def test_vectorized_rrg_quadrants():
    ratio = pd.DataFrame({"S": [101, 101, 99, 99]})
    mom = pd.DataFrame({"S": [101, 99, 99, 101]})
    assert A.rrg_quadrants(ratio, mom)["S"].tolist() == ["Leading", "Weakening", "Lagging", "Improving"]


def test_market_trend_filter_goes_to_cash_below_the_average():
    idx = pd.bdate_range("2000-01-03", periods=900)
    up = np.linspace(100, 200, 450)
    down = np.linspace(200, 80, 450)
    px = pd.Series(np.concatenate([up, down]), index=idx)
    cash = pd.Series(0.003, index=pd.date_range("1999-12-01", periods=60, freq="MS"))
    strat, bh, inm = A.market_trend_filter(px, cash, start="2000-01-01")
    assert inm.iloc[-3:].eq(0).all()  # deep in the decline: out of the market
    assert strat.iloc[-3:].round(4).eq(0.003).all()  # earning T-bills while out
    assert strat.sum() > bh.sum()  # sidestepping the decline beats holding through it
