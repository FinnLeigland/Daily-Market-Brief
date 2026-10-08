"""Warm the caches behind the heavier tabs in the background, so the first click on each one is instant.

Runs once per browser session, right after the Digest has rendered. Every call goes through the same cached
functions (with the same arguments) the tabs use, so the work is shared, never duplicated. Failures are ignored:
the tab simply fetches on demand as before.
"""

import os
import threading
from contextlib import suppress

from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

import config
import data

_running = threading.Lock()  # at most one warm-up at a time across all sessions


def _jobs():
    import signal_checks
    from views import ideas, micro, regime, stock_lab

    yield signal_checks.load  # slowest first: decades of history; its numbers feed notes on several tabs
    yield lambda: data.get_fred(regime.FRED_IDS)
    yield lambda: data.get_prices(tuple(list(config.ALL_SECTORS) + ["SPY"]), period="max", interval="1mo")
    yield lambda: data.get_prices(tuple(list(config.ALL_SECTORS) + [config.BENCHMARK]), period="2y", interval="1wk")

    def _stock_lab():
        info = data.get_info("NVDA")
        if info.get("currentPrice"):
            etf, _ = stock_lab.peer_context("NVDA", info)
            stock_lab.price_history("NVDA", etf)

    def _micro():
        sec = data.get_sector(data.YF_SECTORS["Technology"])
        if sec and sec["industries"]:
            micro.industry_prices("Technology", micro.industry_table(sec))

    yield ideas.inputs  # the daily screen: sector holdings, prices and company data
    yield lambda: ideas._backtest(tuple((g, tuple(ts)) for g, ts in ideas._candidates().items()))
    yield _stock_lab
    yield _micro


def _run() -> None:
    try:
        for job in _jobs():
            with suppress(Exception):
                job()
    finally:
        _running.release()


def warm(session_state) -> None:
    if os.environ.get("DISABLE_PREFETCH") == "1":  # set by the quick data refresh, which only needs one or two tabs
        return
    if session_state.get("_prefetched") or not _running.acquire(blocking=False):
        return
    session_state["_prefetched"] = True
    thread = threading.Thread(target=_run, name="prefetch", daemon=True)
    add_script_run_ctx(thread, get_script_run_ctx())  # cached functions expect a script context
    thread.start()
