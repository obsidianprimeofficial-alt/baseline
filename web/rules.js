// Small port of src/baseline/compute/rules.py and wording.py for the offline page.
// Python is the reference implementation; tests/test_web.py checks this file gives the same flags.
(function (root) {
  const DIRECTIONS = {
    hrv_rmssd_ms: "low", sleep_hours: "low", spo2_pct: "low", mood_1to5: "low",
    heart_rate_bpm: "high", core_temp_c: "high", reaction_ms: "high",
  };
  const SHORT = {
    hrv_rmssd_ms: "hrv", sleep_hours: "sleep", spo2_pct: "spo2", mood_1to5: "mood",
    heart_rate_bpm: "heart_rate", core_temp_c: "core_temp", reaction_ms: "reaction",
  };
  const MIN_HISTORY_DAYS = 14, CONFIRM_Z = 3, THRESHOLD = 2, WINDOW = 30;
  const BLOCKED = ["you have", "you are suffering", "diagnos", "disease", "condition:", "take ", "dose", "medication", "prescri"];

  function baseline(values) {
    const v = values.slice(-WINDOW), n = v.length;
    const mean = v.reduce((a, x) => a + x, 0) / n;
    const sd = Math.sqrt(v.reduce((a, x) => a + (x - mean) ** 2, 0) / (n - 1));
    return { mean, sd, n };
  }

  function ruleZscore(signal, history, current) {
    const direction = DIRECTIONS[signal], b = baseline(history);
    const z = b.sd === 0 ? 0 : (current - b.mean) / b.sd;
    return {
      rule: `${SHORT[signal]}_${direction === "low" ? "below" : "above"}_personal_baseline`,
      signal, current, baseline_mean: b.mean, baseline_sd: b.sd, z,
      fired: direction === "low" ? z <= -THRESHOLD : z >= THRESHOLD,
      window_days: b.n, direction,
    };
  }

  // Two or more different confirmed signals in the 48 hours ending on the latest day.
  function ruleMultiSignal(byDay) {
    const last = Math.max(...Object.keys(byDay).map(Number));
    const signals = new Set();
    for (const [day, rs] of Object.entries(byDay))
      if (last - day < 2) for (const r of rs) if (r.status === "confirmed") signals.add(r.signal);
    const fired = signals.size >= 2;
    return { rule: "two_signals_in_48h", signals: [...signals].sort(), fired, window_days: 2, status: fired ? "confirmed" : null };
  }

  // {day: [fired results]} for every day after MIN_HISTORY_DAYS; status "watch" or "confirmed".
  function evaluate(rows) {
    const fired = {};
    for (let i = MIN_HISTORY_DAYS; i < rows.length; i++) {
      const day = rows[i].day;
      const yesterday = new Set((fired[day - 1] || []).map((r) => r.signal));
      fired[day] = Object.keys(DIRECTIONS)
        .map((s) => ruleZscore(s, rows.slice(0, i).map((r) => r[s]), rows[i][s]))
        .filter((r) => r.fired)
        .map((r) => ({ ...r, status: Math.abs(r.z) >= CONFIRM_Z || yesterday.has(r.signal) ? "confirmed" : "watch" }));
    }
    const out = {};
    for (const [day, results] of Object.entries(fired)) {
      const upTo = Object.fromEntries(Object.entries(fired).filter(([d]) => +d <= +day));
      const multi = ruleMultiSignal(upTo);
      const fresh = results.some((r) => r.status === "confirmed");
      out[day] = fresh && multi.fired ? [...results, multi] : results;
    }
    return out;
  }

  function blocksDiagnostic(text) {
    const lowered = String(text).toLowerCase();
    return BLOCKED.filter((p) => lowered.includes(p));
  }

  const api = { DIRECTIONS, BLOCKED, MIN_HISTORY_DAYS, THRESHOLD, baseline, ruleZscore, evaluate, blocksDiagnostic };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Rules = api;
})(this);
