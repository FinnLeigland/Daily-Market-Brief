"""Stock Lab: is this company expensive, risky, or growing compared with its peers?"""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import ai
import analytics as A
import config
import data
from theme import (
    DOWN,
    INK,
    INK_2,
    INK_3,
    MUTED,
    POS,
    SERIES,
    UP,
    caption,
    chart_title,
    chg_span,
    explain,
    html,
    section,
    style_fig,
    table_html,
)

# key, label, kind, which direction reads as "more" in words, plain-English meaning
METRICS = {
    "Valuation": [
        (
            "trailingPE",
            "P/E (trailing)",
            "x",
            "pricier",
            "Price ÷ last 12 months of earnings. How many dollars you pay per $1 of profit.",
        ),
        ("forwardPE", "P/E (forward)", "x", "pricier", "Price ÷ analysts' expected earnings for the next 12 months."),
        (
            "trailingPegRatio",
            "PEG ratio",
            "x",
            "pricier",
            "P/E ÷ expected growth rate. Around 1 is often called 'fair' for the growth you get.",
        ),
        (
            "priceToSalesTrailing12Months",
            "Price / Sales",
            "x",
            "pricier",
            "Market value ÷ revenue. Useful when earnings are small or negative.",
        ),
        (
            "enterpriseToEbitda",
            "EV / EBITDA",
            "x",
            "pricier",
            "Company value including debt ÷ operating cash earnings. Compares firms with different debt loads.",
        ),
    ],
    "Profitability": [
        (
            "grossMargins",
            "Gross margin",
            "pct",
            "higher",
            "Share of revenue left after the direct cost of making the product.",
        ),
        (
            "operatingMargins",
            "Operating margin",
            "pct",
            "higher",
            "Share of revenue left after all operating costs. A core measure of business quality.",
        ),
        (
            "profitMargins",
            "Net margin",
            "pct",
            "higher",
            "Share of revenue that ends up as profit after interest and taxes.",
        ),
        (
            "returnOnEquity",
            "Return on equity",
            "pct",
            "higher",
            "Profit ÷ shareholders' equity. Buybacks and debt can inflate it.",
        ),
    ],
    "Growth": [
        (
            "revenueGrowth",
            "Revenue growth (YoY)",
            "pct",
            "faster",
            "Latest quarter's revenue vs. the same quarter a year ago.",
        ),
        (
            "earningsGrowth",
            "Earnings growth (YoY)",
            "pct",
            "faster",
            "Latest quarter's earnings vs. the same quarter a year ago.",
        ),
    ],
    "Balance sheet & risk": [
        (
            "debtToEquity",
            "Debt / Equity",
            "de",
            "higher",
            "Total debt ÷ shareholders' equity. Higher means more financial leverage.",
        ),
        ("dividendYield", "Dividend yield", "divpct", "higher", "Annual dividends ÷ share price."),
        (
            "beta",
            "Beta (5Y)",
            "num",
            "higher",
            "How much the stock tends to move when the market moves 1%. Above 1 = more volatile than the market.",
        ),
    ],
}


def _val(info: dict, key: str, kind: str) -> float | None:
    v = info.get(key)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if kind == "pct":
        return v * 100
    if kind == "de":
        return v / 100  # yfinance reports D/E as a percentage
    return float(v)


def _fmt(v: float | None, kind: str) -> str:
    if v is None:
        return "—"
    if kind in ("pct", "divpct"):
        return f"{v:.1f}%"
    if kind in ("x", "de"):
        return f"{v:.1f}×"
    return f"{v:.2f}"


def _compare(v, median, word) -> tuple[str, str]:
    if v is None or median is None or pd.isna(median) or median == 0:
        return "", "flat"
    diff = (v - median) / abs(median)
    if abs(diff) < 0.1:
        return "In line with peers", "flat"
    opposite = {"pricier": "cheaper", "higher": "lower", "faster": "slower"}[word]
    return (f"{word.capitalize()} than peers", "hi") if diff > 0 else (f"{opposite.capitalize()} than peers", "lo")


def _pick_example():
    st.session_state["stock_ticker"] = st.session_state["stock_example"]


def _open_peer(chart_key: str, current: str):
    """Clicking a bar in the peer charts switches the lab to that company."""
    points = st.session_state[chart_key]["selection"]["points"]
    if points and points[0].get("y") and points[0]["y"] != current:
        st.session_state["stock_ticker"] = points[0]["y"]


def _pick_event(chart_key: str):
    points = st.session_state[chart_key]["selection"]["points"]
    event_days = sorted(st.session_state.get("stock_event_days", set()))
    for p in points:
        cd = p.get("customdata")
        day = (cd[0] if isinstance(cd, list) else cd) if cd else str(p.get("x", ""))[:10]
        try:
            clicked = pd.Timestamp(day)
        except ValueError:
            continue
        # The price line sits right under each marker, so accept clicks within a few days of a labeled move.
        nearest = min(event_days, key=lambda d: abs(pd.Timestamp(d) - clicked), default=None)
        if nearest and abs(pd.Timestamp(nearest) - clicked).days <= 4:
            st.session_state["stock_event"] = nearest
            return


def _event_overview(ticker: str, ev: dict, px: pd.Series, volume: pd.Series, etf: str) -> None:
    d, ret, bench = ev["date"], ev["ret"], ev["bench"]
    up = ret > 0
    verb = "jumped" if up else "fell"
    sentences = [
        f"{ticker} {verb} <b>{abs(ret):.1f}%</b> on {d:%A, %B} {d.day}, {d.year}, while the S&amp;P 500 "
        f"{'rose' if bench > 0 else 'fell'} {abs(bench):.1f}%."
    ]
    if ev["tag"].startswith("Market"):
        sentences.append("Most of the move came from the market as a whole, not from company-specific news.")
    else:
        sentences.append(
            f"That's a {ev['sigma']:.1f}-standard-deviation move relative to the market, so it was mostly "
            "about the company itself."
        )
    er = ev["earnings"]
    if er is not None and pd.notna(er.get("Reported EPS")):
        est, rep, surprise = er.get("EPS Estimate"), er["Reported EPS"], er.get("Surprise(%)")
        beat = rep >= est if pd.notna(est) else None
        sentences.append(
            f"It was the reaction to quarterly earnings: EPS of ${rep:.2f} vs. a ${est:.2f} estimate "
            f"({'a beat' if beat else 'a miss'} of {abs(surprise):.1f}%)."
            if beat is not None
            else f"It was the reaction to quarterly earnings (EPS ${rep:.2f})."
        )
        if beat and not up:
            sentences.append(
                "Beating estimates and still falling usually means expectations were even higher, or "
                "guidance for the next quarter disappointed."
            )
        elif beat is False and up:
            sentences.append("Missing estimates and still rising usually means the outlook was better than feared.")
    if not volume.empty and d in volume.index:
        avg = volume.loc[:d].iloc[-51:-1].mean()
        mult = volume.loc[d] / avg if avg else None
        if mult:
            sentences.append(
                f"Trading volume was <b>{mult:.1f}×</b> its 50-day average"
                + (", a sign big investors were acting on the news." if mult >= 2 else ".")
            )
    after = px.loc[d:]
    follow = []
    for k, label in [(5, "1 week"), (21, "1 month")]:
        if len(after) > k:
            follow.append(f"{label} later: {chg_span((after.iloc[k] / after.iloc[0] - 1) * 100, 1)}")
    hl = "".join(
        f'<a class="article" href="{escape(h["link"])}" target="_blank"><div class="t">{escape(h["title"])}</div>'
        f'<div class="src">{escape(h["source"])} · {h["published"]:%b %d}</div></a>'
        for h in ev["news"]
    )
    sector_txt = (
        f'<div><div class="k">Sector ({etf})</div><div class="v">{chg_span(ev["sector"], 1)}</div></div>'
        if ev.get("sector") is not None and pd.notna(ev["sector"])
        else ""
    )
    html(f"""
    <div class="event">
      <div class="event-head">
        <div><div class="eyebrow">What happened · {d:%b %d, %Y}</div>
          <div class="event-title">{ev["tag"]} <span class="chg {"up" if up else "down"}">{"▲" if up else "▼"} {ret:+.1f}%</span></div></div>
        <div class="event-stats">
          <div><div class="k">S&amp;P 500</div><div class="v">{chg_span(bench, 1)}</div></div>
          {sector_txt}
          <div><div class="k">vs. market</div><div class="v">{chg_span(ev["excess"], 1)}</div></div>
        </div>
      </div>
      {f'<div class="ai-line"><span>Why it moved</span>{escape(ev["ai"])}</div>' if ev.get("ai") else ""}
      <p>{" ".join(sentences)}</p>
      {f'<div class="follow">Did it stick? {" · ".join(follow)}</div>' if follow else ""}
      <div class="reading">{hl or '<p class="caption">No headlines found for these dates.</p>'}</div>
    </div>""")


def peer_context(ticker: str, info: dict) -> tuple[str, dict[str, dict]]:
    """The company's sector ETF and up to seven peers (that ETF's largest holdings) with their data."""
    etf = config.SECTOR_ETF_BY_NAME.get(info.get("sector") or "", "SPY")
    holdings = data.get_top_holdings(etf, ("SPY",), n=10) if etf != "SPY" else []
    peers = [h for h in holdings if h != ticker][:7]
    return etf, {k: v for k, v in data.get_infos(peers).items() if v.get("currentPrice")}


def price_history(ticker: str, etf: str) -> pd.DataFrame:
    return data.get_prices(tuple(sorted({ticker, etf, "SPY"})), period="5y")


def render() -> None:

    st.session_state.setdefault("stock_ticker", "NVDA")
    c1, c2 = st.columns([1, 3])
    with c1:
        ticker = st.text_input("Ticker", key="stock_ticker").strip().upper()
    with c2:
        st.pills("Examples", config.STOCK_EXAMPLES, key="stock_example", on_change=_pick_example)

    info = data.get_info(ticker)
    if not info.get("currentPrice"):
        st.warning(f"Couldn't load data for “{ticker}”. Check the symbol, or try again in a minute.")
        return

    etf, infos = peer_context(ticker, info)

    # ----- Header -----
    price, prev = info["currentPrice"], info.get("previousClose") or info["currentPrice"]
    lo, hi = info.get("fiftyTwoWeekLow") or price, info.get("fiftyTwoWeekHigh") or price
    pos = (price - lo) / (hi - lo) * 100 if hi > lo else 50
    cap = info.get("marketCap") or 0
    cap_txt = f"${cap / 1e12:.2f}T" if cap >= 1e12 else f"${cap / 1e9:.1f}B"
    target = info.get("targetMeanPrice")
    upside = (target / price - 1) * 100 if target else None
    html(f"""
    <div class="stock-head">
      <div>
        <div class="eyebrow">{escape(info.get("sector") or "")} · {escape(info.get("industry") or "")}</div>
        <div class="stock-name">{escape(info.get("longName") or ticker)} <span>{ticker}</span></div>
      </div>
      <div class="stock-price"><div class="p">${price:,.2f}</div>{chg_span((price / prev - 1) * 100, 2)}</div>
    </div>
    <div class="stock-facts">
      <div><div class="k">Market cap</div><div class="v">{cap_txt}</div></div>
      <div class="range"><div class="k">52-week range</div>
        <div class="bar"><div class="dot" style="left:{pos:.0f}%"></div></div>
        <div class="ends"><span>${lo:,.2f}</span><span>${hi:,.2f}</span></div></div>
      <div><div class="k">Analyst target ({info.get("numberOfAnalystOpinions") or 0})</div>
        <div class="v">{f"${target:,.2f}" if target else "—"} {chg_span(upside, 1) if upside is not None else ""}</div></div>
      <div><div class="k">Consensus</div><div class="v">{escape((info.get("recommendationKey") or "—").replace("_", " ").title())}</div></div>
    </div>
    """)
    if info.get("longBusinessSummary"):
        with st.expander("What does this company do?"):
            st.write(info["longBusinessSummary"])

    # ----- Price history and risk (needed for takeaways) -----
    hist = price_history(ticker, etf)
    px = hist[ticker].dropna()
    ma200 = px.rolling(200).mean()

    # ----- Scorecard -----
    medians = {}
    for group in METRICS.values():
        for key, _, kind, _, _ in group:
            vals = [_val(i, key, kind) for i in infos.values()]
            vals = [v for v in vals if v is not None]
            medians[key] = pd.Series(vals).median() if vals else None

    takeaways = []
    fpe, fpe_med = _val(info, "forwardPE", "x"), medians.get("forwardPE")
    if fpe and fpe_med:
        d = (fpe / fpe_med - 1) * 100
        takeaways.append(
            f"Valued at <b>{fpe:.1f}× forward earnings</b>, {abs(d):.0f}% {'above' if d > 0 else 'below'} "
            f"the peer median of {fpe_med:.1f}×. "
            + (
                "The market expects faster growth or higher quality than its peers."
                if d > 10
                else "Investors are paying less per dollar of expected profit than for peers."
                if d < -10
                else "Roughly what peers trade at."
            )
        )
    rg, rg_med = _val(info, "revenueGrowth", "pct"), medians.get("revenueGrowth")
    if rg is not None and rg_med is not None:
        takeaways.append(f"Revenue grew <b>{rg:.1f}%</b> year over year vs. a peer median of {rg_med:.1f}%.")
    om, om_med = _val(info, "operatingMargins", "pct"), medians.get("operatingMargins")
    if om is not None and om_med is not None:
        takeaways.append(f"Keeps <b>{om:.0f}¢ of every revenue dollar</b> as operating profit (peers: {om_med:.0f}¢).")
    if len(px) > 200:
        above = px.iloc[-1] > ma200.iloc[-1]
        takeaways.append(
            f"Shares are <b>{abs(px.iloc[-1] / ma200.iloc[-1] - 1) * 100:.0f}% {'above' if above else 'below'}</b> "
            f"their 200-day average, {'a long-term uptrend' if above else 'a sign the long-term trend has turned down'}."
        )
    if upside is not None:
        takeaways.append(
            f"Analysts' average target implies <b>{upside:+.0f}%</b> from here. Treat targets as sentiment, not forecasts."
        )
    html(
        '<div class="brief"><div class="eyebrow">Takeaways</div><ul>'
        + "".join(f"<li>{t}</li>" for t in takeaways)
        + "</ul></div>"
    )

    section("Fundamentals scorecard", f"vs. median of {len(infos)} peers: top holdings of {etf}")
    blocks = []
    for group, rows in METRICS.items():
        trs = []
        for key, label, kind, word, meaning in rows:
            v = _val(info, key, kind)
            verdict, tone = _compare(v, medians.get(key), word)
            trs.append(
                f'<tr title="{escape(meaning)}"><td class="m">{label}<div class="d">{escape(meaning)}</div></td>'
                f'<td class="v">{_fmt(v, kind)}</td><td class="pm">{_fmt(medians.get(key), kind)}</td>'
                f'<td class="vd {tone}">{verdict}</td></tr>'
            )
        blocks.append(
            f'<div class="score"><div class="score-h">{group}</div><table>'
            f'<tr class="th"><td></td><td>{ticker}</td><td>Peers</td><td></td></tr>{"".join(trs)}</table></div>'
        )
    html(f'<div class="score-grid">{"".join(blocks)}</div>')

    # ----- Peer charts -----
    section(
        "Against the peer group",
        "Highlighted bar is " + ticker + " · dotted line is the peer median · click any bar to open that company",
    )
    charts = [
        ("forwardPE", "Forward P/E", "x"),
        ("revenueGrowth", "Revenue growth", "pct"),
        ("operatingMargins", "Operating margin", "pct"),
    ]
    group = {ticker: info, **infos}
    fig = make_subplots(rows=1, cols=3, subplot_titles=[c[1] for c in charts], horizontal_spacing=0.09)
    for col, (key, label, kind) in enumerate(charts, start=1):
        vals = pd.Series({t: _val(i, key, kind) for t, i in group.items()}).dropna().sort_values()
        fig.add_bar(
            x=vals.values,
            y=vals.index,
            orientation="h",
            row=1,
            col=col,
            marker=dict(color=[POS if t == ticker else MUTED for t in vals.index], cornerradius=4),
            text=[_fmt(v, kind) for v in vals.values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="%{y}: %{text}<extra>" + label + "</extra>",
            showlegend=False,
        )
        if medians.get(key) is not None:
            fig.add_vline(x=medians[key], line=dict(color=INK_3, dash="dot", width=1.2), row=1, col=col)
    style_fig(fig, 330, ysuffix="").update_layout(hovermode="closest", bargap=0.3, margin=dict(t=40, r=30))
    fig.update_xaxes(showgrid=False, showticklabels=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", zeroline=False)
    fig.update_annotations(font=dict(size=12, color=INK_2))
    peer_key = f"peer_chart_{ticker}"
    st.plotly_chart(
        fig,
        width="stretch",
        key=peer_key,
        on_select=lambda: _open_peer(peer_key, ticker),
        selection_mode="points",
        config={"displayModeBar": False},
    )

    # ----- Price & trend, with the big moves explained -----
    section("Price and trend", "Labels mark unusually large moves vs. the market · click a label to see what happened")
    period = (
        st.segmented_control("Window", ["1Y", "3Y", "5Y"], default="1Y", key="stock_win", label_visibility="collapsed")
        or "1Y"
    )
    n = {"1Y": 252, "3Y": 756, "5Y": 1260}[period]
    view = pd.DataFrame({"Price": px, "50-day avg": px.rolling(50).mean(), "200-day avg": ma200}).iloc[-n:]

    moves = A.find_moves(
        px.iloc[-n - 1 :], hist["SPY"].iloc[-n - 1 :], max_events={"1Y": 8, "3Y": 10, "5Y": 12}[period]
    )
    days = [d.strftime("%Y-%m-%d") for d in moves.index]
    news = data.get_events_news(ticker, info.get("longName") or ticker, days)
    earnings = data.get_earnings(ticker)
    sector_r = hist[etf].pct_change() * 100 if etf in hist else None
    events = []
    for d, row in moves.iterrows():
        key = d.strftime("%Y-%m-%d")
        er = A.earnings_day(earnings, d)
        tag = A.tag_move(row["ret"], row["bench"], [h["title"] for h in news[key]], er is not None)
        events.append(
            {
                "day": key,
                "date": d,
                "tag": tag,
                "earnings": er,
                "news": news[key],
                **row.to_dict(),
                "sector": sector_r.get(d) if sector_r is not None else None,
                "ai": None,
            }
        )

    # Let Claude read each move's headlines and name the catalyst (cached on disk after the first run).
    if events and ai.available():
        with st.spinner("Reading the headlines behind each move…"):
            explained = ai.explain_moves(ticker, info.get("longName") or ticker, events)
        for e in events:
            if e["day"] in explained:
                e["ai"] = explained[e["day"]]["summary"]
                e["tag"] = explained[e["day"]]["tag"]

    fig = go.Figure()
    for i, col in enumerate(view.columns):
        fig.add_scatter(
            x=view.index,
            y=view[col],
            name=col,
            mode="lines",
            line=dict(color=SERIES[i], width=2 if i == 0 else 1.5, dash=None if i == 0 else "dot"),
            hovertemplate="$%{y:,.2f}",
        )
    for up in (True, False):
        evs = [e for e in events if (e["ret"] > 0) == up]
        if not evs:
            continue
        fig.add_scatter(
            x=[e["date"] for e in evs],
            y=[px.loc[e["date"]] for e in evs],
            mode="markers",
            name="Big up day" if up else "Big down day",
            marker=dict(
                symbol="triangle-up" if up else "triangle-down",
                size=13,
                color=UP if up else DOWN,
                line=dict(color="#0e0e0d", width=1.5),
            ),
            text=[f"{e['tag']} {e['ret']:+.0f}%" for e in evs],
            customdata=[[e["day"]] for e in evs],
            hovertemplate="%{x|%b %d, %Y}: %{text}<br><i>Click for what happened</i><extra></extra>",
        )
    # Labels as small tags offset from each marker (up above, down below). When two moves on the same side fall
    # within a few weeks of each other, the later tag steps further out so they never sit on top of each other.
    last_at: dict[bool, tuple[pd.Timestamp, int]] = {}
    for e in sorted(events, key=lambda e: e["date"]):
        up = e["ret"] > 0
        prev = last_at.get(up)
        level = 2 if prev and (e["date"] - prev[0]).days < 45 and prev[1] == 1 else 1
        last_at[up] = (e["date"], level)
        offset = 26 * level
        fig.add_annotation(
            x=e["date"],
            y=px.loc[e["date"]],
            text=f"{e['tag']} {e['ret']:+.0f}%",
            showarrow=True,
            arrowhead=0,
            arrowwidth=1,
            arrowcolor=MUTED,
            ax=0,
            ay=-offset if up else offset,
            font=dict(size=10, color=INK),
            bgcolor="rgba(24,24,23,0.92)",
            bordercolor=UP if up else DOWN,
            borderwidth=1,
            borderpad=3,
        )
    style_fig(fig, 400, ysuffix="").update_yaxes(tickprefix="$")
    fig.update_layout(hovermode="closest", clickmode="event+select")
    st.session_state["stock_event_days"] = {e["day"] for e in events}
    price_key = f"price_chart_{ticker}_{period}"
    st.plotly_chart(
        fig,
        width="stretch",
        key=price_key,
        on_select=lambda: _pick_event(price_key),
        selection_mode="points",
        config={"displayModeBar": False},
    )

    if events:
        chosen = st.session_state.get("stock_event")
        ev = next((e for e in events if e["day"] == chosen), None) or events[-1]
        _event_overview(ticker, ev, px, data.get_volume(ticker), etf)
    reason = ai.disabled_reason()
    if reason:
        caption(
            {
                "no_key": "Labels are keyword-based. Add an Anthropic API key (see README) and Claude will read the "
                "headlines and explain each move in one line.",
                "bad_key": "AI explanations are off: the Anthropic API key was rejected. Check the key in "
                ".streamlit/secrets.toml.",
                "no_access": "AI explanations are off: this API key can't use the model.",
            }[reason]
        )

    # ----- Risk vs market -----
    section("Risk vs. the market", f"{period} window · {ticker} vs. its sector ({etf}) and the S&P 500 (SPY)")
    window = hist.iloc[-n:]
    rows = {
        name: A.risk_stats(window[t], window["SPY"])
        for name, t in [(ticker, ticker), (f"Sector ({etf})", etf), ("S&P 500", "SPY")]
        if t in window
    }
    table = pd.DataFrame(rows).T[["cagr", "vol", "sharpe", "max_dd", "beta"]]
    table.columns = ["Annual return", "Volatility", "Sharpe", "Max drawdown", "Beta"]
    c1, c2 = st.columns([1.1, 1], gap="large")
    with c1:
        html(
            table_html(
                table,
                {
                    "Annual return": "{:+.1f}%",
                    "Volatility": "{:.1f}%",
                    "Sharpe": "{:.2f}",
                    "Max drawdown": "{:.1f}%",
                    "Beta": "{:.2f}",
                },
                emphasize=(ticker,),
            )
        )
        s, m = rows[ticker], rows["S&P 500"]
        caption(
            f"{ticker} has been <b>{s['vol'] / m['vol']:.1f}× as volatile</b> as the S&amp;P 500 and, with a beta of "
            f"{s['beta']:.2f}, has typically moved about {abs(s['beta']):.1f}% for every 1% move in the market. Its worst "
            f"peak-to-trough fall in this window was {s['max_dd']:.0f}%, vs. {m['max_dd']:.0f}% for the index.",
            teach=True,
        )
    with c2:
        fig = go.Figure()
        for i, (name, t) in enumerate([(ticker, ticker), ("S&P 500", "SPY")]):
            dd = A.drawdown(window[t])
            fig.add_scatter(
                x=dd.index,
                y=dd,
                name=name,
                mode="lines",
                line=dict(color=SERIES[i], width=2),
                hovertemplate="%{y:.1f}%",
            )
        chart_title("Drawdown: % below the previous peak")
        st.plotly_chart(style_fig(fig, 300), width="stretch")

    explain(
        "valuation vs. growth",
        """
    <p><b>Why compare with peers?</b> Valuation multiples only make sense relative to something. Within one sector,
    companies share similar business models, so differences in P/E usually reflect differences in expected growth,
    profitability or risk.</p>
    <p><b>The core trade-off.</b> A high P/E is justified when growth is fast and margins are high. When a stock is
    pricier than its peers but growing slower, ask what the market is seeing that the numbers don't show yet.</p>
    <p><b>Sharpe ratio</b> is annual return divided by volatility: return per unit of risk. Above 1 is strong over
    long periods. <b>Max drawdown</b> is the worst peak-to-trough fall, the loss you would have had to sit through.</p>
    """,
    )
