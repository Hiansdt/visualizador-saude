"""Entrada do app: `uv run streamlit run app.py`."""

import streamlit as st

from saude_br.ui.data import require_data
from saude_br.ui.filters import render_sidebar

st.set_page_config(page_title="Gastos e cortes municipais em saúde", page_icon="🩺", layout="wide")

PAGES = [
    st.Page("views/linha_do_tempo.py", title="Linha do tempo", icon=":material/show_chart:", default=True),
    st.Page("views/mapa.py", title="Mapa", icon=":material/map:"),
]

page = st.navigation(PAGES)
require_data()
render_sidebar()
page.run()
