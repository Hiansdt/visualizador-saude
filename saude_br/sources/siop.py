"""SIOP — endpoint SPARQL do Orçamento Federal (execução por função, 2000+)."""

from pathlib import Path

import pandas as pd

from saude_br.config import FIRST_YEAR, LAST_YEAR
from saude_br.sources.base import Source, read_json, write_json
from saude_br.sources.http import sparql

ENDPOINT = "https://www1.siop.planejamento.gov.br/sparql/"
SAUDE = "10"
# Ação 21C0 = Enfrentamento da Emergência de Saúde Pública (Covid-19).
# Vacinas Covid foram em parte pela ação regular 20YE e não são separadas aqui.
COVID_ACTION = "21C0"
VALUES = ("dot_ini", "dot_atual", "emp", "liq", "pago")

PREFIX = """PREFIX loa: <http://vocab.e.gov.br/2013/09/loa#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""
# OPTIONAL + COALESCE: um item sem valorPago (comum no ano corrente) não
# pode sumir das somas das outras colunas.
Q_FUNCOES = PREFIX + """
SELECT ?cod (SUM(COALESCE(?dot,0)) AS ?dot_ini) (SUM(COALESCE(?atual,0)) AS ?dot_atual)
       (SUM(COALESCE(?emp,0)) AS ?emp) (SUM(COALESCE(?liq,0)) AS ?liq) (SUM(COALESCE(?pago,0)) AS ?pago)
WHERE { ?i loa:temExercicio ?ex . ?ex loa:identificador %(year)d .
  ?i loa:temFuncao ?f . ?f loa:codigo ?cod .
  OPTIONAL { ?i loa:valorDotacaoInicial ?dot } OPTIONAL { ?i loa:valorLeiMaisCredito ?atual }
  OPTIONAL { ?i loa:valorEmpenhado ?emp }     OPTIONAL { ?i loa:valorLiquidado ?liq }
  OPTIONAL { ?i loa:valorPago ?pago } }
GROUP BY ?cod"""

Q_SAUDE_POR = PREFIX + """
SELECT ?cod ?nome (SUM(?emp) AS ?emp)
WHERE { ?i loa:temExercicio ?ex . ?ex loa:identificador %(year)d .
  ?i loa:temFuncao ?f . ?f loa:codigo "10" .
  ?i loa:%(prop)s ?d . ?d loa:codigo ?cod . OPTIONAL { ?d rdfs:label ?nome }
  ?i loa:valorEmpenhado ?emp }
GROUP BY ?cod ?nome"""

# Ação x subfunção: base dos cortes por área e do orçado vs executado.
Q_ACOES = PREFIX + """
SELECT ?acao ?nome ?sub (SUM(COALESCE(?pl,0)) AS ?ploa) (SUM(COALESCE(?dot,0)) AS ?dot_ini)
       (SUM(COALESCE(?atual,0)) AS ?dot_atual) (SUM(COALESCE(?emp,0)) AS ?emp) (SUM(COALESCE(?pago,0)) AS ?pago)
WHERE { ?i loa:temExercicio ?ex . ?ex loa:identificador %(year)d .
  ?i loa:temFuncao ?f . ?f loa:codigo "10" .
  ?i loa:temAcao ?a . ?a loa:codigo ?acao . OPTIONAL { ?a rdfs:label ?nome }
  ?i loa:temSubfuncao ?sf . ?sf loa:codigo ?sub .
  OPTIONAL { ?i loa:valorProjetoLei ?pl } OPTIONAL { ?i loa:valorDotacaoInicial ?dot }
  OPTIONAL { ?i loa:valorLeiMaisCredito ?atual } OPTIONAL { ?i loa:valorEmpenhado ?emp }
  OPTIONAL { ?i loa:valorPago ?pago } }
GROUP BY ?acao ?nome ?sub"""
ACAO_VALUES = ("ploa", "dot_ini", "dot_atual", "emp", "pago")

Q_COVID = PREFIX + """
SELECT ?ano (SUM(?emp) AS ?emp)
WHERE { ?i loa:temExercicio ?ex . ?ex loa:identificador ?ano .
  ?i loa:temFuncao ?f . ?f loa:codigo "10" .
  ?i loa:temAcao ?a . ?a loa:codigo "%s" .
  ?i loa:valorEmpenhado ?emp }
GROUP BY ?ano""" % COVID_ACTION


class Siop(Source):
    key = "siop"
    name = "SIOP — Orçamento Federal (SPARQL)"
    url = "https://www1.siop.planejamento.gov.br/sparql/"
    description = (
        "Despesa da União por função, subfunção e localizador (empenhado, "
        "liquidado, pago e dotações), 2000 em diante."
    )

    def fetch(self, root: Path, refresh: bool = False) -> None:
        d = self.raw_dir(root)
        # TODO(siop-1998-1999): add federal health spending for 1998 and 1999
        # WHY: SIOP SPARQL starts at 2000, and Portal da Transparência downloads
        #      (dadosabertos-download.cgu.gov.br) return 403 to scripted clients.
        # DONE-WHEN: `uv run python -m saude_br.pipeline && grep -cE '^(1998|1999),' data/processed/anual.csv` prints 2
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            path = d / f"{year}.json"
            # O exercício corrente muda todo dia: sempre rebaixa.
            if path.exists() and not refresh and year != LAST_YEAR:
                continue
            write_json(path, {
                "funcoes": sparql(ENDPOINT, Q_FUNCOES % {"year": year}),
                "subfuncoes": sparql(ENDPOINT, Q_SAUDE_POR % {"year": year, "prop": "temSubfuncao"}),
                "localizadores": sparql(ENDPOINT, Q_SAUDE_POR % {"year": year, "prop": "temSubtitulo"}),
            })
            print(f"  siop {year}")
        # Arquivo separado: anos já baixados antes desta consulta existir também a recebem.
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            path = d / f"acoes_{year}.json"
            if path.exists() and not refresh and year != LAST_YEAR:
                continue
            write_json(path, sparql(ENDPOINT, Q_ACOES % {"year": year}))
            print(f"  siop ações {year}")
        write_json(d / "covid.json", sparql(ENDPOINT, Q_COVID))

    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        d = self.raw_dir(root)
        funcoes, subfuncoes, localizadores = [], [], []
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            raw = read_json(d / f"{year}.json")
            funcoes += [{"ano": year, "funcao": r["cod"], **{k: float(r[k]) for k in VALUES}}
                        for r in raw["funcoes"]]
            subfuncoes += [{"ano": year, "codigo": r["cod"], "nome": r.get("nome", r["cod"]),
                            "emp": float(r["emp"])} for r in raw["subfuncoes"]]
            localizadores += [{"ano": year, "codigo": r["cod"], "nome": r.get("nome", r["cod"]),
                               "emp": float(r["emp"])} for r in raw["localizadores"]]
        acoes = [{"ano": year, "acao": r["acao"], "nome": r.get("nome", r["acao"]), "subfuncao": r["sub"],
                  **{k: float(r[k]) for k in ACAO_VALUES}}
                 for year in range(FIRST_YEAR, LAST_YEAR + 1)
                 for r in read_json(d / f"acoes_{year}.json")]
        covid = [{"ano": int(r["ano"]), "emp": float(r["emp"])} for r in read_json(d / "covid.json")]
        return {
            "funcoes": pd.DataFrame(funcoes),
            "subfuncoes": pd.DataFrame(subfuncoes),
            "localizadores": pd.DataFrame(localizadores),
            "covid": pd.DataFrame(covid, columns=["ano", "emp"]),
            "acoes": pd.DataFrame(acoes),
        }
