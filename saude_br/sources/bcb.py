"""Banco Central — SGS série 433 (IPCA mensal), usado como deflator."""

from pathlib import Path

import pandas as pd

from saude_br.config import FIRST_YEAR, LAST_YEAR
from saude_br.sources.base import Source, read_json, write_json
from saude_br.sources.http import get_json


class Bcb(Source):
    key = "bcb"
    name = "Banco Central — SGS 433 (IPCA)"
    url = "https://www3.bcb.gov.br/sgspub/"
    description = "IPCA mensal, base do deflator (média anual do índice)."

    def fetch(self, root: Path, refresh: bool = False) -> None:
        path = self.raw_dir(root) / "ipca_mensal.json"
        series = []
        for start in range(FIRST_YEAR, LAST_YEAR + 1, 10):  # API limita a 10 anos
            end = min(start + 9, LAST_YEAR)
            series += get_json(
                "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json"
                f"&dataInicial=01/01/{start}&dataFinal=31/12/{end}"
            )
        write_json(path, series)

    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        monthly = read_json(self.raw_dir(root) / "ipca_mensal.json")
        idx, rows = 1.0, []
        for m in monthly:  # índice encadeado, jan/2000 = 1
            idx *= 1 + float(m["valor"]) / 100
            rows.append({"ano": int(m["data"][-4:]), "indice": idx})
        annual = pd.DataFrame(rows).groupby("ano", as_index=False)["indice"].mean()
        return {"ipca": annual.rename(columns={"indice": "ipca_indice_medio"})}
