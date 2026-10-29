"use strict";
// Chart series for one signal, kept apart from the page so tests/test_web.py can run it in node.
// The usual-range band and the flag marks are computed on the full record, then the last `days` are cut
// for display, so the 7-day view shows the same values as the 30-day view for those days. Display only.
(function (root) {
  const Rules = root.Rules || require("./rules.js");

  // rows: the record shown on the console; flags: Rules.evaluate(rows); days: 7, or 0 for the whole record.
  function series(rows, flags, signal, days) {
    const vals = rows.map((r) => r[signal]);
    const band = rows.map((_, i) => (i < Rules.MIN_HISTORY_DAYS ? null : Rules.baseline(vals.slice(0, i))));
    const marks = rows.map((r) => (flags[r.day] || []).find((f) => f.signal === signal) || null);
    const from = days ? Math.max(0, rows.length - days) : 0;
    return {
      vals, band, // full record: the y-axis fits these, so both views share one scale
      shown: { days: rows.slice(from).map((r) => r.day), vals: vals.slice(from), band: band.slice(from), marks: marks.slice(from) },
    };
  }

  const api = { series };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Trend = api;
})(this);
