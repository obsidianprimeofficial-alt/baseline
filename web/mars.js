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
        ["How far", `${m.z.toFixed(1)}× the usual spread (caution at ${m.threshold_z}×)`],
        ["Status", e.label],
      ],
      why: `${e.trigger_note} ${e.practice_note}`,
      step: e.countermeasure,
      source: e.countermeasure_source,
      strength: `Evidence strength: ${e.strength}`,
      note: `Real NASA MSL RAD data, not simulated. Cached ${m.fetched_at.slice(0, 10)}.`,
      queue: `${name} (real NASA MSL RAD, not a crew reading): ${amount(today)} on ${m.date}, usual ${amount(m.baseline_mean)} over ${n} days, ${m.z.toFixed(1)} spreads above usual.`,
    };
  }

  // Replay of the real 20 May 2024 surge (web/data/mars-surge-2024-05-20.json, scripts/build_mars_surge.py): the same card,
  // the rule's own output on that day, with replay words. Copy from private/mars_replay_2026-11-05.md §4; 8,100 is always the peak.
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const day = (iso) => `${+iso.slice(8, 10)} ${MONTHS[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
  const BUTTON = "Replay a real Mars radiation surge: 20 May 2024";
  const LABEL = "Replay of a real 2024 event, not today's data.";
  const STRENGTH = "Evidence strength: Step: NASA article and standard, not a study. Event: real NASA readings; " +
    "peak and average from the RAD team's slides; peer-reviewed paper on the same event."; // Hrishin, 7 Nov; the live card keeps its own

  // [line before the card, card]. ev: the replay file; e: the evidence map entry.
  function replay(ev, e) {
    const c = card({ ...ev, date: day(ev.date) }, e), [article, slides, paper] = ev.sources.slice(1);
    const utc = (iso) => `${iso.slice(11, 16)} UTC`;
    return [
      `Replay of real NASA data, ${day(ev.date)}. The day before: ${amount(ev.before.dose_ugy_day)}, usual ${ev.before.baseline_mean.toFixed(1)}.`,
      { ...c,
        chip: "Replay – real NASA MSL RAD data",
        badge: "Replay – real NASA data", // header, in place of "Simulated data"; short like the alert's "Replay – real NOAA data" (Hrishin, 7 Nov)
        label: LABEL,
        numbers: [["That day", amount(ev.dose_ugy_day)], ...c.numbers.slice(1)],
        notes: [
          `Daily figure: the average of ${ev.n_obs} readings that day. Highest reading: ${amount(ev.peak.ugy_day)}, at ${utc(ev.peak.time_tag)}.`,
          "The RAD team lists this event as about 1,900 µGy per day on average and 8,100 µGy per day at the peak.",
          "NASA, June 2024: \"the biggest surge measured by Curiosity's Radiation Assessment Detector, or RAD, since the rover landed 12 years ago.\"",
        ],
        sources: [
          "NASA's article gives 8,100 micrograys for this event. The RAD team's table lists 8,100 as the peak, in µGy per day.",
          `Source for the readings: NASA SPDF CDAWeb, MSL_RAD_OBS-L2, DOI ${ev.doi}`,
          `Source for the event: ${article.name}, ${article.url}`,
          `Source for the peak and average: MSL RAD team slides, A Solar Cycle of Radiation Measurements on the Surface of Mars, p.17, ${slides.url}`,
          `Second source: Posner, Richardson and Zeitlin, Mars Ground Level Enhancements in the Context of the Solar Energetic Particle Clock, Solar Physics 300, 102 (2025), ${paper.url}`,
        ],
        strength: STRENGTH,
        note: `Replay of real NASA MSL RAD data, not simulated. Fetched ${ev.fetched_at.slice(0, 10)}.`,
        back: "Back to the console",
      },
    ];
  }

  // Every line of the replay in screen order (for the wording test).
  const replayLines = (ev, e) => {
    const [before, c] = replay(ev, e);
    return [BUTTON, before, c.chip, c.badge, c.title, c.plain, c.label, ...c.numbers.flat(), ...c.notes, c.why, c.step, c.strength, "Sources", ...c.sources, c.note, c.back];
  };

  const api = { card, replay, replayLines, BUTTON };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Mars = api;
})(this);
