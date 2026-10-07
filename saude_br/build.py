"""Transforma as tabelas das fontes nos datasets processados que o app lê.

Funções puras (DataFrame -> DataFrame) para poderem ser testadas sem rede.
"""

import re

import pandas as pd

from saude_br.config import BASE_YEAR, FIRST_YEAR, LAST_YEAR
from saude_br.domain.geography import REGIONS, UF_BY_SIGLA, UF_NAME, UF_SIGLA, classify_localizador, region_of
from saude_br.domain.governments import LOA_FROM_PREVIOUS_GOV, SPLIT_YEAR, term_for
from saude_br.sources.siop import SAUDE

ENCARGOS_ESPECIAIS = "28"


def deflators(ipca: pd.DataFrame) -> pd.Series:
    """Multiplicador que leva reais de cada ano para reais de BASE_YEAR."""
    idx = ipca.set_index("ano")["ipca_indice_medio"]
    return idx[BASE_YEAR] / idx


def build_anual(funcoes, covid, ipca, indicadores) -> pd.DataFrame:
    saude = funcoes[funcoes["funcao"] == SAUDE].set_index("ano")
    total = funcoes[funcoes["funcao"] != ENCARGOS_ESPECIAIS].groupby("ano")["emp"].sum()
    covid_emp = covid.set_index("ano")["emp"].reindex(saude.index, fill_value=0.0)
    ind = indicadores.set_index("ano").reindex(saude.index)
    defl = deflators(ipca).reindex(saude.index)

    df = pd.DataFrame(index=saude.index)
    df["presidente"] = [term_for(y).president for y in df.index]
    df["mandato"] = [term_for(y).key for y in df.index]
    df["ano_parcial"] = df.index == LAST_YEAR
    df["ano_dividido"] = df.index == SPLIT_YEAR
    df["loa_governo_anterior"] = df.index.isin(LOA_FROM_PREVIOUS_GOV)
    df["dotacao_inicial"] = saude["dot_ini"]
    df["dotacao_atual"] = saude["dot_atual"]
    df["empenhado"] = saude["emp"]
    df["liquidado"] = saude["liq"]
    df["pago"] = saude["pago"]
    df["covid"] = covid_emp
    df["empenhado_sem_covid"] = df["empenhado"] - df["covid"]
    df["despesa_federal_excl_encargos"] = total
    df["deflator"] = defl
    df["pib_nominal"] = ind["pib_nominal"]
    df["populacao"] = ind["populacao"]
    df["wb_gasto_publico_saude_pct_pib"] = ind["wb_gasto_publico_saude_pct_pib"]

    for suffix, emp in (("", df["empenhado"]), ("_sem_covid", df["empenhado_sem_covid"])):
        real = emp * df["deflator"]
        df[f"empenhado_real{suffix}"] = real
        df[f"real_per_capita{suffix}"] = real / df["populacao"]
        df[f"nominal_per_capita{suffix}"] = emp / df["populacao"]
        df[f"pct_pib{suffix}"] = 100 * emp / df["pib_nominal"]
    df["pct_orcamento"] = 100 * df["empenhado"] / total
    df["pct_orcamento_sem_covid"] = 100 * df["empenhado_sem_covid"] / (total - df["covid"])
    df["execucao_pct"] = 100 * df["empenhado"] / df["dotacao_atual"]
    return df.reset_index()


def build_regional(localizadores, populacao_uf, ipca) -> dict[str, pd.DataFrame]:
    loc = localizadores.copy()
    parsed = loc["nome"].map(classify_localizador)
    loc["nivel"] = parsed.str[0]
    loc["cod"] = parsed.str[1]
    defl = deflators(ipca)

    cobertura = loc.pivot_table(index="ano", columns="nivel", values="emp", aggfunc="sum", fill_value=0.0)
    cobertura = cobertura.reindex(columns=["uf", "regiao", "nao_regionalizado"], fill_value=0.0)
    cobertura["total"] = cobertura.sum(axis=1)
    cobertura["pct_uf"] = 100 * cobertura["uf"] / cobertura["total"]
    cobertura["pct_regionalizado"] = 100 * (cobertura["uf"] + cobertura["regiao"]) / cobertura["total"]

    uf = (loc[loc["nivel"] == "uf"].groupby(["ano", "cod"], as_index=False)["emp"].sum()
          .rename(columns={"cod": "cod_uf"}))
    uf["cod_uf"] = uf["cod_uf"].astype(int)
    uf = uf.merge(populacao_uf, on=["ano", "cod_uf"], how="left")
    uf["sigla"] = uf["cod_uf"].map(UF_SIGLA)
    uf["nome"] = uf["cod_uf"].map(UF_NAME)
    uf["cod_regiao"] = uf["cod_uf"].map(region_of)
    uf["empenhado_real"] = uf["emp"] * uf["ano"].map(defl)
    uf["real_per_capita"] = uf["empenhado_real"] / uf["populacao"]

    # Região = soma das UFs + o que foi localizado direto na região.
    direct = (loc[loc["nivel"] == "regiao"].groupby(["ano", "cod"])["emp"].sum()
              .rename_axis(["ano", "cod_regiao"]))
    regiao = uf.groupby(["ano", "cod_regiao"])[["emp", "populacao"]].sum()
    regiao["emp"] = regiao["emp"].add(direct.reindex(regiao.index), fill_value=0.0)
    regiao = regiao.reset_index()
    regiao["nome"] = regiao["cod_regiao"].map(REGIONS)
    regiao["empenhado_real"] = regiao["emp"] * regiao["ano"].map(defl)
    regiao["real_per_capita"] = regiao["empenhado_real"] / regiao["populacao"]

    return {"uf": uf, "regiao": regiao, "regionalizacao": cobertura.reset_index()}


def build_subfuncao(subfuncoes, ipca) -> pd.DataFrame:
    df = subfuncoes.groupby(["ano", "codigo"], as_index=False)["emp"].sum()
    # Nome mais recente de cada código (alguns mudaram ao longo dos anos).
    latest = subfuncoes.sort_values("ano").groupby("codigo")["nome"].last()
    df["nome"] = df["codigo"].map(latest)
    df["empenhado_real"] = df["emp"] * df["ano"].map(deflators(ipca))
    return df


# --- Cortes ---------------------------------------------------------------

COVID_ACTION = "21C0"
# Ações de custeio que recebem emendas parlamentares ("incremento temporário"):
# oscilam com as emendas, não com a política do Ministério.
_EMENDA = re.compile(r"incremento\s+tempor[aá]rio", re.I)
EMENDA_ACTIONS = {"2E89", "2E90"}


def build_execucao(anual: pd.DataFrame, acoes: pd.DataFrame) -> pd.DataFrame:
    """Do projeto de lei ao pago, por ano. "Não executado" = autorizado − empenhado."""
    df = anual[["ano", "presidente", "mandato", "ano_parcial", "deflator"]].copy()
    df["ploa"] = df["ano"].map(acoes.groupby("ano")["ploa"].sum())
    for col in ("dotacao_inicial", "dotacao_atual", "empenhado", "pago"):
        df[col] = anual[col]
    df["nao_executado"] = df["dotacao_atual"] - df["empenhado"]
    for col in ("ploa", "dotacao_inicial", "dotacao_atual", "empenhado", "pago", "nao_executado"):
        df[f"{col}_real"] = df[col] * df["deflator"]
    df["nao_executado_pct"] = 100 * df["nao_executado"] / df["dotacao_atual"]
    df["congresso_pct"] = 100 * (df["dotacao_inicial"] / df["ploa"] - 1)
    return df


def build_acoes(acoes: pd.DataFrame, ipca: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por ano e ação; subfunção principal = a de maior empenho."""
    values = ["ploa", "dot_ini", "dot_atual", "emp", "pago"]
    df = acoes.groupby(["ano", "acao"], as_index=False)[values].sum()
    main_sub = (acoes.sort_values("emp").groupby(["ano", "acao"])["subfuncao"].last())
    df["subfuncao"] = [main_sub[(a, c)] for a, c in zip(df["ano"], df["acao"])]
    latest = acoes.sort_values("ano").groupby("acao")["nome"].last()
    df["nome"] = df["acao"].map(latest)
    df["emenda"] = df["acao"].isin(EMENDA_ACTIONS) | df["nome"].str.contains(_EMENDA)
    defl = df["ano"].map(deflators(ipca))
    for col in values:
        df[f"{col}_real"] = df[col] * defl
    return df


def build_area(acoes: pd.DataFrame, subfuncao: pd.DataFrame, ipca: pd.DataFrame) -> pd.DataFrame:
    """Gasto real por subfunção (área do SUS), com e sem a ação Covid."""
    defl = deflators(ipca)
    total = acoes.groupby(["ano", "subfuncao"])["emp"].sum()
    sem = acoes[acoes["acao"] != COVID_ACTION].groupby(["ano", "subfuncao"])["emp"].sum()
    df = pd.DataFrame({"emp": total, "emp_sem_covid": sem.reindex(total.index, fill_value=0.0)}).reset_index()
    names = subfuncao.sort_values("ano").groupby("codigo")["nome"].last()
    df["nome"] = df["subfuncao"].map(names).fillna(df["subfuncao"])
    df["emp_real"] = df["emp"] * df["ano"].map(defl)
    df["emp_real_sem_covid"] = df["emp_sem_covid"] * df["ano"].map(defl)
    return df


# --- Desvios --------------------------------------------------------------

_ENTITY_PREFIX = re.compile(r"^(?:entidades?|unidades?|[óo]rg[ãa]os?)\s*(?:jurisdicionad[ao]s?)?\s*:\s*", re.I)
_ENTITY_UF = re.compile(r"(?:[/–-]\s*|\()([A-Z]{2})\)?\.?\s*$")


def _uf_of(entidade: str):
    m = _ENTITY_UF.search(entidade)
    return m.group(1) if m and m.group(1) in UF_BY_SIGLA else None


def build_desvios(casos: pd.DataFrame, ipca: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Dano ao erário julgado pelo TCU em TCEs da saúde.

    Só débitos com ocorrência a partir de FIRST_YEAR: antes disso não há
    deflator, e antes de 1994 os valores estão em cruzeiros.
    """
    c = casos.copy()
    c["sessao"] = pd.to_datetime(c["data_sessao"], dayfirst=True, errors="coerce")
    # Primeira condenação de cada processo; o mesmo débito às vezes volta em
    # outro processo (desmembramento), então também deduplica pela assinatura.
    c = c.sort_values("sessao").drop_duplicates("proc")
    c["assinatura"] = c["entidade"].str.lower() + "|" + c["debitos"].map(lambda d: str(sorted(map(tuple, d))))
    c = c[c["debitos"].map(len) > 0].drop_duplicates("assinatura")

    defl = deflators(ipca)
    pairs = c[["proc", "debitos"]].explode("debitos")
    pairs["valor"] = pairs["debitos"].str[0].astype(float)
    pairs["ano_ocorrencia"] = pairs["debitos"].str[1].astype(int)
    pairs = pairs[pairs["ano_ocorrencia"].between(FIRST_YEAR, LAST_YEAR)].drop(columns="debitos")
    pairs["valor_real"] = pairs["valor"] * pairs["ano_ocorrencia"].map(defl)
    pairs = pairs.merge(c[["proc", "categoria", "origem"]], on="proc")

    per_case = pairs.groupby("proc").agg(valor_real=("valor_real", "sum"), valor_nominal=("valor", "sum"),
                                         ano_ocorrencia=("ano_ocorrencia", "min"))
    cases = c.drop(columns=["debitos", "assinatura", "sessao"]).merge(per_case, on="proc")
    cases["entidade"] = cases["entidade"].str.replace(_ENTITY_PREFIX, "", regex=True)
    cases["uf"] = cases["entidade"].map(_uf_of)
    cases["ano_julgamento"] = cases["ano_julgamento"].astype(int)
    cases["defasagem"] = cases["ano_julgamento"] - cases["ano_ocorrencia"]

    # Quanto de cada ano de ocorrência já deve ter sido julgado: distribuição da
    # defasagem nos casos antigos (ocorridos há 15+ anos, quase todos já julgados).
    old = cases.loc[cases["ano_ocorrencia"] <= LAST_YEAR - 15, "defasagem"]
    def julgado(year):
        return float((old <= LAST_YEAR - year).mean()) if len(old) else float("nan")

    ocorrencia = pairs.groupby(["ano_ocorrencia", "categoria"], as_index=False)["valor_real"].sum()
    n = cases.groupby("ano_ocorrencia").size()
    ocorrencia["casos_no_ano"] = ocorrencia["ano_ocorrencia"].map(n)
    ocorrencia["pct_ja_julgado_estimado"] = 100 * ocorrencia["ano_ocorrencia"].map(julgado)

    julgamento = cases.groupby(["ano_julgamento", "categoria"], as_index=False).agg(
        valor_real=("valor_real", "sum"), casos=("proc", "count"))
    return {"desvios_casos": cases, "desvios_ocorrencia": ocorrencia, "desvios_julgamento": julgamento}
