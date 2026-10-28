"""Entrada do app: `uv run streamlit run app.py`."""

import streamlit as st

from saude_br.ui.data import require_data
from saude_br.ui.filters import render_filters

st.set_page_config(page_title="Gastos e cortes municipais em saúde", page_icon="🩺", layout="wide", initial_sidebar_state="collapsed")

PAGES = [
    st.Page("views/linha_do_tempo.py", title="Linha do tempo", icon=":material/show_chart:", default=True),
    st.Page("views/mapa.py", title="Mapa", icon=":material/map:"),
    st.Page("views/conclusoes.py", title="Conclusões", icon=":material/fact_check:"),
]

page = st.navigation(PAGES, position="top")
require_data()
render_filters()
page.run()
