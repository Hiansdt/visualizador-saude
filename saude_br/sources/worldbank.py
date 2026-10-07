"""Banco Mundial — PIB nominal, população e gasto público em saúde (todas as esferas)."""

from pathlib import Path

import pandas as pd

from saude_br.config import FIRST_YEAR, LAST_YEAR
from saude_br.sources.base import Source, read_json, write_json
from saude_br.sources.http import get_json

INDICATORS = {
    "NY.GDP.MKTP.CN": "pib_nominal",
    "SP.POP.TOTL": "populacao",
    "SH.XPD.GHED.GD.ZS": "wb_gasto_publico_saude_pct_pib",
}


class WorldBank(Source):
    key = "worldbank"
    name = "Banco Mundial — World Development Indicators"
    url = "https://data.worldbank.org/country/brazil"
    description = (
        "PIB nominal (R$), população e gasto público em saúde de todas as "
        "esferas (% do PIB, só como contexto)."
    )

    def fetch(self, root: Path, refresh: bool = False) -> None:
        d = self.raw_dir(root)
        for ind in INDICATORS:
            url = (f"https://api.worldbank.org/v2/country/BRA/indicator/{ind}"
                   f"?format=json&per_page=100&date={FIRST_YEAR}:{LAST_YEAR}")
            write_json(d / f"{ind}.json", get_json(url)[1])

    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        d = self.raw_dir(root)
        df = pd.DataFrame({"ano": range(FIRST_YEAR, LAST_YEAR + 1)})
        for ind, col in INDICATORS.items():
            values = {int(r["date"]): r["value"] for r in read_json(d / f"{ind}.json")}
            df[col] = df["ano"].map(values)
        return {"indicadores": df}
