"""Daily alert check. Run after the US market close (GitHub Actions does this on weekdays).

    uv run python scripts/daily_check.py --dry-run     # print today's alerts, send nothing
    uv run python scripts/daily_check.py               # send alerts through the configured channels
    uv run python scripts/daily_check.py --test        # send a test notification

Reads the watchlist and open positions from the WATCHLIST_JSON environment variable (a GitHub secret, copied from
the app) or, when running locally, straight from journal.json.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import alerts as AL  # noqa: E402
import journal as J  # noqa: E402
import notify  # noqa: E402


def load_config() -> dict:
    raw = os.environ.get("WATCHLIST_JSON")
    return json.loads(raw) if raw else J.automation_config(J.load())


def explain_big_moves(found: list, closes, day) -> None:
    """Add Claude's one-line explanation to unusual moves, when an API key is configured. Never fails the run."""
    try:
        import ai
        import data

        if not ai.available():
            return
        bench = closes["SPY"].pct_change(fill_method=None).iloc[-1] * 100
        for a in (x for x in found if x.kind == "big_move"):
            info = data.get_info(a.ticker)
            name = info.get("longName") or a.ticker
            ret = closes[a.ticker].pct_change(fill_method=None).iloc[-1] * 100
            ev = {
                "day": f"{day:%Y-%m-%d}",
                "ret": ret,
                "bench": bench,
                "earnings": None,
                "news": data.get_event_news(a.ticker, name, f"{day:%Y-%m-%d}"),
            }
            why = ai.explain_moves(a.ticker, name, [ev]).get(ev["day"])
            if why:
                a.detail += f". Why: {why['summary']}"
    except Exception as e:  # explanations are a bonus; the alert still goes out
        print(f"(skipped AI explanations: {e})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print alerts without sending them")
    ap.add_argument("--test", action="store_true", help="send a test notification and exit")
    ap.add_argument("--any-day", action="store_true", help="evaluate even if there's no new close today")
    args = ap.parse_args()

    if args.test:
        used = notify.send("Daily Market Brief · test", "Alerts are set up. You'll hear from me after the close.", 3)
        print(f"Test sent via: {', '.join(used) or 'nothing (no channel configured)'}")
        return 0

    cfg = load_config()
    tickers = sorted({x["ticker"] for x in cfg["positions"] + cfg["watchlist"]} | {"SPY"})
    if tickers == ["SPY"]:
        print("Watchlist and positions are empty. Nothing to check.")
        return 0

    closes = yf.download(tickers, period="2y", auto_adjust=True, progress=False)["Close"].dropna(how="all")
    last_day = closes.index[-1]
    today = datetime.now(ZoneInfo("America/New_York")).date()
    if last_day.date() != today and not args.any_day:
        print(f"No new close today (latest is {last_day:%a %b %d}): weekend or market holiday. Nothing sent.")
        return 0

    now = datetime.now(ZoneInfo("America/New_York"))
    if last_day.date() == now.date() and (now.hour, now.minute) < (16, 5):
        print("Note: the market is still open, so today's prices are intraday, not closing prices.")
    found = AL.evaluate(cfg, closes)
    print(f"Checked {len(tickers) - 1} tickers for {last_day:%a %b %d, %Y}: {len(found)} alert(s).")
    if not found:
        return 0
    explain_big_moves(found, closes, last_day)
    title, body, priority = AL.summarize(found, last_day)
    print(f"\n{title}\n{body}\n")
    if args.dry_run:
        print("Dry run: nothing sent.")
        return 0
    used = notify.send(title, body, priority, click=os.environ.get("DASHBOARD_URL"))
    print(f"Sent via: {', '.join(used)}" if used else "No channel configured (set NTFY_TOPIC or SMTP_*): printed only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
