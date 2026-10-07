"""Trade journal storage: positions, dated thesis notes and a watchlist, saved as JSON next to the app."""

import json
import uuid
from pathlib import Path

import config

PATH = Path(__file__).with_name("journal.json")


def load() -> dict:
    journal = {}
    if PATH.exists():
        try:
            journal = json.loads(PATH.read_text())
        except json.JSONDecodeError:
            journal = {}
    for key in ("positions", "notes", "watchlist"):  # older files have no watchlist yet
        journal.setdefault(key, [])
    return journal


def save(journal: dict) -> None:
    PATH.write_text(json.dumps(journal, indent=2))


def add_position(journal: dict, **fields) -> dict:
    pos = {"id": uuid.uuid4().hex[:8], "status": "open", "exit_price": None, "exit_date": None, **fields}
    journal["positions"].append(pos)
    add_note(
        journal,
        fields["ticker"],
        f"Opened position. Thesis: {fields['thesis']}",
        fields["conviction"],
        fields["target"],
        kind="open",
    )
    save(journal)
    return pos


def add_note(
    journal: dict, ticker: str, text: str, conviction: int | None, target: float | None, kind: str = "note"
) -> None:
    journal["notes"].append(
        {
            "ticker": ticker,
            "date": config.today_et().isoformat(),
            "text": text,
            "conviction": conviction,
            "target": target,
            "kind": kind,
        }
    )
    save(journal)


def update_position(journal: dict, pos_id: str, **fields) -> None:
    for p in journal["positions"]:
        if p["id"] == pos_id:
            p.update(fields)
    save(journal)


def delete_position(journal: dict, pos_id: str) -> None:
    ticker = next((p["ticker"] for p in journal["positions"] if p["id"] == pos_id), None)
    journal["positions"] = [p for p in journal["positions"] if p["id"] != pos_id]
    if ticker and not any(p["ticker"] == ticker for p in journal["positions"]):
        journal["notes"] = [n for n in journal["notes"] if n["ticker"] != ticker]
    save(journal)


EXAMPLES = [
    dict(
        ticker="NVDA",
        shares=10,
        entry_price=180.0,
        entry_date="2026-03-16",
        conviction=4,
        target=280.0,
        stop=150.0,
        horizon="1–2 years",
        thesis="Data-center spending keeps compounding; margins hold above 60% as new chips ramp.",
        wrong_if="Hyperscaler capex guidance gets cut, or gross margin falls below 60% for two quarters.",
    ),
    dict(
        ticker="PLD",
        shares=25,
        entry_price=118.0,
        entry_date="2026-05-04",
        conviction=3,
        target=150.0,
        stop=105.0,
        horizon="2–3 years",
        thesis="Warehouse rents keep rising faster than inflation; the stock re-rates once the Fed starts cutting.",
        wrong_if="Occupancy drops below 94% or long-term rates keep climbing past 5.75%.",
    ),
    dict(
        ticker="COST",
        shares=4,
        entry_price=905.0,
        entry_date="2025-11-10",
        conviction=3,
        target=1050.0,
        stop=820.0,
        horizon="3+ years",
        thesis="Membership renewals above 90% make earnings unusually steady. I'm paying a premium for safety.",
        wrong_if="Renewal rate slips below 89% or same-store sales growth turns negative.",
    ),
]


# ---------- Watchlist ----------


def watch(journal: dict, ticker: str, buy_below: float, note: str = "", source: str = "manual") -> dict:
    """Add a stock to the watchlist, or update its buy zone if it's already there."""
    ticker = ticker.strip().upper()
    for item in journal["watchlist"]:
        if item["ticker"] == ticker:
            item.update(buy_below=float(buy_below), note=note or item.get("note", ""), source=source)
            save(journal)
            return item
    item = {
        "id": uuid.uuid4().hex[:8],
        "ticker": ticker,
        "buy_below": float(buy_below),
        "note": note,
        "source": source,
        "added": config.today_et().isoformat(),
    }
    journal["watchlist"].append(item)
    save(journal)
    return item


def unwatch(journal: dict, item_id: str) -> None:
    journal["watchlist"] = [w for w in journal["watchlist"] if w["id"] != item_id]
    save(journal)


def automation_config(journal: dict) -> dict:
    """The minimal data the daily alert job needs (no theses or notes), for a GitHub Actions secret."""
    return {
        "positions": [
            {"ticker": p["ticker"], "entry_price": p["entry_price"], "target": p["target"], "stop": p["stop"]}
            for p in journal["positions"]
            if p.get("status") == "open"
        ],
        "watchlist": [{"ticker": w["ticker"], "buy_below": w["buy_below"]} for w in journal["watchlist"]],
    }
