"""Baixa as fontes e gera data/processed/ (o app só lê essa pasta).

Uso:
    uv run python -m saude_br.pipeline              # baixa o que falta + reconstrói
    uv run python -m saude_br.pipeline --offline    # só reconstrói a partir de data/raw
    uv run python -m saude_br.pipeline --refresh    # rebaixa tudo
    uv run python -m saude_br.pipeline --only siop  # baixa só uma fonte
"""

import argparse
import json
from datetime import datetime

from saude_br import build
from saude_br.config import BASE_YEAR, FIRST_YEAR, LAST_YEAR, PROCESSED_DIR, RAW_DIR
from saude_br.domain.geography import UFS, rewind_for_d3
from saude_br.sources import SOURCES


def check(anual, regional, subfuncao, acoes) -> None:
    """Invariantes: as quebras precisam somar o total da função Saúde."""
    total = anual.set_index("ano")["empenhado"]
    reg = regional["regionalizacao"].set_index("ano")["total"]
    sub = subfuncao.groupby("ano")["emp"].sum()
    aco = acoes.groupby("ano")["emp"].sum()
    # O SIOP soma em ponto flutuante: sobram alguns reais de arredondamento por ano.
    for name, parts in (("localizadores", reg), ("subfunções", sub), ("ações", aco)):
        gap = ((parts - total).abs() / total).max()
        assert gap < 1e-8, f"{name} não somam o total da saúde (dif. relativa máx. {gap:.2e})"
    ufs_por_ano = regional["uf"].groupby("ano")["cod_uf"].nunique()
    assert (ufs_por_ano == len(UFS)).all(), f"anos sem as 27 UFs:\n{ufs_por_ano[ufs_por_ano != len(UFS)]}"


def run(refresh=False, only=None, offline=False) -> None:
    if not offline:
        for key, source in SOURCES.items():
            if only is None or key in only:
                print(f"baixando {key}…", flush=True)
                source.fetch(RAW_DIR, refresh=refresh)

    t = {key: source.load(RAW_DIR) for key, source in SOURCES.items()}
    siop, ipca = t["siop"], t["bcb"]["ipca"]
    anual = build.build_anual(siop["funcoes"], siop["covid"], ipca, t["worldbank"]["indicadores"])
    regional = build.build_regional(siop["localizadores"], t["ibge"]["populacao_uf"], ipca)
    subfuncao = build.build_subfuncao(siop["subfuncoes"], ipca)
    acoes = build.build_acoes(siop["acoes"], ipca)
    check(anual, regional, subfuncao, acoes)
    tables = {
        "anual": anual,
        "subfuncao": subfuncao,
        **regional,
        "execucao": build.build_execucao(anual, siop["acoes"]),
        "acoes": acoes,
        "area": build.build_area(siop["acoes"], siop["subfuncoes"], ipca),
        **build.build_desvios(t["tcu"]["casos"], ipca),
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)
    for level in ("uf", "regiao"):
        geo = json.loads(SOURCES["ibge"].geojson_path(RAW_DIR, level).read_text())
        (PROCESSED_DIR / f"malha_{level}.geojson").write_text(json.dumps(rewind_for_d3(geo)))
    meta = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "ano_base": BASE_YEAR,
        "anos": [FIRST_YEAR, LAST_YEAR],
        "ano_parcial": LAST_YEAR,
    }
    (PROCESSED_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))

    cob = regional["regionalizacao"].set_index("ano")["pct_regionalizado"].round(0).astype(int)
    print("% regionalizado por ano:", cob.to_dict())
    casos = tables["desvios_casos"]
    print(f"TCU: {len(casos)} casos de saúde, julgados em {sorted(casos['ano_julgamento'].unique().tolist())}")
    print(f"-> {PROCESSED_DIR} ({len(anual)} anos)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--refresh", action="store_true", help="rebaixa tudo, mesmo o que já existe")
    p.add_argument("--offline", action="store_true", help="não baixa nada, só reconstrói")
    p.add_argument("--only", nargs="+", choices=list(SOURCES), help="baixa só estas fontes")
    a = p.parse_args()
    run(refresh=a.refresh, only=a.only, offline=a.offline)


if __name__ == "__main__":
    main()
