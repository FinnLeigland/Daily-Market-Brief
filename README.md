# Daily Market Brief: Macro & Equity Research Dashboard

A dark-mode markets dashboard: a five-minute daily brief, plus labs that each answer one question about equities and the economy. Built with Python, Streamlit, pandas, Plotly and scikit-learn on live data from Yahoo Finance, FRED and Google News.

## Tabs

| Tab | What's inside |
|---|---|
| **Digest** | Market pulse, an auto-written brief, trend cards for six sectors (Technology, AI via Global X AIQ, Financials, Consumer Discretionary, Energy, Real Estate) (50/200-day moving-average classification, top-holding moves, lead headline), curated reading list, term of the day |
| **Macro** | An institutional-style macro report: a regime call with a five-line assessment, an indicator monitor (latest, prior, 6M, 1Y, 24-month trend, as-of dates and sources), then a five-section read: (1) growth (industrial production, payrolls, unemployment), (2) inflation (headline and core CPI vs. the 2% target), (3) rates (Fed funds, 2Y, 10Y, curve), (4) the growth × inflation regime with the best and worst sectors in each since 1999, (5) recession odds from a logistic-regression model trained on NBER dates, plus five warning lights |
| **Micro** | The structure inside a sector: sector anatomy (market cap, share of the US market, companies, employees), an industry treemap and returns table vs. the sector ETF, then an industry deep dive with concentration (leader share, CR3, HHI under the 2023 U.S. Merger Guidelines), a growth-vs-margin competitive landscape, a peer comparison table, top performers and fastest growers, and one-click hand-off to the Stock Lab |
| **Sector Rotation** | Relative rotation graph (RS-Ratio vs. RS-Momentum, weekly, with tails), quadrant changes, cyclicals-vs-defensives risk-appetite line, returns by period |
| **Stock Lab** | 14 fundamentals vs. the median of the company's sector-ETF peers, peer bar charts (click a bar to open that company), auto-generated takeaways, a price chart that labels unusually large moves vs. the market (earnings, guidance, deals, market-wide selloffs…) with a click-through overview of each one: the move vs. the S&P 500 and sector, the earnings surprise, volume, what happened next, and the headlines from those days. Plus beta / volatility / Sharpe / max drawdown vs. sector and S&P 500 |
| **Equity Screen** | A new stock in each of the six featured sectors every day, chosen from the sector ETF's top holdings by a five-signal screen (momentum, trend, valuation, growth, analyst targets). Each idea leans up or down with a conviction level, the reasons, and what would prove it wrong; with an API key, Claude adds a short thesis from that day's headlines. Below the picks: a 10-year backtest of the screen's price signals and a live track record that grades every call after about a month |
| **Analyst Desk** | Private (PIN required). |

## Methods

- **Regimes:** growth momentum = 6-month change in smoothed industrial-production YoY growth; inflation momentum = the same for CPI. A switch must hold for two months. Regime labels are applied to returns two months later to reflect publication lag.
- **Recession model:** logistic regression predicting an NBER recession within 12 months from the 12-month average gap between the 10-year and 3-month Treasury yields, the Sahm-rule unemployment gap, and industrial production growth. Out-of-sample AUC ≈ 0.78 (fit 1982 to 2005, tested 2006 onward).
- **Rotation graph:** simplified JdK-style RRG on weekly data, lightly smoothed.
- **Notable moves:** a day is labeled when the stock's return beyond the S&P 500 exceeds 2.5× its typical daily excess move; nearby days are merged. Earnings dates and EPS surprises come from Yahoo Finance; headlines come from a date-restricted Google News search.
- **Valuation:** DCF grows trailing free cash flow at a chosen rate for 10 years, then at a terminal rate, discounted at a required return, plus net cash. The reverse DCF bisects for the growth rate that equates DCF value with the market price. Cash-flow models are skipped for financials.

## Features across the app

- **Clean view:** a *Hide explanations* switch hides every ratio description, how-to-read note and
  explainer across all tabs (hover a metric to still see its definition). Click it again to bring them back.
- **AI move explanations:** in the Stock Lab, Claude (`claude-opus-5-5`, low effort) reads the headlines around each
  labeled price move and names the catalyst in one line. Results are cached in `.cache/`, so each move is explained once.
  Without an API key the app falls back to keyword labels.
- **Field guide:** a hidden page:
  43 concepts across seven topics (basics, reading a company, valuation, trading mechanics, risk, macro, investor
  behavior), an A to Z glossary, and, with an API key, an *Ask a question* box answered by Claude.
- **Warnings next to the signals they judge:** each signal is backtested (see below) and the result sits beside it:
  a caution under the Digest's trend labels and the rotation graph (no measured edge), the regime playbook flagged
  as fragile in Macro, and the Equity Screen backtest under the picks. Macro's assessment also shows the one rule that
  held up, the S&P 500 vs. its 200-day average, with today's status. A *Hide warnings* switch, next to *Hide
  explanations*, hides all of them.
- **Lazy tabs:** only the open tab runs, so clicks and toggles stay fast.
- **Outage-safe caching:** a failed or empty fetch (rate limit, timeout) is never cached, so the next load retries instead of showing stale gaps.

## What the backtests found

| Signal | Result | Verdict |
|---|---|---|
| Trend labels (sector ETFs, since 1999) | Uptrend sectors trailed the S&P 500 by 0.05 pts the next month (t ≈ −0.5) | No edge |
| Rotation quadrants (weekly, since 1999) | Leading sectors didn't keep leading; slight mean reversion, too small to trade | No edge |
| Regime playbook (walk-forward, since 2005) | ~13% vs. ~11%/yr, but t ≈ 1.1 and it reverses with small rule changes | Fragile |
| S&P 500 vs. 200-day average (since 1994) | Similar return (~10.5% vs. ~10.8%) with the worst drawdown cut from −51% to −22% | Reduces risk |
| Equity Screen price signals (monthly, since 2017) | Strongest picks beat their sector group by 1.1 pts/month, but the weakest beat it too (+0.5); spread +0.6 pts, t ≈ 0.7 | No edge |

Every test uses only data available on the decision date (a unit test plants a future price shock to prove it),
samples non-overlapping windows, and charges 10 bps per unit of turnover. Numbers update as new data arrives. The
Equity Screen test uses today's largest holdings, so survivorship bias flatters it; valuation, growth and analyst
targets can't be tested without point-in-time history.

## Daily alerts (automation)

`scripts/daily_check.py` evaluates a personal watchlist and open positions after each close and sends one combined
notification when a stock enters its buy zone, crosses a target or stop, or makes an unusually large move vs. the
market (with an optional AI one-line explanation). Rules fire only on the day a level is crossed, so the job is
stateless and never repeats alerts. `.github/workflows/daily-alerts.yml` runs it every weekday at 4:30pm ET.

- **Delivery:** [ntfy](https://ntfy.sh) push notifications (`NTFY_TOPIC`) and/or email (`SMTP_*`, `ALERT_EMAIL_TO`).
- **GitHub secrets:** `WATCHLIST_JSON` (tickers and price levels only, no notes), the delivery settings above, and
  optionally `ANTHROPIC_API_KEY`.
- **Locally:** `uv run python scripts/daily_check.py --dry-run` prints today's alerts without sending; `--test`
  sends a test notification.

## Set up AI features (optional)

1. Get an API key at [console.anthropic.com](https://console.anthropic.com).
2. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste the key in (or set the
   `ANTHROPIC_API_KEY` environment variable).
3. Restart the app.

## Run it

Uses [uv](https://docs.astral.sh/uv/) for the environment (it reads `pyproject.toml` and the pinned `uv.lock`):

```bash
uv sync
uv run streamlit run app.py
```

Without uv: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/streamlit run app.py`.

## Publish it (Streamlit Community Cloud)

1. Push the project to a GitHub repo. Personal files (`journal.json`, `progress.json`, `.streamlit/secrets.toml`)
   are gitignored and stay on your machine.
2. At [share.streamlit.io](https://share.streamlit.io), create an app from the repo with `app.py` as the entry point.
   It installs from `requirements.txt`.
3. In the app's **Settings → Secrets**, add:
   ```toml
   DESK_PIN = "choose-your-own"   # required for a public site: the built-in default is visible in the code
   ANTHROPIC_API_KEY = "sk-ant-..."  # optional, turns on the AI write-ups
   ```
4. In the GitHub repo, **Settings → Actions → General → Workflow permissions**: choose *Read and write*, so the
   daily picks job can commit.

**What keeps itself up to date**

| Data | Refreshes |
|---|---|
| Prices and the market pulse | every 15 minutes (from GitHub's copy when Yahoo blocks the server) |
| Headlines | every 30 minutes |
| Company data, macro (FRED) data | every 6 hours |
| Sector and industry structure, signal backtests | every 12 hours |
| Equity Screen picks | once a day (New York date); `daily-ideas.yml` commits them each morning |

- **Track record survives restarts:** a hosted app's disk is wiped whenever it restarts or redeploys, so
  `.github/workflows/daily-ideas.yml` makes the day's picks at 7:15am ET and commits `ideas.json`. Each commit also
  redeploys the app with the full record. If you also run the app locally, `git pull` before you commit.
- **Anything else the app saves while running** stays on the server's disk only and resets when a hosted app
  restarts; keep personal records on a local copy.
- **Dates and times** are always New York time, whatever time zone the server runs in.
- **When Yahoo Finance blocks the server:** Yahoo (and sometimes FRED) refuses shared cloud servers like Streamlit's. Every
  successful Yahoo and FRED response is saved, and `.github/workflows/snapshot.yml` refreshes a bundle of the app's data on
  GitHub's servers every 15 minutes during market hours (prices, headlines, picks) and every hour for everything else and publishes it as the `data-snapshot` release. When the live site can't
  reach Yahoo, it serves that saved data, shows a note with the time it was saved, and switches back to live data
  as soon as Yahoo answers.
- `.github/workflows/tests.yml` runs the linter and the test suite on every push.

## Development

```bash
uv run pytest            # 162 offline tests: equity screen, backtest and grading, valuation, risk, move detection, regimes, recession model, backtests (incl. look-ahead checks), alert rules, AI parsing, industry concentration, outage handling
uv run ruff check .      # lint
uv run ruff format .     # format
uv add <package>         # add a dependency (updates pyproject.toml and uv.lock)
uv export --no-dev --no-hashes --format requirements-txt -o requirements.txt   # refresh requirements.txt after changes
```

`requirements.txt` is generated from `uv.lock` for hosts that only read requirements files (e.g. Streamlit Community
Cloud); regenerate it after adding packages or merging a Dependabot update. Dependabot (`.github/dependabot.yml`)
checks for updates weekly once the repo is on GitHub, with `yfinance` in its own pull request because it breaks most often.

## Layout

- `app.py`: app shell and tabs
- `views/`: one module per tab
- `views/micro.py`: industry analysis
- `views/ideas.py`, `ideas.py`: equity screen, picks, backtest and track record
- `signal_checks.py`: backtests of the dashboard's own signals (feeds the warnings)
- `views/scorecard.py`: the old Scorecard page (not a tab; add it back to `app.py` to restore it)
- `alerts.py`, `notify.py`, `scripts/daily_check.py`: alert rules, delivery, and the daily job
- `scripts/daily_ideas.py`: makes the day's Equity Screen picks (run by `daily-ideas.yml`)
- `ai.py`: Claude calls (move explanations, tutor) with on-disk caching
- `learn_content.py`: field guide lessons
- `analytics.py`: all finance and statistics (no UI code, so it's testable on its own)
- `data.py`: data fetching and caching
- `snapshot.py`, `scripts/build_snapshot.py`: saved copies of Yahoo data, and the hourly bundle that backs up the live site
- `config.py`: tickers, sectors, presets, glossary
- `theme.py`, `style.css`: dark theme and chart styling
- `tests/`: pytest suite (runs offline on synthetic data)

*For education only, not investment advice.*
