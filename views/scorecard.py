"""Signal Scorecard (not shown as a tab; its findings now sit next to each signal): do the dashboard's own signals actually work? Out-of-sample backtests, net of costs."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics as A
import config
from signal_checks import COST_BPS
from signal_checks import compute as _compute
from signal_checks import t_stat as _t
from signal_checks import verdict as _verdict
from theme import (
    BAD,
    GOOD,
    INK_2,
    INK_3,
    NEG,
    POS,
    SERIES,
    WARN,
    caption,
    chart_title,
    explain,
    html,
    section,
    style_fig,
)


def _pill(text: str, tone: str) -> str:
    color = {"good": GOOD, "warn": WARN, "bad": BAD, "flat": INK_3}[tone]
    icon = {"good": "●", "warn": "▲", "bad": "■", "flat": "○"}[tone]
    return f'<span class="status" style="color:{color}">{icon} {text}</span>'


def _growth_chart(runs: pd.DataFrame, title: str, height: int = 320) -> None:
    chart_title(title)
    fig = go.Figure()
    for i, col in enumerate(runs.columns):
        g = (1 + runs[col].fillna(0)).cumprod()
        fig.add_scatter(
            x=g.index,
            y=g,
            name=col,
            mode="lines",
            line=dict(color=SERIES[i], width=2),
            hovertemplate="$%{y:.2f}<extra>" + col + "</extra>",
        )
    top = max(float((1 + runs[c].fillna(0)).cumprod().max()) for c in runs.columns)
    low = min(float((1 + runs[c].fillna(0)).cumprod().min()) for c in runs.columns)
    ticks = [v for v in (0.5, 1, 2, 3, 5, 10, 20, 30, 50, 100) if low * 0.8 <= v <= top * 1.25]
    style_fig(fig, height, ysuffix="").update_yaxes(
        type="log", tickvals=ticks, ticktext=[f"${v:g}" for v in ticks], minor=dict(showgrid=False)
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _label_chart(sc: pd.DataFrame, title: str, horizon: str) -> None:
    chart_title(title)
    fig = go.Figure(
        go.Bar(
            x=sc.index,
            y=sc["avg"],
            marker=dict(color=[POS if v >= 0 else NEG for v in sc["avg"]], cornerradius=4),
            text=[f"{a:+.2f}" for a in sc["avg"]],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color=INK_2, size=12),
            customdata=np.stack([sc["hit"], sc["obs"], sc["t"]], axis=1),
            hovertemplate="<b>%{x}</b><br>Avg %{y:+.2f} pts vs. S&P 500, "
            + horizon
            + "<br>Beat the market %{customdata[0]:.0f}% of the time"
            + "<br>%{customdata[1]:.0f} observations · t = %{customdata[2]:.2f}<extra></extra>",
        )
    )
    lim = max(0.6, sc["avg"].abs().max() * 1.6)
    style_fig(fig, 300, ysuffix="").update_layout(
        hovermode="closest", bargap=0.35, uniformtext=dict(minsize=11, mode="show")
    )
    fig.update_yaxes(range=[-lim, lim], title=dict(text=f"pts vs. S&P 500, {horizon}", font=dict(size=11, color=INK_3)))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def _stats_table(runs: pd.DataFrame) -> None:
    rows = []
    for col in runs.columns:
        s = A.portfolio_stats(runs[col].dropna())
        rows.append(
            {
                "": col,
                "Return / yr": s["cagr"],
                "Volatility": s["vol"],
                "Sharpe": s["sharpe"],
                "Worst drawdown": s["max_dd"],
            }
        )
    st.dataframe(
        pd.DataFrame(rows)
        .set_index("")
        .style.format(
            {"Return / yr": "{:.1f}%", "Volatility": "{:.1f}%", "Sharpe": "{:.2f}", "Worst drawdown": "{:.1f}%"}
        ),
        width="stretch",
    )


def render() -> None:
    with st.spinner("Running backtests on 25+ years of data…"):
        try:
            r = _compute()
        except Exception:
            st.warning("Price or macro history couldn't be loaded right now. Try again in a minute.")
            return

    tsc, qsc = r["trend_sc"], r["rrg_sc"]
    up_t, up_avg = tsc.loc["Uptrend", "t"], tsc.loc["Uptrend", "avg"]
    lead_t, lead_avg = qsc.loc["Leading", "t"], qsc.loc["Leading", "avg"]
    reg = r["regime_runs"]
    reg_t = _t(reg["Regime playbook"] - reg["S&P 500"])
    reg_s, spy_s = A.portfolio_stats(reg["Regime playbook"]), A.portfolio_stats(reg["S&P 500"])
    fr = r["filter_runs"]
    f_s, bh_s = A.portfolio_stats(fr["Trend filter"]), A.portfolio_stats(fr["Buy & hold S&P 500"])
    fragile = (r["robust"]["t vs. S&P 500"] < 0).any()

    cards = [
        (
            "Trend labels",
            "Do Uptrend sectors beat the market next month?",
            f"{up_avg:+.2f} pts/month · t = {up_t:.1f}",
            _verdict(up_t, up_avg),
        ),
        (
            "Rotation quadrants",
            "Do Leading sectors beat the market over the next 4 weeks?",
            f"{lead_avg:+.2f} pts · t = {lead_t:.1f}",
            _verdict(lead_t, lead_avg),
        ),
        (
            "Regime playbook",
            "Does holding the regime's best 2 sectors beat the market?",
            f"{reg_s['cagr']:.1f}% vs. {spy_s['cagr']:.1f}%/yr · t = {reg_t:.1f}",
            ("Fragile, not reliable", "warn")
            if fragile and abs(reg_t) < 2
            else _verdict(reg_t, reg_s["cagr"] - spy_s["cagr"]),
        ),
        (
            "Market trend filter",
            "Does exiting below the 200-day average reduce losses?",
            f"Worst drop {f_s['max_dd']:.0f}% vs. {bh_s['max_dd']:.0f}%",
            ("Cuts drawdowns", "good") if f_s["max_dd"] > bh_s["max_dd"] + 10 else ("No clear benefit", "flat"),
        ),
    ]
    html(
        '<div class="verdicts">'
        + "".join(
            f'<div class="verdict-card"><div class="eyebrow">{name}</div><div class="vq">{q}</div>'
            f'<div class="vr">{res}</div>{_pill(*v)}</div>'
            for name, q, res, v in cards
        )
        + "</div>"
    )
    caption(
        f"Every test uses only information available at the time, scores what happened next, and charges "
        f"{COST_BPS} bps per trade. Data through {r['as_of']:%b %d, %Y}. A t-stat above about 2 is the usual bar "
        "for 'probably not luck'.",
        teach=True,
    )

    # ----- 1. Trend labels -----
    section("Trend labels", "Sector ETFs since 1999 · label at each month-end, scored on the next month")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        _label_chart(tsc, "Average next-month return vs. the S&P 500, by label", "next month")
    with c2:
        _growth_chart(r["trend_runs"], "Growth of $1 · holding only Uptrend sectors vs. the market")
    _stats_table(r["trend_runs"])
    caption(
        "Being in an uptrend has <b>not</b> predicted which sector beats the market next month. The labels describe "
        "the past well, but by the time a sector is clearly trending, the move is largely priced in. Use them for "
        "context, not as buy signals.",
        teach=True,
    )

    # ----- 2. Rotation quadrants -----
    section("Rotation quadrants", "Weekly since 1999 · quadrant every 4 weeks, scored on the next 4 weeks")
    _label_chart(qsc, "Average next-4-week return vs. the S&P 500, by quadrant", "next 4 weeks")
    caption(
        "'Leading' sectors haven't kept leading, and 'Lagging' ones have done slightly better if anything, a hint of "
        "short-term mean reversion that is too small to trade after costs.",
        teach=True,
    )

    # ----- 3. Regime playbook -----
    section("Regime playbook, walk-forward", "Since 2005 · each month uses only regime history known at the time")
    c1, c2 = st.columns([1.6, 1], gap="large")
    with c1:
        _growth_chart(reg, "Growth of $1 · top 2 sectors for the current regime vs. the market")
    with c2:
        picks = r["regime_picks"]
        names = ", ".join(config.ALL_SECTORS.get(t.strip(), t.strip()) for t in picks.iloc[-1].split(","))
        html(
            f'<div class="side"><div class="eyebrow">This month the playbook would hold</div>'
            f'<div class="term">{picks.iloc[-1]}</div><p>{names}</p></div>'
        )
    chart_title("Robustness: the same test with small changes to the rules")
    st.dataframe(
        r["robust"].style.format({"CAGR": "{:.1f}%", "Sharpe": "{:.2f}", "t vs. S&P 500": "{:+.2f}"}),
        width="stretch",
    )
    _stats_table(reg)
    caption(
        f"The base case beat the market ({reg_s['cagr']:.1f}% vs. {spy_s['cagr']:.1f}% a year), but with t = "
        f"{reg_t:.1f} it isn't statistically significant, and the edge disappears with small rule changes (top 3 "
        "sectors, or a one-month-longer data lag). That pattern usually means a result is partly luck. Treat the "
        "playbook as a gentle tilt, not a strategy.",
        teach=True,
    )

    # ----- 4. Market trend filter -----
    section("Market trend filter", "S&P 500 since 1994 · in the market above the 200-day average, T-bills below")
    c1, c2 = st.columns([1.3, 1], gap="large")
    with c1:
        _growth_chart(fr, "Growth of $1 · trend filter vs. buy and hold")
    with c2:
        chart_title("Drawdown: % below the previous peak")
        fig = go.Figure()
        for i, col in enumerate(fr.columns):
            g = (1 + fr[col]).cumprod()
            dd = (g / g.cummax() - 1) * 100
            fig.add_scatter(
                x=dd.index,
                y=dd,
                name=col,
                mode="lines",
                line=dict(color=SERIES[i], width=1.6),
                hovertemplate="%{y:.1f}%<extra>" + col + "</extra>",
            )
        style_fig(fig, 320)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    _stats_table(fr)
    status = "invested" if r["spy_vs_200"] > 0 else "in T-bills"
    html(
        f'<div class="flag">Today the S&amp;P 500 is <b>{r["spy_vs_200"]:+.1f}%</b> versus its 200-day average, so the '
        f"filter would be <b>{status}</b>. Historically it spent {r['time_in_market']:.0f}% of months invested and "
        f"switched about {r['switches_per_year']:.1f} times a year.</div>"
    )
    caption(
        "This is the one signal that held up: roughly the same long-run return with less than half the worst "
        "drawdown, because it stepped aside during the long bear markets of 2000–02 and 2008–09. It lags in sharp "
        "V-shaped rebounds, and switching in a taxable account triggers capital-gains taxes, which this test ignores.",
        teach=True,
    )

    explain(
        "how these backtests are built",
        f"""
    <p><b>No look-ahead.</b> Every signal is computed from data available on the decision date, and scored on what
    happened afterwards. The regime playbook ranks sectors using only months before the one it trades, and applies
    each month's macro data two months later to allow for publication delays. A test in the project checks this by
    planting a huge future price jump and confirming earlier decisions don't change.</p>
    <p><b>Non-overlapping windows.</b> Labels are sampled once per scoring window (monthly, or every 4 weeks), so the
    same price move isn't counted twice.</p>
    <p><b>Costs.</b> {COST_BPS} basis points per unit of turnover. Taxes and bid-ask spreads beyond that aren't modeled.</p>
    <p><b>Honest limits.</b> Macro data uses today's revised figures, not what was first published. Only a few
    signals and parameters were tried, but every extra variant tested raises the chance of finding something that
    worked by luck, which is why the robustness table matters. Past results don't guarantee future ones.</p>
    """,
    )
