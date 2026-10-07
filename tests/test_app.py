"""Smoke test: cada página renderiza sem exceção, com e sem o desconto Covid."""

import pytest
from streamlit.testing.v1 import AppTest

from saude_br.config import ROOT

PAGES = ["views/panorama.py", "views/governos.py", "views/mapa.py", "views/composicao.py", "views/cortes.py",
         "views/desvios.py", "views/estatistica.py", "views/metodo.py"]


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("sem_covid", [False, True])
def test_page_renders(page, sem_covid):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["sem_covid"] = sem_covid
    at.run()
    at.switch_page(page).run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("nivel", ["Estados", "Regiões"])
@pytest.mark.parametrize("modo", ["Valor no ano", "Variação no período"])
@pytest.mark.parametrize("medida", ["Por habitante", "Total"])
def test_map_modes(nivel, modo, medida):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    at.switch_page("views/mapa.py")
    at.session_state["mapa_nivel"] = nivel
    at.session_state["mapa_modo"] = modo
    at.session_state["mapa_medida"] = medida
    at.run()
    assert not at.exception, at.exception


def test_composition_share_mode():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    at.switch_page("views/composicao.py")
    at.session_state["comp_modo"] = "% do ano"
    at.run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("periodo", [(2010, 2010), (2000, 2000), (2026, 2026), (2000, 2026), (2025, 2026)])
def test_period_edges(page, periodo):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.session_state["periodo"] = periodo
    at.run()
    at.switch_page(page).run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("ano", [2005, 2018, 2022])
def test_cortes_ranking_years(ano):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    at.switch_page("views/cortes.py")
    at.session_state["cortes_ano"] = ano
    at.run()
    assert not at.exception, at.exception


def test_desvios_by_judgment_year():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    at.switch_page("views/desvios.py")
    at.session_state["desvios_eixo"] = "do julgamento"
    at.run()
    assert not at.exception, at.exception


@pytest.mark.parametrize("grupo", ["Período todo", "Presidente", "Mandato"])
@pytest.mark.parametrize("transf", ["Valor do ano", "Variação ano a ano"])
def test_estatistica_modes(grupo, transf):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    at.switch_page("views/estatistica.py")
    at.session_state["est_grupo"] = grupo
    at.session_state["est_transf"] = transf
    at.run()
    assert not at.exception, at.exception
