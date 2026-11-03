"use strict";
// Words for the Mars radiation caution (PLAN R2, open item 0c). No rule here: the card shows only when the Python rule
// fired on the latest cached MSL RAD day (web/data/radiation.json, scripts/build_radiation_summary.py). The step, its
// sources and the two plain notes come from the evidence map entry mars_radiation_caution.
// tests/test_mars_caution.py runs every line through the wording check.
(function (root) {
  const amount = (v) => `${v.toFixed(1)} µGy per day`;

  // null unless the rule fired on the latest cached day. m: msl_rad in radiation.json; e: the evidence map entry.
  function card(m, e) {
    if (!m.fired) return null;
    const today = m.dose_ugy_day, n = m.window_days, name = `${e.label}: Mars surface radiation`;
    return {
      title: name,
      row: `${amount(today)} on ${m.date}. Usual: ${amount(m.baseline_mean)}.`,
      status: `Above the usual range of the previous ${n} days.`,
      plain: `Mars surface radiation on ${m.date} was ${amount(today)}. The previous ${n} days averaged ${amount(m.baseline_mean)}, ` +
        `so this day is ${amount(today - m.baseline_mean)} higher. The reading comes from a detector on the Curiosity rover, not from a crew member.`,
      numbers: [
        ["Latest day", amount(today)],
        [`Usual (mean of ${n} days)`, amount(m.baseline_mean)],
        ["Usual spread (1 SD)", amount(m.baseline_sd)],
        ["How far", `${m.z.toFixed(1)}× the usual spread (flag at ${m.threshold_z}×)`],
        ["Status", e.label],
      ],
      why: `${e.trigger_note} ${e.practice_note}`,
      step: e.countermeasure,
      source: e.countermeasure_source,
      strength: `Evidence strength: ${e.strength}`,
      note: `Real NASA MSL RAD data, not simulated. Cached ${m.fetched_at.slice(0, 10)}.`,
      rule: `Rule: mars_radiation_caution (2 SD above the mean of the previous ${n} days)`,
      queue: `${name} (real NASA MSL RAD, not a crew reading): ${amount(today)} on ${m.date}, usual ${amount(m.baseline_mean)} over ${n} days, z = +${m.z.toFixed(1)}.`,
    };
  }

  const api = { card };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Mars = api;
})(this);
