import statistics

import pytest

from saude_br.domain.stats import cv_reading, mode, summarize

DATA = [520.0, 560.0, 549.0, 505.0, 568.0, 582.0, 615.0]


def test_matches_python_statistics():
    s = summarize(DATA)
    assert s.n == 7
    assert s.media == pytest.approx(statistics.fmean(DATA))
    assert s.mediana == pytest.approx(statistics.median(DATA))
    assert s.amplitude == pytest.approx(max(DATA) - min(DATA))
    assert s.var_pop == pytest.approx(statistics.pvariance(DATA))
    assert s.var_amostral == pytest.approx(statistics.variance(DATA))
    assert s.dp_pop == pytest.approx(statistics.pstdev(DATA))
    assert s.dp_amostral == pytest.approx(statistics.stdev(DATA))
    assert s.cv_pop == pytest.approx(100 * statistics.pstdev(DATA) / statistics.fmean(DATA))
    assert s.cv_amostral == pytest.approx(100 * statistics.stdev(DATA) / statistics.fmean(DATA))


def test_even_count_median():
    assert summarize([1, 2, 3, 10]).mediana == 2.5


def test_single_value_has_no_sample_measures():
    s = summarize([857.0])
    assert s.var_pop == 0 and s.var_amostral is None and s.dp_amostral is None and s.cv_amostral is None


def test_mode():
    assert mode([1.0, 2.0, 3.0], 0) == []                     # amodal
    assert mode([1.04, 1.01, 2.0], 1) == [1.0]                # compara na precisão exibida
    assert mode([1.0, 1.0, 2.0, 2.0, 3.0], 0) == [1.0, 2.0]   # bimodal


def test_cv_reading():
    assert cv_reading(10) == "baixa dispersão"
    assert cv_reading(20) == "média dispersão"
    assert cv_reading(40) == "alta dispersão"
