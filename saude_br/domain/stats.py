"""Estatística descritiva: as medidas pedidas na disciplina.

População: os valores são todos os anos do grupo (divide por n).
Amostra: os anos são tratados como amostra de um processo maior (divide por n − 1).
"""

import math
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Summary:
    n: int
    media: float
    mediana: float
    moda: list[float]  # vazia = amodal (nenhum valor se repete)
    minimo: float
    maximo: float
    amplitude: float
    var_pop: float
    var_amostral: float | None  # None quando n < 2
    dp_pop: float
    dp_amostral: float | None
    cv_pop: float | None  # % ; None quando a média é 0
    cv_amostral: float | None


def mode(values: list[float], decimals: int) -> list[float]:
    """Valores mais frequentes, comparados na precisão exibida. Vazio se nenhum se repete."""
    counts = Counter(round(v, decimals) for v in values)
    top = max(counts.values())
    return [] if top == 1 else sorted(v for v, c in counts.items() if c == top)


def summarize(values: list[float], decimals: int = 2) -> Summary:
    x = [float(v) for v in values]
    n = len(x)
    if n == 0:
        raise ValueError("sem valores")
    media = sum(x) / n
    s = sorted(x)
    mediana = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    sq = sum((v - media) ** 2 for v in x)
    var_pop = sq / n
    var_am = sq / (n - 1) if n > 1 else None
    dp_pop = math.sqrt(var_pop)
    dp_am = math.sqrt(var_am) if var_am is not None else None

    def cv(dp):
        return None if dp is None or media == 0 else 100 * dp / abs(media)

    return Summary(
        n=n, media=media, mediana=mediana, moda=mode(x, decimals),
        minimo=s[0], maximo=s[-1], amplitude=s[-1] - s[0],
        var_pop=var_pop, var_amostral=var_am, dp_pop=dp_pop, dp_amostral=dp_am,
        cv_pop=cv(dp_pop), cv_amostral=cv(dp_am),
    )


def cv_reading(cv: float | None) -> str:
    """Leitura usual do coeficiente de variação."""
    if cv is None:
        return "—"
    if cv < 15:
        return "baixa dispersão"
    if cv <= 30:
        return "média dispersão"
    return "alta dispersão"


@dataclass(frozen=True)
class ModalClass:
    k: int  # número de classes (Sturges)
    largura: float
    inferior: float
    superior: float
    frequencia: int
    freq_anterior: int  # classe antes da modal (0 se não houver)
    freq_posterior: int  # classe depois da modal (0 se não houver)
    czuber: float  # moda estimada dentro da classe modal


def modal_class(values: list[float]) -> ModalClass:
    """Classe modal com k = 1 + 3,322·log10(n) classes (Sturges) e a moda de Czuber.

    Czuber: Mo = Li + h · d1 / (d1 + d2), com d1 e d2 = diferença de frequência para a
    classe anterior e a seguinte.
    """
    x = sorted(float(v) for v in values)
    n = len(x)
    k = max(1, math.ceil(1 + 3.322 * math.log10(n)))
    lo, h = x[0], (x[-1] - x[0]) / k or 1.0
    freq = [0] * k
    for v in x:
        freq[min(int((v - lo) / h), k - 1)] += 1
    i = max(range(k), key=lambda j: freq[j])
    before = freq[i - 1] if i > 0 else 0
    after = freq[i + 1] if i < k - 1 else 0
    d1, d2 = freq[i] - before, freq[i] - after
    li = lo + i * h
    return ModalClass(k=k, largura=h, inferior=li, superior=li + h, frequencia=freq[i],
                      freq_anterior=before, freq_posterior=after,
                      czuber=li + h * d1 / (d1 + d2) if d1 + d2 else li + h / 2)


def measures(values: list[float], decimals: int = 2) -> dict:
    """As medidas da disciplina numa linha de tabela (populacional e amostral)."""
    s = summarize(values, decimals)
    m = modal_class(values)
    return {
        "n": s.n, "Média": s.media, "Mediana": s.mediana, "Moda (Czuber)": m.czuber,
        "Classe modal (início)": m.inferior, "Classe modal (fim)": m.superior,
        "Mínimo": s.minimo, "Máximo": s.maximo, "Amplitude": s.amplitude,
        "Variância pop.": s.var_pop, "Variância amostral": s.var_amostral,
        "DP pop.": s.dp_pop, "DP amostral": s.dp_amostral,
        "CV pop. (%)": s.cv_pop, "CV amostral (%)": s.cv_amostral,
    }
