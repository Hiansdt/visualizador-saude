"""Filtros globais na barra lateral, compartilhados pelas duas páginas."""

from dataclasses import dataclass

import streamlit as st

from saude_br.config import FIRST_YEAR, LAST_YEAR
from saude_br.domain.temas import TEMAS, Tema


@dataclass(frozen=True)
class Filters:
    tema: Tema
    ano: int


def render_sidebar() -> None:
    with st.sidebar:
        st.segmented_control("Tema", list(TEMAS), default="Gastos", key="tema")
        tema = TEMAS[st.session_state.get("tema") or "Gastos"]
        st.caption(tema.explicacao)
        st.session_state.setdefault("ano", LAST_YEAR)
        # Mesmo intervalo nos dois temas: mudar o intervalo recria o slider e perde o ano escolhido.
        st.slider("Ano", FIRST_YEAR, LAST_YEAR, key="ano")
        if tema.key == "Cortes" and st.session_state["ano"] == FIRST_YEAR:
            st.caption(f"Cortes comparam com o ano anterior: {FIRST_YEAR} não tem variação, mostrando {FIRST_YEAR + 1}.")


def get_filters() -> Filters:
    tema = TEMAS[st.session_state.get("tema") or "Gastos"]
    ano = st.session_state.get("ano", LAST_YEAR)
    # Cortes comparam com o ano anterior: o primeiro ano não tem variação.
    return Filters(tema=tema, ano=max(ano, FIRST_YEAR + 1) if tema.key == "Cortes" else ano)
