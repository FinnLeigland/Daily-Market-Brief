"""Build the saved-data bundle that keeps the live site working when Yahoo blocks its server.

    uv run python scripts/build_snapshot.py snapshot.tar.gz

Starts from the currently published bundle (so nothing already saved is lost), renders every tab's default view plus
the common Stock Lab and Micro choices, so each Yahoo response they need is saved, then packs everything into one
.tar.gz. GitHub Actions (snapshot.yml) runs this hourly on weekdays and publishes it as a release asset.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("SNAPSHOT_DIR", tempfile.mkdtemp(prefix="snapshot-"))
# Work on a copy of the real picks, so the Equity Screen fetches exactly the stocks the live site shows, without
# ever writing to the real file.
_ideas_copy = Path(tempfile.mkdtemp()) / "ideas.json"
if (ROOT / "ideas.json").exists():
    _ideas_copy.write_text((ROOT / "ideas.json").read_text())
os.environ["IDEAS_FILE"] = str(_ideas_copy)
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest  # noqa: E402

import config  # noqa: E402
import data  # noqa: E402
import prefetch  # noqa: E402
import signal_checks  # noqa: E402
import snapshot  # noqa: E402


def render(tab: str, **state) -> None:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=600)
    at.session_state["main_tab"] = tab
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    problems = [e.value for e in at.exception]
    print(f"  {tab:16} {state or ''} {'ok' if not problems else problems[0][:120]}")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "snapshot.tar.gz")
    added = snapshot.refresh_from_remote(force=True)
    print(f"Started from the published bundle: {added} files")

    for tab in ["Digest", "Macro", "Sector Rotation", "Equity Screen"]:
        render(tab)
    for sector in data.YF_SECTORS:
        render("Micro", micro_sector=sector)
    saved_picks = json.loads((ROOT / "ideas.json").read_text()) if (ROOT / "ideas.json").exists() else {"days": {}}
    picks = [i["ticker"] for d in list(saved_picks["days"].values())[-5:] for i in d]  # the last week's picks
    for ticker in dict.fromkeys(["NVDA", *config.STOCK_EXAMPLES, *picks]):
        render("Stock Lab", stock_ticker=ticker)

    signal_checks.load()
    with prefetch._running:  # wait for any background warm-up a render started
        pass

    if data.stale_since() is not None:
        print("Note: some views used saved copies, so Yahoo refused at least one request during this run.")
    n = snapshot.bundle(out)
    print(f"Wrote {out} with {n} files ({out.stat().st_size / 1e6:.1f} MB)")
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
