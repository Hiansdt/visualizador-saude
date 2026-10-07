import pandas as pd
import streamlit as st

from saude_br.config import BASE_YEAR
from saude_br.domain.governments import TERMS, term_for
from saude_br.domain.metrics import METRICS
from saude_br.domain.stats import cv_reading, summarize
from saude_br.ui import charts
from saude_br.ui.data import table
from saude_br.ui.filters import get_filters
from saude_br.ui.theme import PLOTLY_CONFIG

f = get_filters()


def _br(v: float | None, d: int) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _tex(v: float, d: int) -> str:
    return _br(v, d).replace(",", "{,}")


def _variables() -> dict[str, tuple]:
    """nome -> (série ano/valor, unidade, casas decimais)."""
    anual = table("anual")
    out = {}
    for m in METRICS.values():
        unit = {"R$": "R$", "bi": "R$ bi", "%": "%"}[m.unit]
        out[m.label] = (anual[["ano"]].assign(valor=anual[m.col(f.sem_covid)] / m.scale), unit, max(m.decimals, 1))
    ex = table("execucao")
    out["Não executado (% do autorizado)"] = (ex[["ano"]].assign(valor=ex["nao_executado_pct"]), "%", 1)
    oc = table("desvios_ocorrencia")
    if not oc.empty:
        # Só anos de ocorrência em que a maior parte dos casos já foi julgada.
        oc = oc[oc["pct_ja_julgado_estimado"] >= 70]
        d = oc.groupby("ano_ocorrencia", as_index=False)["valor_real"].sum()
        out[f"Dano julgado pelo TCU (R$ mi de {BASE_YEAR}, ano da ocorrência)"] = (
            pd.DataFrame({"ano": d["ano_ocorrencia"], "valor": d["valor_real"] / 1e6}), "R$ mi", 1)
    return out


st.title("Estatística descritiva")
st.caption("Medidas de posição e de dispersão sobre os dados do app. Cada ano é uma observação. "
           f"Período {f.start}–{f.end} da barra lateral; o ano em andamento fica de fora.")

variables = _variables()
c1, c2, c3 = st.columns([3, 2, 2])
var = c1.selectbox("Variável", list(variables), key="est_var")
transform = c2.segmented_control("Usar", ["Valor do ano", "Variação ano a ano"], default="Valor do ano",
                                 key="est_transf") or "Valor do ano"
group_by = c3.segmented_control("Agrupar por", ["Período todo", "Presidente", "Mandato"],
                                default="Período todo", key="est_grupo") or "Período todo"

series, unit, dec = variables[var]
series = series.dropna().sort_values("ano")
if transform == "Variação ano a ano":
    series = series.assign(valor=100 * series["valor"].pct_change()).dropna()
    unit, dec = "%", 1
data = f.closed(series).copy()
if data.empty:
    st.info("Sem dados para esta variável no período escolhido.")
    st.stop()

data["presidente"] = data["ano"].map(lambda y: term_for(int(y)).president)
data["mandato"] = data["ano"].map(lambda y: term_for(int(y)).key)
order = {"Presidente": list(dict.fromkeys(t.president for t in TERMS)), "Mandato": [t.key for t in TERMS]}
if group_by == "Período todo":
    data["grupo"] = f"{int(data['ano'].min())}–{int(data['ano'].max())}"
else:
    data["grupo"] = data["presidente" if group_by == "Presidente" else "mandato"]
groups = [g for g in order.get(group_by, [data["grupo"].iloc[0]]) if g in set(data["grupo"])]
summaries = {g: summarize(data.loc[data["grupo"] == g, "valor"].tolist(), dec) for g in groups}

# --- Tabela ---------------------------------------------------------------
u2 = f"({unit})²" if unit != "%" else "(p.p.)²"
rows = []
for g, s in summaries.items():
    rows.append({
        "Grupo": g, "n": s.n,
        "Média": _br(s.media, dec), "Mediana": _br(s.mediana, dec),
        "Moda": ", ".join(_br(m, dec) for m in s.moda) if s.moda else "amodal",
        "Mínimo": _br(s.minimo, dec), "Máximo": _br(s.maximo, dec), "Amplitude": _br(s.amplitude, dec),
        f"Variância pop. {u2}": _br(s.var_pop, 2), f"Variância amostral {u2}": _br(s.var_amostral, 2),
        "DP pop.": _br(s.dp_pop, dec), "DP amostral": _br(s.dp_amostral, dec),
        "CV pop. (%)": _br(s.cv_pop, 1), "CV amostral (%)": _br(s.cv_amostral, 1),
        "Dispersão (CV amostral)": cv_reading(s.cv_amostral),
    })
summary_df = pd.DataFrame(rows)
st.subheader(f"{var}" + (" — variação ano a ano" if transform != "Valor do ano" else ""))
st.caption(f"Unidade: {unit}. Variância na unidade ao quadrado. DP = desvio padrão; CV = coeficiente de "
           "variação (DP ÷ média). Grupos com 1 ano não têm medidas amostrais (n − 1 = 0).")
st.dataframe(summary_df, hide_index=True, width="stretch")
st.download_button("Baixar tabela (CSV)", summary_df.to_csv(index=False).encode(), "estatisticas.csv", "text/csv")

# --- Gráfico --------------------------------------------------------------
if group_by == "Período todo":
    s = summaries[groups[0]]
    st.plotly_chart(charts.series_with_mean(data, s.media, s.dp_pop, unit), width="stretch", config=PLOTLY_CONFIG)
    st.caption("Barras: valor de cada ano. Linha: média. Faixa cinza: média ± 1 desvio padrão (populacional).")
else:
    st.plotly_chart(charts.group_dots(data, groups, {g: s.media for g, s in summaries.items()}, unit),
                    width="stretch", config=PLOTLY_CONFIG)
    st.caption("Cada ponto é um ano; o traço é a média do grupo. Grupos espalhados = maior desvio padrão.")

# --- Passo a passo --------------------------------------------------------
with st.expander("Passo a passo do cálculo"):
    g = st.selectbox("Grupo", groups, key="est_passo") if len(groups) > 1 else groups[0]
    s = summaries[g]
    d = data[data["grupo"] == g][["ano", "valor"]].copy()
    d["desvio"] = d["valor"] - s.media
    d["desvio²"] = d["desvio"] ** 2
    show = d.assign(**{c: d[c].map(lambda v, k=c: _br(v, 2 if k == "desvio²" else dec)) for c in ("valor", "desvio", "desvio²")})
    show.columns = ["Ano", "xᵢ", "xᵢ − x̄", "(xᵢ − x̄)²"]
    st.dataframe(show, hide_index=True, width="stretch")
    total, sq, n = d["valor"].sum(), d["desvio²"].sum(), s.n
    ordered = ", ".join(_br(v, dec) for v in sorted(d["valor"]))
    st.markdown(f"**n = {n}** · valores em ordem: {ordered}")
    st.latex(rf"\bar{{x}} = \frac{{\sum x_i}}{{n}} = \frac{{{_tex(total, dec)}}}{{{n}}} = {_tex(s.media, dec)}")
    pos = f"o valor central (posição {(n + 1) // 2})" if n % 2 else f"a média dos valores nas posições {n // 2} e {n // 2 + 1}"
    st.markdown(f"**Mediana** = {pos} da lista ordenada = **{_br(s.mediana, dec)}**")
    st.markdown("**Moda** = " + (", ".join(_br(m, dec) for m in s.moda) + " (valor que mais se repete)"
                                if s.moda else "amodal — nenhum valor se repete (comum em dados contínuos)"))
    st.latex(rf"\text{{Amplitude}} = x_{{máx}} - x_{{mín}} = {_tex(s.maximo, dec)} - {_tex(s.minimo, dec)} = {_tex(s.amplitude, dec)}")
    st.latex(rf"\sigma^2 = \frac{{\sum (x_i - \bar{{x}})^2}}{{n}} = \frac{{{_tex(sq, 2)}}}{{{n}}} = {_tex(s.var_pop, 2)}"
             rf"\qquad \sigma = \sqrt{{\sigma^2}} = {_tex(s.dp_pop, dec)}")
    if s.var_amostral is not None:
        st.latex(rf"s^2 = \frac{{\sum (x_i - \bar{{x}})^2}}{{n - 1}} = \frac{{{_tex(sq, 2)}}}{{{n - 1}}} = {_tex(s.var_amostral, 2)}"
                 rf"\qquad s = \sqrt{{s^2}} = {_tex(s.dp_amostral, dec)}")
    if s.cv_pop is not None:
        cv_am = rf"\qquad CV_{{amostral}} = \frac{{s}}{{\bar{{x}}}} \times 100 = {_tex(s.cv_amostral, 1)}\%" if s.cv_amostral is not None else ""
        st.latex(rf"CV_{{pop}} = \frac{{\sigma}}{{\bar{{x}}}} \times 100 = {_tex(s.cv_pop, 1)}\%" + cv_am)
    st.caption("Populacional (÷ n): os anos do grupo são todos os dados que interessam. Amostral (÷ n − 1): "
               "os anos são vistos como amostra de um processo maior; corrige o viés de estimar a variância "
               "a partir de poucos dados. Leitura usual do CV: até 15% baixa, 15–30% média, acima de 30% alta dispersão.")
