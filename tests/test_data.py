"""Data-layer resilience: a failed fetch must never be cached as 'no data'."""

import types

import pytest
import requests

import config
import data

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Stock market rallies as Fed holds rates - Reuters</title><link>https://example.com/a</link>
<pubDate>Mon, 05 Oct 2026 12:00:00 GMT</pubDate><source url="https://reuters.com">Reuters</source></item>
</channel></rss>"""


@pytest.fixture(autouse=True)
def clear_caches():
    data._news.clear()
    data._event_news.clear()
    yield
    data._news.clear()
    data._event_news.clear()


def _ok(*args, **kwargs):
    return types.SimpleNamespace(content=RSS, raise_for_status=lambda: None)


def _down(*args, **kwargs):
    raise requests.ConnectionError("rate limited")


def test_news_outage_is_not_cached(monkeypatch):
    monkeypatch.setattr(data.requests, "get", _down)
    assert not any(data.get_news().values())  # nothing loaded…

    monkeypatch.setattr(data.requests, "get", _ok)
    news = data.get_news()  # …and the next load retries instead of replaying the failure
    assert news["Market"][0]["title"] == "Stock market rallies as Fed holds rates"


def test_partial_news_outage_shows_what_loaded_without_caching_it(monkeypatch):
    calls = {"n": 0}

    def flaky(url, **kwargs):
        calls["n"] += 1
        if "Federal" in requests.utils.unquote(url):  # only the market-wide query mentions the Fed
            raise requests.Timeout()
        return _ok()

    monkeypatch.setattr(data.requests, "get", flaky)
    first = data.get_news()
    assert first["Market"] == []
    n_after_first = calls["n"]
    data.get_news()
    assert calls["n"] > n_after_first  # retried, not served from cache


def test_complete_news_results_are_cached(monkeypatch):
    calls = {"n": 0}

    def counting(*args, **kwargs):
        calls["n"] += 1
        return _ok()

    monkeypatch.setattr(data.requests, "get", counting)
    data.get_news()
    data.get_news()
    assert calls["n"] == 1 + len(config.FEATURED_SECTORS)  # one round of searches, then the cache


def test_failed_event_search_is_not_cached_as_no_headlines(monkeypatch):
    monkeypatch.setattr(data.requests, "get", _down)
    assert data.get_event_news("NVDA", "NVIDIA Corporation", "2026-08-27") == []
    monkeypatch.setattr(data.requests, "get", _ok)
    # The stub's headline doesn't mention NVIDIA, so it's filtered, but the search did run again:
    calls = {"n": 0}

    def counting(*args, **kwargs):
        calls["n"] += 1
        return _ok()

    monkeypatch.setattr(data.requests, "get", counting)
    data.get_event_news("NVDA", "NVIDIA Corporation", "2026-08-27")
    assert calls["n"] == 1


def test_company_lookup_retries_a_transient_yahoo_error(monkeypatch):
    calls = {"n": 0}

    class FlakyTicker:
        def __init__(self, symbol):
            pass

        @property
        def info(self):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("HTTP Error 401: Invalid Crumb")
            return {"currentPrice": 100.0, "marketCap": 1e9}

    resets = []
    monkeypatch.setattr(data.yf, "Ticker", FlakyTicker)
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    monkeypatch.setattr(data, "_reset_yahoo_session", lambda: resets.append(1))
    data._info.clear()
    assert data.get_info("ZZZT")["currentPrice"] == 100.0
    assert calls["n"] == 2 and resets == [1]  # a crumb error resets the session before retrying
    data._info.clear()


def test_company_lookup_gives_up_without_caching(monkeypatch):
    class DeadTicker:
        def __init__(self, symbol):
            pass

        info = property(lambda self: (_ for _ in ()).throw(RuntimeError("down")))

    monkeypatch.setattr(data.yf, "Ticker", DeadTicker)
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    data._info.clear()
    assert data.get_info("ZZZD") == {}
    data._info.clear()


def test_mixed_currency_price_to_sales_is_blanked():
    assert data._sanitize({"priceToSalesTrailing12Months": 0.004})["priceToSalesTrailing12Months"] is None
    assert data._sanitize({"priceToSalesTrailing12Months": 8.9})["priceToSalesTrailing12Months"] == 8.9
    assert data._sanitize({"priceToSalesTrailing12Months": None})["priceToSalesTrailing12Months"] is None
