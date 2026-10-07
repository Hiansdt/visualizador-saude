"""build_desvios: deduplicação, filtro de anos e deflação."""

import pandas as pd
import pytest

from saude_br.build import build_desvios

IPCA = pd.DataFrame({"ano": range(2000, 2027), "ipca_indice_medio": [1.0] * 26 + [1.0]})


def case(proc, sessao, debitos, entidade="Município de X/PB", ano=2015, categoria="Outras irregularidades"):
    return {"proc": proc, "acordao": f"ACÓRDÃO {proc}", "data_sessao": sessao, "entidade": entidade,
            "uf": None, "origem": "FNS", "categoria": categoria, "debitos": debitos, "ano_julgamento": ano}


def test_dedupes_process_and_signature_and_drops_old_currency():
    casos = pd.DataFrame([
        case("1", "01/02/2015", [(100.0, 2008)]),
        case("1", "01/02/2017", [(100.0, 2008)], ano=2017),           # recurso/reapreciação do mesmo processo
        case("2", "01/03/2015", [(100.0, 2008)]),                      # mesmo débito em outro processo
        case("3", "01/03/2015", [(500.0, 1993), (50.0, 2001)], entidade="Entidade: Município de Y (PI)"),
        case("4", "01/03/2015", []),                                   # condenação sem valor legível
    ])
    out = build_desvios(casos, IPCA)
    cases = out["desvios_casos"].set_index("proc")
    assert sorted(cases.index) == ["1", "3"]
    assert cases.loc["1", "ano_julgamento"] == 2015
    assert cases.loc["3", "valor_real"] == pytest.approx(50.0)      # 1993 (cruzeiros) fica de fora
    assert cases.loc["3", "entidade"] == "Município de Y (PI)" and cases.loc["3", "uf"] == "PI"
    assert out["desvios_ocorrencia"]["valor_real"].sum() == pytest.approx(150.0)
