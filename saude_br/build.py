"""Transforma as tabelas das fontes no dataset que o app lê (municipios.csv).

Funções puras (DataFrame -> DataFrame) para poderem ser testadas sem rede.
"""

import pandas as pd

from saude_br.config import BASE_YEAR, FIRST_YEAR, LAST_YEAR
from saude_br.domain.geography import REGIONS, UF_SIGLA, region_of
from saude_br.domain.governments import term_for

# Fora deste intervalo em torno da mediana do ano o valor é tratado como erro de
# registro (ex.: R$ 0,60 por habitante) e sai da análise, com o motivo anotado.
EXTREME_LOW, EXTREME_HIGH = 0.2, 10.0
SEM_GASTO = "não informou gasto"
SEM_POPULACAO = "sem população"
EXTREMO = "valor extremo (abaixo de 0,2× ou acima de 10× a mediana do ano)"


def deflators(ipca: pd.DataFrame) -> pd.Series:
    """Multiplicador que leva reais de cada ano para reais de BASE_YEAR."""
    idx = ipca.set_index("ano")["ipca_indice_medio"]
    return idx[BASE_YEAR] / idx


def interpolate_population(pop: pd.DataFrame) -> pd.DataFrame:
    """Preenche os anos sem estimativa do IBGE (2007, 2010, 2022, 2023) por município."""
    wide = pop.pivot(index="ano", columns="cod_ibge", values="populacao")
    wide = wide.reindex(range(wide.index.min(), wide.index.max() + 1))
    out = wide.interpolate(method="index", limit_area="inside").stack().rename("populacao").reset_index()
    original = set(zip(pop["ano"], pop["cod_ibge"]))
    out["populacao_interpolada"] = [(a, c) not in original for a, c in zip(out["ano"], out["cod_ibge"])]
    return out


def build_municipios(gasto: pd.DataFrame, populacao: pd.DataFrame, ipca: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por município e ano, com gasto real por habitante e variação sobre o ano anterior."""
    df = gasto[gasto["ano"].between(FIRST_YEAR, LAST_YEAR)].merge(
        interpolate_population(populacao), on=["cod_ibge", "ano"], how="left")
    df["cod_uf"] = df["cod_ibge"].str[:2].astype(int)
    df["uf"] = df["cod_uf"].map(UF_SIGLA)
    df["regiao"] = df["cod_uf"].map(region_of).map(REGIONS)
    df["presidente"] = df["ano"].map(lambda y: term_for(y).president)
    df["mandato"] = df["ano"].map(lambda y: term_for(y).key)
    df["gasto_real_pc"] = df["gasto"] / df["populacao"] * df["ano"].map(deflators(ipca))

    df["exclusao"] = ""
    df.loc[df["populacao"].isna(), "exclusao"] = SEM_POPULACAO
    df.loc[df["gasto"] <= 0, "exclusao"] = SEM_GASTO
    ok = df["exclusao"] == ""
    rel = df["gasto_real_pc"] / df["ano"].map(df[ok].groupby("ano")["gasto_real_pc"].median())
    df.loc[ok & ~rel.between(EXTREME_LOW, EXTREME_HIGH), "exclusao"] = EXTREMO
    df["valido"] = df["exclusao"] == ""

    # Variação real só entre dois anos válidos seguidos do mesmo município.
    prev = df[df["valido"]].assign(ano=lambda d: d["ano"] + 1).set_index(["cod_ibge", "ano"])["gasto_real_pc"]
    key = pd.MultiIndex.from_frame(df[["cod_ibge", "ano"]])
    df["gasto_real_pc_ano_anterior"] = prev.reindex(key).to_numpy()
    df.loc[~df["valido"], "gasto_real_pc_ano_anterior"] = float("nan")
    df["variacao_real_pct"] = 100 * (df["gasto_real_pc"] / df["gasto_real_pc_ano_anterior"] - 1)
    df["corte"] = df["variacao_real_pct"] < 0
    return df.sort_values(["ano", "cod_ibge"]).reset_index(drop=True)
