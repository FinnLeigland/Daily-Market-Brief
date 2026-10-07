"""Pure analytics: risk statistics, sector rotation, macro regimes, recession model, portfolio math.

Nothing in here touches Streamlit, so every function can be unit-tested or reused in a notebook.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# ---------- Single-asset risk ----------


def drawdown(prices: pd.Series) -> pd.Series:
    """Percent below the running peak (0 at new highs)."""
    p = prices.dropna()
    return (p / p.cummax() - 1) * 100


def risk_stats(prices: pd.Series, bench: pd.Series, periods_per_year: int = 252) -> dict:
    """Annualized return, volatility, Sharpe (rf=0), max drawdown, and beta/correlation to a benchmark."""
    df = pd.concat([prices, bench], axis=1, keys=["a", "b"]).dropna()
    r = df.pct_change().dropna()
    years = len(r) / periods_per_year
    cagr = (df["a"].iloc[-1] / df["a"].iloc[0]) ** (1 / years) - 1
    vol = r["a"].std() * np.sqrt(periods_per_year)
    beta = r["a"].cov(r["b"]) / r["b"].var()
    return {
        "cagr": cagr * 100,
        "vol": vol * 100,
        "sharpe": (r["a"].mean() * periods_per_year) / vol if vol else np.nan,
        "max_dd": drawdown(df["a"]).min(),
        "beta": beta,
        "corr": r["a"].corr(r["b"]),
    }


# ---------- Notable price moves ----------

MOVE_TAGS = [  # (keywords in headlines, short label) checked in order
    (("guidance", "outlook", "forecast"), "Guidance"),
    (("upgrade",), "Upgrade"),
    (("downgrade",), "Downgrade"),
    (("acquire", "acquisition", "merger", "buyout", "takeover", "to buy"), "Deal news"),
    (("fda", "trial", "approval"), "FDA / trial"),
    (("lawsuit", "probe", "investigation", "antitrust", "sec ", "doj"), "Legal / regulatory"),
    (("tariff", "export", "china", "sanction"), "Trade / tariffs"),
    (("ceo", "resign", "steps down", "appoint"), "Leadership"),
    (("contract", "partnership", "deal with", "agreement"), "Partnership"),
    (("recall", "outage", "breach", "crash"), "Incident"),
]


def find_moves(px: pd.Series, bench: pd.Series, max_events: int = 8, min_gap: int = 10, z: float = 2.5) -> pd.DataFrame:
    """Days where the stock moved unusually far *relative to the market*.

    A day qualifies when its excess return over the benchmark is more than `z` standard deviations of the stock's
    typical excess return. Nearby days are merged (only the biggest within `min_gap` trading days is kept).
    """
    df = pd.concat([px, bench], axis=1, keys=["p", "b"]).dropna()
    r = df.pct_change().dropna() * 100
    excess = r["p"] - r["b"]
    threshold = z * excess.std()
    cands = excess[excess.abs() > threshold].abs().sort_values(ascending=False)
    picked: list[pd.Timestamp] = []
    pos = {d: i for i, d in enumerate(r.index)}
    for d in cands.index:
        if all(abs(pos[d] - pos[p]) >= min_gap for p in picked):
            picked.append(d)
        if len(picked) >= max_events:
            break
    out = pd.DataFrame({"ret": r.loc[picked, "p"], "bench": r.loc[picked, "b"], "excess": excess.loc[picked]})
    out["sigma"] = out["excess"].abs() / excess.std()
    return out.sort_index()


def earnings_day(earnings: pd.DataFrame | None, day: pd.Timestamp) -> pd.Series | None:
    """The earnings report that would have moved the stock on `day` (same day if before the open, prior day if after the close)."""
    if earnings is None or earnings.empty:
        return None
    for ts, row in earnings.iterrows():
        report_day = pd.Timestamp(ts.date())
        trading_day = report_day + pd.offsets.BDay(1) if ts.hour >= 12 else report_day
        if trading_day == day or report_day == day:
            return row
    return None


def tag_move(ret: float, bench: float, headlines: list[str], is_earnings: bool) -> str:
    if is_earnings:
        return "Earnings"
    if abs(bench) >= 1.5 and np.sign(bench) == np.sign(ret) and abs(ret - bench) < abs(ret) * 0.5:
        return "Market rally" if ret > 0 else "Market selloff"
    text = " ".join(headlines[:3]).lower()
    for keys, label in MOVE_TAGS:
        if any(k in text for k in keys):
            return label
    return "News" if headlines else "Unexplained"


# ---------- Industry structure ----------


def concentration(shares: list[float]) -> dict:
    """Concentration of an industry from each company's share of it (fractions, largest first or any order).

    HHI is the sum of squared percentage shares (0–10,000). Thresholds follow the 2023 U.S. Merger Guidelines:
    above 1,800 is highly concentrated, 1,000–1,800 moderately concentrated, below 1,000 unconcentrated.
    Shares here are market-cap based, a common proxy when revenue shares aren't available.
    """
    s = sorted((x for x in shares if x and x > 0), reverse=True)
    hhi = sum((x * 100) ** 2 for x in s)
    label = "Highly concentrated" if hhi > 1800 else "Moderately concentrated" if hhi >= 1000 else "Unconcentrated"
    return {
        "leader": s[0] * 100 if s else 0.0,
        "cr3": sum(s[:3]) * 100,
        "cr5": sum(s[:5]) * 100,
        "hhi": hhi,
        "coverage": sum(s) * 100,
        "label": label,
        "n": len(s),
    }


# ---------- Sector rotation (relative rotation graph) ----------


def relative_rotation(weekly: pd.DataFrame, bench: pd.Series, lookback: int = 10, momentum: int = 4):
    """Simplified RRG coordinates.

    RS-Ratio: the sector's price relative to the benchmark, versus its own 10-week average (100 = in line).
    RS-Momentum: the rate of change of RS-Ratio over 4 weeks (100 = flat).
    """
    rs = weekly.div(bench, axis=0)
    ratio = (100 * rs / rs.rolling(lookback).mean()).ewm(span=3).mean()  # light smoothing keeps tails readable
    mom = (100 * ratio / ratio.shift(momentum)).ewm(span=3).mean()
    return ratio.dropna(how="all"), mom.dropna(how="all")


def rrg_quadrant(x: float, y: float) -> str:
    if x >= 100:
        return "Leading" if y >= 100 else "Weakening"
    return "Improving" if y >= 100 else "Lagging"


# ---------- Macro regimes ----------

REGIMES = ["Goldilocks", "Reflation", "Stagflation", "Slowdown"]
REGIME_DESC = {  # the textbook view; the cards show what actually happened since 1999 right below it
    "Goldilocks": "Growth accelerating, inflation cooling. The textbook view: the friendliest backdrop for stocks.",
    "Reflation": "Growth and inflation both accelerating. The textbook view: good for cyclicals, energy and banks.",
    "Stagflation": "Growth slowing while inflation heats up. The textbook view: the hardest regime for stocks and bonds.",
    "Slowdown": "Growth and inflation both cooling. The textbook view: defensives and bonds hold up best.",
}


def macro_panel(fred: dict[str, pd.Series]) -> pd.DataFrame:
    """Monthly panel of the indicators the regime and recession models use."""

    # Interpolate short gaps (e.g. the October 2025 shutdown left no CPI or jobs report for that month).
    def m(sid: str) -> pd.Series:
        return fred[sid].resample("MS").mean().interpolate(limit=2, limit_area="inside")

    df = pd.DataFrame(
        {
            "indpro_yoy": m("INDPRO").pct_change(12, fill_method=None) * 100,
            "cpi_yoy": m("CPIAUCSL").pct_change(12, fill_method=None) * 100,
            "unrate": m("UNRATE"),
            "spread": m("T10Y3M"),
            "usrec": m("USREC"),
        }
    )
    u3 = df["unrate"].rolling(3).mean()
    df["sahm"] = u3 - u3.shift(1).rolling(12).min()
    df["spread_avg12"] = df["spread"].rolling(12).mean()
    # Growth/inflation momentum: change in the smoothed YoY rate over the last 6 months.
    df["growth_mom"] = df["indpro_yoy"].rolling(3).mean().diff(6)
    df["infl_mom"] = df["cpi_yoy"].rolling(3).mean().diff(6)
    return df


def classify_regimes(panel: pd.DataFrame, confirm: int = 2) -> pd.Series:
    """Label each month with a regime. A switch only counts once the new reading holds for `confirm` months,
    which filters out one-month flips when momentum hovers near zero."""
    g, i = panel["growth_mom"], panel["infl_mom"]
    raw = pd.Series(
        np.select([(g > 0) & (i <= 0), (g > 0) & (i > 0), (g <= 0) & (i > 0)], REGIMES[:3], default=REGIMES[3]),
        index=panel.index,
    )[g.notna() & i.notna()]
    out, current, candidate, streak = [], raw.iloc[0], None, 0
    for value in raw:
        if value == current:
            candidate, streak = None, 0
        elif value == candidate:
            streak += 1
            if streak >= confirm:
                current, candidate, streak = value, None, 0
        else:
            candidate, streak = value, 1
            if confirm <= 1:
                current = value
        out.append(current)
    return pd.Series(out, index=raw.index)


def regime_runs(regimes: pd.Series) -> pd.DataFrame:
    """Collapse monthly regime labels into continuous stretches: regime, start, end (last month), months."""
    if regimes.empty:
        return pd.DataFrame(columns=["regime", "start", "end", "months"])
    block = (regimes != regimes.shift()).cumsum()
    runs = regimes.groupby(block).agg(regime="first")
    runs["start"] = regimes.index.to_series().groupby(block).min().values
    runs["end"] = regimes.index.to_series().groupby(block).max().values
    runs["months"] = regimes.groupby(block).size().values
    return runs.reset_index(drop=True)


def regime_sector_returns(regimes: pd.Series, monthly: pd.DataFrame, bench: str, lag: int = 2) -> pd.DataFrame:
    """Annualized excess return vs. the benchmark for each asset in each regime.

    `lag` avoids look-ahead: data for month m is published during m+1, so it is only used
    to label the returns of month m+2.
    """
    rets = monthly.pct_change(fill_method=None)
    label = regimes.shift(lag, freq="MS").reindex(rets.index)
    excess = rets.sub(rets[bench], axis=0).drop(columns=bench)
    excess["regime"] = label
    grouped = excess.dropna(subset=["regime"]).groupby("regime")
    table, counts = grouped.mean() * 12 * 100, grouped.count()
    return table.reindex(REGIMES), counts.reindex(REGIMES).fillna(0).astype(int)


# ---------- Recession probability ----------

RECESSION_FEATURES = {
    "spread_avg12": "10Y–3M Treasury spread, 12-mo avg (pts)",
    "sahm": "Unemployment gap vs. 12-mo low (Sahm, pts)",
    "indpro_yoy": "Industrial production, YoY %",
}


def recession_model(panel: pd.DataFrame, horizon: int = 12) -> dict:
    """Logistic regression: P(the economy is in an NBER recession at some point in the next `horizon` months)."""
    feats = list(RECESSION_FEATURES)
    target = panel["usrec"].shift(-horizon).rolling(horizon).max()  # any recession in months t+1..t+horizon
    df = panel[feats].ffill(limit=2).assign(y=target)
    train = df.dropna()
    train = train[train.index >= "1982-01-01"]

    model = make_pipeline(StandardScaler(), LogisticRegression())
    model.fit(train[feats], train["y"].astype(int))

    # Out-of-sample check: fit through 2005, score 2006 onward (covers 2008 and 2020).
    split = train.index < "2006-01-01"
    oos = make_pipeline(StandardScaler(), LogisticRegression()).fit(
        train.loc[split, feats], train.loc[split, "y"].astype(int)
    )
    oos_auc = roc_auc_score(train.loc[~split, "y"], oos.predict_proba(train.loc[~split, feats])[:, 1])

    scorable = df[feats].dropna()
    scorable = scorable[scorable.index >= "1982-01-01"]
    prob = pd.Series(model.predict_proba(scorable)[:, 1] * 100, index=scorable.index)

    scaler, lr = model.named_steps["standardscaler"], model.named_steps["logisticregression"]
    raw_coef = lr.coef_[0] / scaler.scale_  # effect per one raw unit of each feature
    return {
        "prob": prob,
        "latest": scorable.iloc[-1],
        "latest_date": scorable.index[-1],
        "odds_per_unit": dict(zip(feats, np.exp(raw_coef), strict=True)),
        "auc_in": roc_auc_score(train["y"], model.predict_proba(train[feats])[:, 1]),
        "auc_oos": oos_auc,
        "n_train": len(train),
        "base_rate": train["y"].mean() * 100,
    }


# ---------- Valuation ----------


def dcf_per_share(
    fcf: float,
    growth: float,
    discount: float,
    terminal: float,
    shares: float,
    cash: float = 0,
    debt: float = 0,
    years: int = 10,
) -> float:
    """Value per share from a two-stage DCF.

    Free cash flow grows at `growth` for `years`, then at `terminal` forever. Everything is discounted at
    `discount` (rates as decimals). Net cash is added to get equity value.
    """
    flows = [fcf * (1 + growth) ** t for t in range(1, years + 1)]
    pv = sum(f / (1 + discount) ** t for t, f in enumerate(flows, start=1))
    terminal_value = flows[-1] * (1 + terminal) / (discount - terminal)
    pv += terminal_value / (1 + discount) ** years
    return (pv + cash - debt) / shares


def implied_growth(
    price: float,
    fcf: float,
    discount: float,
    terminal: float,
    shares: float,
    cash: float = 0,
    debt: float = 0,
    years: int = 10,
) -> float | None:
    """Reverse DCF: the 10-year FCF growth rate that makes the DCF value equal today's price."""
    if fcf <= 0 or shares <= 0:
        return None
    lo, hi = -0.5, 1.0

    def value(g: float) -> float:
        return dcf_per_share(fcf, g, discount, terminal, shares, cash, debt, years)

    if not (value(lo) <= price <= value(hi)):
        return None
    for _ in range(80):  # bisection; value is monotonic in growth
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if value(mid) < price else (lo, mid)
    return (lo + hi) / 2


# ---------- Signal scorecard (backtests of the dashboard's own signals) ----------
#
# Every test below follows two rules: a signal on date t uses only data up to t, and it is scored on what happened
# *after* t. Observations are sampled so forward windows don't overlap.

TREND_LABELS = ["Uptrend", "Recovering", "Pulling back", "Rebounding", "Weakening", "Downtrend"]
QUADRANTS = ["Leading", "Weakening", "Lagging", "Improving"]


def trend_labels(prices: pd.DataFrame) -> pd.DataFrame:
    """The Digest's trend label (from 50/200-day averages) for every asset on every day, vectorized."""
    ma50, ma200 = prices.rolling(50).mean(), prices.rolling(200).mean()
    p = prices
    conds = [
        (p > ma50) & (ma50 > ma200),
        (p < ma50) & (ma50 < ma200),
        (p > ma200) & (p < ma50),
        (p > ma200),
        (p > ma50),
    ]
    picks = ["Uptrend", "Downtrend", "Pulling back", "Recovering", "Rebounding"]
    out = np.select([c.to_numpy() for c in conds], picks, default="Weakening").astype(object)
    out[ma200.isna().to_numpy() | p.isna().to_numpy()] = None
    return pd.DataFrame(out, index=prices.index, columns=prices.columns)


def label_scorecard(labels: pd.DataFrame, fwd_excess: pd.DataFrame, order: list[str]) -> pd.DataFrame:
    """For each label: observations, average and median forward excess return (pts), hit rate, and a t-stat.

    The t-stat is computed on each period's average across assets, because assets labeled the same way in the same
    period tend to move together; treating them as independent would overstate the evidence.
    """
    stacked = pd.DataFrame({"label": labels.stack(), "excess": fwd_excess.reindex_like(labels).stack()}).dropna()
    rows = {}
    for label in order:
        obs = stacked[stacked["label"] == label]
        if obs.empty:
            continue
        per_period = obs.groupby(level=0)["excess"].mean()
        se = per_period.std() / np.sqrt(len(per_period)) if len(per_period) > 1 else np.nan
        rows[label] = {
            "obs": len(obs),
            "periods": len(per_period),
            "avg": obs["excess"].mean(),
            "median": obs["excess"].median(),
            "hit": (obs["excess"] > 0).mean() * 100,
            "t": per_period.mean() / se if se and se > 0 else np.nan,
        }
    return pd.DataFrame(rows).T


def selection_backtest(
    selected: pd.DataFrame, next_returns: pd.DataFrame, fallback: pd.Series, cost_bps: float = 10
) -> pd.Series:
    """Equal-weight the selected assets each period and earn their next-period return, net of trading costs.

    `selected` (bool) and `next_returns` share an index: row t holds the selection made at t and the returns
    from t to t+1. Periods with nothing selected hold the fallback (e.g. SPY). Costs: `cost_bps` per unit of
    turnover (sum of absolute weight changes).
    """
    sel = selected.reindex_like(next_returns).fillna(False).astype(bool) & next_returns.notna()
    n = sel.sum(axis=1)
    weights = sel.div(n.replace(0, np.nan), axis=0).fillna(0.0)
    gross = (weights * next_returns.fillna(0)).sum(axis=1)
    gross = gross.where(n > 0, fallback.reindex(gross.index))
    fb_weight = (n == 0).astype(float)
    turnover = weights.diff().abs().sum(axis=1) + fb_weight.diff().abs()
    turnover.iloc[0] = weights.iloc[0].sum() + fb_weight.iloc[0]
    return (gross - turnover * cost_bps / 1e4).dropna()


def rrg_quadrants(ratio: pd.DataFrame, mom: pd.DataFrame) -> pd.DataFrame:
    out = np.select(
        [(ratio >= 100) & (mom >= 100), (ratio >= 100) & (mom < 100), (ratio < 100) & (mom < 100)],
        ["Leading", "Weakening", "Lagging"],
        default="Improving",
    ).astype(object)
    out[(ratio.isna() | mom.isna()).to_numpy()] = None
    return pd.DataFrame(out, index=ratio.index, columns=ratio.columns)


def regime_walkforward(
    regimes: pd.Series,
    monthly: pd.DataFrame,
    bench: str,
    top_n: int = 2,
    start: str = "2005-01-01",
    min_obs: int = 12,
    lag: int = 2,
    cost_bps: float = 10,
) -> tuple[pd.Series, pd.Series]:
    """Walk-forward test of the regime playbook.

    Each month, look up the current regime (lagged `lag` months for publication delay), rank sectors by their
    average excess return in that regime using only months *before* this one, and hold the top `top_n` for the
    month. Returns (strategy monthly returns, the picks each month).
    """
    rets = monthly.pct_change(fill_method=None)
    label = regimes.shift(lag, freq="MS").reindex(rets.index)
    excess = rets.sub(rets[bench], axis=0).drop(columns=bench)
    picks, out, prev = {}, {}, set()
    for t in rets.index[rets.index >= start]:
        regime = label.get(t)
        past = excess[(excess.index < t) & (label == regime)] if isinstance(regime, str) else excess.iloc[0:0]
        ranked = past.mean()[past.count() >= min_obs].sort_values(ascending=False)
        chosen = [c for c in ranked.index[:top_n] if pd.notna(rets.at[t, c])]
        r = rets.loc[t, chosen].mean() if chosen else rets.at[t, bench]
        now = set(chosen) or {bench}
        turnover = 2.0 if not prev else len(now ^ prev) / max(len(now), 1)
        out[t] = r - turnover * cost_bps / 1e4
        picks[t] = ", ".join(chosen) if chosen else bench
        prev = now
    return pd.Series(out).dropna(), pd.Series(picks)


def market_trend_filter(
    prices: pd.Series, cash_monthly: pd.Series, window: int = 200, cost_bps: float = 10, start: str = "1994-01-01"
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Hold the index while it closes a month above its `window`-day average, otherwise hold T-bills.

    The decision is made at each month-end close and applied to the following month. Returns (strategy returns,
    buy-and-hold returns, in-market flag), all monthly and indexed by the decision date.
    """
    me = prices.resample("ME").last()
    avg = prices.rolling(window).mean().resample("ME").last()
    in_market = (me > avg).astype(float).where(avg.notna())
    nxt = me.pct_change(fill_method=None).shift(-1)
    cash = cash_monthly.resample("ME").last().reindex(me.index).ffill().shift(-1).fillna(0)
    switch = in_market.diff().abs().fillna(0)
    strat = in_market * nxt + (1 - in_market) * cash - switch * cost_bps / 1e4
    keep = strat.notna() & nxt.notna() & (strat.index >= start)
    return strat[keep], nxt[keep], in_market[keep]


# ---------- Portfolio ----------

STRESS_WINDOWS = {
    "2008 financial crisis": ("2007-11-01", "2009-02-01"),
    "2011 euro debt scare": ("2011-05-01", "2011-09-01"),
    "2018 Q4 selloff": ("2018-10-01", "2018-12-01"),
    "2020 COVID crash": ("2020-02-01", "2020-03-01"),
    "2022 rate shock": ("2022-01-01", "2022-09-01"),
}


def portfolio_returns(monthly: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Monthly returns of a portfolio rebalanced back to target weights every month."""
    rets = monthly[list(weights)].pct_change(fill_method=None).dropna()
    w = pd.Series(weights) / sum(weights.values())
    return rets @ w


def portfolio_stats(r: pd.Series, rf: pd.Series | None = None) -> dict:
    """Annualized stats from monthly returns, plus 95% one-month VaR and CVaR (expected shortfall)."""
    r = r.dropna()
    rf = rf.reindex(r.index).fillna(0) if rf is not None else pd.Series(0, index=r.index)
    growth = (1 + r).cumprod()
    excess = r - rf
    var95 = r.quantile(0.05)
    return {
        "cagr": (growth.iloc[-1] ** (12 / len(r)) - 1) * 100,
        "vol": r.std() * np.sqrt(12) * 100,
        "sharpe": excess.mean() / excess.std() * np.sqrt(12),
        "max_dd": ((growth / growth.cummax()) - 1).min() * 100,
        "worst_month": r.min() * 100,
        "var95": var95 * 100,
        "cvar95": r[r <= var95].mean() * 100,
        "pct_up": (r > 0).mean() * 100,
    }


def risk_contributions(monthly: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """Share of total portfolio variance coming from each holding (sums to 100%)."""
    rets = monthly[list(weights)].pct_change(fill_method=None).dropna()
    w = pd.Series(weights) / sum(weights.values())
    cov = rets.cov()
    marginal = cov @ w
    return (w * marginal) / (w @ cov @ w) * 100


def stress_test(r: pd.Series) -> dict[str, float | None]:
    out = {}
    for name, (start, end) in STRESS_WINDOWS.items():
        window = r.loc[start:end]
        out[name] = ((1 + window).prod() - 1) * 100 if len(window) and window.index[0] <= pd.Timestamp(start) else None
    return out
