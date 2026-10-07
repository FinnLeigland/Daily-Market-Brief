"""Field guide: a hidden page (opened from the bottom of the Trade Journal) explaining markets from the ground up."""

from html import escape

import streamlit as st

import ai
from learn_content import MODULES, all_terms
from theme import caption, html


def _open():
    st.session_state["learn_open"] = True


def _close():
    st.session_state["learn_open"] = False
    st.session_state["main_tab"] = "Analyst Desk"  # return to where the guide was opened from


def entry_link() -> None:
    """The deliberately quiet way in: a faint link at the very bottom of the last tab."""
    _, right = st.columns([6, 1])
    with right:
        st.button(
            "field guide",
            key="learn_link",
            on_click=_open,
            type="tertiary",
            help="Concepts behind equities, trading and markets",
        )


def render() -> None:
    st.button("Back to the dashboard", key="learn_back", on_click=_close, icon=":material/arrow_back:")
    html("""
    <div class="guide-head">
      <div class="eyebrow">Field guide</div>
      <div class="h1">How markets actually work</div>
      <p>Pick a topic, then click any concept for a plain-English explanation, a worked example, and where to find it
      in this dashboard.</p>
    </div>
    """)

    module = (
        st.pills("Topic", list(MODULES), default=list(MODULES)[0], key="learn_module", label_visibility="collapsed")
        or list(MODULES)[0]
    )
    concepts = MODULES[module]
    names = [c[0] for c in concepts]
    concept = (
        st.pills("Concept", names, default=names[0], key=f"learn_concept_{module}", label_visibility="collapsed")
        or names[0]
    )
    name, one_line, body, example, where = next(c for c in concepts if c[0] == concept)
    i = names.index(name)
    html(f"""
    <div class="lesson">
      <div class="lesson-top"><div class="eyebrow">{escape(module)} · {i + 1} of {len(names)}</div></div>
      <div class="lesson-title">{escape(name)}</div>
      <div class="lesson-one">{escape(one_line)}</div>
      <p>{escape(body)}</p>
      <div class="lesson-ex"><span>Example</span>{escape(example)}</div>
      <div class="lesson-where"><span>Where to see it</span>{escape(where)}</div>
    </div>
    """)

    # ----- Ask a question -----
    html(
        '<div class="section-h"><div class="h2">Ask a question</div><span>Anything about stocks, trading or the economy</span></div>'
    )
    if ai.available():
        with st.form("tutor", clear_on_submit=False):
            q = st.text_input(
                "Question", placeholder="Why do stocks fall when interest rates rise?", label_visibility="collapsed"
            )
            asked = st.form_submit_button("Explain it", icon=":material/school:")
        if asked and q.strip():
            with st.spinner("Thinking it through…"):
                answer = ai.ask_tutor(q.strip())
            st.session_state["tutor_answer"] = (q.strip(), answer)
        if st.session_state.get("tutor_answer"):
            q, answer = st.session_state["tutor_answer"]
            if answer:
                html(f'<div class="lesson tutor"><div class="eyebrow">{escape(q)}</div></div>')
                st.markdown(answer)
            else:
                caption("Couldn't get an answer right now. Try again in a moment.")
    else:
        caption(
            "Add an Anthropic API key (see the README) to ask Claude your own questions here. The topics above "
            "work without one."
        )

    # ----- Glossary -----
    html('<div class="section-h"><div class="h2">Glossary A–Z</div><span>Every term in this guide</span></div>')
    search = (
        st.text_input(
            "Search the glossary",
            placeholder="Search: beta, spread, CPI…",
            key="learn_search",
            label_visibility="collapsed",
        )
        .strip()
        .lower()
    )
    terms = [t for t in all_terms() if not search or search in t[0].lower() or search in t[1].lower()]
    rows = "".join(
        f'<div class="term-row"><div class="t">{escape(t)}</div><div class="d">{escape(d)}'
        f"<span>{escape(m)}</span></div></div>"
        for t, d, m in terms
    )
    html(f'<div class="glossary">{rows or "<p class=caption>No matching terms.</p>"}</div>')
