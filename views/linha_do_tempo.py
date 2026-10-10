import math

import streamlit as st

from saude_br.domain.stats import cv_reading, modal_class, summarize
from saude_br.ui import charts
from saude_br.ui.data import valid, yearly
from saude_br.ui.filters import get_filters
from saude_br.ui.fmt import br, md, value
from saude_br.ui.theme import PLOTLY_CONFIG

f = get_filters()
t = f.tema
yr = yearly(t.key)
first, last = yr.iloc[0], yr.iloc[-1]
y0, y1 = int(first["Ano"]), int(last["Ano"])
u2 = "(R$)²" if t.unit == "R$" else "(p.p.)²"

# Medida -> (séries [(coluna, rótulo)], unidade do gráfico)
GROUPS = {
    "Média, mediana e moda": ([("Média", "Média"), ("Mediana", "Mediana"), ("Moda (Czuber)", "Moda (Czuber)")], t.unit),
    "Amplitude": ([("Amplitude", "Amplitude")], t.unit),
    "Variância": ([("Variância pop.", "Populacional"), ("Variância amostral", "Amostral")], ""),
    "Desvio padrão": ([("DP pop.", "Populacional"), ("DP amostral", "Amostral")], t.unit),
    "Coeficiente de variação": ([("CV pop. (%)", "Populacional"), ("CV amostral (%)", "Amostral")], "%"),
    "Municípios (n)": ([("n", "n")], ""),
}
if t.key == "Cortes":
    GROUPS = {"% de municípios com corte": ([("% com corte", "% com corte")], "%"), **GROUPS}

if t.key == "Gastos":
    st.title("Quanto os municípios gastam com saúde por habitante?")
else:
    st.title("Quantos municípios cortaram o gasto com saúde?")
st.caption(f"{t.variavel}. Cada ponto resume os ~5.000 municípios válidos do ano.")

group = st.segmented_control("Medida", list(GROUPS), default=list(GROUPS)[0], key=f"lt_medida_{t.key}") \
    or list(GROUPS)[0]
series, unit = GROUPS[group]
st.plotly_chart(charts.stat_timeline(yr, series, unit, t.decimals if unit else 0, ano=f.ano),
                width="stretch", config=PLOTLY_CONFIG)


# --- Leitura do gráfico (calculada a partir dos dados) -----------------------
def v(x, u=t.unit, d=t.decimals):
    return value(x, u, d)


row = yr.set_index("Ano")
if group == "% de municípios com corte":
    s = row["% com corte"]
    reading = (f"Em média, {br(s.mean(), 0)}% dos municípios cortam por ano. O pior ano foi **{s.idxmax()}** "
               f"({br(s.max(), 0)}%) e o melhor, **{s.idxmin()}** ({br(s.min(), 0)}%).")
elif group == "Média, mediana e moda":
    above = int((row["Média"] > row["Mediana"]).sum())
    reading = (f"A média foi de **{v(first['Média'])}** em {y0} para **{v(last['Média'])}** em {y1}. "
               f"A média ficou acima da mediana em **{above} de {len(row)}** anos: alguns municípios "
               "com valores altos puxam a média para cima.")
elif group == "Amplitude":
    reading = (f"Distância entre o maior e o menor valor: **{v(first['Amplitude'])}** em {y0}, "
               f"**{v(last['Amplitude'])}** em {y1}. Depende só de dois municípios extremos, por isso "
               "varia muito e engana sozinha.")
elif group == "Variância":
    n = int(row.loc[f.ano, "n"])
    reading = (f"Em {u2}, difícil de ler diretamente. Com n = {br(n)} municípios em {f.ano}, a amostral "
               f"(÷ n − 1) é só {br(100 * (n / (n - 1) - 1), 3)}% maior que a populacional (÷ n).")
elif group == "Desvio padrão":
    reading = (f"Desvio padrão populacional: **{v(first['DP pop.'])}** em {y0}, **{v(last['DP pop.'])}** em {y1}. "
               "É a distância típica de um município até a média, na mesma unidade dos dados.")
elif group == "Coeficiente de variação":
    reading = (f"CV populacional: **{br(first['CV pop. (%)'], 1)}%** em {y0} ({cv_reading(first['CV pop. (%)'])}) "
               f"e **{br(last['CV pop. (%)'], 1)}%** em {y1} ({cv_reading(last['CV pop. (%)'])}). "
               + ("O CV compara a dispersão com a média: dá para comparar anos com níveis de gasto diferentes."
                  if t.key == "Gastos" else
                  "Aqui a média é pequena perto do desvio padrão, então o CV fica enorme e instável: "
                  "o CV só funciona bem quando a média é bem maior que zero."))
else:
    reading = f"Entre {br(row['n'].min())} e {br(row['n'].max())} municípios válidos por ano."
st.markdown(md(reading))
st.caption("Faixas: mandato presidencial da época (contexto; o gasto é decidido por cada prefeitura).")

with st.expander("Tabela com todas as medidas, por ano"):
    show = yr.copy()
    st.dataframe(show, hide_index=True, width="stretch", column_config={
        "Ano": st.column_config.NumberColumn(format="%d"),
        **{c: st.column_config.NumberColumn(format="%.2f") for c in show.columns if c not in ("Ano", "n")},
    })
    st.download_button("Baixar (CSV)", show.to_csv(index=False).encode(), f"medidas_{t.key.lower()}.csv", "text/csv")


# --- Passo a passo -----------------------------------------------------------
def tex(x, d=t.decimals):
    return br(x, d).replace(",", "{,}")


with st.expander(f"Passo a passo do cálculo — {f.ano} (troque o ano na barra lateral)"):
    x = valid(t.key).query("ano == @f.ano")[t.column]
    s = summarize(x.tolist(), t.decimals)
    m = modal_class(x.tolist())
    n, total, sq = s.n, x.sum(), ((x - s.media) ** 2).sum()
    st.markdown(md(f"**n = {br(n)}** municípios válidos em {f.ano}. Menor valor {v(s.minimo)}, maior {v(s.maximo)}."))
    st.latex(rf"\bar{{x}} = \frac{{\sum x_i}}{{n}} = \frac{{{tex(total)}}}{{{br(n)}}} = {tex(s.media)}")
    pos = (f"o valor da posição {(n + 1) // 2}" if n % 2 else f"a média das posições {n // 2} e {n // 2 + 1}")
    st.markdown(md(f"**Mediana:** com os {br(n)} valores em ordem, {pos} = **{v(s.mediana)}**."))
    k_exact = br(1 + 3.322 * math.log10(n), 2)
    st.markdown(md(f"**Moda:** valores contínuos quase nunca se repetem, então usamos classes. Sturges: "
                   f"k = 1 + 3,322·log₁₀({br(n)}) ≈ {k_exact} → **{m.k} classes** de largura "
                   f"h = amplitude ÷ k = {v(m.largura)}. Classe modal: **{v(m.inferior)} a {v(m.superior)}** "
                   f"({br(m.frequencia)} municípios)."))
    d1, d2 = m.frequencia - m.freq_anterior, m.frequencia - m.freq_posterior
    st.latex(rf"Mo = L_i + h \cdot \frac{{d_1}}{{d_1 + d_2}} = {tex(m.inferior)} + {tex(m.largura)} \cdot "
             rf"\frac{{{d1}}}{{{d1} + {d2}}} = {tex(m.czuber)}")
    st.latex(rf"\text{{Amplitude}} = x_{{máx}} - x_{{mín}} = {tex(s.maximo)} - ({tex(s.minimo)}) = {tex(s.amplitude)}")
    st.latex(rf"\sigma^2 = \frac{{\sum (x_i - \bar{{x}})^2}}{{n}} = \frac{{{tex(sq)}}}{{{br(n)}}} = {tex(s.var_pop)}"
             rf"\qquad s^2 = \frac{{\sum (x_i - \bar{{x}})^2}}{{n - 1}} = \frac{{{tex(sq)}}}{{{br(n - 1)}}} = {tex(s.var_amostral)}")
    st.latex(rf"\sigma = \sqrt{{\sigma^2}} = {tex(s.dp_pop)} \qquad s = \sqrt{{s^2}} = {tex(s.dp_amostral)}")
    st.latex(rf"CV_{{pop}} = \frac{{\sigma}}{{\bar{{x}}}} \times 100 = {tex(s.cv_pop, 1)}\% \qquad "
             rf"CV_{{amostral}} = \frac{{s}}{{\bar{{x}}}} \times 100 = {tex(s.cv_amostral, 1)}\%")
    st.caption("Populacional (÷ n): os municípios do ano são praticamente todos os do país, então é a fórmula "
               "adequada. Amostral (÷ n − 1): trata os dados como amostra; com n tão grande a diferença some.")
