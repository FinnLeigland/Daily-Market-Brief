"""Trade Journal: track what you own, why you own it, and what it's worth."""

import json
from datetime import date
from html import escape

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import alerts as AL
import analytics as A
import config
import data
import journal as J
import notify
from theme import (
    BAD,
    GOOD,
    GRID,
    INK,
    INK_2,
    INK_3,
    MUTED,
    SERIES,
    WARN,
    caption,
    chart_title,
    chg_span,
    explain,
    fmt_pct,
    html,
    section,
    style_fig,
    table_html,
)

STATUS = {
    "target": ("Target hit: review", GOOD, "●"),
    "near_target": ("Near target", GOOD, "◐"),
    "stop": ("Below stop: re-check thesis", BAD, "■"),
    "near_stop": ("Near stop", WARN, "▲"),
    "ok": ("On track", INK_3, "○"),
}


def _status(price: float, target: float, stop: float) -> str:
    if target and price >= target:
        return "target"
    if stop and price <= stop:
        return "stop"
    if target and (target - price) / price < 0.05:
        return "near_target"
    if stop and (price - stop) / price < 0.05:
        return "near_stop"
    return "ok"


def _stars(n) -> str:
    n = int(n or 0)
    return f'<span class="stars" title="Conviction {n}/5">{"●" * n}<span>{"●" * (5 - n)}</span></span>'


def _money(x: float) -> str:
    return f"-${abs(x):,.0f}" if x < 0 else f"${x:,.0f}"


# ---------- Positions ----------


def _positions_view(jr: dict) -> None:
    open_pos = [p for p in jr["positions"] if p["status"] == "open"]
    closed = [p for p in jr["positions"] if p["status"] == "closed"]

    if not jr["positions"]:
        html(
            '<div class="empty"><div class="h2">Your journal is empty</div><p>Add the stocks you own below: why you '
            "bought them, what they're worth to you, and the price that would prove you wrong. Or load three example "
            "positions to see how it works, then delete them.</p></div>"
        )
        if st.button("Load example positions", key="jr_examples"):
            for ex in J.EXAMPLES:
                J.add_position(jr, **ex)
            st.rerun()

    if open_pos:
        tickers = sorted({p["ticker"] for p in open_pos})
        px = data.get_prices(tuple(tickers + ["SPY"]), period="2y")
        infos = data.get_infos(tickers)
        rows = []
        for p in open_pos:
            price = px[p["ticker"]].dropna().iloc[-1]
            prev = px[p["ticker"]].dropna().iloc[-2]
            rows.append(
                {
                    **p,
                    "price": price,
                    "day": (price / prev - 1) * 100,
                    "value": price * p["shares"],
                    "pnl": (price - p["entry_price"]) * p["shares"],
                    "pnl_pct": (price / p["entry_price"] - 1) * 100,
                    "to_target": (p["target"] / price - 1) * 100 if p["target"] else None,
                    "cushion": (price / p["stop"] - 1) * 100 if p["stop"] else None,
                    "analyst": infos.get(p["ticker"], {}).get("targetMeanPrice"),
                    "status": _status(price, p["target"], p["stop"]),
                    "days": (config.today_et() - date.fromisoformat(p["entry_date"])).days,
                }
            )
        df = pd.DataFrame(rows)
        value, cost = df["value"].sum(), (df["entry_price"] * df["shares"]).sum()
        alerts = df[df["status"].isin(["target", "stop", "near_stop"])]

        tiles = [
            ("Market value", f"${value:,.0f}", ""),
            ("Unrealized P&amp;L", _money(value - cost), chg_span((value / cost - 1) * 100, 1)),
            ("Today", _money((df["value"] - df["value"] / (1 + df["day"] / 100)).sum()), ""),
            ("Open positions", str(len(df)), ""),
            ("Need attention", str(len(alerts)), '<span class="chg flat">at target or near stop</span>'),
        ]
        html(
            '<div class="pulse">'
            + "".join(
                f'<div class="pulse-item"><div class="pulse-label">{k}</div><div class="pulse-value">{v}</div>{d}</div>'
                for k, v, d in tiles
            )
            + "</div>"
        )

        section("Positions", "Live prices · your targets vs. the analyst consensus")
        trs = []
        for r in df.sort_values("value", ascending=False).itertuples():
            label, color, icon = STATUS[r.status]
            analyst = f"${r.analyst:,.0f}" if r.analyst else "—"
            trs.append(f"""<tr>
              <td><b class="tk">{r.ticker}</b><div class="d">{r.shares:g} sh · {r.days}d held</div></td>
              <td class="n">${r.price:,.2f}<div class="d">{chg_span(r.day, 2)}</div></td>
              <td class="n">${r.entry_price:,.2f}</td>
              <td class="n">{_money(r.pnl)}<div class="d">{chg_span(r.pnl_pct, 1)}</div></td>
              <td class="n">${r.target:,.0f}<div class="d">{fmt_pct(r.to_target, 0, arrow=False)} to go</div></td>
              <td class="n">${r.stop:,.0f}<div class="d">{fmt_pct(r.cushion, 0, arrow=False)} cushion</div></td>
              <td class="n">{analyst}</td>
              <td>{_stars(r.conviction)}</td>
              <td><span class="status" style="color:{color}">{icon} {label}</span></td></tr>""")
        html(
            '<div class="tbl-wrap"><table class="tbl"><tr class="th"><td>Position</td><td>Price</td><td>Entry</td>'
            "<td>P&amp;L</td><td>My target</td><td>Stop</td><td>Analysts</td><td>Conviction</td><td>Status</td></tr>"
            + "".join(trs)
            + "</table></div>"
        )

        # Stop → target ranges
        chart_title("Where each stock sits between your stop and your target")
        fig = go.Figure()
        d = df.sort_values("ticker", ascending=False)
        for i, r in enumerate(d.itertuples()):
            prog = (r.price - r.stop) / (r.target - r.stop) * 100
            entry = (r.entry_price - r.stop) / (r.target - r.stop) * 100
            fig.add_scatter(
                x=[0, 100],
                y=[r.ticker] * 2,
                mode="lines",
                line=dict(color=MUTED, width=8),
                hoverinfo="skip",
                showlegend=False,
            )
            fig.add_scatter(
                x=[entry],
                y=[r.ticker],
                mode="markers",
                marker=dict(size=12, color="rgba(0,0,0,0)", line=dict(color=INK_2, width=2)),
                name="Entry",
                showlegend=i == 0,
                hovertemplate=f"Entry ${r.entry_price:,.2f}<extra>{r.ticker}</extra>",
            )
            fig.add_scatter(
                x=[np.clip(prog, -10, 110)],
                y=[r.ticker],
                mode="markers",
                name="Now",
                marker=dict(
                    size=13,
                    color=STATUS[r.status][1] if r.status != "ok" else SERIES[0],
                    line=dict(color="#0e0e0d", width=2),
                ),
                showlegend=i == 0,
                hovertemplate=f"Now ${r.price:,.2f} ({prog:.0f}% of the way)<extra>{r.ticker}</extra>",
            )
        style_fig(fig, 90 + 46 * len(d), ysuffix="").update_layout(hovermode="closest", margin=dict(t=30, l=8, r=8))
        fig.update_xaxes(
            range=[-12, 112],
            tickvals=[0, 50, 100],
            ticktext=["Stop", "Halfway", "Target"],
            showgrid=True,
            gridcolor=GRID,
        )
        fig.update_yaxes(zeroline=False, gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")

        # Per-position detail and editing
        section("Manage positions", "Thesis, update your view, close, or delete")
        for r in df.sort_values("value", ascending=False).itertuples():
            with st.expander(f"{r.ticker}: {STATUS[r.status][0]} · {fmt_pct(r.pnl_pct, 1)}"):
                c1, c2 = st.columns([1.3, 1], gap="large")
                with c1:
                    html(
                        f'<div class="thesis"><div class="k">Why I own it</div><p>{escape(r.thesis)}</p>'
                        f'<div class="k">I\'m wrong if</div><p>{escape(r.wrong_if or "—")}</p>'
                        f'<div class="k">Horizon</div><p>{escape(r.horizon or "—")}</p></div>'
                    )
                with c2:
                    with st.form(f"upd_{r.id}"):
                        a, b, c = st.columns(3)
                        tgt = a.number_input("Target", value=float(r.target), min_value=0.0, step=1.0)
                        stp = b.number_input("Stop", value=float(r.stop), min_value=0.0, step=1.0)
                        conv = c.number_input("Conviction", value=int(r.conviction), min_value=1, max_value=5)
                        note = st.text_area("What changed? (saved to your thesis log)", height=80)
                        if st.form_submit_button("Save update"):
                            J.update_position(jr, r.id, target=tgt, stop=stp, conviction=int(conv))
                            changes = [
                                f"target ${r.target:,.0f} → ${tgt:,.0f}" if tgt != r.target else "",
                                f"stop ${r.stop:,.0f} → ${stp:,.0f}" if stp != r.stop else "",
                                f"conviction {r.conviction} → {int(conv)}" if conv != r.conviction else "",
                            ]
                            changes = "; ".join(c for c in changes if c)
                            J.add_note(
                                jr,
                                r.ticker,
                                (note.strip() + (f" ({changes})" if changes else "")).strip()
                                or changes
                                or "Reviewed, no change.",
                                int(conv),
                                tgt,
                                kind="update",
                            )
                            st.rerun()
                    a, b = st.columns(2)
                    exit_px = a.number_input("Exit price", value=float(round(r.price, 2)), key=f"exit_{r.id}")
                    if a.button("Close position", key=f"close_{r.id}"):
                        J.update_position(
                            jr, r.id, status="closed", exit_price=exit_px, exit_date=config.today_et().isoformat()
                        )
                        J.add_note(
                            jr,
                            r.ticker,
                            f"Closed at ${exit_px:,.2f} ({(exit_px / r.entry_price - 1) * 100:+.1f}%).",
                            None,
                            None,
                            kind="close",
                        )
                        st.rerun()
                    if b.checkbox("Confirm delete", key=f"cdel_{r.id}") and b.button("Delete", key=f"del_{r.id}"):
                        J.delete_position(jr, r.id)
                        st.rerun()

        # Portfolio-level risk
        if len(df) > 1:
            section("How concentrated is your risk?", "1 year of daily returns · weights by market value")
            w = dict(zip(df["ticker"], df["value"], strict=True))
            yr = px[list(w) + ["SPY"]].iloc[-253:].ffill()
            rc = A.risk_contributions(yr[list(w)], w).sort_values()
            wt = (pd.Series(w) / value * 100).reindex(rc.index)
            port_r = yr[list(w)].pct_change().dropna() @ (pd.Series(w) / value)
            spy_r = yr["SPY"].pct_change().dropna()
            beta = port_r.cov(spy_r) / spy_r.var()
            c1, c2 = st.columns([1.3, 1], gap="large")
            with c1:
                fig = go.Figure()
                fig.add_bar(
                    y=rc.index,
                    x=wt,
                    name="Share of money",
                    orientation="h",
                    marker=dict(color=MUTED, cornerradius=4),
                    hovertemplate="%{y}: %{x:.0f}% of money<extra></extra>",
                )
                fig.add_bar(
                    y=rc.index,
                    x=rc,
                    name="Share of risk",
                    orientation="h",
                    marker=dict(color=SERIES[1], cornerradius=4),
                    hovertemplate="%{y}: %{x:.0f}% of risk<extra></extra>",
                )
                style_fig(fig, 90 + 50 * len(rc)).update_layout(barmode="group", hovermode="closest", bargap=0.25)
                fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID)
                fig.update_yaxes(ticksuffix="", zeroline=False, gridcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig, width="stretch")
            with c2:
                top = rc.idxmax()
                caption(
                    f"Your portfolio's beta is <b>{beta:.2f}</b>: on a day the S&amp;P 500 falls 1%, it has tended "
                    f"to fall about {beta:.1f}%. <b>{top}</b> is {wt[top]:.0f}% of your money but {rc[top]:.0f}% "
                    "of your risk. If one position drives most of the swings, sizing it down cuts risk faster than "
                    "adding new names."
                )

    if closed:
        section("Closed trades", "Realized results")
        trs = "".join(
            f'<tr><td><b class="tk">{p["ticker"]}</b></td><td class="n">${p["entry_price"]:,.2f}</td>'
            f'<td class="n">${p["exit_price"]:,.2f}</td><td class="n">{chg_span((p["exit_price"] / p["entry_price"] - 1) * 100)}</td>'
            f'<td class="n">{_money((p["exit_price"] - p["entry_price"]) * p["shares"])}</td>'
            f"<td>{'Hit target' if p['exit_price'] >= p['target'] else 'Stopped out' if p['exit_price'] <= p['stop'] else 'Exited early'}</td></tr>"
            for p in closed
        )
        html(
            '<div class="tbl-wrap"><table class="tbl"><tr class="th"><td>Ticker</td><td>Entry</td><td>Exit</td>'
            f"<td>Return</td><td>P&amp;L</td><td>Outcome</td></tr>{trs}</table></div>"
        )

    with st.expander("Add a position", expanded=not jr["positions"]), st.form("add_pos", clear_on_submit=True):
        a, b, c, d = st.columns(4)
        ticker = a.text_input("Ticker").strip().upper()
        shares = b.number_input("Shares", min_value=0.0, value=10.0, step=1.0)
        entry = c.number_input("Entry price", min_value=0.0, value=0.0, step=1.0)
        entry_date = d.date_input("Entry date", value=config.today_et())
        a, b, c, d = st.columns(4)
        target = a.number_input("My price target", min_value=0.0, value=0.0, step=1.0)
        stop = b.number_input("Stop (I'm wrong below)", min_value=0.0, value=0.0, step=1.0)
        conviction = c.slider("Conviction", 1, 5, 3)
        horizon = d.selectbox("Horizon", ["< 6 months", "6–12 months", "1–2 years", "2–3 years", "3+ years"])
        thesis = st.text_area("Why I own it (my thesis)", placeholder="What does the market not appreciate yet?")
        wrong_if = st.text_area("I'm wrong if…", placeholder="The specific evidence that would make you sell.")
        if st.form_submit_button("Add to journal"):
            info = data.get_info(ticker) if ticker else {}
            if not info.get("currentPrice"):
                st.error(f"Couldn't find “{ticker}”.")
            elif not (entry and target and stop and thesis.strip()):
                st.error("Entry price, target, stop and a thesis are required. Writing them down is the point.")
            elif not stop < entry < target:
                st.error("Your stop should be below your entry, and your target above it.")
            else:
                J.add_position(
                    jr,
                    ticker=ticker,
                    shares=shares,
                    entry_price=entry,
                    entry_date=entry_date.isoformat(),
                    target=target,
                    stop=stop,
                    conviction=conviction,
                    horizon=horizon,
                    thesis=thesis.strip(),
                    wrong_if=wrong_if.strip(),
                )
                st.rerun()


# ---------- Price target builder ----------


def _target_view(jr: dict) -> None:
    held = sorted({p["ticker"] for p in jr["positions"] if p["status"] == "open"})
    c1, c2 = st.columns([1, 3])
    st.session_state.setdefault("pt_ticker", held[0] if held else "AAPL")
    ticker = c1.text_input("Ticker", key="pt_ticker").strip().upper()
    if held:
        c2.pills(
            "Your positions",
            held,
            key="pt_pick",
            on_change=lambda: st.session_state.update(pt_ticker=st.session_state["pt_pick"]),
        )

    info = data.get_info(ticker)
    price = info.get("currentPrice")
    if not price:
        st.warning(f"Couldn't load data for “{ticker}”.")
        return
    html(
        f'<div class="stock-head"><div><div class="eyebrow">{escape(info.get("sector") or "")} · '
        f'{escape(info.get("industry") or "")}</div><div class="stock-name">{escape(info.get("longName") or ticker)} '
        f'<span>{ticker}</span></div></div><div class="stock-price"><div class="p">${price:,.2f}</div></div></div>'
    )

    # Peer multiples for the P/E method
    etf = config.SECTOR_ETF_BY_NAME.get(info.get("sector") or "")
    peers = [h for h in (data.get_top_holdings(etf, ("SPY",), n=10) if etf else []) if h != ticker][:7]
    peer_pe = pd.Series([i.get("forwardPE") for i in data.get_infos(peers).values()], dtype=float).dropna()
    peer_pe = peer_pe[(peer_pe > 0) & (peer_pe < 150)]
    own_pe = info.get("forwardPE")
    q = (
        peer_pe.quantile([0.25, 0.5, 0.75]).tolist()
        if len(peer_pe) >= 3
        else [own_pe * 0.8, own_pe, own_pe * 1.2]
        if own_pe
        else [15, 20, 25]
    )

    section("Your assumptions", "Defaults come from the company's numbers and its sector peers. Change them.")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        html('<div class="chart-title">Method 1 · Earnings × multiple</div>')
        eps = st.number_input(
            "EPS over the next 12 months ($)",
            value=float(round(info.get("forwardEps") or 0, 2)),
            step=0.1,
            help="Analysts' consensus forward EPS by default.",
        )
        a, b, c = st.columns(3)
        pe_bear = a.number_input("Bear P/E", value=float(round(q[0], 1)), step=0.5)
        pe_base = b.number_input("Base P/E", value=float(round(q[1], 1)), step=0.5)
        pe_bull = c.number_input("Bull P/E", value=float(round(q[2], 1)), step=0.5)
        caption(
            f"Peer forward P/Es (top holdings of {etf or 'n/a'}): 25th pct {q[0]:.1f}×, median {q[1]:.1f}×, "
            f"75th pct {q[2]:.1f}×. {ticker} trades at {own_pe or float('nan'):.1f}× today."
        )
    fcf = info.get("freeCashflow")
    shares = info.get("sharesOutstanding")
    cash, debt = info.get("totalCash") or 0, info.get("totalDebt") or 0
    dcf_ok = bool(fcf and fcf > 0 and shares) and info.get("sector") != "Financial Services"
    with c2:
        html('<div class="chart-title">Method 2 · Discounted cash flow</div>')
        if dcf_ok:
            rg = info.get("revenueGrowth") or 0.05
            a, b, c = st.columns(3)
            g = (
                a.number_input("FCF growth, yrs 1–10 (%)", value=float(round(np.clip(rg * 100, 2, 20), 1)), step=0.5)
                / 100
            )
            r = (
                b.number_input(
                    "Required return (%)",
                    value=9.0,
                    step=0.5,
                    help="Your discount rate: the annual return you demand for owning this stock.",
                )
                / 100
            )
            tg = c.number_input("Growth after year 10 (%)", value=2.5, step=0.25) / 100
            caption(
                f"Starts from trailing free cash flow of ${fcf / 1e9:,.1f}B, adds ${cash / 1e9:,.1f}B cash, subtracts "
                f"${debt / 1e9:,.1f}B debt, over {shares / 1e9:,.2f}B shares."
            )
        else:
            caption(
                "A cash-flow model doesn't fit here: "
                + (
                    "banks and insurers don't have meaningful free cash flow "
                    "(lending is their business), so they're usually valued on P/E or price-to-book."
                    if info.get("sector") == "Financial Services"
                    else "free cash flow is negative or unavailable."
                )
            )

    # Build the football field
    lines = []
    lo52, hi52 = info.get("fiftyTwoWeekLow"), info.get("fiftyTwoWeekHigh")
    if lo52 and hi52:
        lines.append(("52-week range", lo52, None, hi52))
    if info.get("targetLowPrice") and info.get("targetHighPrice"):
        lines.append(
            (
                f"Analyst targets ({info.get('numberOfAnalystOpinions') or 0})",
                info["targetLowPrice"],
                info.get("targetMeanPrice"),
                info["targetHighPrice"],
            )
        )
    if eps > 0:
        lines.append(("Earnings × P/E", eps * pe_bear, eps * pe_base, eps * pe_bull))
    if dcf_ok:
        vals = [A.dcf_per_share(fcf, g, rr, tg, shares, cash, debt) for rr in (r + 0.01, r, max(r - 0.01, tg + 0.005))]
        lines.append(("DCF (±1 pt return)", *vals))
    my = next((p for p in jr["positions"] if p["ticker"] == ticker and p["status"] == "open"), None)

    section(
        "Valuation range",
        "The bars show each method's low–high range, the white tick is the base case, and the dotted line is today's price",
    )
    fig = go.Figure()
    for name, low, mid, high in reversed(lines):
        fig.add_bar(
            y=[name],
            x=[high - low],
            base=[low],
            orientation="h",
            marker=dict(color=SERIES[0], opacity=0.8, cornerradius=4),
            hovertemplate=f"{name}<br>${low:,.0f} – ${high:,.0f}<extra></extra>",
            showlegend=False,
            width=0.5,
        )
        fig.add_annotation(
            x=low, y=name, text=f"${low:,.0f} ", showarrow=False, xanchor="right", font=dict(size=11, color=INK_2)
        )
        fig.add_annotation(
            x=high, y=name, text=f" ${high:,.0f}", showarrow=False, xanchor="left", font=dict(size=11, color=INK_2)
        )
        if mid:
            fig.add_scatter(
                x=[mid],
                y=[name],
                mode="markers",
                marker=dict(symbol="line-ns", size=22, color=INK, line=dict(width=3, color=INK)),
                hovertemplate=f"Base ${mid:,.0f}<extra>{name}</extra>",
                showlegend=False,
            )
    fig.add_vline(
        x=price,
        line=dict(color=INK, dash="dot", width=1.5),
        annotation=dict(text=f"Price ${price:,.0f}", font=dict(size=11, color=INK)),
        annotation_position="top",
    )
    if my:
        fig.add_vline(
            x=my["target"],
            line=dict(color=GOOD, dash="dash", width=1.5),
            annotation=dict(text=f"My target ${my['target']:,.0f}", font=dict(size=11, color=GOOD)),
            annotation_position="bottom",
        )
    style_fig(fig, 110 + 62 * len(lines), ysuffix="").update_layout(
        hovermode="closest", margin=dict(t=36, b=36, l=8, r=60)
    )
    fig.update_xaxes(tickprefix="$", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(zeroline=False, gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")

    bases = [m for _, _, m, _ in lines[1:] if m]
    blended = float(np.mean(bases)) if bases else None
    if blended:
        c1, c2 = st.columns([2, 1], gap="large")
        with c1:
            caption(
                f"Averaging the base cases gives a blended target of <b>${blended:,.0f}</b>, "
                f"<b>{(blended / price - 1) * 100:+.0f}%</b> from today. When the methods disagree widely, that spread "
                "is the real answer: the value depends on which assumption you believe."
            )
        with c2:
            if my and st.button(f"Set ${blended:,.0f} as my target for {ticker}", key="pt_save"):
                J.update_position(jr, my["id"], target=round(blended, 2))
                J.add_note(
                    jr,
                    ticker,
                    f"Updated target from the valuation builder: ${my['target']:,.0f} → ${blended:,.0f}.",
                    my["conviction"],
                    round(blended, 2),
                    kind="update",
                )
                st.rerun()
        a, b, _ = st.columns([1, 1.4, 1.6], vertical_alignment="bottom")
        mos = a.number_input(
            "Margin of safety (%)",
            min_value=0,
            max_value=50,
            value=15,
            step=5,
            key="pt_mos",
            help="How far below your blended value you'd want to buy, as a cushion for being wrong.",
        )
        buy_below = blended * (1 - mos / 100)
        if b.button(
            f"Watch {ticker} below ${buy_below:,.0f}", key="pt_watch", icon=":material/notifications:", width="stretch"
        ):
            J.watch(
                jr,
                ticker,
                round(buy_below, 2),
                f"Blended value ${blended:,.0f}, {mos}% margin of safety",
                source="builder",
            )
            st.toast(f"{ticker} added to your watchlist with a buy zone below ${buy_below:,.0f}")

    # Reverse DCF
    if dcf_ok:
        section("What's priced in?", "Reverse DCF: solve for the growth that justifies today's price")
        implied = A.implied_growth(price, fcf, r, tg, shares, cash, debt)
        rg = (info.get("revenueGrowth") or 0) * 100
        c1, c2 = st.columns([1, 1.3], gap="large")
        with c1:
            if implied is not None:
                verdict = (
                    "a high bar"
                    if implied * 100 > rg + 3
                    else "a low bar"
                    if implied * 100 < rg - 3
                    else "roughly in line with recent growth"
                )
                html(
                    f'<div class="hero"><div class="eyebrow">At ${price:,.2f}, the market expects</div>'
                    f'<div class="hero-big">{implied * 100:.1f}% a year</div>'
                    f"<p>free-cash-flow growth for the next 10 years, at a {r * 100:.1f}% required return. Revenue grew "
                    f"{rg:.1f}% last quarter, so that's <b>{verdict}</b>.</p></div>"
                )
            else:
                caption(
                    "The price is outside what any growth rate between −50% and 100% can explain with these inputs."
                )
        with c2:
            grid = (
                pd.DataFrame(
                    {
                        f"{d * 100:.0f}% return": [
                            A.implied_growth(price, fcf, d, t, shares, cash, debt) for t in (0.02, 0.025, 0.03)
                        ]
                        for d in (0.08, 0.09, 0.10, 0.11)
                    },
                    index=["2.0% terminal", "2.5% terminal", "3.0% terminal"],
                )
                * 100
            )
            chart_title("Implied 10-year growth under different assumptions")
            html(table_html(grid, {c: "{:.1f}%" for c in grid.columns}, emphasize=("2.5% terminal",)))
            caption(
                "A higher required return means you demand more from the stock, so it needs faster growth to justify "
                "the same price. Use this to sanity-check your thesis: do you believe the company can beat this number?",
                teach=True,
            )

    explain(
        "price targets",
        """
    <p><b>Earnings × multiple</b> is how most analysts set targets: estimate next year's earnings per share, then
    decide what P/E the market will pay. The P/E range comes from the company's own peers.</p>
    <p><b>DCF (discounted cash flow)</b> values the business as all the cash it will ever produce, discounted back
    to today. It's very sensitive to the growth and required-return inputs; small changes swing the answer a lot.</p>
    <p><b>Reverse DCF</b> flips the question. Instead of guessing growth to get a value, it takes the price as given
    and asks what growth it implies. That's often more useful: it tells you what you have to believe to own the stock.</p>
    """,
    )


# ---------- Thesis log ----------


def _log_view(jr: dict) -> None:
    tickers = sorted({n["ticker"] for n in jr["notes"]})
    if not tickers:
        caption("No notes yet. Add a position first; every update you save shows up here.")
        return
    ticker = st.selectbox("Stock", tickers, key="log_ticker")
    notes = sorted([n for n in jr["notes"] if n["ticker"] == ticker], key=lambda n: n["date"])
    pos = next((p for p in jr["positions"] if p["ticker"] == ticker), None)

    px = data.get_prices((ticker, "SPY"), period="2y")[ticker].dropna()
    start = pd.Timestamp(pos["entry_date"]) - pd.Timedelta(days=30) if pos else px.index[-252]
    px = px[px.index >= start]
    fig = go.Figure()
    fig.add_scatter(
        x=px.index, y=px, mode="lines", name="Price", line=dict(color=SERIES[0], width=2), hovertemplate="$%{y:,.2f}"
    )
    targets = [(pd.Timestamp(n["date"]), n["target"]) for n in notes if n.get("target")]
    if targets:
        tx = [t for t, _ in targets] + [px.index[-1]]
        ty = [v for _, v in targets] + [targets[-1][1]]
        fig.add_scatter(
            x=tx,
            y=ty,
            mode="lines",
            line=dict(color=GOOD, width=1.5, dash="dash", shape="hv"),
            name="My target",
            hovertemplate="Target $%{y:,.0f}",
        )
    if pos:
        fig.add_hline(
            y=pos["entry_price"],
            line=dict(color=INK_3, width=1, dash="dot"),
            annotation=dict(text=f"Entry ${pos['entry_price']:,.0f}", font=dict(size=10, color=INK_3)),
        )
        fig.add_hline(
            y=pos["stop"],
            line=dict(color=BAD, width=1, dash="dot"),
            annotation=dict(text=f"Stop ${pos['stop']:,.0f}", font=dict(size=10, color=BAD)),
        )
    note_x = [pd.Timestamp(n["date"]) for n in notes]
    note_y = [px.asof(x) if x >= px.index[0] else px.iloc[0] for x in note_x]
    fig.add_scatter(
        x=note_x,
        y=note_y,
        mode="markers",
        name="Notes",
        marker=dict(size=11, color=WARN, line=dict(color="#0e0e0d", width=2)),
        customdata=[escape(n["text"][:120]) for n in notes],
        hovertemplate="%{x|%b %d}: %{customdata}<extra></extra>",
    )
    st.plotly_chart(style_fig(fig, 340, ysuffix="").update_yaxes(tickprefix="$"), width="stretch")

    items = "".join(
        f'<div class="note {n["kind"]}"><div class="when">{date.fromisoformat(n["date"]):%b %d, %Y}'
        f'<span>{n["kind"].title()}</span></div><div class="txt">{escape(n["text"])}</div>'
        f'<div class="meta">{_stars(n["conviction"]) if n.get("conviction") else ""}'
        f"{' · target $' + format(n['target'], ',.0f') if n.get('target') else ''}</div></div>"
        for n in reversed(notes)
    )
    c1, c2 = st.columns([1.5, 1], gap="large")
    with c1:
        html(f'<div class="notes">{items}</div>')
    with c2:
        with st.form("log_note", clear_on_submit=True):
            text = st.text_area("New note", placeholder="Earnings beat but guidance was soft…")
            conv = st.slider("Conviction now", 1, 5, int(pos["conviction"]) if pos else 3)
            if st.form_submit_button("Add note") and text.strip():
                J.add_note(jr, ticker, text.strip(), conv, pos["target"] if pos else None)
                if pos:
                    J.update_position(jr, pos["id"], conviction=conv)
                st.rerun()
        caption(
            "Write down what you think <i>before</i> earnings and big news, then compare afterwards. The log is "
            "the most honest record of whether your reasoning, not just your luck, is improving.",
            teach=True,
        )


def _remove_watch(jr: dict) -> None:
    item = st.session_state.get("wl_remove")
    if item:
        J.unwatch(jr, item)


def _watchlist_view(jr: dict) -> None:
    with st.expander("Add to watchlist", expanded=not jr["watchlist"]):
        with st.form("wl_add", clear_on_submit=True, border=False):
            a, b, c = st.columns([1, 1, 2])
            ticker = a.text_input("Ticker").strip().upper()
            level = b.number_input("Buy below ($)", min_value=0.0, value=0.0, step=1.0)
            note = c.text_input("Note", placeholder="Why you'd buy it at this price")
            if st.form_submit_button("Add", icon=":material/add:"):
                if not data.get_info(ticker).get("currentPrice"):
                    st.error(f"Couldn't find “{ticker}”.")
                elif level <= 0:
                    st.error("Set the price you'd want to buy below.")
                else:
                    J.watch(jr, ticker, level, note.strip())
                    st.rerun()
        caption("Tip: the Price target builder can set this for you from its valuation, with a margin of safety.")

    if not jr["watchlist"]:
        html(
            '<div class="empty"><div class="h2">Nothing on your watchlist yet</div><p>Add stocks you\'d like to own '
            "and the price you'd pay. You'll see how close each one is, and the daily job can alert you the day one "
            "drops into your buy zone.</p></div>"
        )
        return

    cfg = J.automation_config(jr)
    tickers = sorted({w["ticker"] for w in jr["watchlist"]} | {p["ticker"] for p in cfg["positions"]})
    try:
        px = data.get_prices(tuple(tickers + ["SPY"]), period="2y")
    except Exception:
        st.warning("Prices couldn't be loaded right now.")
        return
    infos = data.get_infos([w["ticker"] for w in jr["watchlist"]])

    section("Watchlist", f"Latest close {px.index[-1]:%b %d} · sorted by distance to your buy zone")
    rows = []
    for w in jr["watchlist"]:
        s = px[w["ticker"]].dropna() if w["ticker"] in px else pd.Series(dtype=float)
        if len(s) < 2:
            continue
        price, prev = s.iloc[-1], s.iloc[-2]
        rows.append((price / w["buy_below"] - 1, w, price, (price / prev - 1) * 100))
    trs = []
    for gap, w, price, day in sorted(rows, key=lambda r: r[0]):
        label, tone = AL.zone_status(price, w["buy_below"])
        color = {"good": GOOD, "warn": WARN, "flat": INK_3}[tone]
        target = infos.get(w["ticker"], {}).get("targetMeanPrice")
        trs.append(
            f'<tr><td><b class="tk">{w["ticker"]}</b><div class="d">since {w["added"]}</div></td>'
            f'<td class="n">${price:,.2f}<div class="d">{chg_span(day, 2)}</div></td>'
            f'<td class="n">${w["buy_below"]:,.2f}</td>'
            f'<td><div class="zone-bar"><div style="width:{max(4, min(100, 100 - gap * 200)):.0f}%;background:{color}"></div></div>'
            f'<span class="status" style="color:{color}">{label}</span></td>'
            f'<td class="n">{f"${target:,.0f}" if target else "—"}</td>'
            f'<td class="note-cell">{escape(w.get("note") or "")}</td></tr>'
        )
    html(
        '<div class="tbl-wrap"><table class="tbl"><tr class="th"><td>Ticker</td><td>Price</td><td>Buy below</td>'
        "<td>Distance to zone</td><td>Analysts</td><td>Note</td></tr>" + "".join(trs) + "</table></div>"
    )
    a, b, _ = st.columns([1.2, 0.6, 2], vertical_alignment="bottom")
    a.selectbox(
        "Remove",
        [w["id"] for w in jr["watchlist"]],
        key="wl_remove",
        label_visibility="collapsed",
        format_func=lambda i: next(w["ticker"] for w in jr["watchlist"] if w["id"] == i),
    )
    b.button("Remove", key="wl_remove_btn", on_click=_remove_watch, args=(jr,))

    # What the daily job would send for the latest close
    found = AL.evaluate(cfg, px)
    section("Today's alerts", f"What the daily check sends for the {px.index[-1]:%b %d} close")
    if found:
        icons = {"stop": ("■", BAD), "target": ("●", GOOD), "buy_zone": ("●", GOOD), "big_move": ("▲", WARN)}
        html(
            '<div class="alert-list">'
            + "".join(
                f'<div class="alert-item"><span style="color:{icons[x.kind][1]}">{icons[x.kind][0]}</span>'
                f'<div><b>{escape(x.title)}</b><div class="d">{escape(x.detail)}</div></div></div>'
                for x in found
            )
            + "</div>"
        )
    else:
        caption("No alerts for the latest close: nothing crossed a buy zone, target or stop, and no unusual moves.")

    with st.expander("Get these alerts on your phone every evening"):
        used = notify.channels()
        status = ", ".join(used) if used else "none configured yet"
        html(f"""<div class="explain">
        <p><b>Delivery channels:</b> {status}.</p>
        <p><b>1. Phone:</b> install the free <b>ntfy</b> app, subscribe to a topic name only you know (it works like a
        password, e.g. <code>md-alerts-7f3k9</code>), and set <code>NTFY_TOPIC</code> to it. Email works too with
        <code>SMTP_HOST</code>, <code>SMTP_USER</code>, <code>SMTP_PASSWORD</code> and <code>ALERT_EMAIL_TO</code>.</p>
        <p><b>2. Every weekday automatically:</b> in your GitHub repo, add these as Actions secrets, plus
        <code>WATCHLIST_JSON</code> below. The workflow in <code>.github/workflows/daily-alerts.yml</code> runs at
        4:30pm ET (5:30pm in summer). Update the secret when your watchlist changes.</p>
        <p><b>Or run it yourself:</b> <code>uv run python scripts/daily_check.py --dry-run</code> prints today's alerts
        from this journal without sending anything.</p></div>""")
        st.code(json.dumps(cfg, separators=(",", ":")), language="json")
        caption("WATCHLIST_JSON holds only tickers and price levels: no notes, theses or position sizes.")
        if used and st.button("Send a test alert", key="wl_test", icon=":material/send:"):
            notify.send("Daily Market Brief · test", "Alerts are set up. You'll hear from me after the close.", 3)
            st.toast(f"Test sent via {', '.join(used)}")


def render() -> None:
    jr = J.load()
    view = (
        st.segmented_control(
            "View",
            ["My positions", "Watchlist", "Price target builder", "Thesis log"],
            default="My positions",
            key="jr_view",
            label_visibility="collapsed",
        )
        or "My positions"
    )
    if view == "My positions":
        _positions_view(jr)
    elif view == "Watchlist":
        _watchlist_view(jr)
    elif view == "Price target builder":
        _target_view(jr)
    else:
        _log_view(jr)
