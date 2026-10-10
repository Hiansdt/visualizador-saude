"""IBGE — malha de UFs para o mapa (API de malhas)."""

import json
from pathlib import Path

import pandas as pd

from saude_br.domain.geography import rewind_for_d3
from saude_br.sources.base import Source, write_json
from saude_br.sources.http import get_json

MALHA = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
         "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF")


class Ibge(Source):
    key = "ibge"
    name = "IBGE — API de malhas"
    url = "https://servicodados.ibge.gov.br/api/docs/malhas"
    description = "Contornos das UFs para o mapa."

    def fetch(self, root: Path, refresh: bool = False) -> None:
        path = self.raw_dir(root) / "malha_uf.geojson"
        if refresh or not path.exists():
            write_json(path, get_json(MALHA))

    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        return {}

    def geojson(self, root: Path) -> dict:
        """Malha pronta para o Plotly (anéis no sentido que o d3 espera)."""
        return rewind_for_d3(json.loads((self.raw_dir(root) / "malha_uf.geojson").read_text()))
