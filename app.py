"""Daily Market Brief: a macro & equity research dashboard. A five-minute read on markets, plus research labs."""

import traceback
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

import config
import data
import prefetch
from theme import html, show_help, show_warnings
from views import desk, digest, ideas, learn, micro, regime, rotation, stock_lab

st.set_page_config(page_title="Daily Market Brief", page_icon=":material/finance_mode:", layout="wide")
st.markdown(f"<style>{Path(__file__).with_name('style.css').read_text()}</style>", unsafe_allow_html=True)
if not show_help():
    # "Clean view": hide inline descriptions that live inside HTML blocks (helpers skip the rest).
    st.markdown(
        "<style>.help, .score td.m .d, .quad p, .legend-row .desc { display: none !important; }</style>",
        unsafe_allow_html=True,
    )
if not show_warnings():
    st.markdown("<style>.warn-note { display: none !important; }</style>", unsafe_allow_html=True)

data.reset_stale()
holdings = {s["etf"]: data.get_top_holdings(s["etf"], tuple(s["fallback_holdings"])) for s in config.FEATURED_SECTORS}
tickers = {p["ticker"] for p in config.PULSE} | {config.BENCHMARK} | set(config.ALL_SECTORS) | set(config.INDICES)
tickers |= {s["etf"] for s in config.FEATURED_SECTORS}
tickers |= {h for hs in holdings.values() for h in hs}

prices = None
with st.spinner("Pulling this morning's numbers…"), suppress(RuntimeError):
    prices = data.get_prices(tuple(sorted(tickers)))
if prices is None:  # outside the spinner, so it doesn't stay on screen above the message
    st.error(
        "Market data couldn't be loaded right now: Yahoo Finance didn't respond and no saved copy is available yet. "
        "Refresh in a minute."
    )
    st.stop()

session = prices[config.BENCHMARK].dropna().index[-1]
now_et = datetime.now(ZoneInfo("America/New_York"))

html(f"""
<div class="masthead">
  <div>
    <div class="eyebrow">Daily Market Brief</div>
    <div class="h1">{now_et.strftime("%A, %B")} {now_et.day}</div>
  </div>
  <div class="meta">Latest session: {session.strftime("%a %b")} {session.day}<br>Updated {now_et.strftime("%-I:%M %p")} ET</div>
</div>
""")

stale_note = st.empty()  # filled at the end of the run, once every fetch on this page has happened

if st.session_state.get("learn_open"):
    learn.render()
else:
    # Lazy tabs: only the open tab's code runs, so every click stays fast.
    tabs = st.tabs(
        ["Digest", "Macro", "Micro", "Sector Rotation", "Stock Lab", "Equity Screen", "Analyst Desk"],
        key="main_tab",
        on_change="rerun",
    )

    def _digest() -> None:
        with st.spinner("Gathering headlines…"):
            news = data.get_news()
        digest.render(prices, news, holdings)

    views = [
        _digest,
        lambda: regime.render(prices),
        micro.render,
        lambda: rotation.render(prices),
        stock_lab.render,
        ideas.render,
        desk.render,  # PIN-protected: trade journal, daily lesson, display settings
    ]
    for tab, view in zip(tabs, views, strict=True):
        if tab.open:
            with tab:
                try:
                    view()
                except Exception:  # Streamlit's own stop/rerun signals are BaseExceptions and pass through
                    traceback.print_exc()  # full details in the server log
                    st.warning(
                        "Part of this tab couldn't load right now (market data didn't arrive). Refresh in a minute."
                    )

if (saved_at := data.stale_since()) is not None:
    when = datetime.fromtimestamp(saved_at, ZoneInfo("America/New_York"))
    stale_note.info(
        f"Yahoo Finance isn't responding to this server right now, so some numbers come from a copy saved "
        f"{when:%a %b} {when.day}, {when:%-I:%M %p} ET. They update on their own once Yahoo responds.",
        icon=":material/history:",
    )

prefetch.warm(st.session_state)

html(
    '<div class="footnote">Prices via Yahoo Finance (yfinance), macro data via FRED, recession dates via NBER, '
    "headlines via Google News. For education only, not investment advice.</div>"
)
