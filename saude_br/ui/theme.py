"""Paleta (validada com o validador do skill dataviz) e estilo base dos gráficos."""

import streamlit as st

from saude_br.domain.governments import PRESIDENTS

LIGHT = {
    "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"],
    "ink": "#0b0b0b",
    "ink_2": "#52514e",
    "muted": "#898781",
    "grid": "#e1e0d9",
    "axis": "#c3c2b7",
    "surface": "#fcfcfb",
    "other": "#c3c2b7",
    "neutral": "#f0efec",
}
DARK = {
    "series": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9"],
    "ink": "#ffffff",
    "ink_2": "#c3c2b7",
    "muted": "#898781",
    "grid": "#2c2c2a",
    "axis": "#383835",
    "surface": "#1a1a19",
    "other": "#52514e",
    "neutral": "#383835",
}
# Sequencial (azul, claro -> escuro) e divergente (vermelho <- cinza -> azul).
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
NEG, POS = "#d03b3b", "#2a78d6"
# Sem barra de ferramentas: atrapalha na projeção e cobre rótulos.
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}


def is_dark() -> bool:
    # Tema fixo no config: st.context.theme vem "dark" na 1ª carga (preferência do SO) antes de assentar.
    base = st.get_option("theme.base")
    if base in ("light", "dark"):
        return base == "dark"
    try:
        return st.context.theme.type == "dark"
    except AttributeError:
        return False


def palette() -> dict:
    return DARK if is_dark() else LIGHT


def president_color(president: str) -> str:
    return palette()["series"][PRESIDENTS.index(president)]


def diverging_scale() -> list:
    return [[0, NEG], [0.5, palette()["neutral"]], [1, POS]]


def style(fig, height=420, legend=True):
    p = palette()
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        font=dict(family='"Source Sans", "Source Sans Pro", system-ui, sans-serif', color=p["ink_2"]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0, title=None),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor=p["axis"], tickfont_color=p["muted"], ticks="")
    fig.update_yaxes(gridcolor=p["grid"], zeroline=False, linecolor=p["axis"], tickfont_color=p["muted"])
    return fig
