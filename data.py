"""Data access: prices (yfinance), news (Google News RSS), macro (FRED)."""

import io
import re
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


# ---------- Prices ----------


@st.cache_data(ttl=60 * 60 * 24, show_spinner=False)
def _top_holdings(etf: str, n: int) -> list[str]:
    try:
        symbols = [s.replace(".", "-") for s in yf.Ticker(etf).funds_data.top_holdings.index[:n]]
    except Exception as e:
        raise NoData from e
    if not symbols:
        raise NoData
    return symbols


def get_top_holdings(etf: str, fallback: tuple, n: int = 5) -> list[str]:
    try:
        return _top_holdings(etf, n)
    except NoData:
        return list(fallback)


@st.cache_data(ttl=60 * 15, show_spinner=False)
def get_prices(tickers: tuple, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    """Adjusted closes, one column per ticker."""
    df = yf.download(list(tickers), period=period, interval=interval, progress=False, auto_adjust=True, threads=True)[
        "Close"
    ]
    if isinstance(df, pd.Series):
        df = df.to_frame(tickers[0])
    df = df.dropna(how="all")
    if df.empty:
        raise RuntimeError("Price download returned no data")  # not cached; Streamlit shows the error
    return df


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
    try:
        info = _yahoo(lambda: _info_once(ticker))
    except Exception as e:
        raise NoData from e  # don't remember the failure
    return _sanitize({k: info.get(k) for k in INFO_FIELDS})


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
    except NoData:
        return {}


def get_infos(tickers: list[str]) -> dict[str, dict]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(tickers, pool.map(get_info, tickers), strict=True))


# ---------- Event context for price moves ----------


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _earnings(ticker: str) -> pd.DataFrame:
    try:
        df = yf.Ticker(ticker).get_earnings_dates(limit=24)
        df.index = df.index.tz_localize(None)
    except Exception as e:
        raise NoData from e
    return df


def get_earnings(ticker: str) -> pd.DataFrame | None:
    try:
        return _earnings(ticker)
    except NoData:
        return None


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _volume(ticker: str) -> pd.Series:
    try:
        v = yf.Ticker(ticker).history(period="5y", auto_adjust=True)["Volume"]
    except Exception as e:
        raise NoData from e
    if v.empty:
        raise NoData
    v.index = v.index.tz_localize(None).normalize()
    return v


def get_volume(ticker: str) -> pd.Series:
    try:
        return _volume(ticker)
    except NoData:
        return pd.Series(dtype=float)


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
    try:
        out = _yahoo(lambda: _sector_once(key))
    except Exception as e:
        raise NoData from e
    if not out["industries"]:
        raise NoData
    return out


def get_sector(key: str) -> dict | None:
    """Sector overview plus its industries: [{key, name, symbol, market weight}]."""
    try:
        return _sector(key)
    except NoData:
        return None


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def _industry(key: str) -> dict:
    try:
        ind = yf.Industry(key)
        out = {
            "overview": ind.overview or {},
            "top_companies": _records(ind.top_companies),
            "top_performing": _records(ind.top_performing_companies),
            "top_growth": _records(ind.top_growth_companies),
        }
    except Exception as e:
        raise NoData from e
    if not out["top_companies"]:
        raise NoData
    return out


def get_industry(key: str) -> dict | None:
    """Industry overview, largest companies (with share of the industry), top performers and fastest growers."""
    try:
        return _industry(key)
    except NoData:
        return None


# ---------- Macro ----------


def _fred_one(series_id: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"])
    return pd.to_numeric(df.set_index("date")[series_id], errors="coerce").dropna()


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fred(ids: tuple) -> dict[str, pd.Series]:
    with ThreadPoolExecutor(max_workers=len(ids)) as pool:
        series = list(pool.map(lambda i: _safe(_fred_one, i), ids))
    out = {i: s for i, s in zip(ids, series, strict=True) if s is not None and not s.empty}
    if len(out) < len(ids):
        raise NoData(partial=out)
    return out


def get_fred(ids: tuple) -> dict[str, pd.Series]:
    """FRED series by id. Only a complete set is cached; a partial one is returned uncached and retried next load."""
    try:
        return _fred(ids)
    except NoData as e:
        return e.partial or {}


def _safe(fn, *args):
    try:
        return fn(*args)
    except Exception:
        return None
