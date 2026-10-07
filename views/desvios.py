import streamlit as st

from saude_br.config import BASE_YEAR, LAST_YEAR
from saude_br.ui import charts
from saude_br.ui.data import table
from saude_br.ui.filters import get_filters
from saude_br.ui.theme import PLOTLY_CONFIG

f = get_filters()
casos = table("desvios_casos")
ocorr = table("desvios_ocorrencia")
julg = table("desvios_julgamento")
anual = table("anual").set_index("ano")

st.title("Desvios de verbas da saúde")
st.caption(
    "Dinheiro federal da saúde que o Tribunal de Contas da União (TCU) mandou devolver, em processos de "
    "Tomada de Contas Especial julgados irregulares. Valores originais do dano, corrigidos pela inflação "
    f"(R$ de {BASE_YEAR}), sem juros."
)

if casos.empty:
    st.info("Dados do TCU ainda não processados. Rode `uv run python -m saude_br.pipeline --only tcu`.")
    st.stop()

sel = casos[casos["ano_ocorrencia"].between(f.start, f.end)]
total = sel["valor_real"].sum()
saude = (anual.loc[f.start:f.end, "empenhado_real"]).sum()
lag = casos["defasagem"].median()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Dano julgado", f"R$ {total / 1e6:,.0f} mi".replace(",", "."), border=True)
c2.metric("Casos (processos)", f"{len(sel):,}".replace(",", "."), border=True)
c3.metric("Do gasto federal em saúde", f"{100 * total / saude:.3f}%".replace(".", ",") if saude else "—", border=True,
          help="Dano julgado dividido pelo gasto federal em saúde no mesmo período.")
c4.metric("Tempo até o julgamento", f"{lag:.0f} anos (mediana)", border=True,
          help="Do primeiro débito até o acórdão, em todos os casos.")

by = st.segmented_control("Contar pelo ano", ["da ocorrência", "do julgamento"], default="da ocorrência",
                          key="desvios_eixo") or "da ocorrência"
x = "ano_ocorrencia" if by == "da ocorrência" else "ano_julgamento"
d = (ocorr if by == "da ocorrência" else julg).pipe(lambda t: t[t[x].between(f.start, f.end)])
if d.empty:
    st.info("Nenhum caso julgado no período escolhido.")
elif by == "da ocorrência":
    pct = d.drop_duplicates("ano_ocorrencia").set_index("ano_ocorrencia")["pct_ja_julgado_estimado"]
    fig = charts.desvio_bars(d, "ano_ocorrencia", censored=pct.to_dict())
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)
    recent = pct[pct < 70]
    if not recent.empty:
        st.caption(
            f"Os anos apagados ainda estão em julgamento: pelo histórico, só cerca de "
            f"{recent.iloc[0]:.0f}% dos casos ocorridos em {recent.index[0]} já teriam sido julgados até "
            f"{LAST_YEAR}. A queda no fim da série é atraso do julgamento, não menos desvio."
        )
else:
    st.plotly_chart(charts.desvio_bars(d, "ano_julgamento"), width="stretch", config=PLOTLY_CONFIG)
    st.caption("Pelo ano do julgamento a série é completa, mas mistura desvios de governos anteriores: "
               f"o TCU leva em média {lag:.0f} anos para julgar.")

left, right = st.columns([2, 3])
with left:
    st.subheader("Por estado")
    uf = sel.dropna(subset=["uf"]).groupby("uf", as_index=False)["valor_real"].sum().nlargest(15, "valor_real")
    if not uf.empty:
        st.plotly_chart(charts.uf_bars(uf), width="stretch", config=PLOTLY_CONFIG)
    if len(sel):
        st.caption(f"{sel['uf'].isna().mean():.0%} dos casos sem UF identificável no nome da entidade.")
with right:
    st.subheader("Maiores casos")
    top = sel.nlargest(15, "valor_real")[["entidade", "uf", "ano_ocorrencia", "origem", "categoria",
                                          "valor_real", "acordao"]].copy()
    top["valor_real"] = top["valor_real"] / 1e6
    st.dataframe(top, hide_index=True, width="stretch", height=480, column_config={
        "entidade": "Entidade", "uf": "UF", "ano_ocorrencia": st.column_config.NumberColumn("Ocorrência", format="%d"),
        "origem": "Dinheiro de", "categoria": "Tipo",
        "valor_real": st.column_config.NumberColumn(f"R$ mi de {BASE_YEAR}", format="%.1f"),
        "acordao": "Acórdão do TCU",
    })

with st.expander("Como ler estes números"):
    st.markdown(f"""
- **É um piso, não o total desviado.** Só entra o que virou processo no TCU, foi julgado irregular e
  teve o valor do dano escrito no acórdão. Fraudes não descobertas, casos arquivados e processos na
  Justiça comum não aparecem.
- **Quem desviou, em geral, não foi o governo federal.** Quase todos os casos são verbas federais
  repassadas a prefeituras, estados e entidades e mal aplicadas lá. As faixas de presidente são
  só contexto de época.
- **Nem tudo é roubo.** "Omissão ou não comprovação" = o gestor não prestou contas ou não provou o
  uso do dinheiro. "Indícios de desvio ou fraude" = o resumo do acórdão fala em desvio, fraude,
  superfaturamento, empresa de fachada etc.
- **Funasa × FNS.** Muitos casos da Funasa são convênios de saneamento (módulos sanitários, água),
  não atendimento de saúde.
- **Método.** Acórdãos do TCU de {casos['ano_julgamento'].min()} a {casos['ano_julgamento'].max()},
  lidos automaticamente: entram os que julgam contas irregulares e condenam a devolver dinheiro ao
  Fundo Nacional de Saúde, à Funasa ou ao Ministério da Saúde. Um caso por processo (recursos não
  contam de novo). Valores de antes de {f.start if f.start > 2000 else 2000} ficam de fora.
  Nomes de pessoas não são guardados.
""")
