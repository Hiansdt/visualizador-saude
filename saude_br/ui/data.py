"""Leitura cacheada de data/processed/. O app nunca acessa a rede."""

import json

import pandas as pd
import streamlit as st

from saude_br.config import PROCESSED_DIR
from saude_br.domain.stats import measures
from saude_br.domain.temas import TEMAS


def require_data() -> None:
    if not (PROCESSED_DIR / "municipios.csv").exists():
        st.error("Dados processados não encontrados. Rode `uv run python -m saude_br.pipeline`.")
        st.stop()


@st.cache_data
def municipios() -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / "municipios.csv", dtype={"cod_ibge": str})


@st.cache_data
def valid(tema: str) -> pd.DataFrame:
    """Linhas válidas que têm valor para o tema (Cortes precisa de dois anos seguidos)."""
    df = municipios()
    return df[df["valido"]].dropna(subset=[TEMAS[tema].column])


@st.cache_data
def yearly(tema: str) -> pd.DataFrame:
    """As medidas da disciplina para cada ano, sobre todos os municípios válidos."""
    t = TEMAS[tema]
    rows = []
    for ano, g in valid(tema).groupby("ano"):
        row = {"Ano": ano, **measures(g[t.column].tolist(), t.decimals)}
        if tema == "Cortes":
            row["% com corte"] = 100 * g["corte"].mean()
        rows.append(row)
    return pd.DataFrame(rows)


@st.cache_data
def by_uf(tema: str, ano: int) -> pd.DataFrame:
    """Média, mediana, CV e % com corte de cada UF no ano."""
    col = TEMAS[tema].column
    g = valid(tema)[lambda d: d["ano"] == ano].groupby(["cod_uf", "uf"])
    out = g[col].agg(n="size", media="mean", mediana="median", dp="std").reset_index()
    out["cv"] = 100 * out["dp"] / out["media"].abs()
    out["pct_corte"] = 100 * g["corte"].mean().to_numpy()
    return out


@st.cache_data
def geojson() -> dict:
    return json.loads((PROCESSED_DIR / "malha_uf.geojson").read_text())


@st.cache_data
def meta() -> dict:
    return json.loads((PROCESSED_DIR / "meta.json").read_text())
