import pytest

from saude_br.domain.geography import classify_localizador


@pytest.mark.parametrize("label, expected", [
    ("Nacional", ("nao_regionalizado", None)),
    ("No Estado de São Paulo", ("uf", 35)),
    ("No Estado de Mato Grosso do Sul", ("uf", 50)),  # localizador 0054, IBGE 50
    ("No Estado de Mato Grosso", ("uf", 51)),
    ("No Estado do Pará", ("uf", 15)),
    ("No Estado do Paraná", ("uf", 41)),
    ("No Estado da Paraíba", ("uf", 25)),
    ("No Distrito Federal", ("uf", 53)),
    ("No Município de Porto Alegre - RS", ("uf", 43)),
    ("No Município do Rio de Janeiro - RJ (Hospital Geral de Bonsucesso)", ("uf", 33)),
    ("Região Metropolitana de João Pessoa - No Estado da Paraíba", ("uf", 25)),
    ("Na Região Sul", ("regiao", 4)),
    ("Na Região Sudeste", ("regiao", 3)),
    ("Na Região Centro Oeste", ("regiao", 5)),
    ("Na Região Centro-Oeste", ("regiao", 5)),
    ("Na Amazônia Legal", ("nao_regionalizado", None)),
])
def test_classify_localizador(label, expected):
    assert classify_localizador(label) == expected
