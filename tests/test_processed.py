"""Regressão sobre data/processed/municipios.csv (números conferidos no planejamento)."""

import pandas as pd
import pytest

from saude_br.config import PROCESSED_DIR
from saude_br.domain.stats import summarize

df = pd.read_csv(PROCESSED_DIR / "municipios.csv", dtype={"cod_ibge": str})
ok = df[df["valido"]]


def test_at_least_1000_rows_every_year():
    assert (ok.groupby("ano").size() >= 1000).all()
    assert (ok.dropna(subset=["variacao_real_pct"]).groupby("ano").size() >= 1000).all()


def test_headline_numbers():
    s02 = summarize(ok.loc[ok["ano"] == 2002, "gasto_real_pc"].tolist())
    s25 = summarize(ok.loc[ok["ano"] == 2025, "gasto_real_pc"].tolist())
    assert s02.media == pytest.approx(560, abs=1)
    assert s25.media == pytest.approx(2081, abs=1)
    assert s02.cv_pop == pytest.approx(55.4, abs=0.1)
    assert s25.cv_pop == pytest.approx(43.2, abs=0.1)


def test_worst_year_for_cuts_is_2015():
    pct = ok.dropna(subset=["variacao_real_pct"]).groupby("ano")["corte"].mean()
    assert pct.idxmax() == 2015 and pct.max() == pytest.approx(0.731, abs=0.002)


def test_exclusions_are_small_and_labeled():
    assert (~df["valido"]).mean() < 0.01
    assert (df.loc[~df["valido"], "exclusao"] != "").all()
