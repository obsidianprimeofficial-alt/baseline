import numpy as np

from baseline.compute.baselines import personal_baseline, zscore


def test_mean_and_sd_match_numpy():
    series = [52.1, 55.4, 54.0, 57.3, 53.8, 56.2, 55.0, 54.7]
    b = personal_baseline(series)
    assert b.mean == np.mean(series)
    assert abs(b.sd - np.std(series, ddof=1)) < 1e-12
    assert b.n == len(series)


def test_window_keeps_most_recent_values():
    assert personal_baseline(list(range(40)), window=30).mean == np.mean(range(10, 40))


def test_zscore_is_zero_when_sd_is_zero():
    assert zscore(10.0, personal_baseline([5.0, 5.0, 5.0])) == 0.0
