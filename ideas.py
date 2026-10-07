"""Equity Screen: one stock per featured sector each day, with a lean (up or down) and the reasons behind it.

How a pick is made, per sector:
1. Candidates are the sector ETF's top holdings.
2. Each candidate gets a score from five signals, each ranked against the other candidates in its sector (z-score):
   12-1 month momentum, distance from the 200-day average, forward P/E (cheaper scores higher), revenue growth,
   and the upside to analysts' average target.
3. A positive score leans up and a negative one leans down; the size of the score is the conviction.
4. The day's pick is the candidate with the strongest score (either direction) that hasn't been featured in the
   last COOLDOWN_DAYS days, so there's a new stock every day.

Every idea is saved to ideas.json with the price at the time, so the track record shows whether the calls worked.
"""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

PATH = Path(os.environ.get("IDEAS_FILE") or Path(__file__).with_name("ideas.json"))
COOLDOWN_DAYS = 10  # a stock can't be featured again for this many days
HORIZON = 21  # trading days (about a month) before a call is graded as final

# signal, weight, plain-English name
SIGNALS = [
    ("momentum", 0.35, "momentum"),
    ("trend", 0.20, "trend"),
    ("value", 0.15, "valuation"),
    ("growth", 0.15, "growth"),
    ("analysts", 0.15, "analyst targets"),
]


# ---------- Storage ----------


def load() -> dict:
    try:
        hist = json.loads(PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        hist = {}
    hist.setdefault("days", {})
    return hist


def save(hist: dict) -> None:
    tmp = PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(hist, indent=1))
    tmp.replace(PATH)  # atomic, so a half-written file never replaces a good one


# ---------- Signals and scores ----------


def _z(s: pd.Series) -> pd.Series:
    """Standardize within the candidate group; missing values score 0 (neutral)."""
    sd = s.std()
    if s.notna().sum() < 2 or not sd or pd.isna(sd):
        return pd.Series(0.0, index=s.index)
    return ((s - s.mean()) / sd).clip(-2.5, 2.5).fillna(0.0)


def raw_signals(closes: pd.DataFrame, infos: dict[str, dict]) -> pd.DataFrame:
    """One row per ticker with the raw inputs (decimals, not percents). Tickers without a year of prices are dropped."""
    rows = {}
    for t in closes.columns:
        px = closes[t].dropna()
        if len(px) < 253:
            continue
        info = infos.get(t) or {}
        price = px.iloc[-1]
        fpe = info.get("forwardPE")
        target = info.get("targetMeanPrice")
        rows[t] = {
            "price": price,
            "momentum": px.iloc[-22] / px.iloc[-253] - 1,  # 12-month return skipping the latest month
            "month": price / px.iloc[-22] - 1,
            "trend": price / px.iloc[-200:].mean() - 1,
            "ma200": px.iloc[-200:].mean(),
            "vol_m": px.pct_change().iloc[-252:].std() * np.sqrt(21),  # a typical one-month move
            "fpe": fpe if fpe and fpe > 0 else np.nan,
            "growth": info.get("revenueGrowth", np.nan),
            "analysts": target / price - 1 if target else np.nan,
            "name": info.get("longName") or info.get("shortName") or t,
        }
    return pd.DataFrame.from_dict(rows, orient="index")


def score(raw: pd.DataFrame) -> pd.DataFrame:
    """Add a z-score per signal, each signal's weighted contribution, the total score, lean and conviction."""
    df = raw.copy()
    z = {
        "momentum": _z(df["momentum"]),
        "trend": _z(df["trend"]),
        "value": _z(-df["fpe"]),  # a lower P/E is cheaper, so it scores higher
        "growth": _z(df["growth"].astype(float)),
        "analysts": _z(df["analysts"].astype(float)),
    }
    df["score"] = 0.0
    for key, weight, _ in SIGNALS:
        df[f"c_{key}"] = weight * z[key]
        df["score"] += df[f"c_{key}"]
    df["lean"] = np.where(df["score"] >= 0, "up", "down")
    df["conviction"] = pd.cut(df["score"].abs(), [-1, 0.4, 0.8, 99], labels=["Low", "Medium", "High"]).astype(str)
    return df


# ---------- Reasons ----------


def _pct(x: float) -> str:
    return f"{x * 100:+.0f}%"


def _reason(key: str, row: pd.Series, med: pd.Series) -> str:
    if key == "momentum":
        lead = "Leading" if row.momentum >= med.momentum else "Lagging"
        return (
            f"{lead} its sector group: {_pct(row.momentum)} over the past year (excluding the last month) "
            f"vs. a median of {_pct(med.momentum)}"
        )
    if key == "trend":
        side = "above" if row.trend >= 0 else "below"
        return f"Trading {abs(row.trend) * 100:.0f}% {side} its 200-day average (${row.ma200:,.2f})"
    if key == "value":
        cheaper = row.fpe < med.fpe
        return (
            f"{row.fpe:.1f}× forward earnings, {'cheaper' if cheaper else 'pricier'} than the group median of "
            f"{med.fpe:.1f}×"
        )
    if key == "growth":
        pace = "Faster" if row.growth >= med.growth else "Slower"
        return f"{pace} growth than its group: revenue {_pct(row.growth)} year over year vs. a median of {_pct(med.growth)}"
    more = "More" if row.analysts >= med.analysts else "Less"
    return (
        f"{more} analyst upside than its group: the average target is {_pct(row.analysts)} from here "
        f"vs. a median of {_pct(med.analysts)}"
    )


def _available(key: str, row: pd.Series, med: pd.Series) -> bool:
    col = {"value": "fpe"}.get(key, key)
    return pd.notna(row[col]) and pd.notna(med[col])


def explain(row: pd.Series, group: pd.DataFrame, n: int = 3) -> tuple[list[str], str, str]:
    """The top reasons supporting the lean, the key risk (the strongest factor against it), and the invalidation level."""
    med = group[["momentum", "trend", "fpe", "growth", "analysts"]].astype(float).median()
    sign = 1 if row.lean == "up" else -1
    contrib = sorted(
        ((key, row[f"c_{key}"]) for key, _, _ in SIGNALS if _available(key, row, med)),
        key=lambda kv: -kv[1] * sign,
    )
    reasons = [_reason(k, row, med) for k, c in contrib if c * sign > 0.02][:n]
    against = [(k, c) for k, c in contrib if c * sign < -0.02]
    if against:
        k, _ = against[-1]  # the most opposed signal
        risk = f"{_reason(k, row, med)}, which cuts against the call."
    else:
        risk = "All signals point the same way, which can indicate a crowded trade that is prone to sharp reversals."
    return reasons, risk, invalidation_level(row)


STOP_MOVES = 1.5  # invalidation sits about 1.5 typical monthly moves against the call


def invalidation_level(row: pd.Series) -> str:
    """The price that would break the call: the 200-day average when it sits between today's price and a normal-sized
    move against the call (a level the market watches), otherwise a volatility-based level."""
    up = row.lean == "up"
    vol_level = row.price * (1 - STOP_MOVES * row.vol_m) if up else row.price * (1 + STOP_MOVES * row.vol_m)
    side = "below" if up else "above"
    ma_between = vol_level < row.ma200 < row.price if up else row.price < row.ma200 < vol_level
    if ma_between:
        return f"A close {side} ${row.ma200:,.2f}, the 200-day moving average."
    gap = abs(vol_level / row.price - 1) * 100
    return f"A close {side} ${vol_level:,.2f}, {gap:.0f}% from the pick (about {STOP_MOVES:g} typical monthly moves)."


# ---------- Picking ----------


def recent_tickers(hist: dict, today: str, days: int = COOLDOWN_DAYS) -> set[str]:
    cutoff = pd.Timestamp(today) - pd.Timedelta(days=days)
    return {
        i["ticker"]
        for d, ideas in hist["days"].items()
        if cutoff < pd.Timestamp(d) < pd.Timestamp(today)
        for i in ideas
    }


def last_featured(hist: dict, ticker: str) -> str:
    dates = [d for d, ideas in hist["days"].items() if any(i["ticker"] == ticker for i in ideas)]
    return max(dates, default="0000-00-00")


def pick(scored: pd.DataFrame, exclude: set[str], hist: dict) -> str | None:
    """The strongest-scoring candidate (either direction) that isn't excluded; if all are, the least recently featured."""
    if scored.empty:
        return None
    ranked = scored.assign(strength=scored["score"].abs()).sort_values("strength", ascending=False)
    for t in ranked.index:
        if t not in exclude:
            return t
    return min(ranked.index, key=lambda t: last_featured(hist, t))


def make_idea(sector: dict, ticker: str, scored: pd.DataFrame, etf_price: float, today: str) -> dict:
    row = scored.loc[ticker]
    reasons, risk, invalidation = explain(row, scored)
    return {
        "date": today,
        "sector": sector["name"],
        "etf": sector["etf"],
        "ticker": ticker,
        "name": row["name"],
        "lean": row["lean"],
        "score": round(float(row["score"]), 3),
        "conviction": row["conviction"],
        "price": round(float(row["price"]), 2),
        "etf_price": round(float(etf_price), 2),
        "reasons": reasons,
        "risk": risk,
        "invalidation": invalidation,
        "ai": None,
    }


# ---------- Track record ----------


def track(hist: dict, closes: pd.DataFrame, today: str) -> pd.DataFrame:
    """Every past idea (not today's) with its return since the pick and whether the call has been right."""
    rows = []
    for day, ideas in hist["days"].items():
        if day >= today:
            continue
        for i in ideas:
            px, etf = closes.get(i["ticker"]), closes.get(i["etf"])
            if px is None or px.dropna().empty:
                continue
            now = px.dropna().iloc[-1]
            held = int((px.dropna().index > pd.Timestamp(day)).sum())
            ret = (now / i["price"] - 1) * 100
            etf_ret = (
                (etf.dropna().iloc[-1] / i["etf_price"] - 1) * 100 if etf is not None and i.get("etf_price") else None
            )
            rows.append(
                {
                    "date": day,
                    "sector": i["sector"],
                    "ticker": i["ticker"],
                    "lean": i["lean"],
                    "conviction": i.get("conviction"),
                    "price": i["price"],
                    "now": now,
                    "ret": ret,
                    "vs_sector": ret - etf_ret if etf_ret is not None else None,
                    "held": held,
                    "status": "Final" if held >= HORIZON else "Open",
                    "right": (ret > 0) if i["lean"] == "up" else (ret < 0),
                }
            )
    return pd.DataFrame(rows)


def record_summary(tr: pd.DataFrame) -> dict:
    if tr.empty:
        return {"ideas": 0, "final": 0, "hit_final": None, "hit_all": None, "up_avg": None, "down_avg": None}
    final = tr[tr["status"] == "Final"]
    up, down = tr[tr["lean"] == "up"], tr[tr["lean"] == "down"]
    return {
        "ideas": len(tr),
        "final": len(final),
        "hit_final": final["right"].mean() * 100 if len(final) else None,
        "hit_all": tr["right"].mean() * 100,
        "up_avg": up["ret"].mean() if len(up) else None,
        "down_avg": down["ret"].mean() if len(down) else None,
    }


# ---------- Backtest of the price-based part of the screen ----------
#
# Only momentum and trend can be tested honestly: there is no point-in-time history of forward P/E, revenue growth or
# analyst targets. Each month-end, within each sector group, the candidates are scored on those two signals using only
# prices up to that day; the top scorer is the "up" call and the bottom scorer the "down" call. Each is scored on the
# next month's return minus the group's equal-weight average.


def _month_end(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby(df.index.to_period("M")).tail(1)


def backtest_price_screen(groups: dict[str, list[str]], closes: pd.DataFrame, min_names: int = 4) -> pd.DataFrame:
    """One row per (month-end, sector): next-month excess return of the up and down calls vs. their group."""
    mom = closes.shift(21) / closes.shift(252) - 1
    trend = closes / closes.rolling(200).mean() - 1
    me_px, me_mom, me_trend = _month_end(closes), _month_end(mom), _month_end(trend)
    fwd = me_px.pct_change(fill_method=None).shift(-1) * 100
    w_m, w_t = dict((k, w) for k, w, _ in SIGNALS)["momentum"], dict((k, w) for k, w, _ in SIGNALS)["trend"]
    rows = []
    for sector, members in groups.items():
        cols = [c for c in members if c in closes]
        for day in me_px.index[:-1]:  # the last month has no "next month" yet
            sig = pd.DataFrame({"m": me_mom.loc[day, cols], "t": me_trend.loc[day, cols], "f": fwd.loc[day, cols]})
            sig = sig.dropna()
            if len(sig) < min_names:
                continue
            s = w_m * _z(sig["m"]) + w_t * _z(sig["t"])
            avg = sig["f"].mean()
            up, down = s.idxmax(), s.idxmin()
            rows.append(
                {
                    "date": day,
                    "sector": sector,
                    "up": up,
                    "down": down,
                    "up_ex": sig.loc[up, "f"] - avg,
                    "down_ex": sig.loc[down, "f"] - avg,
                }
            )
    return pd.DataFrame(rows)


def backtest_summary(bt: pd.DataFrame) -> dict | None:
    if bt.empty:
        return None
    monthly = bt.groupby("date")[["up_ex", "down_ex"]].mean()
    spread = monthly["up_ex"] - monthly["down_ex"]
    t = spread.mean() / spread.std() * np.sqrt(len(spread)) if len(spread) > 2 and spread.std() > 0 else np.nan
    return {
        "months": len(monthly),
        "calls": len(bt) * 2,
        "start": bt["date"].min(),
        "up_avg": monthly["up_ex"].mean(),
        "down_avg": monthly["down_ex"].mean(),
        "spread": spread.mean(),
        "t": t,
        "up_hit": (bt["up_ex"] > 0).mean() * 100,
        "down_hit": (bt["down_ex"] < 0).mean() * 100,
    }
