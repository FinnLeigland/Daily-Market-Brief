"""Static configuration: tickers, sectors, news queries, glossary."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

MARKET_TZ = ZoneInfo("America/New_York")


def today_et() -> date:
    """Today's date in New York. Servers usually run on UTC, where the day would roll over at 8pm ET."""
    return datetime.now(MARKET_TZ).date()


# Headline market gauges shown in the digest's top strip.
PULSE = [
    {"ticker": "^GSPC", "label": "S&P 500", "kind": "index"},
    {"ticker": "^IXIC", "label": "Nasdaq", "kind": "index"},
    {"ticker": "^RUT", "label": "Russell 2000", "kind": "index"},
    {"ticker": "^TNX", "label": "10Y Treasury", "kind": "yield"},
    {"ticker": "^VIX", "label": "VIX", "kind": "level"},
    {"ticker": "CL=F", "label": "WTI Crude", "kind": "price"},
]

BENCHMARK = "SPY"

# The six sectors featured on the Digest (a 3 × 2 grid). Keywords filter headlines; keywords of three letters
# or fewer (e.g. "ai", "amd") must match a whole word, so "ai" doesn't match "said".
FEATURED_SECTORS = [
    {
        "name": "Technology",
        "etf": "XLK",
        "keywords": [
            "tech",
            "chip",
            "semiconductor",
            "nvidia",
            "apple",
            "microsoft",
            "broadcom",
            "amd",
            "software",
            "nasdaq",
        ],
        "news_query": '("tech stocks" OR semiconductor OR "chip stocks" OR "technology sector")',
        "fallback_holdings": ["NVDA", "AAPL", "MSFT", "AVGO", "AMD"],
    },
    {
        "name": "Artificial Intelligence",
        "short": "AI",
        "etf": "AIQ",  # Global X Artificial Intelligence & Technology ETF: the largest AI-focused fund
        "keywords": [
            "ai",
            "artificial intelligence",
            "openai",
            "anthropic",
            "chatgpt",
            "data center",
            "gpu",
            "nvidia",
            "palantir",
            "machine learning",
            "chatbot",
            "llm",
        ],
        "news_query": '("artificial intelligence" OR "AI stocks" OR "generative AI" OR "AI spending" OR OpenAI OR "data center")',
        "fallback_holdings": ["PLTR", "MSFT", "ORCL", "NFLX", "TSLA"],
    },
    {
        "name": "Financials",
        "etf": "XLF",
        "keywords": [
            "bank",
            "financial",
            "jpmorgan",
            "goldman",
            "morgan stanley",
            "citi",
            "wells fargo",
            "lender",
            "credit",
            "insurer",
            "wall street",
        ],
        "news_query": '("bank stocks" OR "financial stocks" OR JPMorgan OR "Goldman Sachs" OR "Wall Street banks")',
        "fallback_holdings": ["BRK-B", "JPM", "V", "MA", "BAC"],
    },
    {
        "name": "Consumer Discretionary",
        "short": "Consumer",
        "etf": "XLY",
        "keywords": [
            "retail",
            "consumer",
            "shopper",
            "amazon",
            "tesla",
            "home depot",
            "mcdonald",
            "nike",
            "starbucks",
            "retail sales",
            "e-commerce",
            "holiday sales",
        ],
        "news_query": '("consumer spending" OR "retail sales" OR retailers OR Amazon OR "consumer stocks" OR Tesla)',
        "fallback_holdings": ["AMZN", "TSLA", "HD", "MCD", "BKNG"],
    },
    {
        "name": "Energy",
        "etf": "XLE",
        "keywords": ["oil", "crude", "energy", "opec", "gas", "exxon", "chevron", "brent", "lng", "refin", "aramco"],
        "news_query": '("oil prices" OR "energy stocks" OR OPEC OR "natural gas" OR Exxon)',
        "fallback_holdings": ["XOM", "CVX", "COP", "EOG", "SLB"],
    },
    {
        "name": "Real Estate",
        "etf": "XLRE",
        "keywords": [
            "real estate",
            "reit",
            "property",
            "properties",
            "mortgage",
            "housing",
            "office market",
            "office space",
            "office vacanc",
            "cbre",
            "landlord",
            "commercial real estate",
            "commercial property",
            "home prices",
            "home sales",
            "homebuilder",
            "homeowner",
            "rent",
        ],
        "news_query": '(REIT OR "commercial real estate" OR CBRE OR "office market" OR "mortgage rates")',
        "fallback_holdings": ["PLD", "AMT", "EQIX", "WELL", "SPG"],
    },
]

# All 11 GICS sectors via the SPDR Select Sector ETFs (used on the Sectors tab).
ALL_SECTORS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLE": "Energy",
    "XLRE": "Real Estate",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLU": "Utilities",
    "XLC": "Communication Services",
}

INDICES = {"^GSPC": "S&P 500", "^IXIC": "Nasdaq Composite", "^DJI": "Dow Jones", "^RUT": "Russell 2000"}

# News is pulled from Google News RSS, restricted to these outlets.
NEWS_SITES = [
    "reuters.com",
    "cnbc.com",
    "finance.yahoo.com",
    "wsj.com",
    "bloomberg.com",
    "ft.com",
    "marketwatch.com",
    "barrons.com",
    "cbre.com",
    "apnews.com",
]
MARKET_KEYWORDS = [
    "stock",
    "market",
    "wall st",
    "s&p",
    "dow",
    "nasdaq",
    "fed",
    "federal",
    "yield",
    "treasur",
    "rate",
    "earnings",
    "investor",
    "inflation",
    "economy",
]
MARKET_NEWS_QUERY = '("stock market" OR "Wall Street" OR "S&P 500" OR "Federal Reserve")'

# FRED series for the Macro tab (public CSV endpoint, no API key needed).
FRED_SERIES = {
    "DGS10": ("10-Year Treasury Yield", "%"),
    "DGS2": ("2-Year Treasury Yield", "%"),
    "T10Y2Y": ("10Y minus 2Y Spread", "pts"),
    "DFF": ("Fed Funds Rate", "%"),
    "UNRATE": ("Unemployment Rate", "%"),
    "CPIAUCSL": ("CPI Inflation (YoY)", "%"),
    "MORTGAGE30US": ("30-Year Mortgage Rate", "%"),
}

# One term per day, rotating, to build vocabulary.
GLOSSARY = [
    (
        "Moving average",
        "The average closing price over a set window (e.g. 50 or 200 days). Price above its 200-day average is a common shorthand for a long-term uptrend.",
    ),
    (
        "Yield curve",
        "Treasury yields plotted by maturity. When short-term yields exceed long-term ones (an inverted curve), markets are often pricing in slower growth or rate cuts ahead.",
    ),
    (
        "VIX",
        "A measure of expected S&P 500 volatility over the next 30 days, derived from options prices. Readings above ~25 signal elevated fear; below ~15, complacency.",
    ),
    (
        "Basis point",
        "One hundredth of a percentage point (0.01%). A yield moving from 4.25% to 4.50% rose 25 basis points.",
    ),
    (
        "Relative strength",
        "How an asset performs compared with a benchmark. A sector up 3% while the S&P is up 1% shows positive relative strength of 2 points.",
    ),
    (
        "Sector rotation",
        "Investors shifting money between sectors as the economic cycle changes, for example from tech into utilities and staples when growth worries rise.",
    ),
    (
        "REIT",
        "Real Estate Investment Trust: a company that owns income-producing property and must pay out most of its taxable income as dividends. Highly sensitive to interest rates.",
    ),
    (
        "Cap rate",
        "A property's net operating income divided by its value. Higher rates push cap rates up, which pushes property values down.",
    ),
    (
        "P/E ratio",
        "Share price divided by earnings per share. It tells you how many dollars investors pay for each dollar of profit.",
    ),
    (
        "Defensive sector",
        "Sectors like utilities, consumer staples and health care whose earnings hold up in recessions because demand for their products is steady.",
    ),
    (
        "Cyclical sector",
        "Sectors like energy, industrials and consumer discretionary whose profits rise and fall with the economy.",
    ),
    (
        "Spread",
        "The difference between two rates or prices. The 10Y-2Y spread is watched as a recession signal; credit spreads show how nervous lenders are.",
    ),
    (
        "Market breadth",
        "How many stocks are participating in a move. A rally led by a handful of mega-caps has narrow breadth and is considered less durable.",
    ),
    (
        "Duration",
        "A bond's sensitivity to interest rate changes. Long-duration assets, including growth stocks valued on distant profits, fall more when rates rise.",
    ),
]

# yfinance sector names -> the SPDR sector ETF used for peers and comparison.
SECTOR_ETF_BY_NAME = {
    "Technology": "XLK",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Real Estate": "XLRE",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}
STOCK_EXAMPLES = ["NVDA", "AAPL", "JPM", "LLY", "XOM", "PLD", "COST", "TSLA"]
