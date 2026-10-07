"""AI explanations of price moves: Claude reads the headlines around each big move and writes one line.

Needs an Anthropic API key, either in the ANTHROPIC_API_KEY environment variable or in
.streamlit/secrets.toml. Without one, the app falls back to keyword-based labels.
Every explanation is saved to .cache/move_explanations.json, so a move is only ever explained once.
"""

import json
import os
from pathlib import Path

import anthropic
import streamlit as st

MODEL = "claude-opus-5-5"
CACHE = Path(__file__).with_name(".cache") / "move_explanations.json"

SYSTEM = """You explain stock price moves for a dashboard used by someone learning about markets.

For each event you get the date, the stock's return, the S&P 500's return that day, any earnings result, and
headlines published around that date. For each event, return:
- tag: 1–3 words naming the cause, e.g. "Earnings beat", "Weak guidance", "Antitrust probe", "AI chip demand",
  "Market selloff". Title case, no punctuation, no percentages.
- summary: one plain-English sentence (at most 30 words) explaining the most likely reason for the move, written for a
  beginner. Name the specific catalyst from the headlines.

Rules: rely only on the data and headlines given. If the market moved the same way by a similar amount, say the move
was mostly market-wide. If the headlines don't explain the move, use the tag "Unclear catalyst" and say so. Never give
investment advice or predictions."""

SCHEMA = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "string"},
                    "tag": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["day", "tag", "summary"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["events"],
    "additionalProperties": False,
}


def _api_key() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    try:
        return st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets.toml
        return None


def available() -> bool:
    return bool(_api_key()) and not st.session_state.get("ai_disabled_reason")


def disabled_reason() -> str | None:
    if not _api_key():
        return "no_key"
    return st.session_state.get("ai_disabled_reason")


@st.cache_resource(show_spinner=False)
def _client(key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=key, timeout=60.0)


def _load_cache() -> dict:
    try:
        return json.loads(CACHE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, indent=1))


def explain_moves(ticker: str, company: str, events: list[dict]) -> dict[str, dict]:
    """Return {day: {"tag", "summary"}} for each event. Uses the disk cache; calls Claude only for new events."""
    cache = _load_cache()
    out = {e["day"]: cache[f"{ticker}:{e['day']}"] for e in events if f"{ticker}:{e['day']}" in cache}
    todo = [e for e in events if e["day"] not in out]
    if not todo or not available():
        return out

    lines = []
    for e in todo:
        er = e.get("earnings")
        earn = ""
        if er is not None and er.get("Reported EPS") is not None:
            earn = f" Earnings that day: EPS {er.get('Reported EPS')} vs. estimate {er.get('EPS Estimate')}."
        heads = (
            "\n".join(f"  - {h['title']} ({h['source']}, {h['published']:%b %d})" for h in e["news"])
            or "  (no headlines found)"
        )
        lines.append(
            f"Event {e['day']}: {ticker} {e['ret']:+.1f}%, S&P 500 {e['bench']:+.1f}%.{earn}\n  Headlines:\n{heads}"
        )
    prompt = f"Company: {company} ({ticker})\n\n" + "\n\n".join(lines)

    try:
        response = _client(_api_key()).beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        st.session_state["ai_disabled_reason"] = "bad_key"
        return out
    except anthropic.PermissionDeniedError:
        st.session_state["ai_disabled_reason"] = "no_access"
        return out
    except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.APIStatusError):
        return out  # transient: try again on the next run, keyword labels in the meantime

    if response.stop_reason in ("refusal", "max_tokens"):
        return out
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        results = json.loads(text)["events"]
    except (json.JSONDecodeError, KeyError):
        return out
    wanted = {e["day"] for e in todo}
    for r in results:
        if r["day"] in wanted:
            item = {"tag": r["tag"].strip()[:28], "summary": r["summary"].strip()}
            out[r["day"]] = item
            cache[f"{ticker}:{r['day']}"] = item
    _save_cache(cache)
    return out


TUTOR_SYSTEM = """You are a patient tutor inside a markets dashboard used by a college student learning about equities,
trading, and the economy. Answer the question in plain English for a beginner: start with a one-sentence answer, then
explain in at most two short paragraphs, and end with one concrete numerical example. Define any jargon you use. If the
question asks what to buy or sell, explain the concepts involved instead of giving a recommendation."""


def ask_tutor(question: str) -> str | None:
    """Answer a free-form question about markets. Returns None if AI is unavailable or the request fails."""
    if not available():
        return None
    try:
        response = _client(_api_key()).beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=TUTOR_SYSTEM,
            messages=[{"role": "user", "content": question}],
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        st.session_state["ai_disabled_reason"] = "bad_key"
        return None
    except anthropic.APIError:
        return None
    if response.stop_reason == "refusal":
        return "That question couldn't be answered here. Try rephrasing it as a question about how something works."
    return next((b.text for b in response.content if b.type == "text"), None)


IDEAS_SYSTEM = """You write the daily stock ideas in a markets dashboard used by a college student learning to analyze
stocks. Each idea already has a lean (up or down over roughly the next month) chosen by a simple quantitative screen,
the screen's reasons, and recent headlines. For each idea, return:
- thesis: two plain-English sentences (at most 45 words) explaining why the stock leans that way, combining the
  screen's numbers with the most relevant headline. Name the specific catalyst if there is one.
- risk: one sentence (at most 25 words) naming the key risk to the call, written in the measured tone of a
  research note.

Rules: rely only on the data and headlines given; if the headlines don't relate to the lean, say the call rests on the
numbers alone. Write it as analysis of what the screen sees, not as an instruction to buy or sell, and never promise an
outcome."""

IDEAS_SCHEMA = {
    "type": "object",
    "properties": {
        "ideas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string"},
                    "thesis": {"type": "string"},
                    "risk": {"type": "string"},
                },
                "required": ["ticker", "thesis", "risk"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["ideas"],
    "additionalProperties": False,
}


def write_ideas(ideas: list[dict], news: dict[str, list[dict]]) -> dict[str, dict]:
    """{ticker: {"thesis", "risk"}} for the day's ideas, or {} if AI is unavailable or the call fails."""
    if not ideas or not available():
        return {}
    blocks = []
    for i in ideas:
        heads = (
            "\n".join(f"  - {h['title']} ({h['source']}, {h['published']:%b %d})" for h in news.get(i["ticker"], []))
            or "  (no recent headlines found)"
        )
        reasons = "\n".join(f"  - {r}" for r in i["reasons"]) or "  (signals were mixed)"
        blocks.append(
            f"{i['ticker']} ({i['name']}), {i['sector']} sector, ${i['price']:,.2f}. Lean: {i['lean'].upper()} "
            f"({i['conviction'].lower()} conviction).\n  Screen's reasons:\n{reasons}\n  Screen's key risk: {i['risk']}\n"
            f"  Recent headlines:\n{heads}"
        )
    try:
        response = _client(_api_key()).beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=IDEAS_SYSTEM,
            messages=[{"role": "user", "content": "\n\n".join(blocks)}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": IDEAS_SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        st.session_state["ai_disabled_reason"] = "bad_key"
        return {}
    except anthropic.APIError:
        return {}
    if response.stop_reason in ("refusal", "max_tokens"):
        return {}
    text = next((b.text for b in response.content if b.type == "text"), "")
    try:
        results = json.loads(text)["ideas"]
    except (json.JSONDecodeError, KeyError):
        return {}
    wanted = {i["ticker"] for i in ideas}
    return {
        r["ticker"]: {"thesis": r["thesis"].strip(), "risk": r["risk"].strip()}
        for r in results
        if r["ticker"] in wanted
    }
