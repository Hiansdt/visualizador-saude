"""Baixa as fontes e gera data/processed/ (o app só lê essa pasta).

Uso:
    uv run python -m saude_br.pipeline              # baixa o que falta + reconstrói
    uv run python -m saude_br.pipeline --offline    # só reconstrói a partir de data/raw
    uv run python -m saude_br.pipeline --refresh    # rebaixa tudo
    uv run python -m saude_br.pipeline --only ipea  # baixa só uma fonte
"""

import argparse
import json
from datetime import datetime

from saude_br import build
from saude_br.config import BASE_YEAR, FIRST_YEAR, LAST_YEAR, PROCESSED_DIR, RAW_DIR
from saude_br.sources import SOURCES

MIN_ROWS_PER_YEAR = 1000  # requisito da disciplina: cada análise com pelo menos 1000 linhas


def run(refresh=False, only=None, offline=False) -> None:
    if not offline:
        for key, source in SOURCES.items():
            if only is None or key in only:
                print(f"baixando {key}…", flush=True)
                source.fetch(RAW_DIR, refresh=refresh)

    t = {key: source.load(RAW_DIR) for key, source in SOURCES.items()}
    mun = build.build_municipios(t["ipea"]["gasto"], t["ipea"]["populacao"], t["bcb"]["ipca"])
    n = mun[mun["valido"]].groupby("ano").size()
    assert (n >= MIN_ROWS_PER_YEAR).all(), f"anos com menos de {MIN_ROWS_PER_YEAR} municípios:\n{n[n < MIN_ROWS_PER_YEAR]}"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    mun.to_csv(PROCESSED_DIR / "municipios.csv", index=False)
    (PROCESSED_DIR / "malha_uf.geojson").write_text(json.dumps(SOURCES["ibge"].geojson(RAW_DIR)))
    meta = {"gerado_em": datetime.now().isoformat(timespec="seconds"), "ano_base": BASE_YEAR,
            "anos": [FIRST_YEAR, LAST_YEAR], "linhas": len(mun), "validas": int(mun["valido"].sum())}
    (PROCESSED_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"-> {PROCESSED_DIR}: {len(mun)} linhas ({meta['validas']} válidas), "
          f"{n.min()}–{n.max()} municípios por ano")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--refresh", action="store_true", help="rebaixa tudo, mesmo o que já existe")
    p.add_argument("--offline", action="store_true", help="não baixa nada, só reconstrói")
    p.add_argument("--only", nargs="+", choices=list(SOURCES), help="baixa só estas fontes")
    a = p.parse_args()
    run(refresh=a.refresh, only=a.only, offline=a.offline)


if __name__ == "__main__":
    main()
