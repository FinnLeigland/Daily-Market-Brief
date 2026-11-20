import catalysts as C

NAMES = C.aliases(
    {
        "NVDA": "NVIDIA Corporation",
        "JPM": "JPMorgan Chase & Co.",
        "AAPL": "Apple Inc.",
        "AMZN": "Amazon.com, Inc.",
        "C": "Citigroup Inc.",
        "MA": "Mastercard Incorporated",
        "TSM": "Taiwan Semiconductor Manufacturing Company Limited",
    }
)


def read(title, bucket=None):
    return C.read_headline(title, bucket, NAMES)


def test_oil_price_moves_energy_and_consumers_in_opposite_directions():
    assert read("Oil prices jump as Middle East tensions flare")["sectors"] == {
        "Energy": 1,
        "Consumer Discretionary": -1,
    }
    assert read("Crude slides on demand worries")["sectors"] == {"Energy": -1, "Consumer Discretionary": 1}


def test_oil_industry_news_is_not_an_oil_price_call():
    """More drilling isn't higher oil prices: only headlines about the price itself get price effects."""
    r = read("Venezuela Wants to Return to the Days When Its Oil Fields Were Booming", "Energy")
    assert r["sectors"] == {"Energy": 0}


def test_rates_direction_comes_from_cuts_hikes_and_yields():
    up = read("Treasury yields climb as investors brace for higher rates")["sectors"]
    assert up["Real Estate"] == -1 and up["Financials"] == 1
    down = read("Fed signals rate cut as inflation cools")["sectors"]
    assert down["Real Estate"] == 1 and down["Technology"] == 1


def test_tariffs_hurt_importers_and_trade_deficit_is_not_tariffs():
    assert read("New tariffs on Chinese electronics hit Apple")["sectors"]["Consumer Discretionary"] == -1
    assert "tariffs" not in read("Wall Street Bonus Bonanza; Plus, U.S. Trade Deficit Widens")["themes"]


def test_company_names_and_tickers_are_matched_case_insensitively_but_safely():
    assert read("Nvidia beats estimates as data center demand soars")["tickers"] == {"NVDA": 1}
    assert read("3 Things to Watch When Taiwan Semiconductor (TSM) Reports")["tickers"] == {"TSM": 0}
    # one- and two-letter tickers only match in "(C)" or "$MA" form, never as ordinary words
    assert "C" not in read("Stocks rise as C-suite confidence improves")["tickers"]
    assert "MA" not in read("Ma and pa shops brace for holiday season")["tickers"]
    assert read("Citigroup upgrades guidance")["tickers"] == {"C": 1}


def test_stock_direction_only_uses_company_specific_words():
    """A CEO warning about the economy isn't bad news for that CEO's stock."""
    assert read("JPMorgan's CEO sends a stern warning to corporate America")["tickers"] == {"JPM": 0}
    assert read("Analysts downgrade Apple after weak iPhone demand")["tickers"] == {"AAPL": -1}


def test_pick_headlines_merges_the_same_story_from_two_outlets():
    news = {
        "Market": [
            {
                "title": "Amazon in talks to buy AI startup Decart for around $7 billion, WSJ reports",
                "link": "a",
                "published": "2026-10-11 12:00",
            },
            {
                "title": "Amazon Is in Talks to Buy AI Startup Decart, WSJ Reports",
                "link": "b",
                "published": "2026-10-11 11:00",
            },
            {"title": "Weather is nice today", "link": "c", "published": "2026-10-11 10:00"},  # nothing to say
        ]
    }
    assert [x["link"] for x in C.pick_headlines(news, NAMES)] == ["a"]


FOMC_HTML = """
<h4>2026 FOMC Meetings</h4><div>January</div><div>27-28</div><div>March</div><div>17-18*</div>
<div>October</div><div>27-28</div><div>December</div><div>8-9*</div>
<h4>2027 FOMC Meetings</h4><div>January</div><div>25-26</div><div>January</div><div>26-27</div>
<div>April/May</div><div>30-1</div>
"""


def test_parse_fomc_uses_the_decision_day_and_one_meeting_per_month():
    got = C.parse_fomc(FOMC_HTML)
    assert got == ["2026-01-28", "2026-03-18", "2026-10-28", "2026-12-09", "2027-01-27", "2027-05-01"]


BLS_ICS = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261014
SUMMARY:Consumer Price Index for September 2026
END:VEVENT
BEGIN:VEVENT
DTSTART:20261106T083000
SUMMARY:Employment Situation for October 2026
END:VEVENT
BEGIN:VEVENT
DTSTART:20261020T100000
SUMMARY:State Employment and Unemployment
END:VEVENT
END:VCALENDAR"""


def test_parse_bls_ics_keeps_the_releases_that_move_markets():
    assert C.parse_bls_ics(BLS_ICS) == [["2026-10-14", "CPI inflation"], ["2026-11-06", "Jobs report"]]


def test_upcoming_events_window_order_and_pick_flags():
    events = C.upcoming_events(
        fomc=["2026-10-28", "2026-12-09"],
        bls=[["2026-10-14", "CPI inflation"], ["2026-12-04", "Jobs report"]],
        earnings={"JPM": "2026-10-13", "NVDA": "2026-11-17", "AAPL": None},
        today="2026-10-11",
        days=21,
        picks={"JPM"},
        sector_of={"JPM": "Financials", "NVDA": "Technology"},
    )
    assert [e["event"] for e in events] == ["JPM earnings", "CPI inflation", "Fed rate decision"]
    jpm = events[0]
    assert jpm["pick"] and jpm["sectors"] == ["Financials"] and "picks" in jpm["note"]
