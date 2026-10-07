"""Parser dos acórdãos do TCU. Trechos reais (2005/2015) com nomes de pessoas trocados."""

import pytest

from saude_br.sources.tcu import category, condemnation_segment, parse_debits, parse_row, payee

CAAPORA = (
    "9.1. julgar irregulares as contas de Fulana, Construtora X Ltda. e Beltrano e condená-los, "
    "solidariamente, ao pagamento das quantias abaixo discriminadas, fixando-lhes o prazo de 15 (quinze) "
    "dias, a contar das notificações, para comprovarem, perante o Tribunal, o recolhimento das dívidas aos "
    "cofres da Fundação Nacional de Saúde - Funasa, acrescidas da correção monetária e dos juros de mora "
    "calculados a partir das referidas datas até a do efetivo recolhimento, na forma da legislação em vigor: "
    "VALOR ORIGINAL (R$) DATAS DE OCORRÊNCIA 453,14 080/1/2007 755,23 08/01/2007 1.661,51 08/01/2007 "
    "27.339,41 08/01/2007 841,54 10/04/2007 1.402,57 10/04/2007 3.085,66 10/04/2007 50.773,20 10/04/2007 "
    "46.867,56 30/08/2007 776,81 30/08/2007 1.229,68 30/08/2007 2.848,30 30/08/2007 9.2. aplicar, "
    "individualmente, a Fulana multa no valor de R$ R$ 60.000,00 (sessenta mil reais)"
)
SANTA_INES = (
    "julgar irregulares as contas do sr. Fulano e condená-lo ao pagamento da quantia de R$ 96.002,89 "
    "(noventa e seis mil e dois reais e oitenta e nove centavos), atualizada monetariamente e acrescida de "
    "juros a partir de 5/7/2002 até o efetivo recolhimento, abatida a importância de R$ 72.707,83 (setenta "
    "e dois mil, setecentos e sete reais e oitenta e três centavos), a partir de 16/12/2008, fixando o prazo "
    "de 15 (quinze) dias, para que comprove o recolhimento da dívida aos cofres da Fundação Nacional de "
    "Saúde, na forma da legislação em vigor; 9.3. aplicar ao sr. Fulano a multa prevista no art. 57, no "
    "valor de R$ 10.000,00 (dez mil reais)"
)
RESPECTIVAMENTE = (
    "julgar irregulares as contas do Sr. Fulano e em débito este responsável, condenando-o ao pagamento dos "
    "valores de R$ 11.000,00 e R$ 996,50, fixando-lhe o prazo de 15 (quinze) dias para que comprove o "
    "recolhimento da dívida aos cofres da Fundação Nacional de Saúde, calculados a partir de 16/12/1996 e "
    "20/12/1996, respectivamente, até a data do efetivo recolhimento"
)
NOVO_PRAZO = (
    "9.1. fixar novo e improrrogável prazo de quinze dias ao Município de Porto da Folha/SE para que se "
    "comprove o recolhimento das quantias aos cofres do Fundo Nacional de Saúde (FNS) Data de ocorrência "
    "Valor (R$) 26/2/2008 1.521,18 25/3/2008 14.133,58"
)


def test_table_with_typo_date_and_multa_excluded():
    seg = condemnation_segment(CAAPORA)
    debits = parse_debits(seg)
    assert len(debits) == 12
    assert sum(v for v, _ in debits) == pytest.approx(138034.61)
    assert {y for _, y in debits} == {2007}
    assert payee(seg) == "Funasa"


def test_credit_is_subtracted():
    assert parse_debits(condemnation_segment(SANTA_INES)) == [(96002.89, 2002), (-72707.83, 2008)]


def test_respectivamente_list():
    assert parse_debits(condemnation_segment(RESPECTIVAMENTE)) == [(11000.0, 1996), (996.5, 1996)]


def test_new_deadline_is_not_a_condemnation():
    assert condemnation_segment(NOVO_PRAZO) is None


def test_payee_without_cofres():
    assert payee("o recolhimento da dívida ao Fundo Nacional de Saúde;") == "FNS"


def test_category():
    assert category("CONVÊNIO. EMPRESA DE FACHADA. DESVIO DE RECURSOS.") == "Indícios de desvio ou fraude"
    assert category("FUNASA. NÃO APRESENTAÇÃO DA PRESTAÇÃO DE CONTAS FINAL.") == "Omissão ou não comprovação"


def test_parse_row_keeps_no_people():
    row = {"TIPOPROCESSO": "TOMADA DE CONTAS ESPECIAL (TCE)", "SUMARIO": "TCE. FUNASA. DESVIO.",
           "ACORDAO": CAAPORA, "PROC": "000.000/2014-0", "TITULO": "ACÓRDÃO 1/2015 - PLENÁRIO",
           "DATASESSAO": "01/01/2015", "ENTIDADE": " Prefeitura Municipal de Caaporã/PB ",
           "INTERESSADOS": "Fulana; Beltrano"}
    case = parse_row(row)
    assert case["uf"] == "PB" and case["origem"] == "Funasa"
    assert "Fulana" not in str(case)


def test_appeal_is_skipped():
    row = {"TIPOPROCESSO": "TOMADA DE CONTAS ESPECIAL (TCE)", "ACORDAO": CAAPORA,
           "SUMARIO": "Recurso de Reconsideração em Tomada de Contas Especial."}
    assert parse_row(row) is None
