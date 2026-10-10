"""Caminhos e janelas de tempo compartilhados por pipeline e app."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

# Em 2002 os municípios passam à classificação funcional atual (Portaria 42/1999)
# e o gasto com saúde salta de nível: a série começa ali para ser comparável.
FIRST_YEAR = 2002
LAST_YEAR = 2025  # último ano fechado
BASE_YEAR = 2025  # reais constantes
