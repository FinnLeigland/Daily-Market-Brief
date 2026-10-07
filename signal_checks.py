"""Signal checks: out-of-sample backtests of the dashboard's own signals, net of trading costs.

The results feed small notes next to the signals they judge (Digest trend labels, Sector Rotation quadrants), the
Macro tab's market-trend status and regime playbook, and nothing else. Computing them takes a few seconds, so the
background prefetch runs `compute()` once per session and stores a compact summary in `_latest` for instant reads.
"""

import numpy as np
import pandas as pd
import streamlit as st

import analytics as A
import config
import data

COST_BPS = 10
FRED_IDS = ("INDPRO", "CPIAUCSL", "CPILFESL", "UNRATE", "PAYEMS", "T10Y3M", "USREC", "DFF", "DGS2", "DGS10")


def t_stat(excess: pd.Series) -> float:
    e = excess.dropna()
    return e.mean() / e.std() * np.sqrt(len(e)) if len(e) > 2 and e.std() > 0 else float("nan")


def verdict(t: float, effect: float) -> tuple[str, str]:
    """Plain-English verdict from a t-stat and the direction of the effect."""
    if effect <= 0:
        return ("Works in reverse", "bad") if t <= -2 else ("No edge", "flat")
    if t >= 2:
        return "Evidence of an edge", "good"
    return ("Weak, not reliable", "warn") if t >= 1 else ("No edge", "flat")


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def compute() -> dict:
    secs = list(config.ALL_SECTORS)
    daily = data.get_prices(tuple(secs + ["SPY"]), period="max")
    daily = daily[daily.index >= "1998-12-01"]

    # 1. Trend labels → next-month return vs. SPY
    labels = A.trend_labels(daily[secs])
    me_px, me_lab = daily.resample("ME").last(), labels.resample("ME").last()
    nxt = me_px.pct_change(fill_method=None).shift(-1)
    fwd_ex = nxt[secs].sub(nxt["SPY"], axis=0) * 100
    trend_sc = A.label_scorecard(me_lab, fwd_ex, A.TREND_LABELS)
    up = A.selection_backtest(me_lab == "Uptrend", nxt[secs], nxt["SPY"], COST_BPS)
    trend_runs = pd.DataFrame(
        {"Uptrend sectors only": up, "S&P 500": nxt["SPY"], "All sectors, equal weight": nxt[secs].mean(axis=1)}
    ).loc[up.index]

    # 2. Rotation quadrants → next-4-week return vs. SPY (non-overlapping 4-week samples)
    weekly = data.get_prices(tuple(secs + ["SPY"]), period="max", interval="1wk")
    weekly = weekly[weekly.index >= "1999-01-01"]
    ratio, mom = A.relative_rotation(weekly[secs], weekly["SPY"])
    quads = A.rrg_quadrants(ratio, mom).iloc[::4]
    f4 = weekly.shift(-4) / weekly - 1
    rrg_sc = A.label_scorecard(quads, f4[secs].sub(f4["SPY"], axis=0).reindex(quads.index) * 100, A.QUADRANTS)

    # 3. Regime playbook, walk-forward
    panel = A.macro_panel(data.get_fred(FRED_IDS))
    regimes = A.classify_regimes(panel)
    monthly = data.get_prices(tuple(secs + ["SPY"]), period="max", interval="1mo")
    reg, picks = A.regime_walkforward(regimes, monthly, "SPY", cost_bps=COST_BPS)
    mret = monthly.pct_change(fill_method=None)
    regime_runs = pd.DataFrame(
        {"Regime playbook": reg, "S&P 500": mret["SPY"], "All sectors, equal weight": mret[secs].mean(axis=1)}
    ).loc[reg.index]
    robust = []
    for name, kw in [
        ("Top 2 sectors, 2-month lag (base case)", {}),
        ("Top 1 sector", {"top_n": 1}),
        ("Top 3 sectors", {"top_n": 3}),
        ("3-month publication lag", {"lag": 3}),
        ("Costs doubled (20 bps)", {"cost_bps": 20}),
    ]:
        r, _ = A.regime_walkforward(regimes, monthly, "SPY", **{"cost_bps": COST_BPS, **kw})
        stats = A.portfolio_stats(r)
        robust.append(
            {
                "Variant": name,
                "CAGR": stats["cagr"],
                "Sharpe": stats["sharpe"],
                "t vs. S&P 500": t_stat(r - mret["SPY"].reindex(r.index)),
            }
        )

    # 4. S&P 500 vs. its 200-day average → in the market or in T-bills
    spy = data.get_prices(("SPY",), period="max")["SPY"]
    tb = data.get_fred(("TB3MS",)).get("TB3MS", pd.Series(dtype=float)) / 100 / 12
    filt, bh, in_mkt = A.market_trend_filter(spy, tb, cost_bps=COST_BPS)
    spy_vs_200 = (spy.iloc[-1] / spy.rolling(200).mean().iloc[-1] - 1) * 100

    return {
        "trend_sc": trend_sc,
        "trend_runs": trend_runs,
        "rrg_sc": rrg_sc,
        "regime_runs": regime_runs,
        "regime_picks": picks,
        "robust": pd.DataFrame(robust).set_index("Variant"),
        "filter_runs": pd.DataFrame({"Trend filter": filt, "Buy & hold S&P 500": bh}),
        "time_in_market": in_mkt.mean() * 100,
        "switches_per_year": in_mkt.diff().abs().sum() / (len(in_mkt) / 12),
        "spy_vs_200": spy_vs_200,
        "as_of": daily.index[-1],
    }


_latest: dict | None = None


def summary(r: dict) -> dict:
    """The headline numbers and verdicts, small enough to show anywhere."""
    tsc, qsc = r["trend_sc"], r["rrg_sc"]
    reg = r["regime_runs"]
    reg_t = t_stat(reg["Regime playbook"] - reg["S&P 500"])
    reg_s, spy_s = A.portfolio_stats(reg["Regime playbook"]), A.portfolio_stats(reg["S&P 500"])
    fr = r["filter_runs"]
    f_s, bh_s = A.portfolio_stats(fr["Trend filter"]), A.portfolio_stats(fr["Buy & hold S&P 500"])
    picks = r["regime_picks"]
    return {
        "trend_avg": tsc.loc["Uptrend", "avg"],
        "trend_t": tsc.loc["Uptrend", "t"],
        "rrg_avg": qsc.loc["Leading", "avg"],
        "rrg_t": qsc.loc["Leading", "t"],
        "regime_cagr": reg_s["cagr"],
        "spy_cagr": spy_s["cagr"],
        "regime_t": reg_t,
        "regime_fragile": bool((r["robust"]["t vs. S&P 500"] < 0).any()),
        "regime_picks": [t.strip() for t in picks.iloc[-1].split(",")] if len(picks) else [],
        "filter_dd": f_s["max_dd"],
        "bh_dd": bh_s["max_dd"],
        "filter_cagr": f_s["cagr"],
        "bh_cagr": bh_s["cagr"],
        "spy_vs_200": r["spy_vs_200"],
        "time_in_market": r["time_in_market"],
        "switches_per_year": r["switches_per_year"],
        "as_of": r["as_of"],
    }


def load() -> dict | None:
    """Run (or fetch from cache) the backtests and return the summary; None if the data couldn't be loaded."""
    global _latest
    try:
        _latest = summary(compute())
    except Exception:
        return _latest
    return _latest


def peek() -> dict | None:
    """The last summary computed in this server process, without doing any work."""
    return _latest
