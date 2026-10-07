"""Regressão sobre data/processed/: números já conferidos à mão contra o RREO."""

import pandas as pd
import pytest

from saude_br.config import PROCESSED_DIR
from saude_br.domain.analysis import term_changes

anual = pd.read_csv(PROCESSED_DIR / "anual.csv")


def test_matches_rreo():
    # RREO Anexo 02 União, Saúde (inclui intra-orçamentárias): 162,89 + 1,80 bi
    emp = anual.set_index("ano")["empenhado"]
    assert emp[2020] / 1e9 == pytest.approx(164.69, abs=0.01)


@pytest.mark.parametrize("mandato, var_total", [
    ("Lula 1", 0.121),
    ("Bolsonaro", -0.008),
    ("Lula 3", 0.336),
])
def test_term_changes_per_capita(mandato, var_total):
    changes = term_changes(anual, "real_per_capita").set_index("mandato")
    assert changes.loc[mandato, "var_total"] == pytest.approx(var_total, abs=0.001)


def test_partial_year_excluded_from_terms():
    changes = term_changes(anual, "real_per_capita").set_index("mandato")
    assert changes.loc["Lula 3", "ano_fim"] == anual.loc[~anual["ano_parcial"], "ano"].max()


def test_breakdowns_sum_to_total():
    total = anual.set_index("ano")["empenhado"]
    reg = pd.read_csv(PROCESSED_DIR / "regionalizacao.csv").set_index("ano")["total"]
    sub = pd.read_csv(PROCESSED_DIR / "subfuncao.csv").groupby("ano")["emp"].sum()
    # Arredondamento do SIOP: alguns reais por ano em totais de bilhões.
    assert ((reg - total).abs() / total).max() < 1e-8
    assert ((sub - total).abs() / total).max() < 1e-8
