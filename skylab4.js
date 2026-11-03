"use strict";
// Real crew record: Skylab 4 sleep estimates through the app's own sleep rule. Port of src/baseline/compute/skylab4.py;
// tests/test_skylab4.py checks both give the same flags. Kept apart from the page so tests can run it in node.
// A missing night is never filled in, never counted as history and never flagged.
(function (root) {
  const Rules = root.Rules || require("./rules.js"), Trend = root.Trend || require("./trend.js");
  const SIGNAL = "sleep_hours";
  const hasValue = (n) => n.total_sleep_h !== null;

  // {mission_day: [fired result with status]} for one role, nights in order. Same steps as Rules.evaluate, one signal.
  function evaluateSleep(nights) {
    const history = [], fired = {};
    for (const n of nights.filter(hasValue)) {
      if (history.length >= Rules.MIN_HISTORY_DAYS) {
        const r = Rules.ruleZscore(SIGNAL, history, n.total_sleep_h);
        if (r.fired) fired[n.mission_day] = [{ ...r, status: Math.abs(r.z) >= Rules.CONFIRM_Z || fired[n.mission_day - 1] ? "confirmed" : "watch" }];
      }
      history.push(n.total_sleep_h);
    }
    return fired;
  }

  // Band and marks from web/trend.js on the nights with a value, then laid back onto every night: a missing one stays null, so the line breaks there.
  function series(nights) {
    const rows = nights.filter(hasValue).map((n) => ({ day: n.mission_day, [SIGNAL]: n.total_sleep_h }));
    const trend = Trend.series(rows, evaluateSleep(nights), SIGNAL, 0);
    const at = new Map(rows.map((r, i) => [r.day, i]));
    const all = (xs) => nights.map((n) => (at.has(n.mission_day) ? xs[at.get(n.mission_day)] : null));
    const { vals, band, marks } = trend.shown;
    return { vals: trend.vals, band: trend.band, shown: { days: nights.map((n) => n.mission_day), vals: all(vals), band: all(band), marks: all(marks) } };
  }

  const daysOf = (fired, status) => Object.keys(fired).map(Number).filter((d) => fired[d][0].status === status);
  const named = (days) => (days.length ? ` (day${days.length > 1 ? "s" : ""} ${days.join(", ")})` : "");

  function countsLine(nights) {
    const fired = evaluateSleep(nights), watch = daysOf(fired, "watch"), confirmed = daysOf(fired, "confirmed");
    return `${nights.filter(hasValue).length} of ${nights.length} nights with a value · ${watch.length} watching${named(watch)} · ${confirmed.length} flagged${named(confirmed)}.`;
  }

  const printed = (n) => `printed ≈${n.total_sleep_h.toFixed(1)}`;

  // The nights that need saying in words: approximate, or no value on the page.
  function notes(nights) {
    return nights.filter((n) => n.approximate || !hasValue(n))
      .map((n) => `Day ${n.mission_day}: ${n.approximate ? printed(n) : "no value printed, left out"}.`).join(" ");
  }

  const api = { evaluateSleep, series, countsLine, printed, notes };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Skylab = api;
})(this);
