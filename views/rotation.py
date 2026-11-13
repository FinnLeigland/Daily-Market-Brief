"""Sector Rotation: where is market leadership moving?"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics as A
import config
import data
import signal_checks
from theme import (
    GRID,
    INK,
    INK_3,
    MUTED,
    SERIES,
    caption,
    end_labels,
    explain,
    fmt_value,
    html,
    section,
    style_fig,
    warn,
)

QUADRANT_COLORS = {"Leading": SERIES[2], "Weakening": SERIES[3], "Lagging": SERIES[7], "Improving": SERIES[0]}
QUADRANT_MEANING = {
    "Leading": "Outperforming the market, and the outperformance is still building.",
    "Weakening": "Still outperforming, but losing steam. Often the next stop is Lagging.",
    "Lagging": "Underperforming, and still getting worse relative to the market.",
    "Improving": "Still underperforming, but the gap is closing. Watch for a move into Leading.",
}
CYCLICALS, DEFENSIVES = ["XLK", "XLY", "XLI", "XLF"], ["XLU", "XLP", "XLV"]
PERIODS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126, "YTD": "ytd", "1Y": 252}


def _ret(s: pd.Series, period: str) -> float | None:
    return data.ytd_change(s) if period == "YTD" else data.pct_change(s, PERIODS[period])


def _heat(v: float, scale: float) -> str:
    """CSS class for a cell: green for beating the market, red for trailing, four steps of strength.
    (Streamlit strips inline styles from table cells, so the shades live in style.css.)"""
    step = min(4, max(1, int(abs(v) / scale * 4 + 0.999))) if abs(v) >= 0.05 else 0
    return f"heat {'p' if v >= 0 else 'n'}{step}" if step else "heat"


def _risk_line(prices: pd.DataFrame) -> pd.Series:
    yr = prices[CYCLICALS + DEFENSIVES].ffill().iloc[-253:]
    norm = yr / yr.iloc[0]
    return (norm[CYCLICALS].mean(axis=1) / norm[DEFENSIVES].mean(axis=1) - 1) * 100


def _overview(prices: pd.DataFrame, quad_now: dict[str, str]) -> None:
    secs, names = list(config.ALL_SECTORS), config.ALL_SECTORS
    sb = A.sector_scoreboard(prices, secs, config.BENCHMARK)
    risk = _risk_line(prices)
    risk_chg = risk.iloc[-1] - risk.iloc[-22]

    def who(rows: pd.DataFrame, col: str) -> str:
        return ", ".join(f"{names[e]} ({r[col]:+.1f})" for e, r in rows.iterrows())

    def moves(rows: pd.DataFrame) -> str:
        return ", ".join(
            f"{names[e]} ({'▲' if r.rank_change > 0 else '▼'}{abs(int(r.rank_change))} to #{int(r['rank'])})"
            for e, r in rows.iterrows()
        )

    ins = sb[sb.rank_change >= 2].sort_values("rank_change", ascending=False).head(3)
    outs = sb[sb.rank_change <= -2].sort_values("rank_change").head(3)
    above = int((sb.vs_200d > 0).sum())
    breadth = "a broad market" if above >= 8 else "narrow leadership" if above <= 4 else "a mixed market"
    bullets = [
        f"<b>Leading:</b> {who(sb.head(3), '3M')} pts ahead of the S&amp;P 500 over three months. "
        f"<b>Trailing:</b> {who(sb.tail(3).iloc[::-1], '3M')}.",
        f"<b>Rotating in:</b> {moves(ins)}."
        if len(ins)
        else "<b>Rotating in:</b> no sector climbed two or more places this month.",
        f"<b>Rotating out:</b> {moves(outs)}."
        if len(outs)
        else "<b>Rotating out:</b> no sector fell two or more places this month.",
        f"<b>Breadth:</b> {above} of {len(secs)} sectors trade above their 200-day average, {breadth}.",
        f"<b>Risk appetite:</b> cyclicals {'gained' if risk_chg > 0 else 'lost'} {abs(risk_chg):.1f} pts against "
        f"defensives this month, {'a risk-on tilt' if risk_chg > 0 else 'a risk-off tilt'}.",
    ]
    section("Where money is moving", "Select Sector SPDR ETFs vs. the S&P 500 · ranked by 3-month relative strength")
    html('<div class="brief"><ul>' + "".join(f"<li>{b}</li>" for b in bullets) + "</ul></div>")

    # ----- Scoreboard -----
    section("Relative-strength scoreboard", "Each sector's return minus the S&P 500's, in percentage points")
    head = (
        '<tr class="th"><td>#</td><td>Sector</td>'
        + "".join(f'<td class="n">{w}</td>' for w in A.SCOREBOARD_WINDOWS)
        + '<td class="n">Rank vs. 1M ago</td><td class="n">vs. 200-day</td><td>Rotation graph</td></tr>'
    )
    rows = []
    for etf, r in sb.iterrows():
        rc = int(r.rank_change)
        move = (
            f'<span class="chg up">▲ {rc}</span>'
            if rc > 0
            else f'<span class="chg down">▼ {-rc}</span>'
            if rc < 0
            else '<span class="chg flat">–</span>'
        )
        cells = "".join(
            f'<td class="n {_heat(r[w], scale)}">{fmt_value("{:+.1f}", r[w])}</td>'
            for w, scale in zip(A.SCOREBOARD_WINDOWS, (3, 5, 8, 12), strict=True)
        )
        trend = "up" if r.vs_200d > 0 else "down"
        rows.append(
            f'<tr><td class="n rk">{int(r["rank"])}</td><td><b>{names[etf]}</b> <span class="etf">{etf}</span></td>{cells}'
            f'<td class="n">{move}</td><td class="n"><span class="chg {trend}">{fmt_value("{:+.1f}%", r.vs_200d)}</span></td>'
            f'<td><span class="swatch" style="background:{QUADRANT_COLORS[quad_now[etf]]}"></span>{quad_now[etf]}</td></tr>'
        )
    html(f'<div class="tbl-wrap board"><table class="tbl">{head}{"".join(rows)}</table></div>')
    caption(
        "Green cells are beating the S&amp;P 500 over that window, red ones trailing it. A sector climbing the ranks "
        "while still below its 200-day average is a turn worth watching; a leader slipping in rank is often the first "
        "sign of rotation out.",
        teach=True,
    )

    # ----- Leadership race -----
    section("Leadership race", "Six months of each sector vs. the S&P 500 · above 100 means it has beaten the market")
    ri = A.relative_index(prices, secs, config.BENCHMARK, days=126)
    order = sb.index.tolist()
    leaders, laggards = [SERIES[0], SERIES[2], SERIES[6]], [SERIES[7], SERIES[1], SERIES[3]]  # cool vs. warm
    highlight = {**dict(zip(order[:3], leaders, strict=True)), **dict(zip(order[-3:][::-1], laggards, strict=True))}
    fig = go.Figure()
    for etf in reversed(order):  # highlighted lines drawn last, on top
        hl = etf in highlight
        fig.add_scatter(
            x=ri.index,
            y=ri[etf],
            mode="lines",
            name=names[etf],
            line=dict(color=highlight.get(etf, MUTED), width=2.2 if hl else 1),
            opacity=1 if hl else 0.55,
            hovertemplate=f"{names[etf]}: %{{y:.1f}}<extra></extra>",
            showlegend=False,
        )
    fig.add_hline(y=100, line=dict(color=INK_3, width=1, dash="dot"))
    style_fig(fig, 380, ysuffix="").update_layout(hovermode="closest", margin=dict(r=150))
    end_labels(fig, {names[e]: ri[e].iloc[-1] for e in highlight})
    st.plotly_chart(fig, width="stretch")
    caption(
        "The three leaders by three-month relative strength are in cool colors, the three laggards in warm ones; "
        "the rest are grey.",
        teach=True,
    )


def render(prices: pd.DataFrame) -> None:

    weekly = data.get_prices(tuple(list(config.ALL_SECTORS) + [config.BENCHMARK]), period="2y", interval="1wk")
    ratio, mom = A.relative_rotation(weekly[list(config.ALL_SECTORS)], weekly[config.BENCHMARK])
    quad_now = {e: A.rrg_quadrant(ratio[e].iloc[-1], mom[e].iloc[-1]) for e in config.ALL_SECTORS}
    _overview(prices, quad_now)

    section("Relative rotation graph", "Weekly · vs. S&P 500 · tails show the recent path, dot is this week")
    tail = st.slider("Tail length (weeks)", 2, 12, 5, key="rrg_tail")

    fig = go.Figure()
    xs = ratio.iloc[-tail:].stack().tolist()
    ys = mom.iloc[-tail:].stack().tolist()
    pad = 0.6
    x0, x1 = min(xs + [100]) - pad, max(xs + [100]) + pad
    y0, y1 = min(ys + [100]) - pad, max(ys + [100]) + pad
    for name, (qx, qy, ax, ay) in {
        "Leading": (x1, y1, "right", "top"),
        "Weakening": (x1, y0, "right", "bottom"),
        "Lagging": (x0, y0, "left", "bottom"),
        "Improving": (x0, y1, "left", "top"),
    }.items():
        fig.add_annotation(
            x=qx,
            y=qy,
            text=name.upper(),
            showarrow=False,
            xanchor=ax,
            yanchor=ay,
            font=dict(size=11, color=QUADRANT_COLORS[name]),
            opacity=0.9,
        )
    fig.add_hline(y=100, line=dict(color=MUTED, width=1))
    fig.add_vline(x=100, line=dict(color=MUTED, width=1))

    rows = []
    for etf, name in config.ALL_SECTORS.items():
        x, y = ratio[etf].iloc[-tail:], mom[etf].iloc[-tail:]
        quad = A.rrg_quadrant(x.iloc[-1], y.iloc[-1])
        color = QUADRANT_COLORS[quad]
        fig.add_scatter(
            x=x,
            y=y,
            mode="lines+markers",
            line=dict(color=color, width=1.5, shape="spline"),
            opacity=0.6,
            marker=dict(size=[3 + 4 * i / tail for i in range(len(x))]),
            hoverinfo="skip",
            showlegend=False,
        )
        fig.add_scatter(
            x=[x.iloc[-1]],
            y=[y.iloc[-1]],
            mode="markers+text",
            text=[etf],
            textposition="top center",
            textfont=dict(size=11, color=INK),
            marker=dict(size=11, color=color, line=dict(color="#0e0e0d", width=2)),
            name=name,
            showlegend=False,
            hovertemplate=f"<b>{name}</b> ({etf})<br>RS-Ratio %{{x:.2f}}<br>RS-Momentum %{{y:.2f}}<br>{quad}<extra></extra>",
        )
        prev_quad = A.rrg_quadrant(ratio[etf].iloc[-5], mom[etf].iloc[-5])
        rows.append(
            {
                "Sector": name,
                "ETF": etf,
                "Quadrant": quad,
                "4 weeks ago": prev_quad,
                "RS-Ratio": x.iloc[-1],
                "RS-Momentum": y.iloc[-1],
                "1M": _ret(prices[etf], "1M"),
                "3M": _ret(prices[etf], "3M"),
            }
        )
    style_fig(fig, 560, ysuffix="").update_layout(hovermode="closest")
    fig.update_xaxes(
        title=dict(text="RS-Ratio  →  stronger than the market", font=dict(size=11, color=INK_3)),
        range=[x0, x1],
        showgrid=True,
        gridcolor=GRID,
    )
    fig.update_yaxes(
        title=dict(text="RS-Momentum  →  strength improving", font=dict(size=11, color=INK_3)),
        range=[y0, y1],
        zeroline=False,
    )
    st.plotly_chart(fig, width="stretch")

    # Legend + table
    html(
        '<div class="legend-row">'
        + "".join(
            f'<div><span class="swatch" style="background:{c}"></span><b>{q}</b> <span class="desc">{QUADRANT_MEANING[q]}</span></div>'
            for q, c in QUADRANT_COLORS.items()
        )
        + "</div>"
    )
    chk = signal_checks.peek()
    evidence = (
        f" Backtested weekly since 1999, sectors in Leading averaged {chk['rrg_avg']:+.2f} pts vs. the S&P 500 over the "
        f"next 4 weeks (t = {chk['rrg_t']:.1f}): no measurable edge, and Lagging sectors did slightly better if anything."
        if chk
        else " Backtested weekly since 1999, Leading sectors did not keep beating the market over the next 4 weeks."
    )
    warn(f"<b>Quadrants describe where a sector has been, not where it's going.</b>{evidence}")

    table = pd.DataFrame(rows).sort_values(["RS-Ratio"], ascending=False).set_index("Sector")
    moved = table[table["Quadrant"] != table["4 weeks ago"]]
    if len(moved):
        caption(
            "<b>Changed quadrant in the last 4 weeks:</b> "
            + "; ".join(f"{s} ({r['4 weeks ago']} → {r['Quadrant']})" for s, r in moved.iterrows())
            + "."
        )

    explain(
        "the rotation graph",
        """
    <p><b>RS-Ratio (horizontal):</b> the sector's price divided by the S&amp;P 500, compared with its own 10-week
    average. Above 100 means the sector has been outperforming recently.</p>
    <p><b>RS-Momentum (vertical):</b> how fast RS-Ratio is changing over 4 weeks. Above 100 means relative strength is
    accelerating.</p>
    <p><b>Clockwise rotation:</b> a typical path is Improving → Leading → Weakening → Lagging → Improving. Long tails
    mean big moves; tails hugging the center mean a sector is moving with the market. This is a simplified version of
    the JdK RRG used on professional terminals.</p>
    """,
    )

    # ----- Risk appetite -----
    section(
        "Risk appetite: cyclicals vs. defensives",
        "Equal-weight XLK, XLY, XLI, XLF ÷ equal-weight XLU, XLP, XLV · 1 year",
    )
    line = _risk_line(prices)
    fig = go.Figure(
        go.Scatter(
            x=line.index,
            y=line,
            mode="lines",
            line=dict(color=SERIES[0], width=2),
            fill="tozeroy",
            fillcolor="rgba(57,135,229,0.10)",
            hovertemplate="%{y:+.1f}%<extra></extra>",
            name="Cyclicals vs. defensives",
        )
    )
    st.plotly_chart(style_fig(fig, 300).update_layout(hovermode="x"), width="stretch")
    chg = line.iloc[-1] - line.iloc[-22]
    caption(
        f"Cyclicals have {'outperformed' if line.iloc[-1] > 0 else 'underperformed'} defensives by "
        f"<b>{abs(line.iloc[-1]):.1f} pts</b> over the past year, and the gap {'widened' if chg > 0 else 'narrowed'} by "
        f"{abs(chg):.1f} pts in the last month. A rising line means investors are paying up for growth "
        "(risk-on); a falling line means they are hiding in steady earners (risk-off)."
    )
