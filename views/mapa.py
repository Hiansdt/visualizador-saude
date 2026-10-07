import streamlit as st

from saude_br.config import BASE_YEAR, LAST_YEAR
from saude_br.ui import charts
from saude_br.ui.theme import PLOTLY_CONFIG
from saude_br.ui.data import geojson, table
from saude_br.ui.filters import get_filters

f = get_filters()

st.title("Para onde vai o dinheiro")

c1, c2, c3 = st.columns(3)
nivel = c1.segmented_control("Nível", ["Estados", "Regiões"], default="Estados", key="mapa_nivel")
modo = c2.segmented_control("Mostrar", ["Valor no ano", "Variação no período"], default="Valor no ano", key="mapa_modo")
medida = c3.segmented_control("Medida", ["Por habitante", "Total"], default="Por habitante", key="mapa_medida")
nivel, modo, medida = nivel or "Estados", modo or "Valor no ano", medida or "Por habitante"

col = "real_per_capita" if medida == "Por habitante" else "empenhado_real"
level = "uf" if nivel == "Estados" else "regiao"
df = table(level).rename(columns={"cod_uf" if level == "uf" else "cod_regiao": "cod"})
cobertura = table("regionalizacao").set_index("ano")


def fmt(v: float) -> str:
    return (f"R$ {v:,.0f}" if medida == "Por habitante" else f"R$ {v / 1e9:,.2f} bi").replace(",", ".")


if modo == "Valor no ano":
    ano = st.slider("Ano", f.start, f.end, value=f.end)
    if ano == LAST_YEAR:
        st.warning(f"{LAST_YEAR} está em andamento: valores parciais, acumulados até a data da coleta.")
    view = df[df["ano"] == ano].copy()
    view["texto"] = view[col].map(fmt)
    # DF concentra a folha e a sede do Ministério: fica fora da escala para não apagar o resto.
    others = view[view["cod"] != 53][col] if level == "uf" else view[col]
    rng = (others.min(), others.max())
    fig = charts.choropleth(view, geojson(level), col, ["nome", "texto"], range_=rng)
    value_label = f"{medida} (R$ de {BASE_YEAR})"
    pct = cobertura.loc[ano, "pct_regionalizado"]
    note_year = f"em {ano}"
else:
    end = min(f.end, LAST_YEAR - 1)  # variação só entre anos fechados
    if end <= f.start:
        st.info("Escolha um período com pelo menos dois anos fechados.")
        st.stop()
    a, b = df[df["ano"] == f.start], df[df["ano"] == end]
    view = a[["cod", "nome", col]].merge(b[["cod", col]], on="cod", suffixes=("_a", "_b"))
    view["var"] = 100 * (view[f"{col}_b"] / view[f"{col}_a"] - 1)
    view["texto"] = [f"{v:+.1f}% ({fmt(x)} → {fmt(y)})".replace(".", ",", 1)
                     for v, x, y in zip(view["var"], view[f"{col}_a"], view[f"{col}_b"])]
    lim = view.loc[view["cod"] != 53, "var"].abs().max() if level == "uf" else view["var"].abs().max()
    fig = charts.choropleth(view, geojson(level), "var", ["nome", "texto"], diverging=True, range_=(-lim, lim))
    col, value_label = "var", f"Variação real {f.start}→{end} (%)"
    pct = cobertura.loc[[f.start, end], "pct_regionalizado"].min()
    note_year = f"em {f.start}/{end}"

left, right = st.columns([3, 2])
with left:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
with right:
    ranked = view.sort_values(col, ascending=False)
    scale = 1e9 if col == "empenhado_real" else 1
    ranked["valor"] = ranked[col] / scale
    unit = " bi" if scale == 1e9 else ""
    if modo == "Valor no ano":
        column = st.column_config.ProgressColumn(
            value_label + unit, format="%.2f" if scale == 1e9 else "%.0f",
            min_value=0.0, max_value=float(ranked["valor"].max()))
    else:
        column = st.column_config.NumberColumn(value_label, format="%+.1f%%")
    st.dataframe(ranked[["nome", "valor"]], hide_index=True, width="stretch", height=560,
                 column_config={"nome": st.column_config.TextColumn(nivel), "valor": column})

st.caption(
    f"Só {pct:.0f}% do gasto federal em saúde {note_year} tem localizador de estado ou região; "
    "o restante é \"Nacional\" e não aparece no mapa. O localizador indica onde o gasto foi "
    "programado, não necessariamente quem foi atendido. O Distrito Federal concentra a folha e a "
    "sede do Ministério da Saúde, por isso fica fora da escala de cores (aparece saturado) no modo por estado. "
    "O desconto da Covid não se aplica ao mapa."
)
