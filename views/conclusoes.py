"""Conclusões calculadas a partir dos dados, mais fontes e limitações. Usa o período inteiro."""

import streamlit as st

from saude_br.config import BASE_YEAR, FIRST_YEAR, LAST_YEAR
from saude_br.domain.geography import UF_NAME
from saude_br.domain.stats import cv_reading
from saude_br.sources import SOURCES
from saude_br.ui.data import by_uf, meta, municipios, yearly
from saude_br.ui.fmt import br, md

g = yearly("Gastos").set_index("Ano")
c = yearly("Cortes").set_index("Ano")
first, last = g.iloc[0], g.iloc[-1]
y0, y1 = int(g.index[0]), int(g.index[-1])


def reais(v):
    return f"R$ {br(v)}"


st.title("Conclusões")
st.caption(f"Gasto municipal com saúde e saneamento por habitante, corrigido pela inflação (R$ de {BASE_YEAR}), "
           f"{y0}–{y1}. Cada número abaixo é calculado dos dados, para o período inteiro.")

st.subheader("1. Gastos: o nível subiu muito")
above = int((g["Média"] > g["Mediana"]).sum())
st.markdown(md(
    f"- A média por habitante foi de **{reais(first['Média'])}** em {y0} para **{reais(last['Média'])}** em {y1}: "
    f"**{br(last['Média'] / first['Média'], 1)} vezes** mais, já descontada a inflação.\n"
    f"- A mediana ficou abaixo da média em **{above} dos {len(g)} anos** (em {y1}: {reais(last['Mediana'])} "
    f"contra {reais(last['Média'])}). A distribuição é assimétrica à direita: a maioria dos municípios gasta "
    "menos que a média, e poucos municípios com gasto alto puxam a média para cima.\n"
    f"- Moda (Czuber, classes de Sturges) em {y1}: **{reais(last['Moda (Czuber)'])}**, perto da mediana; com "
    "classes mais finas o pico fica um pouco abaixo. Em dados contínuos e assimétricos, a moda depende das classes."
))

st.subheader("2. Gastos: a desigualdade relativa caiu")
n = int(last["n"])
st.markdown(md(
    f"- O desvio padrão subiu de **{reais(first['DP pop.'])}** para **{reais(last['DP pop.'])}**: em reais, "
    "a distância entre os municípios aumentou.\n"
    f"- Mas o coeficiente de variação caiu de **{br(first['CV pop. (%)'], 1)}%** para **{br(last['CV pop. (%)'], 1)}%** "
    f"(ainda {cv_reading(last['CV pop. (%)'])}): em relação à média, os municípios ficaram **menos desiguais**.\n"
    f"- A amplitude ({reais(last['Amplitude'])} em {y1}) depende só de dois municípios extremos e não "
    "mostra essa melhora: por isso é a medida de dispersão menos confiável.\n"
    f"- Com n = {br(n)} municípios, a variância amostral é só {br(100 * (n / (n - 1) - 1), 3)}% maior que a "
    "populacional: como temos praticamente todos os municípios, a populacional é a adequada."
))

st.subheader("3. Cortes: quantos e quando")
pct = c["% com corte"]
worst, best = int(pct.idxmax()), int(pct.idxmin())
st.markdown(md(
    f"- Em média, **{br(pct.mean(), 0)}%** dos municípios cortam o gasto real por habitante a cada ano "
    f"(cerca de 1 em cada {round(100 / pct.mean())}).\n"
    f"- O pior ano foi **{worst}**: **{br(pct.max(), 0)}%** dos municípios cortaram, com variação mediana de "
    f"**{br(c.loc[worst, 'Mediana'], 1)}%**. Crise fiscal e recessão.\n"
    f"- O melhor foi **{best}**: só **{br(pct.min(), 0)}%** cortaram (variação mediana de "
    f"+{br(c.loc[best, 'Mediana'], 1)}%), com o dinheiro extra da Covid."
))

st.subheader("4. Cortes: onde, e o limite do CV")
uf = by_uf("Cortes", worst)
hi, lo = uf.nlargest(1, "pct_corte").iloc[0], uf.nsmallest(1, "pct_corte").iloc[0]
cv_last = c.loc[y1, "CV pop. (%)"]
st.markdown(md(
    f"- Em {worst}, a proporção de municípios que cortaram foi de **{br(hi['pct_corte'], 0)}%** "
    f"({UF_NAME[hi['cod_uf']]}, a maior) a **{br(lo['pct_corte'], 0)}%** ({UF_NAME[lo['cod_uf']]}, a menor).\n"
    f"- Na variação anual, o CV passa de **{br(cv_last, 0)}%** ({y1}): a média fica perto de zero e o desvio "
    "padrão é muito maior que ela. O CV só funciona bem quando a média é bem maior que zero; para "
    "comparar a variação, o desvio padrão é a medida certa."
))

st.subheader("Em uma frase")
st.info(md(
    f"Em {y1 - y0 + 1} anos, o gasto municipal com saúde por habitante quase quadruplicou em termos reais e ficou "
    f"menos desigual entre os municípios, mas não de forma contínua: a cada ano cerca de "
    f"{br(pct.mean(), 0)}% dos municípios cortam, e em {worst} foram {br(pct.max(), 0)}%."
))

st.subheader("Fontes")
st.markdown("\n".join(f"- **[{s.name}]({s.url})** — {s.description}" for s in SOURCES.values()))

st.subheader("Método e limitações")
mun = municipios()
excl = mun.loc[~mun["valido"], "exclusao"].value_counts()
m = meta()
st.markdown(md(
    f"- **{br(m['linhas'])} linhas** (município × ano), {br(m['validas'])} usadas. Fora da análise: "
    + "; ".join(f"{br(v)}: {k}" for k, v in excl.items())
    + ". Esses extremos são tratados como erro de registro.\n"
    f"- Valores corrigidos pela média anual do IPCA para reais de {BASE_YEAR}. Média aritmética simples: cada "
    "município conta uma vez, não importa o tamanho.\n"
    f"- A série começa em {FIRST_YEAR}: nesse ano os municípios passam à classificação orçamentária atual e o "
    f"gasto com saúde muda de nível. Termina em {LAST_YEAR}, último ano fechado.\n"
    "- É gasto **municipal**, decidido por cada prefeitura (com parte do dinheiro vindo de repasses federais "
    "do SUS). As faixas de presidente na linha do tempo são só contexto histórico.\n"
    "- A série junta as funções **Saúde e Saneamento**.\n"
    "- População de 2007, 2010, 2022 e 2023 interpolada (o IBGE não publicou estimativa nesses anos).\n"
    "- **Desvios** ficaram fora: exigem outra base (processos do TCU), que só cobre casos já julgados e "
    "com anos de atraso entre o desvio e o julgamento.\n"
    f"- Dados processados em {m['gerado_em'][:10]}."
))
