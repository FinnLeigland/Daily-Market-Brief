"""Tab 1: the Digest, a five-minute daily brief."""

import re
from html import escape

import streamlit as st

import config
import data
import signal_checks
from theme import chg_span, direction, fmt_pct, html, section, sparkline, warn


def render(prices, news, holdings) -> None:
    spy = prices[config.BENCHMARK]
    # Market pulse strip
    tiles = []
    for p in config.PULSE:
        s = prices[p["ticker"]].dropna()
        last, prev = s.iloc[-1], s.iloc[-2]
        if p["kind"] == "yield":
            bp = (last - prev) * 100
            value, chg = f"{last:.2f}%", chg_span(bp, text=f"{'▲' if bp > 0 else '▼' if bp < 0 else ''} {bp:+.0f} bp")
        else:
            value = f"${last:,.2f}" if p["kind"] == "price" else f"{last:,.2f}"
            chg = chg_span((last / prev - 1) * 100, 2)
        tiles.append(
            f'<div class="pulse-item"><div class="pulse-label">{p["label"]}</div>'
            f'<div class="pulse-value">{value}</div>{chg}</div>'
        )
    html(f'<div class="pulse">{"".join(tiles)}</div>')

    # Sector stats used by both the brief and the cards
    spy_1m = data.pct_change(spy, 21)
    stats = []
    for sec in config.FEATURED_SECTORS:
        s = prices[sec["etf"]]
        stats.append(
            {
                **sec,
                "d1": data.pct_change(s, 1),
                "w1": data.pct_change(s, 5),
                "m1": data.pct_change(s, 21),
                "ytd": data.ytd_change(s),
                "trend": data.trend_state(s),
                "series": s,
            }
        )

    # The brief: rule-based summary sentences
    sp = prices["^GSPC"]
    sp_d1, nq_d1 = data.pct_change(sp, 1), data.pct_change(prices["^IXIC"], 1)
    verb = "rose" if sp_d1 > 0 else "fell"
    by_day = sorted(stats, key=lambda x: x["d1"])
    by_month = sorted(stats, key=lambda x: x["m1"])
    tnx = prices["^TNX"].dropna()
    bp = (tnx.iloc[-1] - tnx.iloc[-2]) * 100
    vix = prices["^VIX"].dropna().iloc[-1]
    vix_mood = "calm" if vix < 15 else "normal" if vix < 20 else "elevated" if vix < 30 else "fearful"
    rate_note = (
        " Rising yields tend to weigh on rate-sensitive groups like real estate and long-duration growth stocks."
        if bp >= 5
        else " Falling yields usually help rate-sensitive groups like real estate."
        if bp <= -5
        else ""
    )
    leader_m = by_month[-1]
    html(f"""
    <div class="brief"><ul>
      <li>Stocks <b>{verb}</b> in the latest session: the S&amp;P 500 {chg_span(sp_d1, 2)} and the Nasdaq {chg_span(nq_d1, 2)}.</li>
      <li>Of the sectors below, <b>{by_day[-1]["name"]}</b> led ({fmt_pct(by_day[-1]["d1"])}) and <b>{by_day[0]["name"]}</b> lagged ({fmt_pct(by_day[0]["d1"])}).</li>
      <li>Over the past month, <b>{leader_m["name"]}</b> is the strongest at {fmt_pct(leader_m["m1"])}, against {fmt_pct(spy_1m)} for the S&amp;P 500.</li>
      <li>The 10-year Treasury yield moved <b>{bp:+.0f} bp</b> to {tnx.iloc[-1]:.2f}%.{rate_note}</li>
      <li>The VIX is at {vix:.1f}, which reads as <b>{vix_mood}</b> (long-run average is about 19).</li>
    </ul></div>
    """)

    # Sector cards
    section("Sectors to watch", "Sector ETFs, plus Global X AIQ for AI · trend from 50- and 200-day averages")
    cards = []
    for st_ in stats:
        t = st_["trend"]
        tone = {"Uptrend": "up", "Recovering": "up", "Downtrend": "down", "Weakening": "down"}.get(t["label"], "flat")
        icon = {"up": "↗", "down": "↘", "flat": "→"}[tone]
        rel = st_["m1"] - spy_1m
        note = (
            f"{'Up' if st_['m1'] >= 0 else 'Down'} {abs(st_['m1']):.1f}% over the past month, "
            f"{'ahead of' if rel >= 0 else 'behind'} the S&amp;P 500 by {abs(rel):.1f} pts. "
            f"Trading {abs(t['vs_ma50']):.1f}% {'above' if t['vs_ma50'] >= 0 else 'below'} its 50-day average "
            f"and {abs(t['vs_ma200']):.1f}% {'above' if t['vs_ma200'] >= 0 else 'below'} its 200-day."
        )
        movers = sorted(
            ((h, data.pct_change(prices[h], 1)) for h in holdings[st_["etf"]] if h in prices),
            key=lambda x: x[1] if x[1] is not None else 0,
            reverse=True,
        )[:4]
        mover_rows = "".join(f'<div class="row"><b>{h}</b>{chg_span(c, 2)}</div>' for h, c in movers)
        top = news.get(st_["name"], [])
        read = (
            (
                f'<div class="card-read"><a href="{escape(top[0]["link"])}" target="_blank">{escape(top[0]["title"])}</a>'
                f'<div class="src">{escape(top[0]["source"])} · {data.time_ago(top[0]["published"])}</div></div>'
            )
            if top
            else ""
        )
        cards.append(f"""
        <div class="card">
          <div class="card-top">
            <div><div class="card-name">{st_["name"]}</div><div class="card-etf">{st_["etf"]}</div></div>
            <span class="pill {tone}">{icon} {t["label"]}</span>
          </div>
          <div class="card-big"><span class="num {direction(st_["d1"])}">{fmt_pct(st_["d1"], 2)}</span><span class="lbl">today</span></div>
          {sparkline(st_["series"].dropna().iloc[-63:])}
          <div class="stats">
            <div><div class="k">1W</div>{chg_span(st_["w1"])}</div>
            <div><div class="k">1M</div>{chg_span(st_["m1"])}</div>
            <div><div class="k">YTD</div>{chg_span(st_["ytd"])}</div>
          </div>
          <div class="card-note">{note}</div>
          <div class="movers"><div class="h">Top holdings today</div>{mover_rows}</div>
          {read}
        </div>""")
    html(f'<div class="sectors">{"".join(cards)}</div>')
    chk = signal_checks.peek()
    evidence = (
        f" Since 1999, sectors labeled Uptrend averaged {chk['trend_avg']:+.2f} pts vs. the S&P 500 the next month "
        f"(t = {chk['trend_t']:.1f}), which is no measurable edge."
        if chk
        else " Backtested since 1999, sectors labeled Uptrend did no better than the market the next month."
    )
    warn(
        f"<b>The trend labels describe the trend; they don't predict it.</b>{evidence} Use them for context, not as buy signals."
    )

    # Reading list + sidebar
    section("Worth reading", "From Reuters, CNBC, Yahoo Finance, WSJ, Bloomberg and others · last 48 hours")

    # Each story appears once: skip anything already shown on a sector card or earlier in the list.
    def key(a: dict) -> str:
        return re.sub(r"[^a-z0-9]", "", a["title"].lower())[:60]

    used = {key(news[s["name"]][0]) for s in config.FEATURED_SECTORS if news.get(s["name"])}
    picks = []
    for a in news.get("Market", []):
        if len(picks) == 3:
            break
        if key(a) not in used:
            picks.append(("Markets", a))
            used.add(key(a))
    for s in config.FEATURED_SECTORS:
        extra = [a for a in news.get(s["name"], []) if key(a) not in used]
        if extra:
            picks.append((s["name"], extra[0]))
            used.add(key(extra[0]))

    left, right = st.columns([2, 1], gap="large")
    with left:
        items = "".join(
            f'<a class="article" href="{escape(a["link"])}" target="_blank"><div class="tag">{tag}</div>'
            f'<div class="t">{escape(a["title"])}</div><div class="src">{escape(a["source"])} · {data.time_ago(a["published"])}</div></a>'
            for tag, a in picks
        )
        html(f'<div class="reading">{items or "<p>No articles could be loaded right now.</p>"}</div>')
    with right:
        term, definition = config.GLOSSARY[config.today_et().toordinal() % len(config.GLOSSARY)]
        html(
            f'<div class="side"><div class="eyebrow">Term of the day</div><div class="term">{term}</div><p>{definition}</p></div>'
        )
        html("""
        <div class="side help"><div class="eyebrow">How to read the trend labels</div><dl>
          <dt>↗ Uptrend</dt><dd>Price above the 50-day average, which is above the 200-day.</dd>
          <dt>↗ Recovering</dt><dd>Back above both averages, but the 50-day is still below the 200-day.</dd>
          <dt>→ Pulling back</dt><dd>Dipped below the 50-day but still above the 200-day.</dd>
          <dt>→ Rebounding</dt><dd>Above the 50-day but still below the 200-day.</dd>
          <dt>↘ Weakening / Downtrend</dt><dd>Below both averages; a downtrend when the 50-day is also below the 200-day.</dd>
        </dl></div>
        """)
