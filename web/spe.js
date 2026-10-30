"use strict";
// Words for the full-screen solar storm alert (design B1). No rule here: the live alert shows only when the
// Python rule fired on the latest cached NOAA reading (web/data/radiation.json, scripts/build_radiation_summary.py).
// The replay reads NOAA's listed values for one real event from web/data/spe-2024-09-09.json.
// tests/test_spe.py renders every card and runs each line through the wording check.
(function (root) {
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const day = (iso) => `${+iso.slice(8, 10)} ${MONTHS[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
  const utc = (iso) => `${iso.slice(11, 16)} UTC`;
  const REPLAY = "Replay of a real 2024 event, not today's data.";

  // The step and its sources, from the evidence map entry for solar_particle_event.
  const shared = (e) => ({
    step: e.countermeasure,
    sources: [
      `Source for the step: ${e.countermeasure_source}`,
      `Source for the alert: ${e.alert_source}`,
      `Source for the S1 level: ${e.threshold_source}`,
    ],
  });

  // null unless the rule fired on the latest cached reading.
  function live(r, e) {
    if (!r.fired) return null;
    return {
      ...shared(e),
      chip: "Cached NOAA data",
      reading: `Solar protons at 10 MeV or more: ${Math.round(r.flux_pfu)} pfu`,
      level: `At or above the NOAA S1 level of ${r.threshold_pfu} pfu`,
      when: `${r.time_tag.slice(0, 10)} ${utc(r.time_tag)} – latest NOAA GOES reading in the cache, cached ${r.fetched_at.slice(0, 10)}.`,
      events: [],
      source: `Source: NOAA GOES, ${r.source_url}`,
    };
  }

  // [line before the start, card at the S1 crossing, card at the maximum], in NOAA's order.
  function replay(ev, e) {
    const base = {
      ...shared(e),
      chip: "Replay – real NOAA data",
      events: ev.sources.map((s) => `Event values: ${s.name}, ${s.url}`),
      source: "Source: NOAA GOES, through NOAA's solar proton event list",
    };
    return [
      `Replay of a real NOAA event, ${day(ev.start)}. Before ${utc(ev.start)}: below the NOAA ${ev.level} level of ${ev.threshold_pfu} pfu.`,
      { ...base,
        reading: `Solar protons at 10 MeV or more: ${ev.threshold_pfu} pfu or more`,
        level: `Reached the NOAA ${ev.level} level of ${ev.threshold_pfu} pfu`,
        when: `${utc(ev.start)}, ${day(ev.start)} – start of the event in NOAA's list. ${REPLAY}` },
      { ...base,
        reading: `Solar protons at 10 MeV or more: ${ev.peak_pfu} pfu`,
        level: `Above the NOAA ${ev.level} level of ${ev.threshold_pfu} pfu`,
        when: `${utc(ev.maximum)}, ${day(ev.maximum)} – maximum in NOAA's list. ${REPLAY}` },
    ];
  }

  // Every line of a card, in screen order (for the wording test).
  const lines = (c) => [c.chip, "Shelter now", c.reading, c.level, c.when, c.step, ...c.sources, ...c.events, c.source];

  const api = { live, replay, lines };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.SPE = api;
})(this);
