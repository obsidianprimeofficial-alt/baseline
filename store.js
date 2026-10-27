"use strict";
// The daily log kept on this device. A saved self-check goes into this browser's own storage
// (localStorage) and nowhere else: no server, no cloud, no network. Every read and write is wrapped,
// so a browser that blocks storage (private mode, cleared site data) still runs the page; the check
// is then kept for this visit only. tests/test_web.py runs this file in node with a stand-in storage.
(function (root) {
  const KEY = "baseline.log.v1", MAX = 400;
  const SELF = ["reaction_ms", "reaction_recorded", "sleep_hours", "sleep_quality_1to5", "mood_1to5", "near_vision_ok", "note"];
  const COLUMNS = ["day", "source", "saved_at", "heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "core_temp_c", "sleep_hours",
    "exercise_min", "reaction_ms", "reaction_recorded", "sleep_quality_1to5", "mood_1to5", "near_vision_ok", "note"];

  function area(s) { try { return s || root.localStorage || null; } catch (e) { return null; } }
  const valid = (e) => e && typeof e === "object" && typeof e.saved_at === "string" &&
    ["reaction_ms", "sleep_hours", "mood_1to5"].every((k) => typeof e[k] === "number" && Number.isFinite(e[k]));

  function load(s) {
    try {
      const v = JSON.parse(area(s).getItem(KEY) || "[]");
      return Array.isArray(v) ? v.filter(valid) : [];
    } catch (e) { return []; }
  }

  // Keeps only the self-check fields; the wearable columns stay in the simulated record.
  function pick(check) {
    const e = { saved_at: check.saved_at };
    for (const k of SELF) if (k in check) e[k] = check[k];
    return e;
  }

  // Returns true when the check is stored on the device, false when storage is blocked.
  function add(check, s) {
    try {
      const log = [...load(s), pick(check)].slice(-MAX);
      area(s).setItem(KEY, JSON.stringify(log));
      return load(s).length === log.length;
    } catch (e) { return false; }
  }

  function clear(s) { try { area(s).removeItem(KEY); return true; } catch (e) { return false; } }
  const latest = (s) => load(s).at(-1) || null;

  // One CSV cell: quoted when needed; a leading = + - @ is prefixed so a spreadsheet never runs it as a formula.
  function cell(v) {
    let t = v === undefined || v === null ? "" : String(v);
    if (/^[=+\-@]/.test(t) && !/^-?\d/.test(t)) t = "'" + t;
    return /[",\r\n]/.test(t) ? `"${t.replace(/"/g, '""')}"` : t;
  }

  // shown: the rows on the console (simulated days, then today's check). saved: every check on this device.
  // Checks saved on this device that are not on the console are listed after the shown days, without a day number.
  function csv(shown, saved) {
    const source = (r) => (!r.self_check ? "simulated"
      : r.saved_at ? "self-check saved on this device; wearable columns simulated"
      : "self-check (not saved); wearable columns simulated");
    const onScreen = new Set(shown.map((r) => r.saved_at).filter(Boolean));
    const rows = [
      ...shown.map((r) => ({ ...r, source: source(r) })),
      ...saved.filter((e) => !onScreen.has(e.saved_at)).map((e) => ({ ...e, day: "", source: "earlier self-check saved on this device" })),
    ];
    return [COLUMNS.join(","), ...rows.map((r) => COLUMNS.map((c) => cell(r[c])).join(","))].join("\r\n") + "\r\n";
  }

  const api = { KEY, MAX, COLUMNS, load, add, clear, latest, csv };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Store = api;
})(this);
