import streamlit as st

from saude_br.config import BASE_YEAR
from saude_br.ui import charts
from saude_br.ui.theme import PLOTLY_CONFIG
from saude_br.ui.data import table
from saude_br.ui.filters import get_filters

TOP = 6  # subfunções com cor própria; o resto vira "Outras"

f = get_filters()
sub = f.closed(table("subfuncao"))

st.title("Em que o dinheiro é gasto")
st.caption("Gasto federal em saúde por subfunção (tipo de ação), corrigido pelo IPCA. "
           "Inclui o gasto Covid, que entra em várias subfunções. Só anos fechados.")

share = st.segmented_control("Mostrar", ["R$ bi corrigidos", "% do ano"], default="R$ bi corrigidos",
                             key="comp_modo") == "% do ano"

top = sub.groupby("nome")["empenhado_real"].sum().nlargest(TOP).index.tolist()
sub = sub.assign(grupo=sub["nome"].where(sub["nome"].isin(top), "Outras"))
agg = sub.groupby(["ano", "grupo"], as_index=False)["empenhado_real"].sum()
agg["valor"] = (100 * agg["empenhado_real"] / agg.groupby("ano")["empenhado_real"].transform("sum")
                if share else agg["empenhado_real"] / 1e9)

st.plotly_chart(charts.composition(agg, top + ["Outras"], share), width="stretch", config=PLOTLY_CONFIG)
st.caption(
    f"Valores em R$ bilhões de {BASE_YEAR}. Cores fixas: a maior subfunção do período é sempre a primeira. "
    "Em 2004 o orçamento classificou os repasses ao SUS (fundo a fundo) como \"Outros Encargos "
    "Especiais\" e \"Outras Transferências\" em vez de Atenção Básica e Assistência Hospitalar; "
    "o salto daquele ano é mudança de rótulo no SIOP, não de política."
)

with st.expander("Ver tabela"):
    wide = agg.pivot(index="ano", columns="grupo", values="valor")[top + ["Outras"]].round(1)
    st.dataframe(wide, width="stretch")
