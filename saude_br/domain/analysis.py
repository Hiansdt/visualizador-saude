"""Comparação entre mandatos.

Método: variação do último ano do mandato anterior até o último ano do
mandato. Assim o primeiro ano (que executa a LOA do governo anterior) conta
como herança, não como resultado. Anos parciais ficam de fora.
"""

import pandas as pd

from saude_br.domain.governments import TERMS


def term_changes(anual: pd.DataFrame, column: str) -> pd.DataFrame:
    closed = anual[~anual["ano_parcial"]]
    vals = closed.set_index("ano")[column].dropna()
    first, last = vals.index.min(), vals.index.max()
    rows = []
    for t in TERMS:
        if t.start > last or t.end < first:
            continue
        base = t.start - 1 if t.start - 1 >= first else first
        end = min(t.end, last)
        if end <= base:
            continue
        v0, v1 = vals[base], vals[end]
        years = range(max(t.start, first), end + 1)
        rows.append({
            "mandato": t.key,
            "presidente": t.president,
            "ano_base": base,
            "ano_fim": end,
            "valor_base": v0,
            "valor_fim": v1,
            "var_total": v1 / v0 - 1,
            "var_anual": (v1 / v0) ** (1 / (end - base)) - 1,
            "media": vals[list(years)].mean(),
            "incompleto": base != t.start - 1 or end != t.end,
        })
    return pd.DataFrame(rows)
