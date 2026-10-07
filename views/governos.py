import streamlit as st

from saude_br.domain.analysis import term_changes
from saude_br.ui import charts
from saude_br.ui.theme import PLOTLY_CONFIG
from saude_br.ui.data import table
from saude_br.ui.filters import get_filters

f = get_filters()
anual = f.years(table("anual"))

st.title("Quem cortou, quem ampliou")
st.caption(f"Métrica: **{f.metric.label}**{' sem Covid' if f.sem_covid and f.metric.column_sem_covid else ''}. "
           "Troque a métrica e o período na barra lateral.")

st.subheader("Variação ano a ano")
st.caption("Barras vermelhas = queda em relação ao ano anterior. Só anos fechados.")
covid_note = not f.sem_covid and f.metric.column_sem_covid is not None
closed = f.closed(table("anual"))
if len(closed) >= 2:
    st.plotly_chart(charts.yoy_bars(closed, f.column, covid_note), width="stretch", config=PLOTLY_CONFIG)
else:
    st.info("Escolha um período com pelo menos dois anos fechados.")
if covid_note:
    st.caption("2020–2022 inclui o gasto emergencial Covid. Ligue \"Descontar gasto emergencial Covid\" "
               "na barra lateral para ver a tendência sem ele.")

changes = term_changes(anual, f.column)
if changes.empty:
    st.info("Período curto demais para comparar mandatos.")
    st.stop()

left, right = st.columns(2)
with left:
    st.subheader("Crescimento médio por ano no mandato")
    st.plotly_chart(charts.term_change_bars(changes), width="stretch", config=PLOTLY_CONFIG)
with right:
    st.subheader("Nível médio no mandato")
    st.plotly_chart(charts.term_level_bars(changes, f.metric), width="stretch", config=PLOTLY_CONFIG)

st.caption(
    "Método: do último ano do mandato anterior ao último ano do mandato. O primeiro ano de "
    "cada governo executa o orçamento (LOA) enviado pelo antecessor, então conta como herança. "
    "\\* = mandato cortado pelo período escolhido ou ainda em curso. "
    "2016 está atribuído a Temer (interino desde maio). Anos parciais ficam de fora."
)

with st.expander("Ver tabela"):
    view = changes.copy()
    for c in ("valor_base", "valor_fim", "media"):
        view[c] = view[c].map(f.metric.fmt)
    for c in ("var_total", "var_anual"):
        view[c] = (100 * view[c]).round(1)
    st.dataframe(view, hide_index=True, width="stretch", column_config={
        "var_total": st.column_config.NumberColumn("var. total (%)"),
        "var_anual": st.column_config.NumberColumn("var. anual (%)"),
    })
