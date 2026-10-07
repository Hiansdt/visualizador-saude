import streamlit as st

from saude_br.domain.metrics import METRICS
from saude_br.ui import charts
from saude_br.ui.theme import PLOTLY_CONFIG
from saude_br.ui.data import table
from saude_br.ui.filters import get_filters

f = get_filters()
anual = f.years(table("anual"))
closed = anual[~anual["ano_parcial"]]

st.title("Quanto o governo federal gasta com saúde?")
st.caption(f"Despesa empenhada da União na função Saúde, {f.start}–{f.end}. "
           "As faixas coloridas marcam cada mandato presidencial.")

if len(closed) >= 2:
    first, last = closed.iloc[0], closed.iloc[-1]
    st.markdown(f"**{int(first['ano'])} → {int(last['ano'])}**")
    cols = st.columns(4)
    for col, key in zip(cols, ("per_capita", "real", "pct_pib", "pct_orcamento")):
        m = METRICS[key]
        c = m.col(f.sem_covid)
        col.metric(m.label, m.fmt(last[c]), f"{m.fmt_delta(first[c], last[c])} desde {int(first['ano'])}",
                   border=True)

events = st.toggle("Mostrar marcos legais", value=True)
st.plotly_chart(charts.timeline(anual, f.metric, f.sem_covid, events=events), width="stretch", config=PLOTLY_CONFIG)

if f.metric.nominal_column:
    st.caption(
        "Linha preta: valores corrigidos pela inflação (IPCA), em reais de hoje, para comparar poder de "
        "compra entre anos. Linha roxa: o mesmo gasto sem correção, em reais de cada ano. A distância "
        "entre as duas é a inflação acumulada."
    )
if anual["ano_parcial"].any():
    st.caption("Círculo vazado = ano em andamento (valor parcial, acumulado até a data da coleta).")

with st.expander("Ver tabela"):
    view = anual[["ano", "mandato", f.column]].copy()
    view[f.metric.label] = view[f.column].map(f.metric.fmt)
    st.dataframe(view[["ano", "mandato", f.metric.label]], hide_index=True, width="stretch")
