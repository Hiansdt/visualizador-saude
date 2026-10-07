"""Caminhos e janelas de tempo compartilhados por pipeline e app."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

FIRST_YEAR = 2000  # primeiro exercício disponível no SIOP
LAST_YEAR = 2026  # exercício corrente: valores parciais (acumulado no ano)
BASE_YEAR = 2025  # reais constantes do último ano fechado
