import streamlit as st

from saude_br.sources import SOURCES
from saude_br.ui.data import csv_bytes, meta

m = meta()

st.title("Dados e método")
st.caption(f"Dados processados em {m['gerado_em'][:10]}. Valores reais em R$ de {m['ano_base']} (IPCA).")

st.subheader("Fontes")
for source in SOURCES.values():
    st.markdown(f"**[{source.name}]({source.url})** — {source.description}")

st.subheader("Como ler os números")
st.markdown(f"""
- **Despesa empenhada** da União na função 10 (Saúde): o valor que o governo se comprometeu a
  gastar no ano. Bate com o RREO do Tesouro (2020 e 2024 conferidos). Antes de 2015 o
  SIOP registra "liquidado" igual ao "empenhado", por isso usamos empenhado na série toda.
- **Valores reais**: corrigidos pela média anual do IPCA para reais de {m['ano_base']}.
- **Só gasto federal.** Estados e municípios também financiam o SUS; a coluna do Banco Mundial
  em `anual.csv` mostra o gasto público de todas as esferas, como contexto.
- **{m['ano_parcial']} é parcial**: acumulado até a data da coleta.
- **2016** é atribuído a Temer (interino desde 12/05, efetivo em 31/08).
- **Primeiro ano de cada governo** (2003, 2011, 2016, 2019, 2023) executa o orçamento enviado
  pelo antecessor.
- **Covid**: o desconto remove a ação 21C0. Parte das vacinas foi comprada pela ação regular
  de imunização (20YE) e continua contada.
- **Sem 1998–1999**: o SIOP começa em 2000.
- **Cortes**: "não executado" = autorizado − empenhado. É um indicador aproximado de bloqueio; o
  bloqueio oficial (contingenciamento) não está em dados abertos estruturados.
- **Desvios**: dano ao erário julgado pelo TCU em Tomadas de Contas Especiais da saúde, lido
  automaticamente dos acórdãos. É um piso: só o que foi descoberto, julgado e teve valor fixado.
""")

st.subheader("Baixar dados")
FILES = ("anual", "uf", "regiao", "subfuncao", "regionalizacao", "execucao", "acoes", "area",
         "desvios_casos", "desvios_ocorrencia")
cols = st.columns(5)
for i, name in enumerate(FILES):
    cols[i % 5].download_button(f"{name}.csv", csv_bytes(name), file_name=f"{name}.csv", mime="text/csv",
                        width="stretch")
