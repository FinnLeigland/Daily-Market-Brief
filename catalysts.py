"""Catalysts: what today's headlines could mean for sectors and stocks, and what's on the calendar.

Two parts, both plain functions so they can be tested offline:

- `read_headline` turns one headline into likely effects. It spots the macro theme (oil, rates, inflation, tariffs,
  AI spending, the consumer, housing, credit, jobs) and which way the headline points, then applies the textbook link
  from that theme to each sector (rising oil helps energy producers and squeezes consumers through fuel costs). It
  also picks out companies the headline names. These are rules of thumb, not forecasts; with an API key, Claude reads
  the headlines instead (ai.read_headlines).
- `parse_fomc` and `parse_bls_ics` read the official Federal Reserve meeting calendar and the Bureau of Labor
  Statistics release calendar, and `upcoming_events` turns them (plus earnings dates) into the next few weeks.
"""

import re
from datetime import date, datetime

SECTORS = ["Technology", "Artificial Intelligence", "Financials", "Consumer Discretionary", "Energy", "Real Estate"]

# ---------- Reading headlines ----------

# theme -> words that signal it (matched as word prefixes, case-insensitive)
THEMES = {
    "oil": ["oil", "crude", "opec", "brent", "gasoline", "fuel prices"],
    "rates": [
        "fed ",
        "federal reserve",
        "rate cut",
        "rate hike",
        "interest rate",
        "yields",
        "treasury yield",
        "powell",
        "fomc",
        "bond market",
    ],
    "inflation": ["inflation", "cpi", "consumer prices", "ppi", "price pressures"],
    "tariffs": ["tariff", "trade war", "export control", "sanction"],
    "ai": ["artificial intelligence", "ai ", "ai-", "data center", "gpu", "chipmaker", "semiconductor", "chip stocks"],
    "consumer": ["consumer spending", "retail sales", "shoppers", "holiday sales", "consumer confidence", "retailer"],
    "housing": ["housing", "home sales", "mortgage", "homebuilder", "home prices", "rent"],
    "credit": ["credit", "loan losses", "default", "bank failure", "lending"],
    "jobs": ["jobs report", "payrolls", "unemployment", "jobless", "hiring", "layoffs"],
}

UP = [
    "rise",
    "rises",
    "rising",
    "rose",
    "jump",
    "surge",
    "soar",
    "rally",
    "rallies",
    "gain",
    "climb",
    "higher",
    "beat",
    "beats",
    "record",
    "boost",
    "strong",
    "stronger",
    "expand",
    "hike",
    "increase",
    "accelerat",
    "upgrade",
    "tops",
    "raises",
    "hot",
    "rebound",
    "spike",
    "boom",
]
DOWN = [
    "fall",
    "falls",
    "fell",
    "drop",
    "slump",
    "plunge",
    "slide",
    "tumble",
    "lower",
    "miss",
    "misses",
    "weak",
    "weaker",
    "cool",
    "ease",
    "eases",
    "decline",
    "slow",
    "slowdown",
    "cut",
    "cuts",
    "downgrade",
    "warning",
    "woes",
    "losses",
    "probe",
    "lawsuit",
    "layoffs",
    "sinks",
    "retreat",
    "crash",
    "fear",
    "worse",
    "struggle",
    "strike",
    "shortfall",
    "bust",
]

# (theme, direction) -> {sector: +1 helps / -1 hurts}, with the reason in plain English
EFFECTS = {
    ("oil", 1): (
        {"Energy": 1, "Consumer Discretionary": -1},
        "Higher oil lifts energy producers' profits and squeezes consumers through fuel costs.",
    ),
    ("oil", -1): (
        {"Energy": -1, "Consumer Discretionary": 1},
        "Cheaper oil hurts energy producers and leaves consumers more to spend.",
    ),
    ("rates", 1): (
        {"Real Estate": -1, "Technology": -1, "Artificial Intelligence": -1, "Financials": 1},
        "Higher rates make borrowing pricier for property and shrink what far-off tech profits are worth "
        "today, while banks earn more on loans.",
    ),
    ("rates", -1): (
        {"Real Estate": 1, "Technology": 1, "Artificial Intelligence": 1},
        "Lower rates cut borrowing costs for property and raise what future tech profits are worth today.",
    ),
    ("inflation", 1): (
        {"Real Estate": -1, "Technology": -1, "Consumer Discretionary": -1, "Energy": 1},
        "Hotter inflation points to higher rates for longer, a headwind for property and growth stocks; "
        "energy tends to hold up.",
    ),
    ("inflation", -1): (
        {"Real Estate": 1, "Technology": 1, "Consumer Discretionary": 1},
        "Cooling inflation opens the door to rate cuts, which helps property and growth stocks.",
    ),
    ("tariffs", 0): (
        {"Consumer Discretionary": -1, "Technology": -1, "Artificial Intelligence": -1},
        "Tariffs raise costs for retailers and hardware makers that rely on imported goods and parts.",
    ),
    ("ai", 1): (
        {"Artificial Intelligence": 1, "Technology": 1},
        "More AI spending goes straight to chip, cloud and software revenue.",
    ),
    ("ai", -1): (
        {"Artificial Intelligence": -1, "Technology": -1},
        "Doubts about AI spending hit the chip and cloud names that have led the market.",
    ),
    ("consumer", 1): ({"Consumer Discretionary": 1}, "Stronger spending feeds straight into retailers' sales."),
    ("consumer", -1): (
        {"Consumer Discretionary": -1},
        "Weaker spending hits retailers and other non-essential sellers.",
    ),
    ("housing", 1): (
        {"Real Estate": 1, "Consumer Discretionary": 1},
        "A firmer housing market helps property owners and home-improvement retailers.",
    ),
    ("housing", -1): (
        {"Real Estate": -1, "Consumer Discretionary": -1},
        "A weaker housing market weighs on property values and big-ticket home spending.",
    ),
    ("credit", -1): (
        {"Financials": -1, "Real Estate": -1},
        "Credit stress means loan losses for lenders and tighter financing for property.",
    ),
    ("credit", 1): ({"Financials": 1}, "Healthy credit and lending growth support bank earnings."),
    ("jobs", 1): (
        {"Consumer Discretionary": 1, "Financials": 1, "Real Estate": -1},
        "Strong hiring supports spending and loan demand, but can keep rates higher.",
    ),
    ("jobs", -1): (
        {"Consumer Discretionary": -1, "Real Estate": 1},
        "Weaker hiring hurts spending, though it makes rate cuts more likely.",
    ),
}

GENERIC_FIRST_WORDS = {"american", "general", "first", "united", "bank", "international", "global", "the", "national"}
NAME_SUFFIXES = re.compile(
    r"\b(incorporated|inc|corporation|corp|company|co|holdings?|group|plc|ltd|limited|class [abc]|n\.?v|s\.?a)\b\.?",
    re.I,
)


def _has(text: str, word: str) -> bool:
    return re.search(r"\b" + re.escape(word.strip()), text, re.I) is not None if word.strip() else False


# Words that say something about a company's own stock (a CEO's warning about the economy doesn't)
STOCK_UP = [
    "beat",
    "beats",
    "upgrade",
    "upgrades",
    "raises guidance",
    "raises outlook",
    "record",
    "surge",
    "soar",
    "jump",
    "rally",
    "tops",
    "boost",
    "wins",
    "approval",
]
STOCK_DOWN = [
    "miss",
    "misses",
    "downgrade",
    "downgrades",
    "cuts guidance",
    "cuts outlook",
    "plunge",
    "tumble",
    "slump",
    "falls",
    "drop",
    "probe",
    "lawsuit",
    "recall",
    "layoffs",
    "sinks",
    "hit",
    "hits",
    "fine",
    "investigation",
]


def stock_direction(title: str) -> int:
    t = title.lower()
    up = sum(_has(t, w) for w in STOCK_UP)
    down = sum(_has(t, w) for w in STOCK_DOWN)
    return (up > down) - (down > up)


def direction(title: str) -> int:
    """+1 if the headline mostly points up, -1 if down, 0 if mixed or neither."""
    t = title.lower()
    up = sum(_has(t, w) for w in UP)
    down = sum(_has(t, w) for w in DOWN)
    return (up > down) - (down > up)


def themes(title: str) -> list[str]:
    t = f" {title.lower()} "
    return [name for name, words in THEMES.items() if any(w in t if w.endswith(" ") else _has(t, w) for w in words)]


OIL_PRICE_WORDS = ["oil price", "oil prices", "crude", "brent", "oil futures", "barrel", "gasoline price", "gas prices"]


def _theme_direction(theme: str, title: str) -> int | None:
    """Which way the theme moves (+1/-1, 0 for no direction), or None if the headline isn't about its price."""
    t = title.lower()
    if theme == "oil" and not any(w in t for w in OIL_PRICE_WORDS):
        return None  # about the oil industry, not the oil price: more drilling doesn't mean higher prices
    if theme == "rates":
        if _has(t, "rate cut") or _has(t, "cut rates") or re.search(r"yields? (fall|drop|slide|ease|retreat)", t):
            return -1
        if _has(t, "rate hike") or _has(t, "raise rates") or re.search(r"yields? (rise|jump|climb|surge|spike)", t):
            return 1
    if theme == "credit" and any(_has(t, w) for w in ["woes", "losses", "default", "stress", "failure", "warning"]):
        return -1
    if theme == "jobs" and _has(t, "layoffs"):
        return -1
    if theme == "tariffs":
        return 0
    return direction(title)


def aliases(names: dict[str, str]) -> dict[str, list[str]]:
    """Ways a headline can name each company: '(TICKER)', '$TICKER', or a cleaned company name ('Apple', 'JPMorgan')."""
    out = {}
    for ticker, name in names.items():
        forms = [f"({ticker})", f"${ticker}"]
        clean = NAME_SUFFIXES.sub("", (name or "").replace(".com", "")).replace(",", " ").strip()
        words = clean.split()
        if words:
            first = words[0]
            if first.lower() in GENERIC_FIRST_WORDS or len(first) < 4:
                forms.append(" ".join(words[:3]))
            else:
                forms.append(first)
        if len(ticker) >= 3 and ticker.isalpha():
            forms.append(ticker)  # 3+ letter tickers are rarely ordinary words; 1-2 letter ones (C, V, MA) are
        out[ticker] = [f for f in dict.fromkeys(forms) if f]
    return out


def mentioned(title: str, names: dict[str, list[str]]) -> list[str]:
    hits = []
    for ticker, forms in names.items():
        for f in forms:
            if f.startswith(("(", "$")):
                if f in title:
                    hits.append(ticker)
                    break
            elif re.search(r"(?<![\w$])" + re.escape(f) + r"(?![\w])", title, 0 if f == ticker else re.I):
                hits.append(ticker)
                break
    return hits


def read_headline(title: str, bucket: str | None, names: dict[str, list[str]]) -> dict:
    """Likely effects of one headline: {"sectors": {sector: +1/-1/0}, "tickers": {ticker: +1/-1/0}, "why": str}.

    `bucket` is the sector whose news search found the headline; it's marked as in focus if no theme applies.
    """
    found = themes(title)
    sectors: dict[str, int] = {}
    reasons = []
    for theme in found[:2]:
        d = _theme_direction(theme, title)
        key = (theme, d) if d is not None and (theme, d) in EFFECTS else None
        if key is None:
            continue
        effects, why = EFFECTS[key]
        for s, v in effects.items():
            sectors[s] = sectors.get(s, 0) + v
        reasons.append(why)
    sectors = {s: (v > 0) - (v < 0) for s, v in sectors.items()}
    tickers = {t: stock_direction(title) for t in mentioned(title, names)}
    if bucket in SECTORS and bucket not in sectors and (tickers or not sectors):
        sectors[bucket] = stock_direction(title) if tickers else 0
    if not reasons and tickers:
        d = stock_direction(title)
        who = " and ".join(tickers)
        reasons.append(
            f"Company news for {who}: "
            + (
                "the headline reads positive."
                if d > 0
                else "the headline reads negative."
                if d < 0
                else "no clear direction from the headline alone."
            )
        )
    return {"sectors": sectors, "tickers": tickers, "why": " ".join(reasons[:2]), "themes": found[:2]}


STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "says",
    "said",
    "report",
    "reports",
    "after",
    "from",
    "into",
    "over",
    "that",
    "this",
    "its",
    "are",
    "was",
    "will",
    "has",
    "have",
    "about",
    "why",
    "how",
    "what",
    "new",
}


def _similar(a: set[str], b: set[str]) -> bool:
    return bool(a and b) and len(a & b) / min(len(a), len(b)) >= 0.6


def pick_headlines(news: dict[str, list[dict]], names: dict[str, list[str]], n: int = 8, per_bucket: int = 2):
    """The most market-relevant recent headlines, at most `per_bucket` from each sector search, newest first."""
    seen, out, word_sets = set(), [], []
    for bucket in ["Market", *SECTORS]:
        taken = 0
        for a in news.get(bucket, []):
            key = re.sub(r"[^a-z0-9]", "", a["title"].lower())[:60]
            words = set(re.findall(r"[a-z0-9]{3,}", a["title"].lower())) - STOPWORDS
            if key in seen or any(_similar(words, w) for w in word_sets):
                continue  # the same story under another outlet's headline
            read = read_headline(a["title"], None if bucket == "Market" else bucket, names)
            if not read["themes"] and not read["tickers"]:
                continue  # nothing to say about it
            seen.add(key)
            word_sets.append(words)
            out.append({**a, "bucket": bucket, "read": read})
            taken += 1
            if taken >= per_bucket:
                break
    out.sort(key=lambda a: str(a.get("published", "")), reverse=True)
    return out[:n]


# ---------- Calendar ----------

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

# What each scheduled release can move, in plain English.
EVENT_NOTES = {
    "Fed rate decision": (
        ["Real Estate", "Financials", "Technology"],
        "The Fed sets short-term rates. Rate-sensitive sectors move most: property, banks, and long-duration tech.",
    ),
    "CPI inflation": (
        ["Real Estate", "Technology", "Consumer Discretionary"],
        "A hot reading pushes yields up and hurts property and growth stocks; a cool one helps them.",
    ),
    "Jobs report": (
        ["Consumer Discretionary", "Financials", "Real Estate"],
        "Hiring and wages: strong numbers support spending and banks but can keep rates higher.",
    ),
    "PPI wholesale prices": (
        ["Consumer Discretionary", "Energy"],
        "Prices businesses pay, an early hint at where consumer inflation is heading.",
    ),
    "Job openings (JOLTS)": (["Consumer Discretionary", "Financials"], "How many jobs employers are trying to fill."),
}
BLS_NAMES = {
    "Employment Situation": "Jobs report",
    "Consumer Price Index": "CPI inflation",
    "Producer Price Index": "PPI wholesale prices",
    "Job Openings and Labor Turnover Survey": "Job openings (JOLTS)",
}


def parse_fomc(html: str) -> list[str]:
    """Rate-decision dates (the last day of each meeting) from the Fed's FOMC calendar page, as ISO dates."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    dates: dict[tuple[int, int], date] = {}
    month = "|".join(MONTHS)
    for block in re.finditer(r"(\d{4}) FOMC Meetings(.*?)(?=\d{4} FOMC Meetings|$)", text):
        year = int(block.group(1))
        for m in re.finditer(rf"\b({month})(?:/({month}))? (\d{{1,2}})-(\d{{1,2}})\*?", block.group(2)):
            last_month = m.group(2) or m.group(1)
            try:
                d = date(year, MONTHS.index(last_month) + 1, int(m.group(4)))
            except ValueError:
                continue
            dates[(d.year, d.month)] = max(d, dates.get((d.year, d.month), d))
    return sorted(d.isoformat() for d in dates.values())


def parse_bls_ics(text: str) -> list[list[str]]:
    """[[iso date, release name]] for the BLS releases the dashboard cares about."""
    out = []
    for ev in text.split("BEGIN:VEVENT")[1:]:
        start = re.search(r"DTSTART[^:\n]*:(\d{8})", ev)
        summary = re.search(r"SUMMARY:([^\r\n]+)", ev)
        if not start or not summary:
            continue
        name = next((v for k, v in BLS_NAMES.items() if summary.group(1).strip().startswith(k)), None)
        if name:
            d = datetime.strptime(start.group(1), "%Y%m%d").date().isoformat()
            out.append([d, name])
    return [list(x) for x in sorted({tuple(x) for x in out})]


def upcoming_events(
    fomc: list[str],
    bls: list[list[str]],
    earnings: dict[str, str],
    today: str,
    days: int = 21,
    picks: set[str] | None = None,
    sector_of: dict[str, str] | None = None,
) -> list[dict]:
    """Everything scheduled from today through `days` ahead, soonest first."""
    start, end = date.fromisoformat(today), date.fromordinal(date.fromisoformat(today).toordinal() + days)
    picks, sector_of = picks or set(), sector_of or {}
    out = []
    for d in fomc:
        if start <= date.fromisoformat(d) <= end:
            sectors, note = EVENT_NOTES["Fed rate decision"]
            out.append({"date": d, "event": "Fed rate decision", "kind": "macro", "sectors": sectors, "note": note})
    for d, name in bls:
        if start <= date.fromisoformat(d) <= end:
            sectors, note = EVENT_NOTES[name]
            out.append({"date": d, "event": name, "kind": "macro", "sectors": sectors, "note": note})
    for ticker, d in earnings.items():
        if d and start <= date.fromisoformat(d) <= end:
            sector = sector_of.get(ticker)
            out.append(
                {
                    "date": d,
                    "event": f"{ticker} earnings",
                    "kind": "earnings",
                    "ticker": ticker,
                    "pick": ticker in picks,
                    "sectors": [sector] if sector else [],
                    "note": "One of today's picks reports inside its one-month call."
                    if ticker in picks
                    else f"A large holding in {sector}: its results can move the whole sector."
                    if sector
                    else "Quarterly results.",
                }
            )
    return sorted(out, key=lambda e: (e["date"], e["kind"] != "macro", e["event"]))
