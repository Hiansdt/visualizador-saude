import pandas as pd
import streamlit as st

from saude_br.domain.geography import UF_NAME
from saude_br.domain.stats import cv_reading, modal_class, summarize
from saude_br.ui import charts
from saude_br.ui.data import by_uf, geojson, valid
from saude_br.ui.filters import get_filters
from saude_br.ui.fmt import br, md, value
from saude_br.ui.theme import PLOTLY_CONFIG

f = get_filters()
t = f.tema

# O que pintar no mapa: rótulo -> (coluna de by_uf, unidade, divergente?)
if t.key == "Gastos":
    LAYERS = {"Média por habitante": ("media", "R$", False), "Mediana por habitante": ("mediana", "R$", False),
              "CV entre os municípios": ("cv", "%", False)}
else:
    LAYERS = {"% de municípios com corte": ("pct_corte", "%", False), "Variação mediana": ("mediana", "%", True),
              "CV entre os municípios": ("cv", "%", False)}

st.title(f"{t.key} por estado em {f.ano}")
st.caption(f"{t.variavel}. Troque o tema e o ano na barra lateral.")

layer = st.segmented_control("Pintar o mapa por", list(LAYERS), default=list(LAYERS)[0], key=f"mapa_{t.key}") \
    or list(LAYERS)[0]
col, unit, diverging = LAYERS[layer]
uf = by_uf(t.key, f.ano)

left, right = st.columns([5, 4])
with left:
    st.plotly_chart(charts.uf_map(uf, geojson(), col, layer, unit, 1, diverging), width="stretch",
                    config=PLOTLY_CONFIG)
    top, bottom = uf.nlargest(1, col).iloc[0], uf.nsmallest(1, col).iloc[0]
    d = 0 if unit == "R$" else 1
    st.markdown(md(f"Maior: **{UF_NAME[top['cod_uf']]}** ({value(top[col], unit, d)}). "
                   f"Menor: **{UF_NAME[bottom['cod_uf']]}** ({value(bottom[col], unit, d)})."))

with right:
    scopes = ["Brasil"] + [f"{UF_NAME[c]} ({u})" for c, u in sorted(zip(uf["cod_uf"], uf["uf"]), key=lambda p: p[1])]
    scope = st.selectbox("Recorte do histograma e das medidas", scopes, key="mapa_recorte")
    data = valid(t.key).query("ano == @f.ano")
    if scope != "Brasil":
        data = data[data["uf"] == scope[-3:-1]]
    x = data[t.column]
    s = summarize(x.tolist(), t.decimals)
    m = modal_class(x.tolist())
    st.plotly_chart(charts.histogram(x, m, s.media, s.mediana, t.unit, 0 if t.unit == "R$" else 1),
                    width="stretch", config=PLOTLY_CONFIG)
    out = int((x > x.quantile(0.99)).sum())
    fine = pd.cut(x[x <= x.quantile(0.99)], 40).value_counts().idxmax()
    st.caption(md(f"Faixa azul: classe modal pelas {m.k} classes de Sturges, onde está a moda de Czuber. "
                  f"Nas barras finas o pico fica em ~{value(fine.mid, t.unit, 0 if t.unit == 'R$' else 1)}: "
                  "com dados assimétricos, a moda por classes depende da largura escolhida. O gráfico vai até "
                  f"o percentil 99 ({out} municípios acima dele ficam fora do desenho, não do cálculo)."))

    def vv(z, d=t.decimals):
        return value(z, t.unit, d)

    u2 = "(R$)²" if t.unit == "R$" else "(p.p.)²"
    rows = [
        ("n (municípios)", br(s.n), ""),
        ("Média", vv(s.media), ""),
        ("Mediana", vv(s.mediana), ""),
        ("Moda (Czuber)", vv(m.czuber), f"classe {vv(m.inferior, 0)} a {vv(m.superior, 0)}"),
        ("Amplitude", vv(s.amplitude), f"{vv(s.minimo)} a {vv(s.maximo)}"),
        (f"Variância {u2}", br(s.var_pop, 2), br(s.var_amostral, 2)),
        ("Desvio padrão", vv(s.dp_pop), vv(s.dp_amostral)),
        ("Coeficiente de variação", f"{br(s.cv_pop, 1)}%", f"{br(s.cv_amostral, 1)}% · {cv_reading(s.cv_amostral)}"),
    ]
    st.dataframe(pd.DataFrame(rows, columns=["Medida", "Valor (populacional)", "Amostral / detalhe"]),
                 hide_index=True, width="stretch")

st.caption("Gasto municipal (decisão de cada prefeitura) nas funções Saúde e Saneamento, corrigido pela inflação. "
           "Fora da análise: municípios que não informaram gasto e valores abaixo de 0,2× ou acima de 10× a "
           "mediana do ano.")
