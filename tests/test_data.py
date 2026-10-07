"""Data-layer resilience: a failed fetch must never be cached as 'no data'."""

import types

import numpy as np
import pandas as pd
import pytest
import requests

import config
import data
import snapshot

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


def _prices_frame():
    idx = pd.bdate_range("2026-01-01", periods=5)
    return pd.DataFrame({"AAA": [1.0, 2, 3, 4, 5], "BBB": [5.0, 4, 3, 2, 1]}, index=idx)


def test_prices_fall_back_to_last_good_copy_when_yahoo_blocks(monkeypatch):
    good = _prices_frame()
    monkeypatch.setattr(data, "_download", lambda *a: good)
    data._prices.clear()
    assert data.get_prices(("AAA", "BBB"), "1mo", "1d").equals(good)  # live, and remembered
    assert data.stale_since() is None

    def blocked(*a):
        raise RuntimeError("YFRateLimitError: Too Many Requests")

    monkeypatch.setattr(data, "_download", blocked)
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    data._prices.clear()
    served = data.get_prices(("AAA", "BBB"), "1mo", "1d")
    assert served["AAA"].tolist() == good["AAA"].tolist()
    assert data.stale_since() is not None  # the page can say it's showing saved data
    data._prices.clear()


def test_no_copy_and_no_yahoo_raises_a_clear_error(monkeypatch):
    monkeypatch.setattr(data, "_download", lambda *a: (_ for _ in ()).throw(RuntimeError("blocked")))
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    data._prices.clear()
    with pytest.raises(RuntimeError):
        data.get_prices(("ZZZ",), "1mo", "1d")
    data._prices.clear()


def test_cooldown_skips_yahoo_after_a_failure(monkeypatch):
    calls = {"n": 0}

    def blocked(*a):
        calls["n"] += 1
        raise RuntimeError("blocked")

    snapshot.save("prices", ("AAA",), "1mo", "1d", value=_prices_frame()[["AAA"]])
    monkeypatch.setattr(data, "_download", blocked)
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    for _ in range(3):
        data._prices.clear()
        data.get_prices(("AAA",), "1mo", "1d")
    assert (
        calls["n"] == data.YAHOO_TRIES
    )  # only the first page load waited on Yahoo; later ones went straight to the copy
    data._prices.clear()


def test_saved_copies_round_trip_without_pickle():
    s = pd.Series([1.0, 2.0], index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    snapshot.save("volume", ("AAA",), value=s)
    snapshot.save("info", ("AAA",), value={"marketCap": np.int64(5), "name": "A"})
    v, _ = snapshot.load("volume", ("AAA",))
    info, _ = snapshot.load("info", ("AAA",))
    assert v.tolist() == [1.0, 2.0] and info == {"marketCap": 5, "name": "A"}
    assert not list(snapshot.DIR.glob("*.pkl"))


def test_remote_bundle_only_extracts_plain_data_files(tmp_path, monkeypatch):
    import io
    import tarfile

    good = snapshot.key("info", ("AAA",)) + ".json"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, body in [(good, b'{"marketCap": 1}'), ("../evil.py", b"print('x')"), ("notes.txt", b"hi")]:
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tar.addfile(info, io.BytesIO(body))

    class Resp:
        content = buf.getvalue()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(snapshot, "URL", "https://example.com/snapshot.tar.gz")
    monkeypatch.setattr(snapshot.requests, "get", lambda *a, **k: Resp())
    assert snapshot.refresh_from_remote(force=True) == 1
    assert [p.name for p in snapshot.DIR.iterdir()] == [good]
    assert not (tmp_path / "evil.py").exists()


def test_any_combination_rebuilds_from_per_stock_copies(monkeypatch):
    """A request never seen before (new tickers, shorter window) is rebuilt from each stock's saved history."""
    idx = pd.bdate_range(end="2026-10-06", periods=400)
    full = pd.DataFrame({"AAA": np.arange(400.0), "BBB": np.arange(400.0) * 2, "CCC": np.ones(400)}, index=idx)
    monkeypatch.setattr(data, "_download", lambda *a: full)
    data._prices.clear()
    data.get_prices(("AAA", "BBB", "CCC"), "2y", "1d")  # live: saves the frame and each ticker on its own

    monkeypatch.setattr(data, "_download", lambda *a: (_ for _ in ()).throw(RuntimeError("blocked")))
    monkeypatch.setattr(data.time, "sleep", lambda s: None)
    data._prices.clear()
    got = data.get_prices(("CCC", "AAA"), "6mo", "1d")  # a combination and window never downloaded
    assert list(got.columns) == ["CCC", "AAA"]
    assert got.index.max() == idx.max() and (got.index.max() - got.index.min()).days <= 183
    assert got["AAA"].iloc[-1] == 399.0 and data.stale_since() is not None
    with pytest.raises(RuntimeError):  # a ticker never saved can't be invented
        data.get_prices(("AAA", "ZZZ"), "6mo", "1d")
    data._prices.clear()


def test_fred_falls_back_to_saved_series_and_is_not_cached(monkeypatch):
    s = pd.Series([4.1, 4.2], index=pd.to_datetime(["2026-08-01", "2026-09-01"]))
    monkeypatch.setattr(data, "_fred_live", lambda i: s)
    data._fred.clear()
    assert data.get_fred(("UNRATE",))["UNRATE"].tolist() == [4.1, 4.2] and data.stale_since() is None

    calls = {"n": 0}

    def down(i):
        calls["n"] += 1
        raise requests.Timeout("FRED timed out")

    monkeypatch.setattr(data, "_fred_live", down)
    data._fred.clear()
    got = data.get_fred(("UNRATE",))
    assert got["UNRATE"].tolist() == [4.1, 4.2] and data.stale_since() is not None
    data.get_fred(("UNRATE",))  # not cached (so live is retried later), and the cooldown skips the slow timeout
    assert calls["n"] == 1
    data._fred.clear()
