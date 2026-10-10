"""Registro de fontes. Fonte nova = módulo novo + uma linha aqui."""

from saude_br.sources.base import Source
from saude_br.sources.bcb import Bcb
from saude_br.sources.ibge import Ibge
from saude_br.sources.ipea import Ipea

SOURCES: dict[str, Source] = {s.key: s for s in (Ipea(), Bcb(), Ibge())}
