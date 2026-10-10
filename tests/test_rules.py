from baseline.compute.baselines import personal_baseline
from baseline.compute.rules import MIN_HISTORY_DAYS, evaluate, rule_multi_signal
from baseline.fixtures import make_fixture


def confirmed(flags, day):
    return {r["rule"] for r in flags[day] if r["status"] == "confirmed"}


def count_confirmed(flags):
    return sum(r["status"] == "confirmed" for rs in flags.values() for r in rs)


def test_anomaly_fixture_confirmed_on_days_27_to_29():
    flags = evaluate(make_fixture(7, anomaly_start=27))
    for day in (27, 28, 29):
        assert {
            "hrv_below_personal_baseline",
            "sleep_below_personal_baseline",
            "reaction_above_personal_baseline",
            "two_signals_in_48h",
        } <= confirmed(flags, day)


def test_clean_fixture_has_no_confirmed_or_multi_signal_flags():
    flags = evaluate(make_fixture(7, anomaly_start=None))
    assert min(flags) == MIN_HISTORY_DAYS + 1
    assert count_confirmed(flags) == 0
    assert not any(r["rule"] == "two_signals_in_48h" for rs in flags.values() for r in rs)


def test_clean_fixtures_average_at_most_one_confirmed_flag():
    counts = [count_confirmed(evaluate(make_fixture(seed, anomaly_start=None))) for seed in range(1, 51)]
    mean = sum(counts) / len(counts)
    print(f"mean confirmed flags per clean fixture, seeds 1-50: {mean:.2f}")
    assert mean <= 1.0


def test_two_consecutive_watch_days_confirm():
    rows = make_fixture(7, anomaly_start=None)
    for i in (20, 21):  # days 21 and 22: 2.5 sd above their own baseline, so watch on its own
        b = personal_baseline([r["heart_rate_bpm"] for r in rows[:i]])
        rows[i]["heart_rate_bpm"] = b.mean + 2.5 * b.sd
    flags = evaluate(rows)
    assert [r["status"] for r in flags[21] if r["signal"] == "heart_rate_bpm"] == ["watch"]
    assert [r["status"] for r in flags[22] if r["signal"] == "heart_rate_bpm"] == ["confirmed"]


def result(signal, status):
    return {"signal": signal, "fired": True, "status": status}


def test_multi_signal_fires_for_two_confirmed_signals_within_48h():
    by_day = {10: [result("hrv_rmssd_ms", "confirmed")], 11: [result("sleep_hours", "confirmed")]}
    assert rule_multi_signal(by_day)["fired"]


def test_multi_signal_does_not_fire_for_one_signal():
    by_day = {10: [result("hrv_rmssd_ms", "confirmed")], 11: [result("hrv_rmssd_ms", "confirmed")]}
    assert not rule_multi_signal(by_day)["fired"]


def test_multi_signal_ignores_watch_items():
    by_day = {10: [result("hrv_rmssd_ms", "confirmed")], 11: [result("sleep_hours", "watch")]}
    assert not rule_multi_signal(by_day)["fired"]


def test_multi_signal_ignores_signals_outside_window():
    by_day = {9: [result("hrv_rmssd_ms", "confirmed")], 11: [result("sleep_hours", "confirmed")]}
    assert not rule_multi_signal(by_day)["fired"]
