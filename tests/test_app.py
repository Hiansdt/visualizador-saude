"""Smoke test: as duas páginas renderizam em todos os temas, anos e seletores."""

import pytest
from streamlit.testing.v1 import AppTest

from saude_br.config import ROOT

TIMELINE_GROUPS = ["Média, mediana e moda", "Amplitude", "Variância", "Desvio padrão",
                   "Coeficiente de variação", "Municípios (n)", "% de municípios com corte"]


def run_page(page, **state):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=90)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    at.switch_page(page).run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("tema", ["Gastos", "Cortes"])
@pytest.mark.parametrize("group", TIMELINE_GROUPS)
def test_timeline(tema, group):
    if tema == "Gastos" and group.startswith("%"):
        pytest.skip("só existe em Cortes")
    run_page("views/linha_do_tempo.py", tema=tema, **{f"lt_medida_{tema}": group})


@pytest.mark.parametrize("tema, layers", [
    ("Gastos", ["Média por habitante", "Mediana por habitante", "CV entre os municípios"]),
    ("Cortes", ["% de municípios com corte", "Variação mediana", "CV entre os municípios"]),
])
@pytest.mark.parametrize("ano", [2002, 2015, 2025])
@pytest.mark.parametrize("recorte", ["Brasil", "Roraima (RR)"])
def test_map(tema, layers, ano, recorte):
    for layer in layers:
        run_page("views/mapa.py", tema=tema, ano=ano, mapa_recorte=recorte, **{f"mapa_{tema}": layer})
