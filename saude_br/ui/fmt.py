"""Números no formato brasileiro (1.234,5)."""

import pandas as pd


def br(v: float | None, decimals: int = 0) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def value(v: float | None, unit: str, decimals: int = 0) -> str:
    """R$ 1.234, 12,3% ou só o número (unit vazia)."""
    if v is None or pd.isna(v):
        return "—"
    if unit == "R$":
        return f"R$ {br(v, decimals)}"
    return f"{br(v, decimals)}%" if unit == "%" else br(v, decimals)


def md(text: str) -> str:
    """Escapa o $ de "R$": no markdown do Streamlit, $...$ vira fórmula."""
    return text.replace("$", "\\$")
