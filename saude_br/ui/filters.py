"""Filtros globais na barra lateral, compartilhados por todas as páginas."""

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from saude_br.config import BASE_YEAR, FIRST_YEAR, LAST_YEAR
from saude_br.domain.metrics import DEFAULT_METRIC, METRICS, Metric


@dataclass(frozen=True)
class Filters:
    start: int
    end: int
    metric: Metric
    sem_covid: bool

    def years(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[df["ano"].between(self.start, self.end)]

    def closed(self, df: pd.DataFrame) -> pd.DataFrame:
        """Só anos fechados: o ano corrente (parcial) distorce variações."""
        return df[df["ano"].between(self.start, min(self.end, LAST_YEAR - 1))]

    @property
    def column(self) -> str:
        return self.metric.col(self.sem_covid)


def render_sidebar() -> None:
    with st.sidebar:
        st.slider("Período", FIRST_YEAR, LAST_YEAR, value=(FIRST_YEAR, BASE_YEAR), key="periodo",
                  help=f"{LAST_YEAR} ainda está em andamento: valores parciais.")
        st.selectbox("Métrica", list(METRICS), index=list(METRICS).index(DEFAULT_METRIC),
                     format_func=lambda k: METRICS[k].label, key="metrica")
        st.caption(METRICS[st.session_state["metrica"]].help)
        st.toggle("Descontar gasto emergencial Covid", key="sem_covid",
                  help="Remove a ação 21C0 (Enfrentamento da Covid-19), R$ 42 bi em 2020 e "
                       "R$ 20 bi em 2021. Sem isso, 2022 parece um corte enorme.")


def get_filters() -> Filters:
    start, end = st.session_state.get("periodo", (FIRST_YEAR, BASE_YEAR))
    if end - start < 1:  # comparações precisam de pelo menos dois anos
        start, end = (end - 1, end) if end > FIRST_YEAR else (start, start + 1)
    return Filters(
        start=start,
        end=end,
        metric=METRICS[st.session_state.get("metrica", DEFAULT_METRIC)],
        sem_covid=st.session_state.get("sem_covid", False),
    )
