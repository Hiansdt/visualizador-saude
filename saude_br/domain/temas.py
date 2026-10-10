"""As duas variáveis da apresentação. Cada tema é uma coluna de municipios.csv."""

from dataclasses import dataclass

from saude_br.config import BASE_YEAR


@dataclass(frozen=True)
class Tema:
    key: str
    variavel: str  # nome da variável, como aparece nos gráficos
    column: str
    unit: str  # "R$" ou "%"
    decimals: int
    explicacao: str


TEMAS = {t.key: t for t in (
    Tema("Gastos", f"Gasto com saúde e saneamento por habitante (R$ de {BASE_YEAR})", "gasto_real_pc", "R$", 2,
         f"Despesa empenhada do município nas funções Saúde e Saneamento ÷ população, corrigida pela "
         f"inflação (IPCA) para reais de {BASE_YEAR}. Cada município conta uma vez."),
    Tema("Cortes", "Variação real do gasto por habitante sobre o ano anterior (%)", "variacao_real_pct", "%", 2,
         "Quanto o gasto real por habitante de cada município mudou em relação ao ano anterior. "
         "Valor negativo = corte."),
)}
