"""Make today's Equity Screen picks and save them to ideas.json.

    uv run python scripts/daily_ideas.py

GitHub Actions runs this every morning and commits ideas.json back to the repo. A hosted app's disk is reset whenever
it restarts or redeploys, so keeping the picks in the repo is what lets the published app show a full track record.
The app makes the same picks itself if it opens on a day this hasn't run yet.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ideas as I  # noqa: E402
from views import ideas as V  # noqa: E402


def main() -> int:
    hist = I.load()
    today = V._today()
    if today in hist["days"]:
        print(f"Picks for {today} already saved: {', '.join(i['ticker'] for i in hist['days'][today])}.")
        return 0
    picks = V._generate(hist, today)
    if not picks:
        print("Market data didn't load, so no picks were made. The app will try again when it opens.")
        return 1
    hist["days"][today] = picks
    I.save(hist)
    for i in picks:
        print(f"{today}  {i['sector']:24} {i['ticker']:6} leans {i['lean']:4} ({i['conviction'].lower()} conviction)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
