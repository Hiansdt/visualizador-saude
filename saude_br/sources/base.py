"""Contrato de uma fonte de dados.

Uma fonte sabe (1) baixar seus arquivos brutos para data/raw/<key>/ e
(2) transformá-los em tabelas organizadas (DataFrames). Para adicionar uma
fonte nova: criar um módulo neste pacote com uma subclasse de Source e
registrá-la em saude_br/sources/__init__.py.
"""

import json
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd


class Source(ABC):
    key: str  # pasta em data/raw/ e chave no registro
    name: str  # nome exibido no app
    url: str  # página pública da fonte
    description: str  # o que usamos dela, em uma frase

    def raw_dir(self, root: Path) -> Path:
        d = root / self.key
        d.mkdir(parents=True, exist_ok=True)
        return d

    @abstractmethod
    def fetch(self, root: Path, refresh: bool = False) -> None:
        """Baixa os arquivos brutos; pula os que já existem, salvo refresh."""

    @abstractmethod
    def load(self, root: Path) -> dict[str, pd.DataFrame]:
        """Lê os arquivos brutos e devolve tabelas nomeadas."""


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def read_json(path: Path):
    return json.loads(path.read_text())
