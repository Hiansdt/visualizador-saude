"""IPEA — séries municipais do Ipeadata (OData).

DFSAUSM: despesa empenhada municipal nas funções Saúde + Saneamento (Tesouro/STN), R$ nominais.
ESTIMA_PO: população residente estimada pelo IBGE em 1º de julho.

Guardamos só o nível "Municípios" (código IBGE, ano, valor): as séries também trazem
áreas mínimas comparáveis (AMC), que não usamos.
"""

import csv
from pathlib import Path

import pandas as pd

from saude_br.sources.base import Source
from saude_br.sources.http import get_json

ODATA = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='%s')"
SERIES = {"DFSAUSM": "gasto", "ESTIMA_PO": "populacao"}


class Ipea(Source):
    key = "ipea"
    name = "Ipeadata — despesa municipal com saúde e saneamento (STN) e população (IBGE)"
    url = "http://www.ipeadata.gov.br/"
    description = ("Despesa empenhada de cada município nas funções Saúde e Saneamento (série DFSAUSM) "
                   "e população estimada (ESTIMA_PO), por ano.")

    def fetch(self, root: Path, refresh: bool = False) -> None:
        d = self.raw_dir(root)
        for code in SERIES:
            path = d / f"{code}.csv"
            if path.exists() and not refresh:
                continue
            rows = [r for r in get_json(ODATA % code, timeout=600)["value"] if r["NIVNOME"] == "Municípios"]
            with path.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["cod_ibge", "ano", "valor"])
                w.writerows((r["TERCODIGO"], r["VALDATA"][:4], r["VALVALOR"]) for r in rows
                            if r["VALVALOR"] is not None)
            print(f"  ipea {code}: {len(rows)} linhas")

    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        d = self.raw_dir(root)
        return {col: pd.read_csv(d / f"{code}.csv", dtype={"cod_ibge": str}).rename(columns={"valor": col})
                for code, col in SERIES.items()}
