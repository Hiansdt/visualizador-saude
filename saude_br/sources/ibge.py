"""IBGE — população estimada por UF (SIDRA 6579) e malhas de UF e região."""

from pathlib import Path

import pandas as pd

from saude_br.config import FIRST_YEAR, LAST_YEAR
from saude_br.sources.base import Source, read_json, write_json
from saude_br.sources.http import get_json

MALHA = ("https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR"
         "?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=%s")


class Ibge(Source):
    key = "ibge"
    name = "IBGE — SIDRA 6579 e API de malhas"
    url = "https://sidra.ibge.gov.br/tabela/6579"
    description = (
        "População estimada por UF (anos sem estimativa são interpolados) e "
        "contornos de UF e região para o mapa."
    )

    def fetch(self, root: Path, refresh: bool = False) -> None:
        d = self.raw_dir(root)
        write_json(d / "populacao_uf.json",
                   get_json("https://apisidra.ibge.gov.br/values/t/6579/n3/all/v/9324/p/all/f/c"))
        for level in ("UF", "regiao"):
            path = d / f"malha_{level.lower()}.geojson"
            if refresh or not path.exists():
                write_json(path, get_json(MALHA % level))

    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        raw = read_json(self.raw_dir(root) / "populacao_uf.json")[1:]  # 1ª linha = cabeçalho
        pop = pd.DataFrame({
            "cod_uf": [int(r["D1C"]) for r in raw],
            "ano": [int(r["D3C"]) for r in raw],
            "populacao": [float(r["V"]) for r in raw],
        })
        # Sem estimativa em anos de censo/contagem (2000, 2007, 2010, 2022, 2023):
        # interpola linearmente; 2000 é extrapolado pela tendência 2001–2002.
        wide = pop.pivot(index="ano", columns="cod_uf", values="populacao")
        wide = wide.reindex(range(FIRST_YEAR, LAST_YEAR + 1))
        estimated = wide.notna().all(axis=1)
        wide = wide.interpolate(method="index", limit_direction="forward")
        wide.loc[FIRST_YEAR] = 2 * wide.loc[FIRST_YEAR + 1] - wide.loc[FIRST_YEAR + 2]
        out = wide.stack().rename("populacao").reset_index()
        out["populacao_interpolada"] = ~out["ano"].map(estimated)
        return {"populacao_uf": out}

    def geojson_path(self, root: Path, level: str) -> Path:
        return self.raw_dir(root) / f"malha_{level}.geojson"
