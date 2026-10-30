"use strict";
// "Show the maths" view (design B2): the histogram behind one flag and its arithmetic in words. Display only:
// mean, SD and z come from Rules.ruleZscore on the same history the rule used, so they equal the evidence card.
// tests/test_maths.py runs this file in node against Rules.evaluate and the wording check.
(function (root) {
  const Rules = root.Rules || require("./rules.js");
  const BINS = 10;

  // Bin rule: 10 equal-width bins over one range that holds every history day, today and both 2-SD lines,
  // widened out to whole multiples of the chart step ÷ 5. Only the history days are counted; today is drawn
  // as its own line. Same input, same picture.
  function histogram(history, today, mean, sd, step) {
    const unit = step / 5, xs = [...history, today, mean - 2 * sd, mean + 2 * sd];
    const lo = Math.floor(Math.min(...xs) / unit) * unit, hi = Math.ceil(Math.max(...xs) / unit) * unit;
    const width = (hi - lo) / BINS, counts = Array(BINS).fill(0);
    for (const v of history) counts[Math.min(BINS - 1, Math.floor((v - lo) / width))]++;
    return { lo, hi, width, counts, edges: counts.map((_, i) => lo + i * width) };
  }

  // rows end with the flagged day; history is the window Rules.baseline uses (up to 30 earlier days).
  function view(rows, signal, spec) {
    const all = rows.slice(0, -1), today = rows.at(-1), r = Rules.ruleZscore(signal, all.map((x) => x[signal]), today[signal]);
    const days = all.slice(-r.window_days), history = days.map((x) => x[signal]);
    return {
      signal, day: today.day, first: days[0].day, last: days.at(-1).day, n: r.window_days,
      today: r.current, mean: r.baseline_mean, sd: r.baseline_sd, z: r.z, direction: r.direction,
      low: r.baseline_mean - Rules.THRESHOLD * r.baseline_sd, high: r.baseline_mean + Rules.THRESHOLD * r.baseline_sd,
      bins: histogram(history, r.current, r.baseline_mean, r.baseline_sd, spec.step),
    };
  }

  // z as on the evidence card: one decimal, ".0" dropped (the card's "3×").
  const one = (v) => v.toFixed(1);
  const zText = (z) => Math.abs(z).toFixed(1).replace(/\.0$/, "");
  // Fewest decimals (at least one) at which today, usual and spread as shown give the shown z (zDecimals, 24 Oct).
  function zDecimals(v) {
    for (let d = 1; d < 6; d++) {
      const [t, m, s] = [v.today, v.mean, v.sd].map((x) => +x.toFixed(d));
      if (Math.abs((t - m) / s).toFixed(1) === Math.abs(v.z).toFixed(1)) return d;
    }
    return 6;
  }

  function lines(v, spec) {
    const u = spec.unit, high = v.direction === "high", d = zDecimals(v), f = (x) => x.toFixed(d);
    const [a, b] = high ? [v.today, v.mean] : [v.mean, v.today];
    return {
      title: `${spec.name}, day ${v.day}`,
      numbers: `Your usual: ${f(v.mean)} ${u}. Usual spread: ${f(v.sd)} ${u}. Today: ${f(v.today)} ${u}.`,
      sum: `Today is (${f(a)} − ${f(b)}) ÷ ${f(v.sd)} = ${zText(v.z)} spreads ${high ? "above" : "below"} your usual.`,
      rule: `The rule flags ${Rules.THRESHOLD} or more.`,
      window: `Your usual range is computed from your own ${v.n} days, days ${v.first} to ${v.last} (simulated record).`,
      bins: `Bars: your ${v.n} days in ${BINS} equal-width bins of ${+v.bins.width.toFixed(2)} ${u}. Today is the line in the flag colour.`,
      aria: `Histogram of your ${v.n} days of ${spec.name.toLowerCase()}, days ${v.first} to ${v.last}. Usual range ${one(v.low)} to ${one(v.high)} ${u}. ` +
        `Today ${one(v.today)} ${u}, ${today(v)}.`,
    };
  }
  const today = (v) => (v.today > v.high ? "above the usual range" : v.today < v.low ? "below the usual range" : "inside the usual range");

  const api = { BINS, histogram, view, lines, zText, zDecimals };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Maths = api;
})(this);
