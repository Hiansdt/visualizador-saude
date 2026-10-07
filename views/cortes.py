import pandas as pd
import streamlit as st

from saude_br.config import BASE_YEAR
from saude_br.ui import charts
from saude_br.ui.data import table
from saude_br.ui.filters import get_filters
from saude_br.ui.theme import NEG, PLOTLY_CONFIG, palette

TOP_AREAS = 8
MIN_BASE = 50e6  # só ações com pelo menos R$ 50 mi no ano anterior entram no ranking
# 2004: repasses ao SUS rotulados como encargos/transferências (ver Composição).
QUIRK_YEARS, QUIRK_SUBS = {2004, 2005}, {"301", "302", "845", "846"}
# Programas com o mesmo código de ação ao longo da janela mostrada; o ano
# inicial pula o ano de criação do código, quando ele ainda recebe quase nada.
PROGRAMS = {
    "Atenção Primária (piso, 219A)": ("219A", 2018),
    "Média e Alta Complexidade (8585)": ("8585", 2005),
    "Farmácia Popular (20YR)": ("20YR", 2013),
    "Vacinas e imunobiológicos (20YE)": ("20YE", 2013),
    "Medicamentos especializados (4705)": ("4705", 2003),
    "Saúde indígena (20YP)": ("20YP", 2013),
}
# TODO(program-stitching): build continuous series for programs whose action code changed (e.g. PAB 8577/20AD -> 219A in 2018, Mais Médicos 214U and successors)
# WHY: SIOP ação codes are recreated at each PPA restructuring; stitching needs a curated code map per program.
# DONE-WHEN: `uv run pytest -k program_stitching` passes a test asserting the primary-care series has no gap between 2005 and 2025

f = get_filters()
st.title("Cortes")
st.caption(f"Valores corrigidos pela inflação (IPCA), em reais de {BASE_YEAR}. Só anos fechados.")

tab_exec, tab_area, tab_rank, tab_prog = st.tabs(
    ["Orçado × executado", "Por área do SUS", "Maiores cortes do ano", "Programas"])

with tab_exec:
    ex = f.closed(table("execucao"))
    st.subheader("Quanto do orçamento autorizado foi usado")
    st.plotly_chart(charts.execution_lines(ex), width="stretch", config=PLOTLY_CONFIG)
    left, right = st.columns(2)
    with left:
        st.markdown("**Não executado** — autorizado mas não empenhado (% do autorizado)")
        st.plotly_chart(charts.share_bars(ex, "nao_executado_pct", "não executado", NEG),
                        width="stretch", config=PLOTLY_CONFIG)
        st.caption("Mostra dinheiro bloqueado ou simplesmente não usado. É um indicador aproximado: "
                   "quando o bloqueio vira cancelamento da dotação, o autorizado cai e a diferença some.")
    with right:
        st.markdown("**Congresso × proposta do governo** — orçamento aprovado vs projeto enviado (%)")
        st.plotly_chart(charts.share_bars(ex, "congresso_pct", "acima da proposta", palette()["series"][0]),
                        width="stretch", config=PLOTLY_CONFIG)
        peak = ex.loc[ex["congresso_pct"].idxmax()]
        st.caption("Acima de zero = o Congresso aprovou mais do que o Executivo propôs (emendas, "
                   f"remanejamentos). Maior diferença no período: {int(peak['ano'])}, "
                   f"{peak['congresso_pct']:+.0f}% sobre o projeto enviado no ano anterior.")
    # TODO(bloqueio-oficial): replace the "não executado" proxy with official contingency blocks for the Health Ministry
    # WHY: SIOP SPARQL has no blocked-appropriation field; blocks are published only in the bimonthly RARDP report annexes.
    # DONE-WHEN: `uv run python -m saude_br.pipeline && head -1 data/processed/execucao.csv | grep -c bloqueado` prints 1
    # TODO(rap-cancelados): add cancelled "restos a pagar" for health spending
    # WHY: SICONFI RREO for the União has no health-specific annex (Anexo 12) with cancelled RAP.
    # DONE-WHEN: `uv run python -m saude_br.pipeline && head -1 data/processed/execucao.csv | grep -c rap_cancelado` prints 1

with tab_area:
    area = f.closed(table("area"))
    col = "emp_real_sem_covid" if f.sem_covid else "emp_real"
    area["subfuncao"] = area["subfuncao"].astype(str)
    top = area.groupby("nome")[col].sum().nlargest(TOP_AREAS).index
    wide = area[area["nome"].isin(top)].pivot_table(index="nome", columns="ano", values=col, aggfunc="sum")
    wide = wide.loc[top]
    yoy = (100 * wide.pct_change(axis=1)).iloc[:, 1:]
    codes = area.drop_duplicates("nome").set_index("nome")["subfuncao"]
    masked = pd.DataFrame(
        [[codes[n] in QUIRK_SUBS and y in QUIRK_YEARS for y in yoy.columns] for n in yoy.index],
        index=yoy.index, columns=yoy.columns)
    st.subheader("Variação real ano a ano, por área")
    st.caption("Vermelho = corte em relação ao ano anterior. "
               + ("Sem o gasto emergencial Covid. " if f.sem_covid else "Inclui o gasto Covid (ligue o desconto na barra lateral). ")
               + "\\* = 2004/2005: mudança de classificação no orçamento, não comparável.")
    if yoy.shape[1]:
        st.plotly_chart(charts.area_heatmap(yoy.round(1), masked), width="stretch", config=PLOTLY_CONFIG)
    else:
        st.info("Escolha um período com pelo menos dois anos fechados.")

with tab_rank:
    acoes = table("acoes")
    acoes["acao"] = acoes["acao"].astype(str)
    years = sorted(y for y in acoes["ano"].unique() if f.start < y <= min(f.end, acoes["ano"].max() - 1))
    if not years:
        st.info("Escolha um período com pelo menos dois anos fechados.")
    else:
        year = st.select_slider("Ano", years, value=years[-1], key="cortes_ano")
        prev = acoes[acoes["ano"] == year - 1].set_index("acao")
        cur = acoes[acoes["ano"] == year].set_index("acao")
        both = prev.index.intersection(cur.index).drop("21C0", errors="ignore")
        d = pd.DataFrame({
            "nome": cur.loc[both, "nome"],
            "antes": prev.loc[both, "emp_real"],
            "depois": cur.loc[both, "emp_real"],
            "emenda": cur.loc[both, "emenda"],
        })
        d = d[d["antes"] >= MIN_BASE]
        d["queda_mi"] = (d["antes"] - d["depois"]) / 1e6
        d["var_pct"] = 100 * (d["depois"] / d["antes"] - 1)
        d = d[d["queda_mi"] > 0].nlargest(12, "queda_mi")
        d["rotulo"] = [f"{n[:48]}… ({c})" if len(n) > 48 else f"{n} ({c})" for n, c in zip(d["nome"], d.index)]
        st.subheader(f"Ações com maior queda real, {year - 1} → {year}")
        if d.empty:
            st.success("Nenhuma ação relevante teve queda real nesse ano.")
        else:
            st.plotly_chart(charts.drop_bars(d), width="stretch", config=PLOTLY_CONFIG)
            view = d.reset_index()[["acao", "nome", "antes", "depois", "var_pct", "emenda"]]
            view[["antes", "depois"]] = view[["antes", "depois"]] / 1e6
            st.dataframe(view, hide_index=True, width="stretch", column_config={
                "acao": "Ação", "nome": "Nome",
                "antes": st.column_config.NumberColumn(f"{year - 1} (R$ mi)", format="%.0f"),
                "depois": st.column_config.NumberColumn(f"{year} (R$ mi)", format="%.0f"),
                "var_pct": st.column_config.NumberColumn("Variação", format="%+.1f%%"),
                "emenda": st.column_config.CheckboxColumn("Emenda?"),
            })
        notes = ["Só ações com o mesmo código nos dois anos e pelo menos R$ 50 mi no ano anterior; "
                 "a ação Covid (21C0) fica de fora.",
                 "\"Emenda?\" marca ações de custeio que recebem emendas parlamentares: oscilam com as "
                 "emendas, não com a política do Ministério."]
        if year == 2018:
            notes.insert(0, "⚠️ 2018: o financiamento da atenção básica foi reorganizado em ações novas; "
                            "quedas nas ações antigas não são cortes.")
        st.caption(" ".join(notes))

with tab_prog:
    acoes = table("acoes")
    acoes["acao"] = acoes["acao"].astype(str)
    acoes = f.closed(acoes)
    series = {name: acoes[(acoes["acao"] == code) & (acoes["ano"] >= first)].sort_values("ano")
              for name, (code, first) in PROGRAMS.items()}
    series = {k: v for k, v in series.items() if not v.empty}
    st.subheader("Programas do SUS")
    st.caption("Cada gráfico tem sua escala. Cada programa aparece só nos anos em que existe com o "
               "mesmo código de ação (programas recriados com código novo não são emendados). "
               "O pico de vacinas em 2021–2022 é a compra de vacinas Covid.")
    if series:
        st.plotly_chart(charts.program_multiples(series, f.start, min(f.end, acoes["ano"].max())),
                        width="stretch", config=PLOTLY_CONFIG)
