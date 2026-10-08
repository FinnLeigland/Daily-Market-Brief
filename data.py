"""Data access: prices (yfinance), news (Google News RSS), macro (FRED)."""

import io
import re
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import feedparser
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

import config
import snapshot

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


class NoData(Exception):
    """Raised inside a cached function when a fetch fails or comes back empty.

    Streamlit never caches a call that raises, so a temporary outage (rate limit, timeout) is retried on the next
    page load instead of being remembered as "no data" for the cache's whole lifetime. Public wrappers catch it.
    `partial` carries whatever did load, so pages can still show it (uncached).
    """

    def __init__(self, partial=None):
        super().__init__("no data")
        self.partial = partial


# ---------- Yahoo: live when possible, last good copy when not ----------

YAHOO_COOLDOWN = 300  # after Yahoo fails, go straight to saved copies for 5 minutes instead of waiting on retries
# Separate timers, so a refused login (company data, ETF holdings) never stops price requests, which use the no-login
# chart endpoint and often still work.
_down = {"login": 0.0, "chart": 0.0}
_stale = {"oldest": None}


def _fresh_or_saved(name: str, args: tuple, fetch, valid=bool, route: str = "login"):
    """Fetch live and remember it; if Yahoo fails (or is cooling down), raise NoData carrying the last good copy.

    NoData is never cached, so the next page load tries Yahoo again once the cooldown has passed.
    """
    if time.time() >= _down[route]:
        try:
            value = fetch()
        except LookupError:
            value = None  # an unknown symbol or an empty answer: not an outage, but fall back if we have a copy
        except Exception:
            _down[route] = time.time() + YAHOO_COOLDOWN
            value = None
        if value is not None and valid(value):
            snapshot.save(name, *args, value=value)
            return value
    snapshot.refresh_from_remote()  # pick up GitHub's newer copy if there is one (checked at most every 15 minutes)
    raise NoData(partial=snapshot.load(name, *args))


def _use_saved(partial, note: bool = True):
    """Unwrap a saved copy from NoData.partial. With `note`, its age counts toward the 'showing saved data' note;
    slow-changing reference data (ETF holdings, sector structure, earnings dates) is served quietly."""
    value, saved_at = partial
    if note:
        _stale["oldest"] = min(_stale["oldest"] or saved_at, saved_at)
    return value


def stale_since() -> float | None:
    """Unix time of the oldest saved copy served since the last reset, or None if everything was live."""
    return _stale["oldest"]


def reset_stale() -> None:
    _stale["oldest"] = None


# ---------- Prices ----------


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def _top_holdings(etf: str, n: int) -> list[str]:
    return _fresh_or_saved(
        "holdings",
        (etf, n),
        lambda: [s.replace(".", "-") for s in _yahoo(lambda: yf.Ticker(etf).funds_data.top_holdings).index[:n]],
    )


def get_top_holdings(etf: str, fallback: tuple, n: int = 5) -> list[str]:
    try:
        return _top_holdings(etf, n)
    except NoData as e:
        return _use_saved(e.partial, note=False) if e.partial else list(fallback)


# ---------- Direct price requests (no login) ----------
#
# yfinance logs in to Yahoo (a cookie plus a "crumb" token) before every kind of request, and that login is what
# shared cloud servers most often get refused on. Yahoo's chart endpoint, which serves price history, works without
# it. So prices come from there first, with a Chrome-like connection (Yahoo rejects other TLS fingerprints), and
# yfinance is only the backup.

CHART_HOSTS = ("query1", "query2")
_chart_local = threading.local()


def _chart_session():
    if not hasattr(_chart_local, "session"):
        from curl_cffi import requests as curl_requests

        _chart_local.session = curl_requests.Session(impersonate="chrome")
    return _chart_local.session


def _chart_one(ticker: str, period: str, interval: str, field: str = "adjclose") -> pd.Series | None:
    """One ticker's history from the chart endpoint: adjusted closes (dividends and splits) or volume."""
    params = {"interval": interval, "events": "div,splits", "includeAdjustedClose": "true"}
    if period == "max":  # range=max quietly downgrades to weekly bars; an explicit date range keeps them daily
        params.update(period1=str(-2208994789), period2=str(int(time.time()) + 86400))
    else:
        params["range"] = period
    for host in CHART_HOSTS:
        try:
            resp = _chart_session().get(
                f"https://{host}.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker)}",
                params=params,
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            result = (resp.json().get("chart") or {}).get("result") or []
            if not result or not result[0].get("timestamp"):
                return None
            r = result[0]
            if (r.get("meta") or {}).get("dataGranularity", interval) != interval:
                return None  # Yahoo sent coarser bars than asked for: let yfinance handle this one
            ind = r.get("indicators") or {}
            if field == "volume":
                values = (ind.get("quote") or [{}])[0].get("volume")
            else:
                values = (ind.get("adjclose") or [{}])[0].get("adjclose") or (ind.get("quote") or [{}])[0].get("close")
            if not values:
                return None
            tz = (r.get("meta") or {}).get("exchangeTimezoneName") or "America/New_York"
            idx = pd.to_datetime(r["timestamp"], unit="s", utc=True).tz_convert(tz).tz_localize(None).normalize()
            out = pd.Series(pd.to_numeric(values, errors="coerce"), index=idx, name=ticker).dropna()
            return out[~out.index.duplicated(keep="last")]
        except Exception:
            continue
    return None


# Weekly and monthly bars from the chart endpoint are labelled and adjusted differently from yfinance's, so they're
# built from daily closes instead: the last close of each week (dated its Monday) or month (dated the 1st).
RESAMPLE = {"1wk": "W-MON", "1mo": "MS"}


def _chart_many(tickers: tuple, period: str, interval: str) -> pd.DataFrame:
    fetch = "1d" if interval in RESAMPLE else interval
    with ThreadPoolExecutor(max_workers=6) as pool:
        series = list(pool.map(lambda t: _chart_one(t, period, fetch), tickers))
    got = {t: s for t, s in zip(tickers, series, strict=True) if s is not None and not s.empty}
    if not got:
        return pd.DataFrame()
    df = pd.DataFrame(got).sort_index()
    if interval in RESAMPLE:
        df = df.resample(RESAMPLE[interval], label="left", closed="left").last().dropna(how="all")
    return df


def _download(tickers: tuple, period: str, interval: str) -> pd.DataFrame:
    df = _chart_many(tickers, period, interval)
    rest = [t for t in tickers if t not in df.columns]
    if rest:  # anything the direct route didn't return: try yfinance before giving up on it
        try:
            more = yf.download(rest, period=period, interval=interval, progress=False, auto_adjust=True, threads=True)[
                "Close"
            ]
            if isinstance(more, pd.Series):
                more = more.to_frame(rest[0])
            df = more if df.empty else df.join(more, how="outer")
        except Exception:
            if df.empty:
                raise
    df = df.dropna(how="all")
    if df.empty:
        raise RuntimeError("Price download returned no data")
    # A rate limit can drop some tickers from an otherwise good download: fill those from the last good copy, so
    # the saved copy never loses columns.
    missing = [t for t in tickers if t not in df.columns or df[t].isna().all()]
    saved = snapshot.load("prices", tickers, period, interval) if missing else None
    if saved is not None:
        have = [t for t in missing if t in saved[0].columns]
        if have:
            df = df.drop(columns=[t for t in have if t in df.columns]).join(saved[0][have], how="outer")
    return df


PERIODS = {"1mo": 31, "3mo": 92, "6mo": 183, "1y": 366, "2y": 731, "5y": 1827, "10y": 3653}


def _save_each(df: pd.DataFrame, period: str, interval: str) -> None:
    """Also keep each ticker's history on its own (the longest seen), so any later combination can be rebuilt."""
    for t in df.columns:
        s = df[t].dropna()
        old = snapshot.load("price1", t, interval)
        if s.empty or (old is not None and len(old[0].dropna()) > len(s) and old[0].index.max() >= s.index.max()):
            continue
        if old is not None:  # keep older history the new window doesn't cover
            s = s.combine_first(old[0])
        snapshot.save("price1", t, interval, value=s)


def _rebuild_from_pieces(tickers: tuple, period: str, interval: str):
    """(frame, oldest saved_at) assembled from per-ticker copies, trimmed to the period; None if any ticker is missing."""
    cols, oldest = {}, None
    for t in tickers:
        got = snapshot.load("price1", t, interval)
        if got is None:
            return None
        cols[t], oldest = got[0], min(oldest or got[1], got[1])
    df = pd.DataFrame(cols).sort_index()
    if period in PERIODS and not df.empty:
        df = df[df.index >= df.index.max() - pd.Timedelta(days=PERIODS[period])]
    return df.dropna(how="all"), oldest


@st.cache_data(ttl=60 * 15, show_spinner=False)
def _prices(tickers: tuple, period: str, interval: str) -> pd.DataFrame:
    def live():
        df = _yahoo(lambda: _download(tickers, period, interval))
        _save_each(df, period, interval)
        return df

    return _fresh_or_saved("prices", (tickers, period, interval), live, valid=lambda df: not df.empty, route="chart")


def get_prices(tickers: tuple, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Adjusted closes, one column per ticker. Live from Yahoo, or the last good copy if Yahoo isn't answering."""
    try:
        return _prices(tickers, period, interval)
    except NoData as e:
        saved = e.partial or _rebuild_from_pieces(tickers, period, interval)
        if saved is None:
            raise RuntimeError("Price download returned no data") from None
        return _use_saved(saved)


def pct_change(series: pd.Series, days: int) -> float | None:
    s = series.dropna()
    if len(s) <= days:
        return None
    return (s.iloc[-1] / s.iloc[-1 - days] - 1) * 100


def ytd_change(series: pd.Series) -> float | None:
    s = series.dropna()
    prior = s[s.index.year < s.index[-1].year]
    if prior.empty:
        return None
    return (s.iloc[-1] / prior.iloc[-1] - 1) * 100


def trend_state(series: pd.Series) -> dict:
    """Classify trend using price vs. 50- and 200-day moving averages."""
    s = series.dropna()
    price, ma50, ma200 = s.iloc[-1], s.rolling(50).mean().iloc[-1], s.rolling(200).mean().iloc[-1]
    if price > ma50 > ma200:
        label = "Uptrend"
    elif price < ma50 < ma200:
        label = "Downtrend"
    elif price > ma200:
        label = "Pulling back" if price < ma50 else "Recovering"
    else:
        label = "Rebounding" if price > ma50 else "Weakening"
    return {
        "label": label,
        "price": price,
        "ma50": ma50,
        "ma200": ma200,
        "vs_ma50": (price / ma50 - 1) * 100,
        "vs_ma200": (price / ma200 - 1) * 100,
    }


# ---------- News ----------

_JUNK = re.compile(
    r"(stock price, news, quote|historical prices|price target|\| ?stock|options chain|forecast,? 20\d\d|market size|market report)",
    re.I,
)


def keyword_match(title: str, keywords: list[str]) -> bool:
    """True if the headline mentions any keyword. Short keywords (≤3 letters, like "ai") must be whole words;
    longer ones match as word prefixes, so "refin" matches "refinery"."""
    for k in keywords:
        k = k.strip()
        pattern = rf"\b{re.escape(k)}" + (r"\b" if len(k) <= 3 else "")
        if re.search(pattern, title, re.I):
            return True
    return False


def _google_news(query: str, keywords: list[str], days: int = 2) -> list[dict]:
    sites = " OR ".join(f"site:{s}" for s in config.NEWS_SITES)
    q = f"{query} when:{days}d ({sites})"
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en-US&gl=US&ceid=US:en"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()  # a failed request raises, so it isn't mistaken for "no news"
    feed = feedparser.parse(resp.content)
    items = []
    for e in feed.entries:
        source = e.get("source", {}).get("title", "")
        title = e.title
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        if _JUNK.search(title) or not keyword_match(title, keywords):
            continue
        letters = [c for c in title if c.isalpha()]
        if letters and sum(c.isupper() for c in letters) > 0.6 * len(letters):  # all-caps press releases
            continue
        try:
            published = parsedate_to_datetime(e.published)
        except Exception:
            published = datetime.now(UTC)
        items.append({"title": title.strip(), "link": e.link, "source": source, "published": published})
    return items


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        key = re.sub(r"[^a-z0-9]", "", it["title"].lower())[:60]
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _try_news(query: str, keywords: list[str]) -> list[dict] | None:
    try:
        return _google_news(query, keywords)
    except Exception:
        return None


@st.cache_data(ttl=60 * 30, show_spinner=False)
def _news() -> dict[str, list[dict]]:
    queries = {"Market": (config.MARKET_NEWS_QUERY, config.MARKET_KEYWORDS)}
    queries.update({s["name"]: (s["news_query"], s["keywords"]) for s in config.FEATURED_SECTORS})
    with ThreadPoolExecutor(max_workers=len(queries)) as pool:
        results = dict(zip(queries, pool.map(lambda qk: _try_news(*qk), queries.values()), strict=True))
    out = {k: _dedupe(v or []) for k, v in results.items()}
    if any(v is None for v in results.values()) or not any(out.values()):
        raise NoData(partial=out)  # some searches failed: show what loaded, retry on the next load
    return out


def get_news() -> dict[str, list[dict]]:
    """Return {'Market': [...], '<sector name>': [...]} sorted newest first. Only complete results are cached."""
    try:
        return _news()
    except NoData as e:
        return e.partial or {}


def time_ago(dt: datetime) -> str:
    mins = int((datetime.now(UTC) - dt).total_seconds() // 60)
    if mins < 60:
        return f"{max(mins, 1)}m ago"
    if mins < 60 * 24:
        return f"{mins // 60}h ago"
    return f"{mins // (60 * 24)}d ago"


# ---------- Company fundamentals ----------

INFO_FIELDS = [
    "longName",
    "shortName",
    "sector",
    "industry",
    "longBusinessSummary",
    "currentPrice",
    "previousClose",
    "marketCap",
    "fiftyTwoWeekLow",
    "fiftyTwoWeekHigh",
    "trailingPE",
    "forwardPE",
    "trailingPegRatio",
    "priceToSalesTrailing12Months",
    "enterpriseToEbitda",
    "grossMargins",
    "operatingMargins",
    "profitMargins",
    "returnOnEquity",
    "revenueGrowth",
    "earningsGrowth",
    "debtToEquity",
    "freeCashflow",
    "dividendYield",
    "beta",
    "targetMeanPrice",
    "recommendationKey",
    "numberOfAnalystOpinions",
    "forwardEps",
    "trailingEps",
    "sharesOutstanding",
    "totalCash",
    "totalDebt",
    "targetLowPrice",
    "targetHighPrice",
]


YAHOO_TRIES = 3


def _reset_yahoo_session() -> None:
    """Drop yfinance's cached cookie and crumb so the next request logs in afresh. yfinance otherwise keeps reusing a
    crumb Yahoo has started rejecting. Uses yfinance internals, so any failure here is ignored."""
    try:
        from yfinance.data import YfData

        yd = YfData()
        with yd._cookie_lock:
            yd._cookie = None
            yd._crumb = None
            yd._session.cookies.clear()
    except Exception:
        pass


def _yahoo(call):
    """Run a Yahoo request with brief retries. When several requests start at once, the first ones can fail with
    'Invalid Crumb' (HTTP 401) while yfinance sets up its session token; a fresh session a moment later works."""
    for attempt in range(YAHOO_TRIES):
        try:
            return call()
        except Exception as e:
            if attempt == YAHOO_TRIES - 1:
                raise
            if "crumb" in str(e).lower() or "401" in str(e):
                _reset_yahoo_session()
            time.sleep(1.0 * (attempt + 1))


def _info_once(ticker: str) -> dict:
    info = yf.Ticker(ticker).info or {}
    if not info.get("currentPrice") and not info.get("marketCap"):
        raise LookupError(ticker)  # an unknown symbol, or a lookup that silently came back empty
    return info


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _info(ticker: str) -> dict:
    return _fresh_or_saved(
        "info",
        (ticker,),
        lambda: _sanitize({k: v for k, v in _yahoo(lambda: _info_once(ticker)).items() if k in INFO_FIELDS}),
    )


def _sanitize(info: dict) -> dict:
    """Blank out ratios that can only come from mixed currencies (e.g. a US listing's dollar market cap over revenue
    reported in won or yen), so they show as missing instead of as a misleading 0.0×."""
    ps = info.get("priceToSalesTrailing12Months")
    if ps is not None and 0 < ps < 0.05:
        info["priceToSalesTrailing12Months"] = None
    return info


def get_info(ticker: str) -> dict:
    try:
        return _info(ticker)
    except NoData as e:
        return _use_saved(e.partial) if e.partial else {}


def get_infos(tickers: list[str]) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=4) as pool:  # gentle on Yahoo, which throttles bursts
        return dict(zip(tickers, pool.map(get_info, tickers), strict=True))


# ---------- Event context for price moves ----------


def _earnings_once(ticker: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).get_earnings_dates(limit=24)
    df.index = df.index.tz_localize(None)
    return df


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _earnings(ticker: str) -> pd.DataFrame:
    return _fresh_or_saved("earnings", (ticker,), lambda: _earnings_once(ticker), valid=lambda df: df is not None)


def get_earnings(ticker: str) -> pd.DataFrame | None:
    try:
        return _earnings(ticker)
    except NoData as e:
        return _use_saved(e.partial, note=False) if e.partial else None


def _volume_once(ticker: str) -> pd.Series:
    v = _chart_one(ticker, "5y", "1d", field="volume")
    if v is not None and not v.empty:
        return v
    v = yf.Ticker(ticker).history(period="5y", auto_adjust=True)["Volume"]
    v.index = v.index.tz_localize(None).normalize()
    return v


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _volume(ticker: str) -> pd.Series:
    return _fresh_or_saved(
        "volume", (ticker,), lambda: _volume_once(ticker), valid=lambda v: not v.empty, route="chart"
    )


def get_volume(ticker: str) -> pd.Series:
    try:
        return _volume(ticker)
    except NoData as e:
        return _use_saved(e.partial) if e.partial else pd.Series(dtype=float)


_LISTICLE = re.compile(
    r"(stocks? to (buy|watch|own)|best .* stocks?|top \d+|\d+ (reasons|things)|should you buy|buy now)", re.I
)
_SHORT_NAME = re.compile(
    r",?\s+(inc\.?|corp(oration)?\.?|co\.?|company|ltd\.?|plc|holdings?|group|n\.v\.|s\.a\.)$", re.I
)


def short_name(name: str) -> str:
    """'JPMorgan Chase & Co.' -> 'JPMorgan Chase', for searching headlines by company name."""
    out = name or ""
    for _ in range(2):
        out = _SHORT_NAME.sub("", out).strip().rstrip("&,").strip()
    return out


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def _event_news(ticker: str, name: str, day: str, max_items: int = 6) -> list[dict]:
    d = pd.Timestamp(day)
    after, before = (d - pd.Timedelta(days=2)).date(), (d + pd.Timedelta(days=3)).date()
    nm = short_name(name)
    q = f'("{nm}" OR {ticker}) after:{after} before:{before}'
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        raise NoData from e  # a failed search isn't "no news that day"
    feed = feedparser.parse(resp.content)
    first = nm.split()[0].lower() if nm else ticker.lower()
    items = []
    for e in feed.entries:
        source = e.get("source", {}).get("title", "")
        title = e.title[: -len(source) - 3] if source and e.title.endswith(f" - {source}") else e.title
        if (
            _JUNK.search(title)
            or _LISTICLE.search(title)
            or (first not in title.lower() and ticker.lower() not in title.lower())
        ):
            continue
        try:
            published = parsedate_to_datetime(e.published)
        except Exception:
            continue
        items.append({"title": title.strip(), "link": e.link, "source": source, "published": published})
    # Prefer headlines that talk about the stock moving
    movey = re.compile(
        r"(stock|shares|soar|surge|jump|rall|plunge|tumble|slide|sink|fall|drop|rise|gain|earnings|results)", re.I
    )
    items = _dedupe(items)
    items.sort(key=lambda it: (not movey.search(it["title"]), abs((it["published"].date() - d.date()).days)))
    return items[:max_items]


def get_event_news(ticker: str, name: str, day: str, max_items: int = 6) -> list[dict]:
    """Headlines about a company from two days before to two days after `day` (YYYY-MM-DD)."""
    try:
        return _event_news(ticker, name, day, max_items)
    except NoData:
        return []


def get_events_news(ticker: str, name: str, days: list[str]) -> dict[str, list[dict]]:
    with ThreadPoolExecutor(max_workers=6) as pool:
        return dict(zip(days, pool.map(lambda d: get_event_news(ticker, name, d), days), strict=True))


# ---------- Sectors and industries (micro structure) ----------

# Yahoo's sector names (as used in company profiles) → keys for yfinance's Sector API.
YF_SECTORS = {
    "Technology": "technology",
    "Communication Services": "communication-services",
    "Consumer Cyclical": "consumer-cyclical",
    "Consumer Defensive": "consumer-defensive",
    "Financial Services": "financial-services",
    "Healthcare": "healthcare",
    "Industrials": "industrials",
    "Energy": "energy",
    "Basic Materials": "basic-materials",
    "Real Estate": "real-estate",
    "Utilities": "utilities",
}


def _records(df: pd.DataFrame | None) -> list[dict]:
    if df is None or df.empty:
        return []
    return df.reset_index().to_dict("records")


def _sector_once(key: str) -> dict:
    sec = yf.Sector(key)
    return {"overview": sec.overview or {}, "industries": _records(sec.industries)}


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _sector(key: str) -> dict:
    return _fresh_or_saved("sector", (key,), lambda: _yahoo(lambda: _sector_once(key)), valid=lambda o: o["industries"])


def get_sector(key: str) -> dict | None:
    """Sector overview plus its industries: [{key, name, symbol, market weight}]."""
    try:
        return _sector(key)
    except NoData as e:
        return _use_saved(e.partial, note=False) if e.partial else None


def _industry_once(key: str) -> dict:
    ind = yf.Industry(key)
    return {
        "overview": ind.overview or {},
        "top_companies": _records(ind.top_companies),
        "top_performing": _records(ind.top_performing_companies),
        "top_growth": _records(ind.top_growth_companies),
    }


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _industry(key: str) -> dict:
    return _fresh_or_saved(
        "industry", (key,), lambda: _yahoo(lambda: _industry_once(key)), valid=lambda o: o["top_companies"]
    )


def get_industry(key: str) -> dict | None:
    """Industry overview, largest companies (with share of the industry), top performers and fastest growers."""
    try:
        return _industry(key)
    except NoData as e:
        return _use_saved(e.partial, note=False) if e.partial else None


# ---------- Macro ----------


FRED_COOLDOWN = 300  # after FRED fails, use saved copies for 5 minutes instead of waiting on timeouts
_fred_down = {"until": 0.0}


def _fred_live(series_id: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"])
    return pd.to_numeric(df.set_index("date")[series_id], errors="coerce").dropna()


def _fred_one(series_id: str):
    """(series, saved_at): saved_at is None when the series came live, else the time of the saved copy used."""
    if time.time() >= _fred_down["until"]:
        try:
            s = _fred_live(series_id)
            if not s.empty:
                snapshot.save("fred", series_id, value=s)
                return s, None
        except Exception:
            _fred_down["until"] = time.time() + FRED_COOLDOWN
    snapshot.refresh_from_remote()
    saved = snapshot.load("fred", series_id)
    return saved if saved is not None else (None, None)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fred(ids: tuple) -> dict[str, pd.Series]:
    with ThreadPoolExecutor(max_workers=len(ids)) as pool:
        results = list(pool.map(_fred_one, ids))
    out = {i: s for i, (s, _) in zip(ids, results, strict=True) if s is not None and not s.empty}
    saved_at = [t for s, t in results if s is not None and t is not None]
    if len(out) < len(ids) or saved_at:  # incomplete or partly saved: don't cache, so live data is retried later
        raise NoData(partial=(out, min(saved_at) if saved_at else None))
    return out


def get_fred(ids: tuple) -> dict[str, pd.Series]:
    """FRED series by id: live when FRED answers, the last good copy when it doesn't. Only a complete live set is
    cached; anything else is returned uncached and retried on the next load."""
    try:
        return _fred(ids)
    except NoData as e:
        if not e.partial:
            return {}
        out, saved_at = e.partial
        if saved_at is not None:
            _use_saved((out, saved_at))
        return out


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return None
