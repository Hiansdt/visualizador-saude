"""Entrada do app: `uv run streamlit run app.py`."""

import streamlit as st

from saude_br.ui.data import require_data
from saude_br.ui.filters import render_sidebar

st.set_page_config(page_title="Saúde no orçamento federal", page_icon="🩺", layout="wide")

PAGES = [
    st.Page("views/panorama.py", title="Panorama", icon=":material/show_chart:", default=True),
    st.Page("views/governos.py", title="Por governo", icon=":material/account_balance:"),
    st.Page("views/mapa.py", title="Mapa", icon=":material/map:"),
    st.Page("views/composicao.py", title="Composição", icon=":material/stacked_bar_chart:"),
    st.Page("views/cortes.py", title="Cortes", icon=":material/content_cut:"),
    st.Page("views/desvios.py", title="Desvios", icon=":material/gavel:"),
    st.Page("views/estatistica.py", title="Estatística", icon=":material/functions:"),
    st.Page("views/metodo.py", title="Dados e método", icon=":material/database:"),
]

page = st.navigation(PAGES)
require_data()
render_sidebar()
page.run()
