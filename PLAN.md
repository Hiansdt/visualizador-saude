ROUTE: inline
size:     ~10 files, 3 layers (source → build → 2 pages), 1 repo
frozen:   yes — built on branch `municipios`; numbers below confirmed against data/processed
streams:  none — both pages read the same municipal dataset

# Plano — Gastos e cortes municipais em saúde (2002–2025)

Tema da disciplina: *Gastos, cortes e desvios de dinheiro público relacionado à saúde no Brasil*.
Escopo: **gastos** e **cortes**. **Desvios** ficam fora, com uma frase de justificativa na fala 1:
exigem outra base (processos do TCU), que só cobre casos já julgados e com anos de atraso.

## Pergunta e conclusão

**Pergunta:** quanto os municípios brasileiros gastam com saúde por habitante, quão desigual é esse
gasto, e quando e onde houve cortes?

**Conclusão:** o gasto real por habitante quase quadruplicou (média R$ 560 → R$ 2.081, 2002–2025),
mas a maioria dos municípios gasta abaixo da média (mediana R$ 1.869). A distância absoluta entre
municípios cresceu (desvio padrão R$ 311 → R$ 898), mas a relativa caiu (CV 55,4% → 43,2%).
Em média, 1 em cada 3 municípios corta o gasto real a cada ano; em 2015 foram 73%, e em 2020
(dinheiro da Covid) só 9%.

## Dados (unidade = município × ano, ~130 mil linhas)

- **Gasto:** IPEA `DFSAUSM` (Tesouro/STN), despesa empenhada municipal nas funções Saúde + Saneamento, R$ nominais.
- **População:** IPEA `ESTIMA_PO` (IBGE). 2007, 2010, 2022 e 2023 sem estimativa → interpolação por município.
- **Inflação:** IPCA (BCB) → reais de 2025. **Mapa:** malha de UFs do IBGE.
- **Regras, mostradas no app:** anos 2002–2025 (em 2002 muda a classificação orçamentária e o nível
  salta); fora gasto ≤ 0 (não informou); fora valores abaixo de 0,2× ou acima de 10× a mediana do
  ano (~0,8% das linhas); n de cada ano visível.
- **Corte** = gasto real por habitante menor que no ano anterior, no mesmo município (os dois anos válidos).
- **Ressalvas na tela:** gasto municipal (decisão do prefeito; presidentes só como contexto
  histórico); saúde e saneamento somados nesta série.

## Build (branch `municipios`)

1. `saude_br/sources/ipea.py` — `Source` que baixa as duas séries e guarda só os municípios (código, ano, valor).
2. `saude_br/build.py::build_municipios` → `data/processed/municipios.csv` (gasto real por habitante,
   variação real anual, corte, motivo de exclusão, UF, presidente). Teste de regressão: média 2002 ≈ 560,
   CV 2025 ≈ 43; n ≥ 1000 em todo ano.
3. `saude_br/domain/stats.py` — classe modal (Sturges) e moda de Czuber; teste com exemplo resolvido à mão.
4. Páginas (remover as demais e as fontes federais deste branch):
   - `views/linha_do_tempo.py`: tema (Gastos/Cortes) e medida; série anual com faixas de presidente;
     tabela das 7 medidas por ano; passo a passo do ano escolhido.
   - `views/mapa.py`: tema e ano; mapa por UF; histograma com classe modal, mediana e média; painel
     com as 7 medidas para Brasil ou UF.
5. AppTest em todas as combinações; conferir no Chrome; commit.

## Apresentação

Roteiro completo (cliques, falas, tempos e perguntas prováveis) no documento compartilhado do grupo:
https://claude.ai/code/artifact/99e12624-cfbf-4152-a27c-792b39ff107b

## Riscos

- Tendência do CV conferida na base limpa (55,4 → 43,2) e no painel balanceado de 3.021 municípios (51,5 → 40,3).
- Média simples ≠ total nacional ÷ população nacional: cada município pesa igual. Dizer isso na fala 1.
- Variação anual tem caudas longas (amplitude de 334 p.p. em 2015, municípios pequenos oscilam muito):
  é exatamente o ponto da fala 4, não precisa de regra extra.
- Moda: a de Czuber usa as classes de Sturges (largas para dados assimétricos). Em 2025 dá R$ 1.878,
  mas nas barras finas do histograma o pico fica perto de R$ 1.600. O app mostra os dois; quem
  apresenta a moda deve citar isso.
