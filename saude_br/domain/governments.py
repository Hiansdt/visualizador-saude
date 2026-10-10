"""Mandatos presidenciais e marcos legais do financiamento federal da saúde."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Term:
    key: str  # rótulo curto exibido nos gráficos
    president: str
    start: int
    end: int


# 2016 é atribuído a Temer (interino desde 12/05, efetivo em 31/08).
TERMS = (
    Term("FHC 2", "FHC", 1999, 2002),
    Term("Lula 1", "Lula", 2003, 2006),
    Term("Lula 2", "Lula", 2007, 2010),
    Term("Dilma 1", "Dilma", 2011, 2014),
    Term("Dilma 2", "Dilma", 2015, 2015),
    Term("Temer", "Temer", 2016, 2018),
    Term("Bolsonaro", "Bolsonaro", 2019, 2022),
    Term("Lula 3", "Lula", 2023, 2026),
)
# Ordem de primeira aparição: define a cor de cada presidente (slot fixo).
PRESIDENTS = ("FHC", "Lula", "Dilma", "Temer", "Bolsonaro")
SPLIT_YEAR = 2016
# Primeiro ano de cada governo executa a LOA enviada pelo governo anterior.
LOA_FROM_PREVIOUS_GOV = frozenset({2003, 2011, 2016, 2019, 2023})

# Marcos com ano certo; texto curto para caber no gráfico.
EVENTS = (
    (2000, "EC 29: piso federal da saúde"),
    (2015, "EC 86: piso vira % da receita"),
    (2017, "EC 95: teto de gastos em vigor"),
    (2020, "Covid-19"),
    (2023, "Fim do teto (EC 126 / LC 200)"),
)


def term_for(year: int) -> Term:
    for term in TERMS:
        if term.start <= year <= term.end:
            return term
    raise ValueError(f"sem mandato cadastrado para {year}")
