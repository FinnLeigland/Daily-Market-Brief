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
    INK_2,
    INK_3,
    MUTED,
    NEG,
    POS,
    SERIES,
    caption,
    explain,
    html,
    section,
    style_fig,
    table_html,
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


def render(prices: pd.DataFrame) -> None:

    weekly = data.get_prices(tuple(list(config.ALL_SECTORS) + [config.BENCHMARK]), period="2y", interval="1wk")
    ratio, mom = A.relative_rotation(weekly[list(config.ALL_SECTORS)], weekly[config.BENCHMARK])

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
    html(
        table_html(
            table,
            {"RS-Ratio": "{:.2f}", "RS-Momentum": "{:.2f}", "1M": "{:+.1f}%", "3M": "{:+.1f}%"},
            first_col="Sector",
            color_cols=("1M", "3M"),
        )
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
    yr = prices[CYCLICALS + DEFENSIVES].ffill().iloc[-253:]
    norm = yr / yr.iloc[0]
    line = (norm[CYCLICALS].mean(axis=1) / norm[DEFENSIVES].mean(axis=1) - 1) * 100
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

    # ----- Returns by period -----
    section("Sector returns", "Select Sector SPDR ETFs vs. the S&P 500")
    period = (
        st.segmented_control("Period", list(PERIODS), default="1M", key="rot_period", label_visibility="collapsed")
        or "1M"
    )
    perf = pd.Series({name: _ret(prices[etf], period) for etf, name in config.ALL_SECTORS.items()}).sort_values()
    spy_ret = _ret(prices[config.BENCHMARK], period)
    fig = go.Figure(
        go.Bar(
            x=perf.values,
            y=perf.index,
            orientation="h",
            marker=dict(color=[POS if v >= 0 else NEG for v in perf.values], cornerradius=4),
            text=[f"{v:+.1f}%" for v in perf.values],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color=INK_2),
            hovertemplate="%{y}: %{x:+.2f}%<extra></extra>",
        )
    )
    fig.add_vline(
        x=spy_ret,
        line=dict(color=INK_3, dash="dot", width=1.5),
        annotation=dict(text=f"S&P 500 {spy_ret:+.1f}%", font_size=11, font_color=INK_3),
        annotation_position="top",
    )
    style_fig(fig, 420).update_layout(hovermode="closest", bargap=0.35)
    fig.update_xaxes(ticksuffix="%", gridcolor=GRID, showgrid=True)
    fig.update_yaxes(ticksuffix="", gridcolor="rgba(0,0,0,0)", zeroline=False)
    st.plotly_chart(fig, width="stretch")
