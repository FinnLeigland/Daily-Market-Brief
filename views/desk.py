"""Analyst Desk: a PIN-protected workspace.

The PIN is a privacy screen for a personal dashboard, not real security: the code is public once it's on GitHub.
Set DESK_PIN in .streamlit/secrets.toml (or the environment) to use your own instead of the default.
"""

import hashlib
import hmac
import os
import threading
import time

import streamlit as st

from theme import html, show_help, show_warnings, toggle_help, toggle_warnings
from views import journal, learn, lessons

DEFAULT_PIN_SHA256 = "edee29f882543b956620b26d0ee0e7e950399b1c4222f5de05e06425b4c995e9"
MAX_TRIES, LOCKOUT_SECONDS = 5, 30
# Server-wide guard: per-session lockouts reset when the page is refreshed, so wrong PINs are also counted across all
# visitors. Every GLOBAL_MAX_FAILS wrong guesses lock the gate for everyone for GLOBAL_LOCKOUT_SECONDS.
GLOBAL_MAX_FAILS, GLOBAL_LOCKOUT_SECONDS = 20, 300
_guard = {"fails": 0, "until": 0.0}
_guard_lock = threading.Lock()
VIEWS = ["Trade Journal", "Daily Lesson"]


def _expected_hash() -> str:
    custom = os.environ.get("DESK_PIN")
    if not custom:
        try:
            custom = st.secrets.get("DESK_PIN")
        except Exception:
            custom = None
    return hashlib.sha256(str(custom).encode()).hexdigest() if custom else DEFAULT_PIN_SHA256


def _try_unlock() -> None:
    state = st.session_state
    pin = state.get("desk_pin_input", "")
    state["desk_pin_input"] = ""
    if time.time() < max(state.get("desk_locked_until", 0), _guard["until"]):
        return
    if hmac.compare_digest(hashlib.sha256(pin.encode()).hexdigest(), _expected_hash()):
        state.update(desk_unlocked=True, desk_fails=0, desk_error=None)
        return
    with _guard_lock:
        _guard["fails"] += 1
        if _guard["fails"] >= GLOBAL_MAX_FAILS:
            _guard.update(fails=0, until=time.time() + GLOBAL_LOCKOUT_SECONDS)
    state["desk_fails"] = state.get("desk_fails", 0) + 1
    if state["desk_fails"] >= MAX_TRIES:
        state.update(desk_locked_until=time.time() + LOCKOUT_SECONDS, desk_fails=0)
        state["desk_error"] = None  # the countdown message takes over
    else:
        left = MAX_TRIES - state["desk_fails"]
        state["desk_error"] = f"Incorrect PIN · {left} {'try' if left == 1 else 'tries'} left"


def _lock() -> None:
    st.session_state.update(desk_unlocked=False, lesson_run=None)


def _save_view() -> None:
    st.session_state["desk_view_saved"] = st.session_state["desk_view"]


def _gate() -> None:
    _, mid, _ = st.columns([1.4, 1, 1.4])
    with mid:
        html(
            '<div class="gate"><div class="lock"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" '
            'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg></div></div>'
        )
        wait = max(st.session_state.get("desk_locked_until", 0), _guard["until"]) - time.time()
        with st.form("desk_gate", clear_on_submit=False, border=False):
            st.text_input(
                "PIN",
                type="password",
                key="desk_pin_input",
                placeholder="Enter PIN",
                label_visibility="collapsed",
                disabled=wait > 0,
            )
            st.form_submit_button("Unlock", on_click=_try_unlock, type="primary", width="stretch", disabled=wait > 0)
        message = (
            f"Too many attempts. Try again in {int(wait) + 1}s." if wait > 0 else st.session_state.get("desk_error")
        )
        if message:
            html(f'<div class="gate-error">{message}</div>')


def render() -> None:
    if not st.session_state.get("desk_unlocked"):
        _gate()
        return

    # Toolbar: view switcher, display setting, lock
    left, mid, warn_col, right = st.columns([2.2, 1.5, 1.35, 0.85], vertical_alignment="center")
    with left:
        saved = st.session_state.get("desk_view_saved", VIEWS[0])
        view = (
            st.segmented_control(
                "Desk view", VIEWS, default=saved, key="desk_view", on_change=_save_view, label_visibility="collapsed"
            )
            or saved
        )
    with mid:
        on = show_help()
        st.button(
            "Hide explanations" if on else "Show explanations",
            key="help_toggle",
            on_click=toggle_help,
            icon=":material/visibility_off:" if on else ":material/visibility:",
            help="Hide or show ratio descriptions, how-to-read notes and explainers on every tab.",
            width="stretch",
        )
    with warn_col:
        on = show_warnings()
        st.button(
            "Hide warnings" if on else "Show warnings",
            key="warn_toggle",
            on_click=toggle_warnings,
            icon=":material/notifications_off:" if on else ":material/warning:",
            help="Hide or show the cautions about how far to trust a signal (backtest results, fragile findings).",
            width="stretch",
        )
    with right:
        st.button("Lock", key="desk_lock", on_click=_lock, icon=":material/lock:", width="stretch")
    html('<div class="desk-rule"></div>')

    if view == "Daily Lesson":
        lessons.render()
    else:
        journal.render()
    learn.entry_link()
