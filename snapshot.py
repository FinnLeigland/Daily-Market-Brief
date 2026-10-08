"""Last-good copies of Yahoo Finance responses, so the app keeps working when Yahoo blocks a server.

Yahoo often rate-limits or blocks shared cloud servers (Streamlit Community Cloud among them) while answering normal
machines fine. So every successful Yahoo response is also saved here, and when a live request fails the app serves the
saved copy instead, labelled with its age. A scheduled GitHub Actions job (snapshot.yml) runs the app's default views
on GitHub's servers every hour on weekdays and publishes the resulting files as a release asset; when the live site
can't reach Yahoo and has no copy of its own yet, it downloads that bundle.

Files are plain Parquet (tables) and JSON (everything else), never pickles, so a downloaded bundle can't run code.
"""

import hashlib
import io
import json
import os
import re
import tarfile
import threading
import time
from pathlib import Path

import pandas as pd
import requests

DIR = Path(os.environ.get("SNAPSHOT_DIR") or Path(__file__).with_name(".cache") / "snapshot")
URL = os.environ.get(
    "SNAPSHOT_URL",
    "https://github.com/FinnLeigland/Daily-Market-Brief/releases/download/data-snapshot/snapshot.tar.gz",
)
REMOTE_EVERY = 10 * 60  # while Yahoo is blocking, check GitHub's bundle for newer copies at most every 10 min
_NAME = re.compile(r"^[0-9a-f]{20}\.(parquet|json)$")
_lock = threading.Lock()
_last_remote = {"at": 0.0}


def _plain(o):
    """JSON fallback that keeps numbers as numbers (numpy scalars) and dates as ISO strings."""
    if hasattr(o, "item"):
        return o.item()
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)


def key(name: str, *args) -> str:
    raw = json.dumps([name, *args], default=str, sort_keys=True)
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def save(name: str, *args, value) -> None:
    """Remember a successful response. Never raises: a failed save must not break the page."""
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        k = key(name, *args)
        if isinstance(value, pd.Series):
            value = value.to_frame("__series__")
        if isinstance(value, pd.DataFrame):
            path, tmp = DIR / f"{k}.parquet", DIR / f"{k}.parquet.tmp"
            df = value.copy()
            df.columns = [str(c) for c in df.columns]
            df.to_parquet(tmp)
        else:
            path, tmp = DIR / f"{k}.json", DIR / f"{k}.json.tmp"
            tmp.write_text(json.dumps(value, default=_plain))
        tmp.replace(path)
    except Exception:
        pass


def load(name: str, *args):
    """(value, saved_at) for the last good copy, or None."""
    k = key(name, *args)
    try:
        if (p := DIR / f"{k}.parquet").exists():
            df = pd.read_parquet(p)
            value = df["__series__"] if list(df.columns) == ["__series__"] else df
            return value, p.stat().st_mtime
        if (p := DIR / f"{k}.json").exists():
            return json.loads(p.read_text()), p.stat().st_mtime
    except Exception:
        return None
    return None


def refresh_from_remote(force: bool = False) -> int:
    """Download the published bundle (at most hourly) and keep any file newer than the local copy. Returns files added."""
    with _lock:
        if not URL or (not force and time.time() - _last_remote["at"] < REMOTE_EVERY):
            return 0
        _last_remote["at"] = time.time()
    try:
        resp = requests.get(URL, timeout=20)
        resp.raise_for_status()
        added = 0
        DIR.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(resp.content), mode="r:gz") as tar:
            for m in tar.getmembers():
                name = Path(m.name).name
                if not m.isfile() or not _NAME.match(name):
                    continue  # only flat data files; no paths, links or anything executable
                dest = DIR / name
                if dest.exists() and dest.stat().st_mtime >= m.mtime:
                    continue
                data = tar.extractfile(m).read()
                tmp = dest.with_suffix(dest.suffix + ".tmp")
                tmp.write_bytes(data)
                os.utime(tmp, (m.mtime, m.mtime))
                tmp.replace(dest)
                added += 1
        return added
    except Exception:
        return 0


def bundle(out: Path) -> int:
    """Pack every saved file into a .tar.gz (used by the GitHub Actions job). Returns the number of files."""
    files = sorted(p for p in DIR.glob("*") if _NAME.match(p.name))
    with tarfile.open(out, "w:gz") as tar:
        for p in files:
            tar.add(p, arcname=p.name)
    return len(files)
