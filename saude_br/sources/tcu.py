"""TCU — acórdãos de Tomada de Contas Especial (TCE) com débito a devolver à saúde.

Cada ano de julgamento é um CSV de 100–500 MB. Lemos em streaming e guardamos
só os campos parseados dos casos de saúde em data/raw/tcu/<ano>.json — sem
nomes nem CPF de pessoas.

Um "caso" é um processo (PROC) julgado irregular com condenação a devolver
dinheiro aos cofres do Fundo Nacional de Saúde, da Funasa ou do Ministério da
Saúde. O valor é o débito original (valor histórico, sem juros), datado pela
ocorrência — não pelo julgamento, que vem anos depois.
"""

import csv
import html
import io
import re
import sys
import urllib.request
from pathlib import Path

import pandas as pd

from saude_br.config import FIRST_YEAR, LAST_YEAR
from saude_br.sources.base import Source, read_json, write_json
from saude_br.sources.http import UA

URL = ("https://sites.tcu.gov.br/dados-abertos/jurisprudencia/arquivos/"
       "acordao-completo/acordao-completo-%d.csv")

_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")
_START = re.compile(r"julgar\s+irregulares", re.I)
_CONDEMN = re.compile(r"conden", re.I)
# A condenação termina no próximo item que aplica multa ou trata de outra coisa.
_END = re.compile(r"\b\d+\.\d+\.?\s*(?:aplicar|autorizar|encaminhar|dar\s+ci[eê]ncia|remeter|enviar|"
                  r"considerar|informar|declarar|determinar|arquivar|excluir|recomendar)\b"
                  r"|\baplicar\b[^.;]{0,200}?\bmulta\b", re.I)
_PAYEE = re.compile(r"(?:cofres\s+d[oa]|\bao|\b[àa])\s+(?:(fundo\s+nacional\s+de\s+sa[uú]de|fns)|"
                    r"(funda[cç][aã]o\s+nacional\s+de\s+sa[uú]de|funasa)|"
                    r"(minist[eé]rio\s+da\s+sa[uú]de|sistema\s+[uú]nico\s+de\s+sa[uú]de|sus))\b", re.I)
_MONEY = re.compile(r"(?<![\d.,/])\d{1,3}(?:\.\d{3})*,\d{2}(?!\d|,\d)")
_DATE = re.compile(r"(?<![\d/])\d{1,3}/\d{1,2}/(\d{4})(?![\d/])")
# Crédito = valor já devolvido, abatido do débito. Janela curta para não pegar
# cabeçalhos de tabela como "Débito/Crédito".
_CREDIT_BEFORE = re.compile(r"(?:abatid|deduzid|cr[eé]dito\s+de|recolhid|ressarcid|devolvid)\w*[^;\d]{0,60}$", re.I)
_CREDIT_AFTER = re.compile(r"^\s*(?:\(\s*C\s*\)|C\b)")
_APPEAL = re.compile(r"^\s*(RECURSO|EMBARGOS|PEDIDO\s+DE\s+REEXAME|AGRAVO)", re.I)
_UF = re.compile(r"[/–-]\s*([A-Z]{2})\b\.?\s*$")

FRAUD = re.compile(r"desvio|fraud|superfatur|sobrepre[cç]o|fachada|fantasma|pagamento[s]?\s+(?:indevid|irregular)"
                   r"|direcionamento|conluio|montagem", re.I)
OMISSION = re.compile(r"omiss|n[aã]o\s+apresenta|aus[eê]ncia\s+de\s+presta|n[aã]o\s+comprova|inexecu", re.I)


def clean(text: str) -> str:
    return _SPACES.sub(" ", _TAGS.sub(" ", html.unescape(text or ""))).strip()


def condemnation_segment(acordao: str) -> str | None:
    """Trecho do dispositivo que julga irregular e condena; None se não houver."""
    m = _START.search(acordao)
    if not m or not _CONDEMN.search(acordao, m.start()):
        return None
    end = _END.search(acordao, m.end())
    seg = acordao[m.start(): end.start() if end else m.start() + 8000]
    return seg if _CONDEMN.search(seg) else None


def parse_debits(segment: str) -> list[tuple[float, int]]:
    """Pares (valor, ano da ocorrência); créditos (valores já devolvidos) vêm negativos.

    Agrupa valores e datas em sequências do mesmo tipo e casa sequências vizinhas
    de mesmo tamanho: cobre tabelas (valor data valor data…, em qualquer ordem) e
    listas ("R$ A e R$ B … a partir de D1 e D2, respectivamente").
    """
    tokens = sorted(
        [(m.start(), m.end(), "money", m.group()) for m in _MONEY.finditer(segment)]
        + [(m.start(), m.end(), "date", m.group(1)) for m in _DATE.finditer(segment)]
    )
    runs = []
    for tok in tokens:
        if runs and runs[-1][0][2] == tok[2]:
            runs[-1].append(tok)
        else:
            runs.append([tok])
    pairs, i = [], 0
    while i < len(runs) - 1:
        a, b = runs[i], runs[i + 1]
        if len(a) != len(b):
            i += 1
            continue
        for x, y in zip(a, b):
            money, date = (x, y) if x[2] == "money" else (y, x)
            year = int(date[3])
            value = float(money[3].replace(".", "").replace(",", "."))
            credit = (_CREDIT_BEFORE.search(segment[max(0, money[0] - 80): money[0]])
                      or _CREDIT_AFTER.match(segment[max(x[1], y[1]):]))
            if 1980 <= year <= LAST_YEAR:
                pairs.append((-value if credit else value, year))
        i += 2
    return pairs


def payee(segment: str) -> str | None:
    m = _PAYEE.search(segment)
    if not m:
        return None
    return "FNS" if m.group(1) else "Funasa" if m.group(2) else "Ministério da Saúde"


def category(sumario: str) -> str:
    if FRAUD.search(sumario):
        return "Indícios de desvio ou fraude"
    if OMISSION.search(sumario):
        return "Omissão ou não comprovação"
    return "Outras irregularidades"


def parse_row(row: dict) -> dict | None:
    """Caso de saúde condenado ou None. Só campos institucionais, sem pessoas."""
    if "TOMADA DE CONTAS ESPECIAL" not in row["TIPOPROCESSO"].upper():
        return None
    if _APPEAL.match(row["SUMARIO"] or ""):
        return None
    seg = condemnation_segment(clean(row["ACORDAO"]))
    if not seg:
        return None
    origem = payee(seg)
    if not origem:
        return None
    entidade = clean(row["ENTIDADE"]).rstrip(".")
    uf = _UF.search(entidade)
    return {
        "proc": row["PROC"],
        "acordao": clean(row["TITULO"]),
        "data_sessao": row["DATASESSAO"],
        "entidade": entidade,
        "uf": uf.group(1) if uf else None,
        "origem": origem,
        "categoria": category(row["SUMARIO"] or ""),
        "debitos": parse_debits(seg),
    }


def parse_stream(lines) -> list[dict]:
    csv.field_size_limit(sys.maxsize)
    return [case for row in csv.DictReader(lines, delimiter="|") if (case := parse_row(row))]


class Tcu(Source):
    key = "tcu"
    name = "TCU — Acórdãos (dados abertos de jurisprudência)"
    url = "https://sites.tcu.gov.br/dados-abertos/jurisprudencia/"
    description = (
        "Tomadas de Contas Especiais julgadas irregulares com débito a devolver ao FNS, "
        "à Funasa ou ao Ministério da Saúde (dano ao erário julgado, por data da ocorrência)."
    )

    def fetch(self, root: Path, refresh: bool = False) -> None:
        d = self.raw_dir(root)
        for year in range(FIRST_YEAR, LAST_YEAR + 1):  # ano do julgamento
            path = d / f"{year}.json"
            if path.exists() and not refresh and year != LAST_YEAR:
                continue
            req = urllib.request.Request(URL % year, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as resp:
                cases = parse_stream(io.TextIOWrapper(resp, encoding="utf-8", newline=""))
            write_json(path, cases)
            print(f"  tcu {year}: {len(cases)} casos de saúde")

    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        cases = []
        for year in range(FIRST_YEAR, LAST_YEAR + 1):
            path = self.raw_dir(root) / f"{year}.json"
            if path.exists():
                cases += [{**c, "ano_julgamento": year} for c in read_json(path)]
        return {"casos": pd.DataFrame(cases)}
