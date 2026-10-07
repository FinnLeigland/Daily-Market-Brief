"""Equity Screen: a new stock in each featured sector every day, with a lean, the reasons, and a running track record."""

from html import escape

import pandas as pd
import streamlit as st

import ai
import config
import data
import ideas as I
import signal_checks
from theme import caption, chg_span, explain, html, section, sparkline, warn

N_CANDIDATES = 10  # top holdings per sector ETF that compete for the daily pick


def _today() -> str:
    return config.today_et().isoformat()


def _candidates() -> dict[str, list[str]]:
    return {
        s["name"]: data.get_top_holdings(s["etf"], tuple(s["fallback_holdings"]), n=N_CANDIDATES)
        for s in config.FEATURED_SECTORS
    }


def inputs() -> tuple[dict[str, list[str]], pd.DataFrame, dict[str, dict]]:
    """Everything the screen needs: candidates per sector, two years of closes, and company data."""
    cands = _candidates()
    tickers = sorted({t for ts in cands.values() for t in ts} | {s["etf"] for s in config.FEATURED_SECTORS})
    closes = data.get_prices(tuple(tickers), period="2y")
    infos = data.get_infos(sorted({t for ts in cands.values() for t in ts}))
    return cands, closes, infos


def _generate(hist: dict, today: str) -> list[dict]:
    cands, closes, infos = inputs()
    chosen: set[str] = I.recent_tickers(hist, today)
    out = []
    for sector in config.FEATURED_SECTORS:
        tickers = [t for t in cands[sector["name"]] if t in closes]
        raw = I.raw_signals(closes[tickers], infos)
        if raw.empty:
            continue
        scored = I.score(raw)
        t = I.pick(scored, chosen, hist)
        if t is None:
            continue
        chosen.add(t)  # one stock can't fill two sectors on the same day (AI and Tech overlap)
        etf_px = closes[sector["etf"]].dropna().iloc[-1] if sector["etf"] in closes else None
        out.append(I.make_idea(sector, t, scored, etf_px or 0, today))
    return out


def _add_ai(todays: list[dict], today: str) -> bool:
    """Fill in Claude's write-up for ideas that don't have one yet. Returns True if anything changed."""
    todo = [i for i in todays if not i.get("ai")]
    if not todo or not ai.available() or st.session_state.get("ideas_ai_tried") == today:
        return False
    st.session_state["ideas_ai_tried"] = today  # one attempt per session per day, so a failure never loops
    news = {i["ticker"]: data.get_event_news(i["ticker"], i["name"], today) for i in todo}
    written = ai.write_ideas(todo, news)
    for i in todo:
        i["ai"] = written.get(i["ticker"])
    return bool(written)


def _open_in_lab() -> None:
    t = st.session_state.get("ideas_open")
    if t:
        st.session_state["stock_ticker"] = t
        st.session_state["main_tab"] = "Stock Lab"


def _card(i: dict, closes: pd.DataFrame) -> str:
    up = i["lean"] == "up"
    pill = f'<span class="pill {"up" if up else "down"}">{"▲ Leans up" if up else "▼ Leans down"}</span>'
    px = closes[i["ticker"]].dropna() if i["ticker"] in closes else pd.Series(dtype=float)
    day_chg = (px.iloc[-1] / px.iloc[-2] - 1) * 100 if len(px) > 1 else None
    spark = sparkline(px.iloc[-63:]) if len(px) > 63 else ""
    width = min(100, abs(i["score"]) / 1.2 * 100)
    body = ""
    if i.get("ai"):
        body = f'<div class="idea-thesis">{escape(i["ai"]["thesis"])}</div>'
    reasons = "".join(f"<li>{escape(r)}</li>" for r in i["reasons"]) or "<li>Signals were mixed.</li>"
    risk = i["ai"]["risk"] if i.get("ai") else i["risk"]
    return f"""
    <div class="card idea">
      <div class="card-top">
        <div><div class="eyebrow">{escape(i["sector"])}</div>
          <div class="card-name">{escape(i["name"])}</div>
          <div class="card-etf">{i["ticker"]} · picked at ${i["price"]:,.2f}{f" · today {chg_span(day_chg, 2)}" if day_chg is not None else ""}</div>
        </div>{pill}
      </div>
      {spark}
      <div class="conv"><span>Conviction</span><b>{i["conviction"]}</b>
        <div class="meter"><div class="{"up" if up else "down"}" style="width:{width:.0f}%"></div></div></div>
      {body}
      <div class="why"><div class="k">Why</div><ul>{reasons}</ul></div>
      <div class="idea-risk"><div class="k">Key risk</div>{escape(risk)}
        {f'<div class="k inv">Invalidation</div>{escape(i["invalidation"])}' if i.get("invalidation") else ""}</div>
    </div>"""


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _backtest(groups: tuple[tuple[str, tuple[str, ...]], ...]) -> dict | None:
    tickers = sorted({t for _, ts in groups for t in ts})
    closes = data.get_prices(tuple(tickers), period="10y")
    return I.backtest_summary(I.backtest_price_screen({g: list(ts) for g, ts in groups}, closes))


def _history_check() -> None:
    section("Has this kind of pick worked?", "Backtest of the screen's price signals · monthly, last 10 years")
    cands = _candidates()
    try:
        with st.spinner("Backtesting the screen…"):
            s = _backtest(tuple((g, tuple(ts)) for g, ts in cands.items()))
    except Exception:
        s = None
    if not s:
        st.info("The backtest couldn't run right now (price history didn't load). Try again in a minute.")
        return
    label, tone = signal_checks.verdict(s["t"], s["spread"])
    color = {"good": "var(--up)", "warn": "var(--warn)", "bad": "var(--down)", "flat": "var(--ink-3)"}[tone]

    def pts(x):
        return f"{x:+.2f} pts"

    html(
        '<div class="pulse">'
        + "".join(
            f'<div class="pulse-item"><div class="pulse-label">{k}</div><div class="pulse-value">{v}</div></div>'
            for k, v in [
                ("'Up' picks vs. their group", pts(s["up_avg"])),
                ("'Down' picks vs. their group", pts(s["down_avg"])),
                ("Spread per month", pts(s["spread"])),
                ("t-stat", f"{s['t']:.1f}"),
                ("Calls right", f"{(s['up_hit'] + s['down_hit']) / 2:.0f}%"),
                ("Verdict", f'<span style="color:{color};font-size:1rem">{label}</span>'),
            ]
        )
        + "</div>"
    )
    caption(
        f"Each month since {s['start']:%b %Y}, in each sector, the strongest and weakest stock on momentum and trend "
        f"were scored on the next month's return against their group's average ({s['months']} months, "
        f"{s['calls']:,} calls). A t-stat above about 2 is the usual bar for 'probably not luck'.",
        teach=True,
    )
    warn(
        "<b>If anything, this result is too kind.</b> The candidates are today's largest holdings, which are by "
        "definition stocks that went on to do well (survivorship bias), so the test flatters momentum. Valuation, "
        "growth and analyst targets can't be tested at all, because their history isn't available as it was known at "
        "the time."
    )


def _track_record(hist: dict, today: str) -> None:
    section("Track record", f"Every past idea, graded after {I.HORIZON} trading days (about a month)")
    past = [i for d, ideas in hist["days"].items() if d < today for i in ideas]
    if not past:
        html(
            '<div class="empty"><div class="h2">The record starts today</div><p>Each idea is saved with its price at '
            "the pick. Come back tomorrow and this table starts filling in: return since the pick, how it did against "
            "its sector ETF, and whether the call was right. That record is the honest test of these ideas.</p></div>"
        )
        return
    tickers = sorted({i["ticker"] for i in past} | {i["etf"] for i in past})
    tr = I.track(hist, data.get_prices(tuple(tickers), period="1y"), today)
    if tr.empty:
        st.info("Prices for past ideas couldn't be loaded right now. Try again in a minute.")
        return
    s = I.record_summary(tr)

    def pct(x, sign=False):
        return "—" if x is None or pd.isna(x) else (f"{x:+.1f}%" if sign else f"{x:.0f}%")

    html(
        '<div class="pulse">'
        + "".join(
            f'<div class="pulse-item"><div class="pulse-label">{k}</div><div class="pulse-value">{v}</div></div>'
            for k, v in [
                ("Ideas so far", f"{s['ideas']}"),
                ("Graded (final)", f"{s['final']}"),
                ("Right, final calls", pct(s["hit_final"])),
                ("Right so far, all", pct(s["hit_all"])),
                ("Avg move, 'up' calls", pct(s["up_avg"], True)),
                ("Avg move, 'down' calls", pct(s["down_avg"], True)),
            ]
        )
        + "</div>"
    )
    caption(
        "A useful screen should show 'up' calls rising more than 'down' calls over time. A dozen ideas is noise; "
        "judge it after a few months.",
        teach=True,
    )
    rows = []
    for r in tr.sort_values(["date", "sector"], ascending=[False, True]).itertuples():
        verdict = ("Right" if r.right else "Wrong") + (" so far" if r.status == "Open" else "")
        tone = "up" if r.right else "down"
        lean = "▲ Up" if r.lean == "up" else "▼ Down"
        rows.append(
            f'<tr><td>{pd.Timestamp(r.date):%b %d}</td><td>{escape(r.sector)}</td><td class="tk"><b>{r.ticker}</b></td>'
            f"<td>{lean}</td><td class='n'>${r.price:,.2f}</td><td class='n'>${r.now:,.2f}</td>"
            f"<td class='n'>{chg_span(r.ret, 1)}</td>"
            f"<td class='n'>{chg_span(r.vs_sector, 1) if r.vs_sector is not None and pd.notna(r.vs_sector) else '—'}</td>"
            f"<td class='n'>{r.held}d</td><td class='chg {tone}'>{verdict}</td></tr>"
        )
    html(
        '<div class="tbl-wrap"><table class="tbl"><tr class="th"><td>Picked</td><td>Sector</td><td>Stock</td>'
        "<td>Call</td><td>Price then</td><td>Now</td><td>Return</td><td>vs. sector</td><td>Held</td><td>Result</td></tr>"
        + "".join(rows)
        + "</table></div>"
    )


def render() -> None:
    today = _today()
    hist = I.load()
    if today not in hist["days"]:
        with st.spinner("Screening each sector for today's ideas…"):
            try:
                todays = _generate(hist, today)
            except Exception:
                todays = []
        if not todays:
            st.warning("Today's ideas couldn't be generated (market data didn't load). Refresh in a minute.")
            _track_record(hist, today)
            return
        hist["days"][today] = todays
        I.save(hist)
    todays = hist["days"][today]
    with st.spinner("Writing up today's ideas…"):
        if _add_ai(todays, today):
            I.save(hist)

    closes = data.get_prices(tuple(sorted({i["ticker"] for i in todays})), period="6mo")
    n_up = sum(i["lean"] == "up" for i in todays)
    section(
        "Today's ideas",
        f"{n_up} lean up, {len(todays) - n_up} lean down · one per sector, new every day · horizon about a month",
    )
    html('<div class="sectors ideas">' + "".join(_card(i, closes) for i in todays) + "</div>")
    if not ai.available():
        caption(
            "Add an Anthropic API key (see the README) and Claude will turn each screen into a short written thesis "
            "using that day's headlines.",
            teach=True,
        )
    st.pills(
        "Open in Stock Lab",
        [i["ticker"] for i in todays],
        key="ideas_open",
        on_change=_open_in_lab,
        label_visibility="visible",
    )
    warn(
        "These calls come from a simple screen, not a forecast or a recommendation. Check the backtest and the track "
        "record below before trusting them."
    )

    _history_check()
    _track_record(hist, today)

    explain(
        "how the ideas are picked",
        f"""
        <p>For each sector, the candidates are the {N_CANDIDATES} largest holdings of its ETF. Each candidate is
        scored on five signals, each ranked against the others in its sector:</p>
        <ul>
          <li><b>Momentum (35%)</b>: the past 12 months' return, skipping the latest month. Stocks that have been
          winning have tended to keep winning for a while; it's one of the most studied effects in finance.</li>
          <li><b>Trend (20%)</b>: how far the price is above or below its 200-day average.</li>
          <li><b>Valuation (15%)</b>: forward P/E; cheaper than the group scores higher.</li>
          <li><b>Growth (15%)</b>: revenue growth over the last year.</li>
          <li><b>Analyst targets (15%)</b>: upside to the average price target. Targets are sentiment, not forecasts.</li>
        </ul>
        <p>Above zero leans up, below zero leans down, and the further from zero the higher the conviction. The pick
        is the strongest score in either direction that hasn't been featured in the last {I.COOLDOWN_DAYS} days, so
        you get a new stock each day. Treat these as ideas to research, and let the backtest and the track record
        tell you whether they work.</p>
        """,
    )
