"""Catálogo de métricas: como cada coluna de anual.csv é exibida.

Métrica nova = coluna nova em build.py + uma entrada aqui; páginas e gráficos
leem este catálogo, então ela aparece nos seletores automaticamente.
"""

from dataclasses import dataclass

from saude_br.config import BASE_YEAR


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    column: str
    column_sem_covid: str | None  # None = métrica não muda sem Covid
    scale: float  # divide o valor bruto antes de exibir
    unit: str  # sufixo do eixo/tooltip
    decimals: int
    help: str
    nominal_column: str | None = None  # mesma métrica sem correção, para comparar

    def col(self, sem_covid: bool) -> str:
        return self.column_sem_covid if sem_covid and self.column_sem_covid else self.column

    def fmt(self, value: float) -> str:
        text = f"{value / self.scale:,.{self.decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if self.unit == "R$":
            return f"R$ {text}"
        if self.unit == "bi":
            return f"R$ {text} bi"
        return f"{text}{self.unit}"

    def fmt_delta(self, first: float, last: float) -> str:
        """Variação percentual; para métricas em %, diferença em pontos percentuais."""
        if self.unit == "%":
            return f"{last - first:+.{self.decimals}f} p.p.".replace(".", ",", 1)
        return f"{100 * (last / first - 1):+.1f}%".replace(".", ",")


METRICS = {m.key: m for m in (
    Metric("per_capita", f"Por habitante, corrigido pela inflação (R$ de {BASE_YEAR})", "real_per_capita",
           "real_per_capita_sem_covid", 1, "R$", 0,
           f"Gasto federal em saúde por pessoa, em reais de {BASE_YEAR}: cada ano é corrigido pela "
           "inflação (IPCA) para comparar poder de compra.", "nominal_per_capita"),
    Metric("real", f"Total, corrigido pela inflação (R$ bi de {BASE_YEAR})", "empenhado_real",
           "empenhado_real_sem_covid", 1e9, "bi", 1,
           f"Valor empenhado em reais de {BASE_YEAR}, corrigido pela inflação (IPCA médio do ano).",
           "empenhado"),
    Metric("pct_pib", "% do PIB", "pct_pib", "pct_pib_sem_covid", 1, "%", 2,
           "Gasto federal em saúde sobre o PIB nominal do ano."),
    Metric("pct_orcamento", "% da despesa federal", "pct_orcamento",
           "pct_orcamento_sem_covid", 1, "%", 1,
           "Sobre a despesa empenhada da União, exceto a função 28 (Encargos "
           "Especiais: dívida e transferências constitucionais)."),
    Metric("nominal", "Total sem correção da inflação (R$ bi de cada ano)", "empenhado", "empenhado_sem_covid",
           1e9, "bi", 1, "Valor empenhado em reais de cada ano, sem correção."),
    Metric("execucao", "Execução do orçamento (%)", "execucao_pct", None, 1, "%", 1,
           "Empenhado sobre a dotação autorizada (lei + créditos). Abaixo de "
           "100% = parte do orçamento autorizado não foi usada."),
)}
DEFAULT_METRIC = "per_capita"
