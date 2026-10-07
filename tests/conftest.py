import pytest

import data
import snapshot


@pytest.fixture(autouse=True)
def _isolated_yahoo_state(tmp_path, monkeypatch):
    """Each test gets its own empty saved-copy folder, no remote bundle, and a fresh 'Yahoo is down' timer."""
    monkeypatch.setattr(snapshot, "DIR", tmp_path / "snapshot")
    monkeypatch.setattr(snapshot, "URL", "")
    monkeypatch.setattr(data, "_yahoo_down", {"until": 0.0})
    data.reset_stale()
    yield
    data.reset_stale()
