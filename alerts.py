"""Alert rules for the watchlist and open positions.

Every rule fires on a *transition* on the latest trading day (yesterday's close on one side of a level, today's on
the other), so a daily job never repeats yesterday's alerts and needs no memory between runs.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

BIG_MOVE_SIGMA = 2.5


@dataclass
class Alert:
    kind: str  # buy_zone | target | stop | big_move
    ticker: str
    title: str
    detail: str
    priority: int  # 1 (low) – 5 (urgent), matches ntfy priorities

    @property
    def line(self) -> str:
        return f"{self.title} · {self.detail}"


def _last_two(s: pd.Series) -> tuple[float, float] | None:
    s = s.dropna()
    return (s.iloc[-2], s.iloc[-1]) if len(s) >= 2 else None


def evaluate(config: dict, closes: pd.DataFrame, bench: str = "SPY") -> list[Alert]:
    """Check open positions and the watchlist against the latest close in `closes` (daily, one column per ticker).

    `config` is {"positions": [{ticker, entry_price, target, stop}], "watchlist": [{ticker, buy_below}]}.
    """
    alerts: list[Alert] = []

    for w in config.get("watchlist", []):
        t, level = w["ticker"], w.get("buy_below")
        pair = _last_two(closes[t]) if t in closes else None
        if not pair or not level:
            continue
        prev, last = pair
        if prev > level >= last:
            alerts.append(
                Alert(
                    "buy_zone",
                    t,
                    f"{t} entered your buy zone",
                    f"${last:,.2f} closed below your ${level:,.2f} buy-below ({(last / prev - 1) * 100:+.1f}% today)",
                    4,
                )
            )

    for p in config.get("positions", []):
        t = p["ticker"]
        pair = _last_two(closes[t]) if t in closes else None
        if not pair:
            continue
        prev, last = pair
        gain = (last / p["entry_price"] - 1) * 100 if p.get("entry_price") else None
        since = f", {gain:+.1f}% from your entry" if gain is not None else ""
        if p.get("target") and prev < p["target"] <= last:
            alerts.append(
                Alert(
                    "target",
                    t,
                    f"{t} hit your ${p['target']:,.0f} target",
                    f"closed at ${last:,.2f}{since}. Time to review the thesis",
                    4,
                )
            )
        if p.get("stop") and prev > p["stop"] >= last:
            alerts.append(
                Alert(
                    "stop",
                    t,
                    f"{t} fell below your ${p['stop']:,.0f} stop",
                    f"closed at ${last:,.2f}{since}. Check your 'I'm wrong if'",
                    5,
                )
            )

    tickers = dict.fromkeys([x["ticker"] for x in config.get("positions", []) + config.get("watchlist", [])])
    if bench in closes:
        b = closes[bench].pct_change(fill_method=None)
        for t in tickers:
            if t not in closes:
                continue
            r = closes[t].pct_change(fill_method=None)
            excess = (r - b).dropna().iloc[-253:]
            if len(excess) < 60:
                continue
            sigma = excess.iloc[:-1].std()
            today = excess.iloc[-1]
            if sigma > 0 and abs(today) > BIG_MOVE_SIGMA * sigma:
                alerts.append(
                    Alert(
                        "big_move",
                        t,
                        f"{t} {'jumped' if today > 0 else 'fell'} {abs(r.iloc[-1]) * 100:.1f}%",
                        f"vs. S&P 500 {b.iloc[-1] * 100:+.1f}%, an unusual {abs(today) / sigma:.1f}σ move for this stock",
                        3,
                    )
                )

    order = {"stop": 0, "target": 1, "buy_zone": 2, "big_move": 3}
    return sorted(alerts, key=lambda a: (order[a.kind], a.ticker))


def zone_status(price: float, buy_below: float) -> tuple[str, str]:
    """Where a price sits relative to a buy zone: (label, tone)."""
    if price <= buy_below:
        return "In buy zone", "good"
    gap = (price / buy_below - 1) * 100
    return (f"{gap:.0f}% above zone", "warn") if gap <= 5 else (f"{gap:.0f}% above zone", "flat")


def summarize(alerts: list[Alert], day: pd.Timestamp) -> tuple[str, str, int]:
    """(title, body, priority) for one combined notification."""
    n = len(alerts)
    title = f"Daily Market Brief · {n} alert{'s' if n != 1 else ''} · {day:%b %d}"
    body = "\n".join(f"• {a.line}" for a in alerts)
    return title, body, int(np.max([a.priority for a in alerts])) if alerts else 1
