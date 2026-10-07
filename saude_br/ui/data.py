"""Leitura cacheada de data/processed/. O app nunca acessa a rede."""

import json

import pandas as pd
import streamlit as st

from saude_br.config import PROCESSED_DIR


def require_data() -> None:
    if not (PROCESSED_DIR / "anual.csv").exists():
        st.error("Dados processados não encontrados. Rode `uv run python -m saude_br.pipeline`.")
        st.stop()


@st.cache_data
def table(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / f"{name}.csv")


@st.cache_data
def geojson(level: str) -> dict:
    return json.loads((PROCESSED_DIR / f"malha_{level}.geojson").read_text())


@st.cache_data
def meta() -> dict:
    return json.loads((PROCESSED_DIR / "meta.json").read_text())


def csv_bytes(name: str) -> bytes:
    return (PROCESSED_DIR / f"{name}.csv").read_bytes()
