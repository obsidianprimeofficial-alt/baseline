"use strict";
// Port of src/baseline/compute/trend.py for the offline page, plus the card's words.
// Python is the reference; tests/test_trend.py checks this file gives the same numbers and cards.
(function (root) {
  const Rules = root.Rules || require("./rules.js");
  const DAYS = 3, THRESHOLD = 2, WITHIN = 30;

  // Least-squares slope per day; for 3 equally spaced days it equals (last − first) / 2.
  function slope(days, values) {
    const n = days.length, mx = days.reduce((a, x) => a + x, 0) / n, my = values.reduce((a, y) => a + y, 0) / n;
    let num = 0, den = 0;
    days.forEach((x, i) => { num += (x - mx) * (values[i] - my); den += (x - mx) ** 2; });
    return num / den;
  }

  // The card for `signal` on the last day of rows, or null: only when the signal was outside its usual
  // range (watch or confirmed) on each of the last 3 consecutive days. Edge = today's band from the rule.
  function projection(rows, signal, flags = Rules.evaluate(rows)) {
    if (rows.length < DAYS) return null;
    const last = rows.slice(-DAYS), days = last.map((r) => r.day);
    if (days.some((d, i) => d !== days[0] + i)) return null;
    const hits = days.map((d) => (flags[d] || []).find((f) => f.signal === signal));
    if (!hits.every(Boolean)) return null;
    const values = last.map((r) => r[signal]), today = hits.at(-1);
    const high = Rules.DIRECTIONS[signal] === "high";
    const edge = today.baseline_mean + (high ? THRESHOLD : -THRESHOLD) * today.baseline_sd;
    const s = slope(days, values), toward = high ? s < 0 : s > 0;
    const back = toward ? Math.floor(Math.abs(values.at(-1) - edge) / Math.abs(s)) + 1 : null;
    return { signal, days, values, slope: s, percent_per_day: (s / values.at(-1)) * 100, direction: Rules.DIRECTIONS[signal], edge, toward, days_back: back };
  }

  // The card's words. spec = { unit, dp } of the signal. No "flat", "rising" or "falling": no cut for them exists.
  function lines(p, spec) {
    const n = (v) => v.toFixed(spec.dp), pct = Math.round(p.percent_per_day * 10) / 10;
    const rate = `${pct < 0 ? "−" : pct > 0 ? "+" : ""}${Math.abs(pct).toFixed(1)}`;
    const high = p.direction === "high";
    const outlook = !p.toward
      ? `If nothing changes, it stays ${high ? "above your usual top" : "below your usual bottom"} of ${n(p.edge)} ${spec.unit}.`
      : p.days_back > WITHIN
        ? `If nothing changes, it is not back inside your usual range within ${WITHIN} days.`
        : `If nothing changes, it is back inside your usual range in ${p.days_back} ${p.days_back === 1 ? "day" : "days"}.`;
    return [
      `Three days outside your usual range: ${p.values.map(n).join(", ")} ${spec.unit}. Changing ${rate} percent per day. ${outlook}`,
      "Projection from your own last 3 days, not a forecast.",
    ];
  }

  const api = { DAYS, slope, projection, lines };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Projection = api;
})(this);
