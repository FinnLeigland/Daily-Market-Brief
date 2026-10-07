"""Micro: the structure inside a sector. Which industries lead, how concentrated each one is, and how its
companies compare on growth, profitability and valuation. (Single-company deep dives live in the Stock Lab.)"""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import analytics as A
import config
import data
from theme import (
    GRID,
    INK,
    INK_2,
    INK_3,
    MID,
    MUTED,
    NEG,
    POS,
    SERIES,
    caption,
    chart_title,
    explain,
    fmt_value,
    html,
    section,
    style_fig,
)

PERIODS = {"1M": 21, "3M": 63, "YTD": "ytd", "1Y": 252}


def _money(x: float | None) -> str:
    if not x:
        return "—"
    return f"${x / 1e12:.2f}T" if x >= 1e12 else f"${x / 1e9:.1f}B" if x >= 1e9 else f"${x / 1e6:.0f}M"


def _count(x: float | None) -> str:
    return "—" if not x else f"{x / 1e6:.1f}M" if x >= 1e6 else f"{x / 1e3:.0f}k" if x >= 1e3 else f"{x:,.0f}"


def _upside(row: dict) -> str:
    target, last = row.get("target price"), row.get("last price")
    return f"{(target / last - 1) * 100:+.0f}%" if target and last else "—"


def _ret(s: pd.Series, period: str) -> float | None:
    return data.ytd_change(s) if period == "YTD" else data.pct_change(s, PERIODS[period])


def _tiles(items: list[tuple[str, str]]) -> None:
    html(
        '<div class="pulse">'
        + "".join(
            f'<div class="pulse-item"><div class="pulse-label">{k}</div><div class="pulse-value">{v}</div></div>'
            for k, v in items
        )
        + "</div>"
    )


def _open_in_lab(key: str) -> None:
    """Jump to the Stock Lab with the chosen company loaded."""
    ticker = st.session_state.get(key)
    if ticker:
        st.session_state["stock_ticker"] = ticker
        st.session_state["main_tab"] = "Stock Lab"


def industry_table(sec: dict) -> pd.DataFrame:
    industries = pd.DataFrame(sec["industries"]).dropna(subset=["symbol"])
    return industries[industries["market weight"] > 0].sort_values("market weight", ascending=False)


def industry_prices(sector: str, industries: pd.DataFrame) -> pd.DataFrame:
    """Two years of each industry index, plus the sector ETF."""
    etf = config.SECTOR_ETF_BY_NAME.get(sector)
    return data.get_prices(tuple(industries["symbol"]) + ((etf,) if etf else ()), period="2y")


def render() -> None:
    sectors = list(data.YF_SECTORS)
    sector = st.pills("Sector", sectors, default="Technology", key="micro_sector", label_visibility="collapsed")
    sector = sector or "Technology"
    with st.spinner("Loading sector structure…"):
        sec = data.get_sector(data.YF_SECTORS[sector])
    if not sec or not sec["industries"]:
        st.warning("Sector data couldn't be loaded right now. Try again in a minute.")
        return
    ov = sec["overview"]
    industries = industry_table(sec)

    # ----- Sector anatomy -----
    section(f"{sector}: sector anatomy", "Yahoo Finance sector and industry classifications")
    _tiles(
        [
            ("Market cap", _money(ov.get("market_cap"))),
            ("Share of US market", f"{(ov.get('market_weight') or 0) * 100:.1f}%"),
            ("Companies", f"{ov.get('companies_count') or 0:,}"),
            ("Industries", str(ov.get("industries_count") or len(industries))),
            ("Employees", _count(ov.get("employee_count"))),
        ]
    )
    if ov.get("description"):
        caption(escape(ov["description"]))

    # Industry performance from Yahoo's industry indexes
    etf = config.SECTOR_ETF_BY_NAME.get(sector)
    px = industry_prices(sector, industries)
    period = (
        st.segmented_control("Period", list(PERIODS), default="3M", key="micro_period", label_visibility="collapsed")
        or "3M"
    )
    rows = []
    for r in industries.to_dict("records"):
        s = px[r["symbol"]] if r["symbol"] in px else pd.Series(dtype=float)
        rows.append(
            {
                "key": r["key"],
                "Industry": r["name"],
                "Weight": r["market weight"] * 100,
                **{p: (_ret(s, p) if s.notna().sum() > 30 else None) for p in PERIODS},
            }
        )
    perf = pd.DataFrame(rows)
    bench = _ret(px[etf], period) if etf and etf in px else None
    if bench is not None:
        perf["vs. sector"] = perf[period] - bench

    c1, c2 = st.container(), st.container()  # stacked full width: long industry names need the room
    with c1:
        chart_title(f"Industry map · size = weight in sector · color = {period} return")
        lim = max(5.0, min(30.0, perf[period].abs().quantile(0.9) if perf[period].notna().any() else 10))
        fig = go.Figure(
            go.Treemap(
                labels=perf["Industry"],
                parents=[""] * len(perf),
                values=perf["Weight"],
                marker=dict(
                    colors=perf[period].fillna(0),
                    colorscale=[[0, NEG], [0.5, MID], [1, POS]],
                    cmin=-lim,
                    cmax=lim,
                    line=dict(color="#0e0e0d", width=2),
                    pad=dict(t=0, l=0, r=0, b=0),  # children cover the implicit root, so no gray frame
                ),
                text=[f"{v:+.1f}%" if pd.notna(v) else "n/a" for v in perf[period]],
                texttemplate="<b>%{label}</b><br>%{text}",
                textfont=dict(color=INK, size=12),
                customdata=perf["Weight"],
                hovertemplate="<b>%{label}</b><br>%{customdata:.1f}% of sector<br>"
                + period
                + ": %{text}<extra></extra>",
                tiling=dict(pad=0),
                root=dict(color="rgba(0,0,0,0)"),
                pathbar=dict(visible=False),
            )
        )
        fig.update_layout(
            height=360,
            margin=dict(l=0, r=0, t=4, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            uniformtext=dict(minsize=10, mode="hide"),  # tiles too small for a readable label show it on hover
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with c2:
        chart_title(
            f"Industry returns · {period}" + (f" · dotted line: sector ETF ({etf})" if bench is not None else "")
        )
        p = perf.dropna(subset=[period]).sort_values(period)
        fig = go.Figure(
            go.Bar(
                x=p[period],
                y=p["Industry"],
                orientation="h",
                marker=dict(color=[POS if v >= 0 else NEG for v in p[period]], cornerradius=3),
                text=[f"{v:+.1f}%" for v in p[period]],
                textposition="outside",
                cliponaxis=False,
                textfont=dict(color=INK_2, size=11),
                hovertemplate="%{y}: %{x:+.1f}%<extra></extra>",
            )
        )
        if bench is not None:
            fig.add_vline(x=bench, line=dict(color=INK_3, dash="dot", width=1.3))
        style_fig(fig, 60 + 26 * len(p), ysuffix="").update_layout(hovermode="closest", bargap=0.3, margin=dict(r=50))
        fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID)
        fig.update_yaxes(zeroline=False, gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    leaders = perf.dropna(subset=[period]).sort_values(period)
    if len(leaders) >= 2 and bench is not None:
        top, bot = leaders.iloc[-1], leaders.iloc[0]
        caption(
            f"Over {period}, <b>{escape(top['Industry'])}</b> led the sector at {top[period]:+.1f}% "
            f"({top['vs. sector']:+.1f} pts vs. {etf}), while <b>{escape(bot['Industry'])}</b> lagged at "
            f"{bot[period]:+.1f}%. The largest industry, {escape(perf.iloc[0]['Industry'])}, is "
            f"{perf.iloc[0]['Weight']:.0f}% of the sector, so it largely sets the sector's direction."
        )

    fmt = {"Weight": "{:.1f}%", **{p: "{:+.1f}%" for p in PERIODS}, "vs. sector": "{:+.1f}"}
    show = perf.drop(columns="key").set_index("Industry")
    st.dataframe(
        show.style.format({c: (lambda v, f=f: fmt_value(f, v)) for c, f in fmt.items()}).map(
            lambda v: f"color: {'#3ec46d' if v > 0 else '#f06a6a'}" if isinstance(v, float) and pd.notna(v) else "",
            subset=[c for c in show.columns if c != "Weight"],
        ),
        width="stretch",
        height=min(38 + 35 * len(show), 460),
    )

    # ----- Industry deep dive -----
    names = dict(zip(perf["Industry"], perf["key"], strict=True))
    choice = st.selectbox("Industry", list(names), key=f"micro_industry_{sector}")
    with st.spinner("Loading industry…"):
        ind = data.get_industry(names[choice])
    if not ind or not ind["top_companies"]:
        st.warning("Industry data couldn't be loaded right now.")
        return
    io = ind["overview"]
    comps = pd.DataFrame(ind["top_companies"]).dropna(subset=["market weight"])
    conc = A.concentration(comps["market weight"].tolist())

    section(f"{choice}: industry structure", f"{io.get('companies_count') or len(comps)} companies")
    _tiles(
        [
            ("Market cap", _money(io.get("market_cap"))),
            ("Share of sector", f"{(io.get('market_weight') or 0) * 100:.1f}%"),
            ("Leader's share", f"{conc['leader']:.0f}%"),
            ("Top 3 share (CR3)", f"{conc['cr3']:.0f}%"),
            ("HHI", f"{conc['hhi']:,.0f}"),
        ]
    )
    if io.get("description"):
        caption(escape(io["description"]))

    c1, c2 = st.columns([1, 1.2], gap="large")
    with c1:
        top10 = comps.sort_values("market weight", ascending=False).head(10).iloc[::-1]
        chart_title(f"Share of industry market cap · {conc['label'].lower()}")
        fig = go.Figure(
            go.Bar(
                x=top10["market weight"] * 100,
                y=top10["symbol"],
                orientation="h",
                marker=dict(
                    color=[SERIES[0] if i == len(top10) - 1 else MUTED for i in range(len(top10))], cornerradius=3
                ),
                text=[f"{v * 100:.1f}%" for v in top10["market weight"]],
                textposition="outside",
                cliponaxis=False,
                textfont=dict(color=INK_2, size=11),
                customdata=top10["name"],
                hovertemplate="%{customdata}: %{x:.1f}% of industry<extra></extra>",
            )
        )
        style_fig(fig, 380, ysuffix="").update_layout(hovermode="closest", bargap=0.3, margin=dict(r=40))
        fig.update_xaxes(ticksuffix="%", showgrid=True, gridcolor=GRID)
        fig.update_yaxes(zeroline=False, gridcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        caption(
            f"HHI of <b>{conc['hhi']:,.0f}</b> reads as <b>{conc['label'].lower()}</b> under the 2023 U.S. Merger "
            "Guidelines (above 1,800 = highly concentrated). Concentrated industries tend to have more pricing power "
            "and steadier margins; fragmented ones compete harder on price. Shares here use market cap as a proxy.",
            teach=True,
        )

    # Fundamentals for the largest companies
    tickers = comps.sort_values("market weight", ascending=False)["symbol"].head(10).tolist()
    with st.spinner("Comparing the largest companies…"):
        infos = {t: i for t, i in data.get_infos(tickers).items() if i.get("marketCap")}
    with c2:
        land = pd.DataFrame(
            [
                {
                    "t": t,
                    "growth": (i.get("revenueGrowth") or 0) * 100,
                    "margin": (i.get("operatingMargins") or 0) * 100,
                    "cap": i["marketCap"],
                    "pe": i.get("forwardPE"),
                }
                for t, i in infos.items()
                if i.get("revenueGrowth") is not None and i.get("operatingMargins") is not None
            ]
        )
        chart_title("Competitive landscape · growth vs. margin · size = market cap")
        if len(land) >= 2:
            size = 18 + 42 * (land["cap"] / land["cap"].max()) ** 0.5
            fig = go.Figure(
                go.Scatter(
                    x=land["growth"],
                    y=land["margin"],
                    mode="markers+text",
                    text=land["t"],
                    textposition="top center",
                    textfont=dict(color=INK, size=11),
                    marker=dict(size=size, color=SERIES[0], opacity=0.75, line=dict(color="#0e0e0d", width=1.5)),
                    customdata=[_money(c) for c in land["cap"]],
                    hovertemplate="<b>%{text}</b><br>Revenue growth %{x:.1f}%<br>Operating margin %{y:.1f}%"
                    "<br>Market cap %{customdata}<extra></extra>",
                )
            )
            fig.add_vline(x=land["growth"].median(), line=dict(color=MUTED, width=1, dash="dot"))
            fig.add_hline(y=land["margin"].median(), line=dict(color=MUTED, width=1, dash="dot"))
            for txt, xa, ya, x, y in [
                ("Growing & profitable", "right", "top", 1, 1),
                ("Profitable, slower", "left", "top", 0, 1),
                ("Growing, thinner margins", "right", "bottom", 1, 0),
                ("Slower, thinner margins", "left", "bottom", 0, 0),
            ]:
                fig.add_annotation(
                    x=x,
                    y=y,
                    xref="paper",
                    yref="paper",
                    text=txt,
                    showarrow=False,
                    xanchor=xa,
                    yanchor=ya,
                    font=dict(size=10, color=INK_3),
                    bgcolor="rgba(14,14,13,0.75)",
                    opacity=0.9,
                )
            style_fig(fig, 380, ysuffix="%").update_layout(hovermode="closest")

            def padded(col: str, pad: float = 0.16) -> list[float]:
                # Room around the bubbles so none sits under a corner label or gets clipped at the edge.
                lo, hi = float(land[col].min()), float(land[col].max())
                span = (hi - lo) or abs(hi) or 1
                return [lo - span * pad, hi + span * pad]

            fig.update_yaxes(range=padded("margin"))
            fig.update_xaxes(
                range=padded("growth"),
                ticksuffix="%",
                showgrid=True,
                gridcolor=GRID,
                title=dict(text="Revenue growth (YoY)", font=dict(size=11, color=INK_3)),
            )
            fig.update_yaxes(title=dict(text="Operating margin", font=dict(size=11, color=INK_3)))
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            caption("Not enough fundamentals available to chart this industry's landscape.")

    # Peer table
    weight = dict(zip(comps["symbol"], comps["market weight"], strict=True))
    table = pd.DataFrame(
        [
            {
                "Company": i.get("shortName") or t,
                "Ticker": t,
                "Market cap": i.get("marketCap"),
                "Share": weight.get(t, 0) * 100,
                "Fwd P/E": i.get("forwardPE"),
                "P/S": i.get("priceToSalesTrailing12Months"),
                "Op margin": (i.get("operatingMargins") or float("nan")) * 100,
                "Rev growth": (i.get("revenueGrowth") or float("nan")) * 100,
                "Rating": (i.get("recommendationKey") or "").replace("_", " ").title(),
            }
            for t, i in infos.items()
        ]
    )
    if not table.empty:
        section("Peer comparison", "The industry's largest companies, side by side")
        st.dataframe(
            table.set_index("Company").style.format(
                {
                    "Market cap": _money,
                    **{
                        c: (lambda v, f=f: fmt_value(f, v))
                        for c, f in {
                            "Share": "{:.1f}%",
                            "Fwd P/E": "{:.1f}×",
                            "P/S": "{:.1f}×",
                            "Op margin": "{:.1f}%",
                            "Rev growth": "{:+.1f}%",
                        }.items()
                    },
                },
                na_rep="—",
            ),
            width="stretch",
        )
        med = table[["Fwd P/E", "Op margin", "Rev growth"]].median()
        caption(
            f"Industry medians: forward P/E <b>{med['Fwd P/E']:.1f}×</b>, operating margin <b>{med['Op margin']:.1f}%</b>, "
            f"revenue growth <b>{med['Rev growth']:+.1f}%</b>."
        )

    # Leaders lists
    c1, c2 = st.columns(2, gap="large")
    with c1:
        perf_rows = ind["top_performing"][:6]
        if perf_rows:
            chart_title("Top performers year to date")
            rows = "".join(
                f'<tr><td><b class="tk">{escape(r["symbol"])}</b><div class="d">{escape(str(r.get("name", "")))}</div></td>'
                f'<td class="n">{(r.get("ytd return") or 0) * 100:+.0f}%</td>'
                f'<td class="n">{_upside(r)}</td></tr>'
                for r in perf_rows
            )
            html(
                f'<div class="tbl-wrap"><table class="tbl"><tr class="th"><td>Company</td><td>YTD</td><td>To analyst target</td></tr>{rows}</table></div>'
            )
    with c2:
        growth_rows = ind["top_growth"][:6]
        if growth_rows:
            chart_title("Fastest expected earnings growth")
            rows = "".join(
                f'<tr><td><b class="tk">{escape(r["symbol"])}</b><div class="d">{escape(str(r.get("name", "")))}</div></td>'
                f'<td class="n">{(r.get("growth estimate") or 0) * 100:+.0f}%</td>'
                f'<td class="n">{(r.get("ytd return") or 0) * 100:+.0f}%</td></tr>'
                for r in growth_rows
            )
            html(
                f'<div class="tbl-wrap"><table class="tbl"><tr class="th"><td>Company</td><td>Growth est.</td><td>YTD</td></tr>{rows}</table></div>'
            )

    # Hand-off to the Stock Lab for single-company work
    lab = list(dict.fromkeys(tickers[:8] + [r["symbol"] for r in ind["top_performing"][:3]]))
    html(
        '<div class="handoff"><div class="eyebrow">Go deeper</div><p>Open any company in the Stock Lab for its '
        "full scorecard, price history and explained price moves.</p></div>"
    )
    st.pills(
        "Open in Stock Lab",
        lab,
        key="micro_open",
        on_change=_open_in_lab,
        args=("micro_open",),
        label_visibility="collapsed",
    )

    explain(
        "industry structure",
        """
    <p><b>Why micro matters.</b> Macro tells you the weather; micro tells you about the terrain. Two companies in the
    same economy can have very different prospects depending on how their industry is structured.</p>
    <p><b>Concentration.</b> CR3 is the combined share of the three largest firms. HHI squares each firm's percentage
    share and adds them up, so it weights big players more heavily: 10,000 is a monopoly; ten equal firms score 1,000.
    Concentrated industries often have pricing power; fragmented ones tend to compete on price.</p>
    <p><b>The landscape chart.</b> Firms in the top-right are growing <i>and</i> keeping more of each dollar, usually
    the industry's strongest competitors. Firms in the bottom-left are under pressure. Compare valuations in the peer
    table to see whether the market is already paying up for the leaders.</p>
    <p><b>Industry vs. sector returns.</b> A sector ETF is a weighted blend of its industries. When one large industry
    dominates, the sector's performance mostly reflects that one industry, which can hide weakness elsewhere.</p>
    """,
    )
