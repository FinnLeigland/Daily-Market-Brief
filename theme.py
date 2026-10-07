"""Shared dark theme: colors, HTML helpers, Plotly styling."""

import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Categorical slots, dark-surface steps (fixed order, never cycled).
SERIES = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
POS, NEG, MID = "#3987e5", "#e66767", "#383835"  # diverging poles + neutral midpoint
UP, DOWN = "#3ec46d", "#f06a6a"  # text-level gain/loss (always paired with ▲▼ and sign)
GOOD, WARN, BAD = "#0ca30c", "#fab219", "#d03b3b"  # status colors, always paired with icon + label
INK, INK_2, INK_3 = "#f2f1ec", "#c3c2b7", "#8c8b84"
GRID, MUTED = "#2b2a27", "#55544f"


def show_help() -> bool:
    """Whether explanations are visible (toggled from the Digest's 'Hide explanations' button)."""
    return st.session_state.get("show_help", True)


def toggle_help() -> None:
    st.session_state["show_help"] = not show_help()


def show_warnings() -> bool:
    """Whether reliability warnings are visible (toggled from the Analyst Desk's 'Hide warnings' button)."""
    return st.session_state.get("show_warnings", True)


def toggle_warnings() -> None:
    st.session_state["show_warnings"] = not show_warnings()


def warning_note(text: str) -> str:
    """HTML for a caution about how far to trust a signal. Hidden by CSS when warnings are off."""
    return f'<div class="warn-note"><span>Caution</span><div>{text}</div></div>'


def warn(text: str) -> None:
    if show_warnings():
        html(warning_note(text))


def direction(x: float | None, flat: float = 0.005) -> str:
    if x is None or pd.isna(x) or abs(x) < flat:
        return "flat"
    return "up" if x > 0 else "down"


def fmt_pct(x: float | None, digits: int = 1, arrow: bool = True) -> str:
    if x is None or pd.isna(x):
        return "—"
    a = {"up": "▲", "down": "▼", "flat": ""}[direction(x)] if arrow else ""
    return f"{a} {fmt_value('{:+.' + str(digits) + 'f}%', x)}".strip()


def chg_span(x: float | None, digits: int = 1, text: str | None = None) -> str:
    return f'<span class="chg {direction(x)}">{text or fmt_pct(x, digits)}</span>'


def sparkline(
    series: pd.Series, width: int = 240, height: int = 46, color: str | None = None, tip: str | None = None
) -> str:
    """Inline SVG trend line. Colored green/red by direction unless a fixed `color` is given."""
    s = series.dropna()
    lo, hi = s.min(), s.max()
    span = (hi - lo) or 1
    pts = [(i / (len(s) - 1) * width, height - 4 - (v - lo) / span * (height - 8)) for i, v in enumerate(s)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{height} {line} {width},{height}"
    color = color or (UP if s.iloc[-1] >= s.iloc[0] else DOWN)
    lx, ly = pts[-1]
    tip = tip or f"3-month range {lo:,.2f} – {hi:,.2f}, now {s.iloc[-1]:,.2f}"
    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" preserveAspectRatio="none"><title>{tip}</title>'
        f'<polygon points="{area}" fill="{color}" opacity="0.10"/>'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.6" '
        f'vector-effect="non-scaling-stroke" stroke-linejoin="round"/>'
        f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2.6" fill="{color}"/></svg>'
    )


def html(markup: str) -> None:
    # Strip leading indentation so Markdown never treats the HTML as a code block.
    st.markdown("\n".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def fmt_value(fmt: str, v) -> str:
    """Format a number for display: missing values become an em dash, and a value that rounds to zero loses its
    sign, so tables never show "-0.0%" or "+0.0%"."""
    if v is None or pd.isna(v):
        return "—"
    out = fmt.format(v)
    return out[1:] if re.fullmatch(r"[+-]0(\.0+)?(%|×| pts)?", out) else out


def table_html(
    df: pd.DataFrame, formats: dict, emphasize: tuple = (), first_col: str = "", color_cols: tuple = ()
) -> str:
    """A compact HTML table in the site's style: numbers right-aligned in tabular figures, chosen rows in bold, and
    `color_cols` shaded green/red by sign. It never scrolls or clips inside narrow columns the way st.dataframe can.
    """
    head = f'<tr class="th"><td>{first_col}</td>' + "".join(
        f'<td class="{"n" if c in formats else ""}">{c}</td>' for c in df.columns
    )
    body = []
    for idx, row in df.iterrows():
        cells = []
        for c, v in row.items():
            if c not in formats:
                cells.append(f"<td>{v}</td>")
                continue
            text = fmt_value(formats[c], v)
            tone = f" {direction(v, flat=0.05)}" if c in color_cols and text != "—" else ""
            cells.append(f'<td class="n{tone}">{text}</td>')
        body.append(f'<tr class="{"em" if idx in emphasize else ""}"><td>{idx}</td>{"".join(cells)}</tr>')
    return f'<div class="tbl-wrap"><table class="tbl compact">{head}</tr>{"".join(body)}</table></div>'


def section(title: str, note: str = "") -> None:
    html(f'<div class="section-h"><div class="h2">{title}</div><span>{note}</span></div>')


def explain(title: str, body: str) -> None:
    """A collapsible 'how this works' note, for the concepts behind a chart."""
    if not show_help():
        return
    with st.expander(f"How to read this: {title}"):
        html(f'<div class="explain">{body}</div>')


def chart_title(text: str) -> None:
    html(f'<div class="chart-title">{text}</div>')


def caption(text: str, teach: bool = False) -> None:
    """A note under a chart. `teach=True` marks it as an explanation that clean view hides."""
    if teach and not show_help():
        return
    html(f'<p class="caption">{text}</p>')


def style_fig(fig: go.Figure, height: int = 380, ysuffix: str = "%") -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=28, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Geist, Inter, sans-serif", color=INK, size=12),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#232321", bordercolor=GRID, font_color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, font_color=INK_2),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont_color=INK_3, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=MUTED, tickfont_color=INK_3, ticksuffix=ysuffix)
    return fig


def end_labels(fig: go.Figure, ends: dict[str, float]) -> None:
    """Direct-label line ends, nudging labels apart so they never overlap."""
    if not ends:
        return
    vals = list(ends.values())
    gap = (max(vals) - min(vals) or 1) * 0.06
    placed: list[float] = []
    for name, y in sorted(ends.items(), key=lambda kv: kv[1]):
        y_lab = max(y, placed[-1] + gap) if placed else y
        placed.append(y_lab)
        fig.add_annotation(
            x=1,
            xref="paper",
            y=y_lab,
            text=f" {name}",
            showarrow=False,
            xanchor="left",
            font=dict(size=11, color=INK_2),
        )


def shade_periods(fig: go.Figure, flags: pd.Series, label: str = "Recession") -> None:
    """Shade contiguous True runs of a boolean series (e.g. NBER recessions)."""
    runs = (flags != flags.shift()).cumsum()
    for _, grp in flags[flags].groupby(runs[flags]):
        fig.add_vrect(x0=grp.index[0], x1=grp.index[-1], fillcolor="#ffffff", opacity=0.06, line_width=0, layer="below")
    if label:
        fig.add_annotation(
            x=0,
            xref="paper",
            y=1,
            yref="paper",
            text=f"Shaded: {label}",
            showarrow=False,
            xanchor="left",
            yanchor="bottom",
            font=dict(size=10, color=INK_3),
        )
