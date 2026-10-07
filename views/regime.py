"""Macro: indicator monitor and assessment, then growth, inflation, policy, regime positioning and recession risk."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics as A
import config
import data
import signal_checks
from theme import (
    BAD,
    GOOD,
    GRID,
    INK,
    INK_2,
    INK_3,
    MID,
    NEG,
    POS,
    SERIES,
    WARN,
    caption,
    chart_title,
    explain,
    html,
    shade_periods,
    show_help,
    sparkline,
    style_fig,
    warn,
)

FRED_IDS = ("INDPRO", "CPIAUCSL", "CPILFESL", "UNRATE", "PAYEMS", "T10Y3M", "USREC", "DFF", "DGS2", "DGS10")
REGIME_COLORS = dict(zip(A.REGIMES, [SERIES[2], SERIES[3], SERIES[7], SERIES[0]], strict=True))
REGIME_SHORT = {
    "Goldilocks": "Growth ↑ · Inflation ↓",
    "Reflation": "Growth ↑ · Inflation ↑",
    "Stagflation": "Growth ↓ · Inflation ↑",
    "Slowdown": "Growth ↓ · Inflation ↓",
}


def _pill(text: str, tone: str) -> str:
    color = {"good": GOOD, "warn": WARN, "bad": BAD, "flat": INK_3}[tone]
    icon = {"good": "●", "warn": "▲", "bad": "■", "flat": "○"}[tone]
    return f'<span class="status" style="color:{color}">{icon} {text}</span>'


def _step(n: int, title: str, verdict: str, note: str = "") -> None:
    html(
        f'<div class="step"><div class="num">{n:02d}</div><div class="h2">{title}</div>{verdict}<span class="snote">{note}</span></div>'
    )


def _source(text: str) -> None:
    html(f'<div class="source">Source: {text}</div>')


def _monthly(s: pd.Series) -> pd.Series:
    """Daily or monthly series → one value per month (the month's last observation)."""
    return s.resample("MS").last().dropna()


def _monitor_row(label: str, s: pd.Series, unit: str, good_when: str | None, src: str, digits: int = 1) -> str:
    """One row of the indicator monitor: latest, prior, 6M and 1Y readings, a 24-month trend, and the 6M change."""
    as_of = s.index[-1]
    m = _monthly(s)

    def ago(months: int) -> float:
        return m.iloc[-1 - months] if len(m) > months else float("nan")

    def fmt(v: float) -> str:
        return "—" if pd.isna(v) else f"{v:,.{digits}f}{unit}"

    latest, prior, six, year = s.iloc[-1], ago(1), ago(6), ago(12)
    chg = latest - six
    if good_when is None or abs(chg) < 10**-digits:
        tone = "flat"
    else:
        tone = "good" if (chg > 0) == (good_when == "up") else "bad"
    arrow = "▲" if chg > 0 else "▼" if chg < 0 else "–"
    spark = sparkline(m.iloc[-24:], width=120, height=28, color=SERIES[0], tip=f"{label}: last 24 months")
    return (
        f'<tr><td class="ind">{label}<div class="src">{src}</div></td><td class="n strong">{fmt(latest)}</td><td class="n">{fmt(prior)}</td>'
        f'<td class="n">{fmt(six)}</td><td class="n">{fmt(year)}</td><td class="sp">{spark}</td>'
        f'<td class="n chg {tone}">{arrow} {abs(chg):,.{digits}f}</td>'
        f'<td class="asof">{as_of:%b %d, %Y}</td></tr>'
    )


def _line(
    series: dict[str, pd.Series], height: int = 240, ref: float | None = None, ref_label: str = "", ysuffix: str = "%"
) -> go.Figure:
    fig = go.Figure()
    for i, (name, s) in enumerate(series.items()):
        fig.add_scatter(
            x=s.index,
            y=s,
            name=name,
            mode="lines",
            line=dict(color=SERIES[i], width=2),
            hovertemplate="%{y:.2f}" + ysuffix,
        )
    if ref is not None:
        fig.add_hline(
            y=ref,
            line=dict(color=INK_3, dash="dot", width=1),
            annotation=dict(text=ref_label, font=dict(size=10, color=INK_3)),
            annotation_position="top left",
        )
    style_fig(fig, height, ysuffix=ysuffix)
    if len(series) == 1:
        fig.update_layout(showlegend=False, hovermode="x")
    return fig


def _chart_and_note():
    """Chart beside an explainer panel; in clean view the chart takes the full width and the note is skipped."""
    if show_help():
        return st.columns([1.6, 1], gap="large")
    return st.container(), st.empty()


def render(prices: pd.DataFrame) -> None:
    fred = data.get_fred(FRED_IDS)
    if len(fred) < len(FRED_IDS):
        st.warning("Some FRED data couldn't be loaded right now. Try again in a minute.")
        return
    panel = A.macro_panel(fred)
    regimes = A.classify_regimes(panel)
    now, as_of = regimes.iloc[-1], regimes.index[-1]
    latest = panel.loc[as_of]
    five_y = pd.Timestamp.today() - pd.DateOffset(years=5)

    def m(sid: str) -> pd.Series:
        return fred[sid].resample("MS").mean().interpolate(limit=2, limit_area="inside")

    # Indicators in plain numbers
    cpi_yoy = panel["cpi_yoy"].dropna()
    core_yoy = (m("CPILFESL").pct_change(12, fill_method=None) * 100).dropna()
    cpi_6m_ago = cpi_yoy.iloc[-7]
    payrolls = m("PAYEMS").diff().dropna()  # thousands of jobs added per month
    jobs_3m = payrolls.iloc[-3:].mean()
    unrate = panel["unrate"].dropna()
    ip_yoy = panel["indpro_yoy"].dropna()
    fed, y2, y10 = fred["DFF"].iloc[-1], fred["DGS2"].iloc[-1], fred["DGS10"].iloc[-1]
    spread = fred["T10Y3M"].iloc[-1]

    monthly = data.get_prices(tuple(list(config.ALL_SECTORS) + ["SPY"]), period="max", interval="1mo")
    table, counts = A.regime_sector_returns(regimes, monthly, "SPY")
    table = table.where(counts >= 18)  # hide cells with too little history (XLRE/XLC launched 2015/2018)
    table.columns = [config.ALL_SECTORS[c] for c in table.columns]
    playbook = table.loc[now].dropna().sort_values(ascending=False)

    model = A.recession_model(panel)
    p_now = model["prob"].iloc[-1]
    growth_up, infl_up = latest["growth_mom"] > 0, latest["infl_mom"] > 0
    real_rate = fed - cpi_yoy.iloc[-1]

    with st.spinner("Checking the signals against history…"):
        chk = signal_checks.load()
    sp = prices["^GSPC"].dropna()
    sp_vs_200 = (sp.iloc[-1] / sp.rolling(200).mean().iloc[-1] - 1) * 100  # live reading, shared by both panels

    # ----- Macro monitor -----
    stance = "Restrictive" if real_rate > 1 else "Neutral" if real_rate > 0 else "Accommodative"
    risk = "Elevated" if p_now >= 40 else "Above average" if p_now >= model["base_rate"] else "Below average"
    assess = [
        (
            "Growth",
            "Accelerating" if growth_up else "Decelerating",
            "good" if growth_up else "warn",
            f"Industrial production {ip_yoy.iloc[-1]:+.1f}% YoY; payrolls {jobs_3m:+,.0f}k/month (3-mo avg); "
            f"unemployment {unrate.iloc[-1]:.1f}%.",
        ),
        (
            "Inflation",
            "Firming" if infl_up else "Moderating",
            "warn" if infl_up else "good",
            f"CPI {cpi_yoy.iloc[-1]:.1f}% YoY, core {core_yoy.iloc[-1]:.1f}%, vs. {cpi_6m_ago:.1f}% six months ago; target 2.0%.",
        ),
        (
            "Policy",
            stance,
            "warn" if stance == "Restrictive" else "flat",
            f"Fed funds {fed:.2f}%, {real_rate:+.1f} pts real; 10Y {y10:.2f}%; 10Y–3M spread {spread:+.2f} pts "
            f"({'inverted' if spread < 0 else 'positive'}).",
        ),
        (
            "Positioning",
            f"{now} regime",
            "flat",
            f"Historically favored: {playbook.index[0]} ({playbook.iloc[0]:+.0f}), {playbook.index[1]} "
            f"({playbook.iloc[1]:+.0f}). Unfavored: {playbook.index[-1]} ({playbook.iloc[-1]:+.0f}) pts/yr vs. S&amp;P 500.",
        ),
        *(
            [
                (
                    "Market trend",
                    "Invested" if sp_vs_200 > 0 else "In cash",
                    "good" if sp_vs_200 > 0 else "warn",
                    f"S&amp;P 500 {sp_vs_200:+.1f}% vs. its 200-day average. Since 1994, holding it only while "
                    f"above cut the worst drawdown from {chk['bh_dd']:.0f}% to {chk['filter_dd']:.0f}% at "
                    f"{chk['filter_cagr']:.1f}% vs. {chk['bh_cagr']:.1f}%/yr.",
                )
            ]
            if chk
            else []
        ),
        (
            "Recession risk",
            f"{p_now:.0f}% · {risk}",
            "bad" if p_now >= 40 else "warn" if p_now >= model["base_rate"] else "good",
            f"12-month probability vs. {model['base_rate']:.0f}% unconditional base rate (logistic model, NBER dates).",
        ),
    ]
    rows = "".join(
        f'<div class="as-row"><div class="as-k">{k}</div><div class="as-v">{_pill(v, tone)}</div><div class="as-d">{d}</div></div>'
        for k, v, tone, d in assess
    )
    html(f"""
    <div class="macro-head">
      <div class="badge" style="border-color:{REGIME_COLORS[now]}">
        <div class="eyebrow">Current macro regime</div>
        <div class="hero-big" style="color:{REGIME_COLORS[now]}">{now}</div>
        <div class="d">{REGIME_SHORT[now]}</div>
        <div class="d small">Monthly data through {as_of:%B %Y}</div>
      </div>
      <div class="assess"><div class="eyebrow">Assessment</div>{rows}</div>
    </div>
    """)
    if chk:
        holds = " and ".join(config.ALL_SECTORS.get(t, t) for t in chk["regime_picks"]) or "nothing yet"
        if chk["regime_fragile"]:
            warn(
                f"<b>The regime playbook is fragile.</b> Tested walk-forward since 2005, holding the regime's top 2 "
                f"sectors returned {chk['regime_cagr']:.1f}%/yr vs. {chk['spy_cagr']:.1f}% for the S&amp;P 500 "
                f"(t = {chk['regime_t']:.1f}), and the edge disappears with small changes (3 sectors instead of 2, or "
                f"a 3-month data lag). This month it would hold {holds}. Treat the 'historically favored' list as "
                "context, not a plan."
            )
        else:
            warn(
                f"<b>The regime playbook isn't proven.</b> Walk-forward since 2005: {chk['regime_cagr']:.1f}%/yr vs. "
                f"{chk['spy_cagr']:.1f}% (t = {chk['regime_t']:.1f}). This month it would hold {holds}."
            )

    payroll_avg = payrolls.rolling(3).mean().dropna()
    spread_s = fred["T10Y3M"]
    groups = [
        (
            "Activity",
            [
                _monitor_row("Industrial production, YoY", ip_yoy, "%", "up", "FRED · INDPRO"),
                _monitor_row("Nonfarm payrolls, 3-mo avg change", payroll_avg, "k", "up", "FRED · PAYEMS", 0),
                _monitor_row("Unemployment rate", unrate, "%", "down", "FRED · UNRATE"),
            ],
        ),
        (
            "Prices",
            [
                _monitor_row("CPI, YoY", cpi_yoy, "%", "down", "FRED · CPIAUCSL"),
                _monitor_row("Core CPI, YoY", core_yoy, "%", "down", "FRED · CPILFESL"),
            ],
        ),
        (
            "Policy & rates",
            [
                _monitor_row("Fed funds effective rate", fred["DFF"], "%", None, "FRED · DFF", 2),
                _monitor_row("2-year Treasury yield", fred["DGS2"], "%", None, "FRED · DGS2", 2),
                _monitor_row("10-year Treasury yield", fred["DGS10"], "%", None, "FRED · DGS10", 2),
                _monitor_row("10Y–3M spread", spread_s, " pts", "up", "FRED · T10Y3M", 2),
            ],
        ),
        (
            "Risk",
            [
                _monitor_row("Recession probability, 12 mo", model["prob"], "%", "down", "Model · NBER", 0),
            ],
        ),
    ]
    body = "".join(f'<tr class="grp"><td colspan="8">{g}</td></tr>' + "".join(rs) for g, rs in groups)
    html(f"""
    <div class="section-h"><div class="h2">Indicator monitor</div><span>Change column compares the latest reading with six months ago</span></div>
    <div class="tbl-wrap monitor"><table class="tbl">
      <tr class="th"><td>Indicator</td><td>Latest</td><td>Prior</td><td>6M ago</td><td>1Y ago</td><td>24-month trend</td>
      <td>Δ 6M</td><td>As of</td></tr>
      {body}
    </table></div>
    """)

    # ----- 1. Growth -----
    _step(
        1,
        "Economic growth",
        _pill("Accelerating" if growth_up else "Decelerating", "good" if growth_up else "warn"),
        f"Growth momentum {latest['growth_mom']:+.2f} pts (6-month change in smoothed IP growth)",
    )
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        chart_title(f"Industrial production, YoY % · {ip_yoy.iloc[-1]:.1f}%")
        st.plotly_chart(_line({"Industrial production": ip_yoy[ip_yoy.index >= five_y]}, ref=0), width="stretch")
        _source("Federal Reserve via FRED (INDPRO)")
        caption(
            "Output of factories, mines and utilities. The most direct monthly read on the real economy.", teach=True
        )
    with c2:
        jobs = payrolls[payrolls.index >= pd.Timestamp.today() - pd.DateOffset(years=2)]
        chart_title(f"Nonfarm payrolls, monthly change (k) · 3-mo avg {jobs_3m:,.0f}k")
        fig = go.Figure(
            go.Bar(
                x=jobs.index,
                y=jobs,
                marker=dict(color=[POS if v >= 0 else NEG for v in jobs], cornerradius=3),
                hovertemplate="%{x|%b %Y}: %{y:,.0f}k<extra></extra>",
            )
        )
        st.plotly_chart(
            style_fig(fig, 240, ysuffix="k").update_layout(hovermode="closest", bargap=0.25), width="stretch"
        )
        _source("BLS via FRED (PAYEMS)")
        caption(
            "Nonfarm payrolls. Roughly 100k+ a month keeps up with population growth; below zero is a warning.",
            teach=True,
        )
    with c3:
        chart_title(f"Unemployment rate, % · {unrate.iloc[-1]:.1f}%")
        st.plotly_chart(_line({"Unemployment": unrate[unrate.index >= five_y]}), width="stretch")
        _source("BLS via FRED (UNRATE)")
        caption(
            "A rise of 0.5 pts from its recent low (the Sahm rule) has marked the start of every recession since 1970.",
            teach=True,
        )

    # ----- 2. Inflation -----
    _step(
        2,
        "Inflation",
        _pill("Firming" if infl_up else "Moderating", "warn" if infl_up else "good"),
        f"Headline CPI {cpi_yoy.iloc[-1]:.1f}% · core {core_yoy.iloc[-1]:.1f}% · target 2.0%",
    )
    c1, c2 = _chart_and_note()
    with c1:
        chart_title("CPI inflation, YoY %")
        st.plotly_chart(
            _line(
                {
                    "Headline CPI": cpi_yoy[cpi_yoy.index >= five_y],
                    "Core CPI (ex food & energy)": core_yoy[core_yoy.index >= five_y],
                },
                height=270,
                ref=2,
                ref_label="Fed target 2%",
            ),
            width="stretch",
        )
        _source("BLS via FRED (CPIAUCSL, CPILFESL)")
    with c2:
        html(f"""<div class="side help"><div class="eyebrow">Why it matters for stocks</div>
        <p>Inflation above target keeps the Fed from cutting rates. Higher rates make future profits worth less today,
        which hits expensive growth stocks and rate-sensitive sectors like real estate and utilities hardest.</p>
        <p style="margin-top:.6rem"><b>Core</b> inflation strips out volatile food and energy prices; the Fed watches it
        for the underlying trend. Core is {core_yoy.iloc[-1]:.1f}% today, {"above" if core_yoy.iloc[-1] > cpi_yoy.iloc[-1] else "below"}
        headline.</p></div>""")

    # ----- 3. Rates -----
    _step(
        3,
        "Monetary policy & rates",
        _pill("Curve inverted" if spread < 0 else "Curve positive", "bad" if spread < 0 else "good"),
        f"Fed funds {fed:.2f}% · 2-year {y2:.2f}% · 10-year {y10:.2f}%",
    )
    c1, c2 = _chart_and_note()
    with c1:

        def r5(sid: str) -> pd.Series:
            return fred[sid][fred[sid].index >= five_y].resample("W").last()

        chart_title("Fed funds vs. 2Y and 10Y Treasury yields, %")
        st.plotly_chart(
            _line({"Fed funds": r5("DFF"), "2-year": r5("DGS2"), "10-year": r5("DGS10")}, height=270), width="stretch"
        )
        _source("Federal Reserve, U.S. Treasury via FRED (DFF, DGS2, DGS10), weekly")
    with c2:
        html(f"""<div class="side help"><div class="eyebrow">How to read this</div>
        <p>The <b>Fed funds rate</b> is set by the Fed. The <b>2-year</b> yield tracks where markets expect it to go. The
        <b>10-year</b> is set by the market and drives mortgage and corporate borrowing costs.</p>
        <p style="margin-top:.6rem">When short rates sit above long rates the curve is <b>inverted</b>: markets expect the Fed
        to cut because the economy will weaken. Today the 10-year minus 3-month spread is <b>{spread:+.2f} pts</b>.</p></div>""")

    # ----- 4. Regime & playbook -----
    _step(
        4,
        "Regime & sector positioning",
        _pill(now, "flat"),
        "Growth × inflation momentum → four regimes; sector excess returns since 1999",
    )
    boxes = []
    for r in ["Stagflation", "Reflation", "Slowdown", "Goldilocks"]:
        row = table.loc[r].dropna().sort_values(ascending=False)
        best = ", ".join(f"{s} <b>{v:+.0f}</b>" for s, v in row.head(2).items())
        worst = ", ".join(f"{s} <b>{v:+.0f}</b>" for s, v in row.tail(2).items())
        boxes.append(f"""<div class="quad {"on" if r == now else ""}" style="--c:{REGIME_COLORS[r]}">
          <div class="qh">{r}{"<span>NOW</span>" if r == now else ""}</div><div class="qs">{REGIME_SHORT[r]}</div>
          <p>{A.REGIME_DESC[r]}</p>
          <div class="qr"><span>Best</span>{best}</div><div class="qr"><span>Worst</span>{worst}</div>
          <div class="qm">{int(counts.loc[r].median())} months of history</div></div>""")
    html(
        '<div class="quad-axis">↑ Inflation rising</div><div class="quads">'
        + "".join(boxes)
        + '</div><div class="quad-axis x"><span>← Growth slowing</span><span>Growth accelerating →</span></div>'
    )
    caption(
        "Best/worst = average annual return vs. the S&amp;P 500, in percentage points. To avoid hindsight, each month's "
        "regime is applied to returns two months later, once the data had actually been published.",
        teach=True,
    )

    chart_title(f"Sector excess return in {now} regimes, pts per year vs. S&P 500")
    pb = playbook.sort_values()
    fig = go.Figure(
        go.Bar(
            x=pb.values,
            y=pb.index,
            orientation="h",
            marker=dict(color=[POS if v >= 0 else NEG for v in pb.values], cornerradius=4),
            text=[f"{v:+.1f}" for v in pb.values],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(color=INK_2),
            hovertemplate="%{y}: %{x:+.1f} pts a year<extra></extra>",
        )
    )
    style_fig(fig, 360, ysuffix="").update_layout(hovermode="closest", bargap=0.3)
    fig.update_xaxes(
        showgrid=True, gridcolor=GRID, title=dict(text="pts per year vs. S&P 500", font=dict(size=11, color=INK_3))
    )
    fig.update_yaxes(zeroline=False, gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")
    _source("SPDR sector ETFs (Yahoo Finance), monthly, regime labels lagged two months")

    # Regime history: recent stretches as a timeline, plus how the four regimes have split the time since 2000
    runs = A.regime_runs(regimes[regimes.index >= "2000-01-01"])
    recent = runs.tail(6).iloc[::-1]
    items = []
    for i, r in enumerate(recent.itertuples()):
        current = i == 0
        span = f"{r.start:%b %Y} – {'now' if current else f'{r.end:%b %Y}'}"
        items.append(
            f'<div class="tl-item {"now" if current else ""}" style="--c:{REGIME_COLORS[r.regime]}">'
            f'<div class="tl-dot"></div><div class="tl-body"><div class="tl-name">{r.regime}'
            f"{'<span>Current</span>' if current else ''}</div>"
            f'<div class="tl-meta">{span} · {r.months} month{"s" if r.months != 1 else ""}</div></div></div>'
        )
    stats = runs.groupby("regime")["months"].agg(["sum", "mean", "max"]).reindex(A.REGIMES)
    total = stats["sum"].sum()
    bar = "".join(
        f'<div style="flex:{stats.loc[r, "sum"]};background:{REGIME_COLORS[r]}" title="{r}: '
        f'{stats.loc[r, "sum"] / total * 100:.0f}% of months"></div>'
        for r in A.REGIMES
    )
    rows = "".join(
        f'<tr><td><span class="swatch" style="background:{REGIME_COLORS[r]}"></span>{r}</td>'
        f'<td class="n">{stats.loc[r, "sum"] / total * 100:.0f}%</td><td class="n">{stats.loc[r, "mean"]:.0f} mo</td>'
        f'<td class="n">{stats.loc[r, "max"]:.0f} mo</td></tr>'
        for r in A.REGIMES
    )
    c1, c2 = st.columns([1, 1.25], gap="large")
    with c1:
        chart_title("Recent regime changes")
        html(f'<div class="timeline">{"".join(items)}</div>')
    with c2:
        chart_title(f"Since 2000 · {len(runs)} stretches · median {runs['months'].median():.0f} months")
        html(
            f'<div class="share-bar">{bar}</div>'
            '<div class="tbl-wrap regime-stats"><table class="tbl"><tr class="th"><td>Regime</td><td>Share</td>'
            f"<td>Avg</td><td>Longest</td></tr>{rows}</table></div>"
        )
    caption(
        "A new regime only counts once it has held for two months in a row, which filters out one-off data blips. "
        "Regimes rarely last more than a year, so treat the sector playbook as a tilt, not a long-term bet.",
        teach=True,
    )

    with st.expander("See every sector in every regime"):
        lim = min(max(abs(table.min().min()), abs(table.max().max())), 12)
        fig = go.Figure(
            go.Heatmap(
                z=table.values,
                x=table.columns,
                y=table.index,
                zmin=-lim,
                zmax=lim,
                colorscale=[[0, NEG], [0.5, MID], [1, POS]],
                xgap=2,
                ygap=2,
                text=[[("n/a" if pd.isna(v) else f"{v:+.1f}") for v in row] for row in table.values],
                texttemplate="%{text}",
                textfont=dict(size=11, color=INK),
                hovertemplate="%{y} · %{x}<br>%{z:+.1f} pts a year vs. S&P 500<extra></extra>",
                showscale=False,
            )
        )
        style_fig(fig, 280, ysuffix="").update_layout(hovermode="closest")
        fig.update_yaxes(autorange="reversed", zeroline=False, gridcolor="rgba(0,0,0,0)")
        fig.update_xaxes(tickangle=-30)
        st.plotly_chart(fig, width="stretch")

    # ----- 5. Recession risk -----
    level = "good" if p_now < model["base_rate"] else "warn" if p_now < 40 else "bad"
    _step(
        5,
        "Recession risk",
        _pill(f"{p_now:.0f}% in the next 12 months", level),
        f"Unconditional base rate {model['base_rate']:.0f}% · logistic model on NBER-dated recessions since 1982",
    )
    lights = [
        (
            "Yield curve (10Y–3M)",
            f"{spread:+.2f} pts",
            "bad" if latest["spread_avg12"] < 0 else "warn" if spread < 0.25 else "good",
            "Inverted for a year on average = warning",
        ),
        (
            "Sahm rule",
            f"{latest['sahm']:+.2f} pts",
            "bad" if latest["sahm"] >= 0.5 else "warn" if latest["sahm"] >= 0.3 else "good",
            "Triggers at +0.50",
        ),
        (
            "Payrolls, 3-mo avg",
            f"{jobs_3m:,.0f}k / month",
            "bad" if jobs_3m < 0 else "warn" if jobs_3m < 75 else "good",
            "Below zero = warning",
        ),
        (
            "Industrial production",
            f"{ip_yoy.iloc[-1]:+.1f}% YoY",
            "bad" if ip_yoy.iloc[-1] < -1 else "warn" if ip_yoy.iloc[-1] < 0 else "good",
            "Shrinking = warning",
        ),
        (
            "S&amp;P 500 vs. 200-day MA",
            f"{sp_vs_200:+.1f}%",
            "bad" if sp_vs_200 < -5 else "warn" if sp_vs_200 < 0 else "good",
            "Below its trend = warning",
        ),
    ]
    c1, c2 = st.columns([1, 1.5], gap="large")
    with c1:
        rows = "".join(
            f'<tr><td class="m">{n}<div class="d">{why}</div></td><td class="v">{val}</td>'
            f"<td>{_pill({'good': 'Clear', 'warn': 'Watch', 'bad': 'Warning'}[lv], lv)}</td></tr>"
            for n, val, lv, why in lights
        )
        on = sum(light[2] != "good" for light in lights)
        html(
            f'<div class="score"><div class="score-h">Recession indicators · {on} of {len(lights)} flashing</div><table>{rows}</table></div>'
        )
        if (p_now >= 40) != (latest["spread_avg12"] < 0):
            html(
                f'<div class="flag">⚠ <b>Signals disagree.</b> The model reads {"elevated" if p_now >= 40 else "low"} risk, '
                f"but the yield curve on its own is {'inverted' if latest['spread_avg12'] < 0 else 'not inverted'}. "
                "Watch the jobs data to break the tie.</div>"
            )
    with c2:
        prob = model["prob"]
        chart_title("Recession probability, next 12 months, % · shaded: NBER recessions")
        fig = go.Figure(
            go.Scatter(
                x=prob.index,
                y=prob,
                mode="lines",
                line=dict(color=SERIES[0], width=2),
                hovertemplate="%{x|%b %Y}: %{y:.0f}%<extra></extra>",
            )
        )
        fig.add_hline(y=50, line=dict(color=INK_3, dash="dot", width=1))
        style_fig(fig, 300).update_layout(hovermode="x", showlegend=False)
        fig.update_yaxes(range=[0, 100])
        shade_periods(fig, panel["usrec"].reindex(prob.index).fillna(0).astype(bool), "")
        st.plotly_chart(fig, width="stretch")
        _source("Model estimates; NBER via FRED (USREC)")

    odds = model["odds_per_unit"]
    explain(
        "the recession model",
        f"""
    <p>A logistic regression estimates the chance the economy is in an official (NBER-dated) recession at some point
    in the next 12 months, from three inputs:</p>
    <ul>
      <li><b>Yield curve, 12-month average:</b> each 1-pt lower spread multiplies the odds by {1 / odds["spread_avg12"]:.1f}×.</li>
      <li><b>Sahm gap (unemployment vs. its recent low):</b> each 1-pt rise multiplies the odds by {odds["sahm"]:.1f}×.</li>
      <li><b>Industrial production growth:</b> each 1-pt drop multiplies the odds by {1 / odds["indpro_yoy"]:.2f}×.</li>
    </ul>
    <p><b>Accuracy:</b> AUC (0.5 = coin flip, 1.0 = perfect) is {model["auc_in"]:.2f} on all data. Trained only on
    1982–2005 and tested on 2006 onward, which includes 2008 and 2020, it scores {model["auc_oos"]:.2f}.</p>
    <p><b>Limits:</b> only ~6 recessions to learn from, and it flashed high odds in 2022–23 when the curve inverted
    deeply and no recession came.</p>
    """,
    )
