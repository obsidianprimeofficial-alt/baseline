"use strict";
// Offline demo page. Every number comes from Rules (web/rules.js, a port of src/baseline/compute)
// run on the simulated fixture plus today's self-check. Nothing is fetched from outside this folder.

const TODAY = 29, NEXT = 30, ROUNDS = Reaction.ROUNDS;
const CHANNELS = ["heart_rate_bpm", "hrv_rmssd_ms", "spo2_pct", "core_temp_c", "sleep_hours", "mood_1to5", "reaction_ms"];const SELF_CHECK = ["reaction_ms", "sleep_hours", "mood_1to5"];
const PREFIX = { osdr: "OSD-", ntrs: "NTRS " };
const SIGNALS = {
  hrv_rmssd_ms: { name: "Heart rate variability", phrase: "Your heart rate variability today", unit: "ms", dp: 1, step: 10, low: "lower", high: "higher" },
  sleep_hours: { name: "Sleep", phrase: "Your sleep last night", unit: "hours", dp: 1, step: 1, low: "shorter", high: "longer" },
  reaction_ms: { name: "Reaction time", phrase: "Your reaction time today", unit: "ms", dp: 0, step: 50, low: "faster", high: "slower" },
  // step for the four below: the smallest of 0.25, 0.5, 1, 2, 2.5, 5, 10 that gives three ticks on days 29 and 30
  // of web/data/crew_a_anomaly.json (values plus usual range): 2 to 6 (mood then capped at 5), 50 to 70, 96 to 100, 36.5 to 37.0
  mood_1to5: { name: "Mood", phrase: "Your mood today", unit: "of 5", diffUnit: "points", dp: 1, step: 2, min: 1, max: 5, low: "lower", high: "higher" }, // axis kept on the 1-to-5 scale
  heart_rate_bpm: { name: "Heart rate", phrase: "Your heart rate today", unit: "beats a minute", dp: 0, step: 10, low: "lower", high: "higher" },
  spo2_pct: { name: "Blood oxygen", phrase: "Your blood oxygen today", unit: "percent", dp: 1, step: 2, low: "lower", high: "higher" },
  core_temp_c: { name: "Core temperature", phrase: "Your core temperature today", unit: "°C", dp: 2, step: 0.25, low: "lower", high: "higher" },
};

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const state = { fixture: [], evidence: {}, radiation: null, rows: [], flags: {}, day: TODAY, trials: [], recorded: false, charts: {}, current: null, range: 0 };

// ---------- text ----------

// Same forbidden-phrase check as src/baseline/compute/wording.py, run on every line before it is shown.
function put(el, text) {
  const hits = Rules.blocksDiagnostic(text);
  if (hits.length) console.error("Wording check blocked", hits, text);
  el.textContent = hits.length ? "Withheld: this line failed the wording check." : text;
  return el;
}
const make = (tag, text, cls) => { const el = put(document.createElement(tag), text); if (cls) el.className = cls; return el; };
const checked = (text) => put(document.createElement("span"), text).textContent; // for attributes such as aria-label

const fmt = (signal, v, unit = SIGNALS[signal].unit) => `${v.toFixed(SIGNALS[signal].dp)} ${unit}`;
// The numbers behind z (today, usual, spread) to one decimal everywhere; z uses the unrounded values,
// and the card and the queue summary say so (ROUNDING_NOTE). Display only.
const fmtZ = (r, v) => `${v.toFixed(1)} ${SIGNALS[r.signal].unit}`;
// A number with its unit, inside a sentence, goes in the number font (design: JetBrains Mono for numbers).
// Runs after put(), on text that already passed the wording check. Display only.
const NUM_UNIT = new RegExp(`(\\d+(?:\\.\\d+)? (?:${[...new Set(Object.values(SIGNALS).map((s) => s.unit)), "µGy", "pfu"].join("|")}))`);
function monoNums(el) {
  el.replaceChildren(...el.textContent.split(NUM_UNIT).map((part, i) =>
    (i % 2 ? Object.assign(document.createElement("span"), { className: "n", textContent: part }) : part)));
  return el;
}
const ROUNDING_NOTE = "Numbers are shown to one decimal; z uses the unrounded values.";
const signed = (z) => `${z < 0 ? "−" : "+"}${Math.abs(z).toFixed(1)}`;
const listWords = (xs) => (xs.length < 2 ? xs.join("") : `${xs.slice(0, -1).join(", ")} and ${xs.at(-1)}`);
const title = (r) => (r.signal ? SIGNALS[r.signal].name : "Several readings together");
const names = (r) => listWords(r.signals.map((s, i) => (i ? SIGNALS[s].name.toLowerCase() : SIGNALS[s].name)));
const flagsFor = (day) =>
  [...(state.flags[day] || [])].sort((a, b) => !a.signal - !b.signal || Math.abs(b.z) - Math.abs(a.z));
const windowDays = (r) => { const h = state.rows.slice(0, -1).slice(-r.window_days); return [h[0].day, h.at(-1).day]; };
const times = (z) => `${Math.abs(z).toFixed(1).replace(/\.0$/, "")}×`;

const WELL_OUTSIDE_Z = 3; // the same cut as CONFIRM_Z in rules.js; wording only, the rule is unchanged
const COUNT = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven"];
const ORDINAL = ["", "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"];

// Days in a row, ending today, that this signal has been outside its usual range (watch or confirmed).
function daysRunning(r) {
  let n = 1;
  while ((state.flags[state.day - n] || []).some((f) => f.signal === r.signal)) n++;
  return n;
}

function plainStatus(r) {
  if (!r.signal) return `${COUNT[r.signals.length] || r.signals.length} readings moved together within 48 hours.`;
  const where = Math.abs(r.z) >= WELL_OUTSIDE_Z ? "Well outside your usual range" : "Outside your usual range";
  const n = daysRunning(r);
  if (n > 1) return `${where}, ${ORDINAL[n] ? `${ORDINAL[n]} day` : `${n} days`} running.`;
  return r.status === "watch" ? `${where}, first day. Watching.` : `${where}.`;
}

function plainWords(r) {
  if (!r.signal) return `${r.signals.length} readings moved outside your usual range within 48 hours: ${names(r)}. This rule fires when two or more do.`;
  const s = SIGNALS[r.signal], diff = r.current - r.baseline_mean, [a, b] = windowDays(r);
  const pct = Math.round((Math.abs(diff) / r.baseline_mean) * 100);
  return `${s.phrase} was ${fmt(r.signal, r.current)}. Over days ${a} to ${b} it averaged ${fmt(r.signal, r.baseline_mean)}, ` +
    `so today is ${fmt(r.signal, Math.abs(diff), s.diffUnit)} ${diff < 0 ? s.low : s.high} (${pct} percent).`;
}

function sourceNote(r) {
  if (state.day === NEXT) return "Day 30 readings come from the simulated record.";
  if (!r.signal) return "Readings come from your self-check and the simulated wearable record.";
  if (r.signal === "reaction_ms" && state.rows.at(-1).reaction_recorded) {
    return "Today's value is the recorded day-29 self-check from the simulated record, as is your usual range.";
  }
  return SELF_CHECK.includes(r.signal)
    ? "Today's value comes from your self-check. Your usual range comes from the simulated record."
    : "This value comes from the simulated wearable record.";
}

// ---------- navigation ----------

function show(id, push = true) {
  for (const s of document.querySelectorAll("main > section")) s.hidden = s.id !== id;
  window.scrollTo(0, 0);
  $(id).querySelector("h1").focus();
  if (push) history.pushState({ screen: id }, ""); // no URL change: a reload still starts at the guide
}
document.addEventListener("click", (e) => { const go = e.target.closest("[data-go]"); if (go) show(go.dataset.go); });

// Browser back (or an iPhone swipe) walks the screens. The screens after the self-check need a saved
// check, so after "Start the demo again" an old entry shows the guide instead.
history.replaceState({ screen: "guide" }, "");
history.scrollRestoration = "manual";
window.addEventListener("popstate", (e) => {
  const id = e.state?.screen || "guide";
  show(state.rows.length || id === "today" ? id : "guide", false);
});

// ---------- screen 1: reaction test ----------

// Timing rules live in web/reaction.js. round tags each round so a late animation frame from an earlier
// round (for example after the tab was hidden) can never draw the circle or start the clock.
const rt = { state: "idle", timer: 0, shownAt: 0, lastDownAt: -Infinity, round: 0 };

function rtShow(text, sub = "", big = false) {
  $("rt-dot").hidden = true;
  $("rt-text").hidden = false;
  $("rt-text").textContent = text;
  $("rt-text").className = big ? "rt-big" : "";
  $("rt-sub").textContent = sub;
}

function rtStatus() {
  const done = state.trials.length;
  $("rt-status").textContent = done === ROUNDS
    ? `Rounds: ${state.trials.join(", ")} ms`
    : `Round ${done + 1} of ${ROUNDS}${done ? `. So far: ${state.trials.join(", ")} ms` : ""}`;
}

function rtNext() {
  const round = ++rt.round;
  rt.state = "waiting";
  rtShow("Wait for the circle");
  rtStatus();
  rt.timer = setTimeout(() => {
    // Draw the circle in the next frame; start the clock in the frame after, once it is on screen.
    requestAnimationFrame(() => {
      if (rt.round !== round || rt.state !== "waiting") return;
      $("rt-text").hidden = true;
      $("rt-sub").textContent = "";
      $("rt-dot").hidden = false;
      requestAnimationFrame(() => {
        if (rt.round !== round || rt.state !== "waiting") return;
        rt.shownAt = performance.now();
        rt.state = "go";
      });
    });
  }, Reaction.delayMs(Math.random()));
}

function rtPress(e) {
  if (e.type === "keydown") {
    if ((e.key !== " " && e.key !== "Enter") || e.repeat) return;
    e.preventDefault();
  }
  const now = performance.now(); // the same clock as shownAt; never e.timeStamp or Date.now()
  const r = Reaction.press(rt, now);
  if (r.kind === "duplicate") return;
  rt.lastDownAt = now;
  if (r.kind === "start") return rtNext();
  if (r.kind === "false-start") { // before the circle, or under 100 ms: this round starts again
    clearTimeout(rt.timer);
    rt.round++;
    rt.state = "pause";
    rtShow("Too soon", "This round starts again.");
    rt.timer = setTimeout(rtNext, 1200);
    return;
  }
  if (r.kind !== "hit") return;
  const ms = r.ms;
  state.trials.push(ms);
  if (state.trials.length < ROUNDS) {
    rt.state = "pause";
    rtShow(`${ms} ms`);
    rtStatus();
    rt.timer = setTimeout(rtNext, 900);
    return;
  }
  rt.state = "done";
  rtShow(`${median(state.trials)} ms`, "median of five rounds", true);
  rtStatus();
  $("rt-again").hidden = false;
}

const median = Reaction.median;

// The clock stops on the first of pointerdown or touchstart (old iOS has no pointer events); Reaction.press
// drops the second event of the same tap. Never click: it fires after the finger lifts.
$("rt-field").addEventListener("pointerdown", rtPress);
$("rt-field").addEventListener("touchstart", rtPress, { passive: true });
$("rt-field").addEventListener("keydown", rtPress);
$("rt-again").addEventListener("click", () => {
  state.trials = [];
  state.recorded = false;
  $("rt-again").hidden = true;
  rtNext();
  $("rt-field").focus();
});

// Demo fallback: the fixture's own day-29 reaction result, so the reaction flag fires every run.
// The live test and its threshold are unchanged; the screen says the value is recorded and simulated.
const recordedReaction = () => state.fixture.find((r) => r.day === TODAY).reaction_ms;
$("rt-recorded").addEventListener("click", () => {
  clearTimeout(rt.timer);
  rt.state = "done";
  state.trials = [];
  state.recorded = true;
  rtShow(fmt("reaction_ms", recordedReaction()), "Recorded, simulated", true);
  $("rt-status").textContent = "Day-29 self-check from the simulated record.";
  $("rt-again").hidden = false;
});

// Sleep hours: typed, or stepped by half an hour with − and +. Anything outside 0 to 12 is asked for again.
const sleepHours = () => { const v = $("sleep").valueAsNumber; return v >= 0 && v <= 12 ? v : NaN; };
for (const b of document.querySelectorAll("[data-step]")) {
  b.addEventListener("click", () => {
    const v = $("sleep").valueAsNumber, next = (Number.isNaN(v) ? 7 : v) + +b.dataset.step;
    $("sleep").value = Math.min(12, Math.max(0, Math.round(next * 2) / 2));
  });
}

const picked = (name) => document.querySelector(`input[name="${name}"]:checked`)?.value;

$("guide-start").addEventListener("click", () => { show("today"); $("rt-field").focus(); });

$("save").addEventListener("click", () => {
  const missing = [
    [state.trials.length === ROUNDS || state.recorded, "the reaction rounds", $("rt-field")],
    [!Number.isNaN(sleepHours()), "how long you slept (0 to 12 hours)", $("sleep")],
    [picked("quality"), "how well you slept", $("quality-1")],
    [picked("mood"), "your mood", $("mood-1")],
    [picked("vision"), "the near vision line", $("vision-clear")],
  ].filter(([ok]) => !ok);
  if (missing.length) {
    put($("missing"), `Still to do: ${listWords(missing.map((m) => m[1]))}.`);
    missing[0][2].focus();
    return;
  }
  $("missing").textContent = "";
  const check = {
    reaction_ms: state.recorded ? recordedReaction() : median(state.trials),
    reaction_recorded: state.recorded,
    sleep_hours: sleepHours(),
    note: $("note").value.trim(), // shown on the sleep card; no rule reads it
    mood_1to5: +picked("mood"),
    sleep_quality_1to5: +picked("quality"), // recorded for the summary; no rule scores it yet
    near_vision_ok: picked("vision") === "clear",
    saved_at: new Date().toISOString(),
  };
  openCheck(check, Store.add(check));
});

// ---------- the daily log on this device (web/store.js) ----------

const when = (iso) => new Date(iso).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

// Today's row = the simulated wearable values for day 29 + the self-check. A check the browser would not
// store loses its saved_at, so the console and the CSV never call it saved.
function openCheck(check, kept) {
  const own = kept ? check : { ...check, saved_at: undefined };
  state.rows = [...state.fixture.filter((r) => r.day < TODAY), { ...state.fixture.find((r) => r.day === TODAY), ...own, self_check: true }];
  put($("saved-line"), kept
    ? `Saved on this device, ${when(check.saved_at)}. Nothing leaves the device.`
    : "Not saved: this browser blocks storage, so this check is kept for this visit only.");
  recompute(TODAY);
  renderSavedBox();
  show("console");
}

function renderSavedBox() {
  const log = Store.load(), last = log.at(-1);
  $("saved-box").hidden = !last;
  if (last) put($("saved-text"), `${log.length} ${log.length === 1 ? "self-check is" : "self-checks are"} saved on this device. The latest is from ${when(last.saved_at)}.`);
}

function clearSaved() {
  Store.clear();
  for (const r of state.rows) delete r.saved_at;
  put($("saved-line"), "Saved days cleared. Only the simulated record is left.");
  renderSavedBox();
}
$("saved-clear").addEventListener("click", clearSaved);
$("clear-saved").addEventListener("click", clearSaved);
$("saved-open").addEventListener("click", () => { const last = Store.latest(); if (last) openCheck(last, true); else renderSavedBox(); });

// The CSV is built in the page and handed to the browser as a file; nothing is sent anywhere.
$("export").addEventListener("click", () => {
  const blob = new Blob([Store.csv(state.rows, Store.load())], { type: "text/csv;charset=utf-8" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `baseline-daily-log-day-${state.day}.csv` });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
});

// ---------- screen 2: console ----------

function recompute(day) {
  state.day = day;
  state.flags = Rules.evaluate(state.rows);
  $("day-label").textContent = `Day ${day}`;
  put($("flags-title"), day === TODAY ? "What changed today" : "What changed on day 30");
  renderConsole();
}

function drawChannel(signal) {
  // Band and marks come from the full record (web/trend.js); the 7-day view only cuts the last days off it.
  const full = Trend.series(state.rows, state.flags, signal, state.range);
  const { days, vals, band, marks } = full.shown, last = days.length - 1;
  const box = document.querySelector(`[data-signal="${signal}"]`), canvas = box.querySelector("canvas");
  const [ink, quiet, scrub, flag] = ["--ink", "--quiet", "--scrub", "--flag"].map(css), mono = { family: css("--mono") };
  const range = (b) => `${fmt(signal, b.mean - 2 * b.sd)} to ${fmt(signal, b.mean + 2 * b.sd)}`;
  const flagged = days.filter((_, i) => marks[i]);
  const bottom = signal === CHANNELS.at(-1), { step, min = 0, max = Infinity } = SIGNALS[signal];
  const span = [...full.vals, ...full.band.filter(Boolean).flatMap((b) => [b.mean - 2 * b.sd, b.mean + 2 * b.sd])];
  const yMin = Math.max(min, Math.floor(Math.min(...span) / step) * step); // three ticks, all whole steps; none below zero
  const yMax = Math.min(max, yMin + Math.ceil((Math.max(...span) - yMin) / (2 * step)) * 2 * step); // nor past the scale

  put(box.querySelector(".val"), fmt(signal, vals[last]));
  canvas.setAttribute("aria-label", checked(
    `${SIGNALS[signal].name}, days ${days[0]} to ${days[last]}. Today ${fmt(signal, vals[last])}; usual range ${range(band[last])}. ` +
    (flagged.length ? `Outside the usual range on day${flagged.length > 1 ? "s" : ""} ${listWords(flagged.map(String))}.` : "No day shown is outside the usual range.")));

  state.charts[signal]?.destroy();
  state.charts[signal] = new Chart(canvas, {
    type: "line",
    data: {
      labels: days,
      datasets: [
        {
          data: vals, order: 0, borderColor: ink, borderWidth: 1.5,
          pointRadius: (c) => (marks[c.dataIndex] ? 4.5 : c.dataIndex === last ? 3.5 : 0),
          pointHoverRadius: (c) => (marks[c.dataIndex] ? 5.5 : 4),
          pointBorderWidth: 2,
          pointBorderColor: (c) => (marks[c.dataIndex] ? flag : ink),
          pointBackgroundColor: (c) => (!marks[c.dataIndex] ? ink : marks[c.dataIndex].status === "confirmed" ? flag : scrub),
        },
        { data: band.map((b) => b && b.mean - 2 * b.sd), order: 1, borderWidth: 0, pointRadius: 0, fill: false },
        { data: band.map((b) => b && b.mean + 2 * b.sd), order: 1, borderWidth: 0, pointRadius: 0, fill: "-1", backgroundColor: css("--band") },
      ],
    },
    options: {
      animation: false,
      maintainAspectRatio: false,
      layout: { padding: { top: 6, right: 8 } },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          filter: (item) => item.datasetIndex === 0,
          displayColors: false, backgroundColor: ink, titleColor: scrub, bodyColor: scrub, cornerRadius: 4, padding: 8,
          callbacks: {
            title: (items) => `Day ${items[0].label}`,
            label: (item) => fmt(signal, item.raw),
            afterLabel: (item) => (band[item.dataIndex] ? `Usual ${range(band[item.dataIndex])}` : "Still learning your usual range"),
          },
        },
      },
      scales: {
        x: {
          display: bottom,
          grid: { display: false },
          border: { color: css("--rule") },
          ticks: {
            autoSkip: false, maxRotation: 0, color: quiet, font: mono,
            callback: (_, i) => { const d = days[i]; return state.range || d === 1 || d % 10 === 0 || i === last ? d : ""; }, // 7 days: every day
          },
        },
        y: {
          display: false, // no y labels (design); the range is in the canvas label, so every strip lines up
          min: yMin, // fit the data, not zero, so a drift is visible
          max: yMax,
        },
      },
    },
  });
}

// Light/Dark switch in the header (web/theme.js picks the first theme). Charts read the colours when drawn.
function themeLabel() {
  $("theme-btn").setAttribute("aria-label", Theme.current() === "dark" ? "Switch to light theme" : "Switch to dark theme");
}
themeLabel();
$("theme-btn").addEventListener("click", () => {
  Theme.set(Theme.current() === "dark" ? "light" : "dark");
  themeLabel();
  if (Object.keys(state.charts).length) CHANNELS.forEach(drawChannel);
});

// 7 days · 30 days switch (design P7b). Not saved on the device; "Start the demo again" sets it back to 30 days.
function setRange(days) {
  state.range = days;
  for (const b of document.querySelectorAll("[data-range]")) b.setAttribute("aria-pressed", String(+b.dataset.range === days));
  if (!state.rows.length) return;
  put($("console-days"), `Your last ${days ? Math.min(days, state.rows.length) : state.rows.length} days`);
  CHANNELS.forEach(drawChannel);
}
for (const b of document.querySelectorAll("[data-range]")) b.addEventListener("click", () => setRange(+b.dataset.range));

function renderConsole() {
  const day = state.day, n = flagsFor(day).filter((r) => r.signal).length;
  put($("legend-band"), `Usual range (from day ${Rules.MIN_HISTORY_DAYS + 1}, ±${Rules.THRESHOLD} SD)`);
  setRange(state.range); // draws the charts
  put($("console-summary"), n === 0
    ? "Nothing is outside your usual range today."
    : `${n} ${n === 1 ? "reading is" : "readings are"} outside your usual range today.`);
  $("to-flags").hidden = n === 0 && !state.radiation.fired;
  $("followup").hidden = day !== NEXT;
  $("restart").hidden = day !== NEXT;
  if (day === NEXT) renderFollowUp();
  renderFlags();
}

// Real NOAA GOES data from web/data/radiation.json (built by scripts/build_radiation_summary.py from the cache).
function radiationReading() {
  const r = state.radiation;
  return { flux: r.flux_pfu >= 10 ? Math.round(r.flux_pfu) : r.flux_pfu.toFixed(2), time: r.time_tag.slice(0, 16).replace("T", " ") };
}

function renderRadiation() {
  const r = state.radiation, { flux, time } = radiationReading();
  monoNums(put($("rad-line"), `Solar protons at 10 MeV or more: ${flux} pfu at ${time} UTC, ` +
    `${r.fired ? "at or above" : "below"} the NOAA alert level of ${r.threshold_pfu} pfu.`));
  put($("rad-source"), `Source: NOAA GOES, cached ${r.fetched_at.slice(0, 10)}`);
  $("radiation").classList.toggle("fired", r.fired);
  renderMarsDose(r.msl_rad);
}

// Mars surface dose measured by the Radiation Assessment Detector on the Curiosity rover (MSL RAD),
// mean of one UTC day, compared with the mean of the earlier days in the cache (same 2-SD rule as the vitals).
function renderMarsDose(m) {
  const level = m.dose_ugy_day.toFixed(0), day = m.date;
  const compare = m.z === null ? `Fewer than ${m.window_days + 1} earlier days cached, so no comparison yet.`
    : `${m.fired ? "Above" : "Within"} the usual range of the previous ${m.window_days} days (mean ${m.baseline_mean.toFixed(0)}, ±2 SD).`;
  monoNums(put($("mars-line"), `Mars surface radiation on ${day}: ${level} µGy per day (tissue-equivalent detector, ${m.n_obs} readings). ${compare}`));
  put($("mars-source"), `Source: NASA MSL RAD via SPDF CDAWeb, DOI ${m.doi}, cached ${m.fetched_at.slice(0, 10)}`);
}

// ---------- screen 6: next day ----------

function renderFollowUp() {
  const list = $("follow-list"), rows = state.rows;
  list.replaceChildren();
  for (const prev of (state.flags[TODAY] || []).filter((r) => r.signal)) {
    const s = prev.signal, now = Rules.ruleZscore(s, rows.slice(0, -1).map((r) => r[s]), rows.at(-1)[s]);
    const verdict = !now.fired ? "Back inside your usual range."
      : Math.abs(now.z) < Math.abs(prev.z) ? "Closer to your usual range, still outside it."
      : "Still outside your usual range.";
    const li = document.createElement("li");
    li.className = now.fired ? "outside" : "recovered"; // recovered rows carry a check mark
    li.append(make("strong", SIGNALS[s].name), monoNums(make("span", `${fmt(s, prev.current)} yesterday, ${fmt(s, now.current)} today. ${verdict}`, "num")));
    list.append(li);
  }
}

// ---------- screen 3: flag list ----------

function renderFlags() {
  const day = state.day, row = state.rows.at(-1), list = $("flag-list");
  const h = state.rows.slice(0, -1);
  put($("flags-meta"), `Day ${day} compared with your days ${h[0].day} to ${h.at(-1).day}.`);
  list.replaceChildren();
  if (state.radiation.fired) {
    // The step shows with "no source cached" until the research lead adds a sourced entry to the evidence map.
    const e = state.evidence.solar_particle_event || {}, sourced = e.countermeasure && e.countermeasure_source;
    const { flux, time } = radiationReading(), li = document.createElement("li");
    li.className = "spe-row";
    li.append(
      make("span", "Solar particle event", "flag-name"),
      monoNums(make("span", `${flux} pfu at ${time} UTC. NOAA alert level: ${state.radiation.threshold_pfu} pfu.`, "flag-line")),
      make("span", `Countermeasure: ${sourced ? e.countermeasure : "Move to the shielded area."}`, "flag-line"),
      make("span", `Source: ${sourced ? e.countermeasure_source : "no source cached"}`, "flag-status"),
    );
    list.append(li);
  }
  for (const r of flagsFor(day)) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `flag ${r.status}`;
    b.append(
      make("span", title(r), "flag-name"),
      monoNums(make("span", r.signal ? `${fmt(r.signal, r.current)} today. Your usual: ${fmt(r.signal, r.baseline_mean)}.` : `${names(r)}.`, "flag-line")),
      make("span", plainStatus(r), "flag-status"),
    );
    b.addEventListener("click", () => { renderEvidence(r); show("evidence"); });
    const li = document.createElement("li");
    li.append(b);
    list.append(li);
    // Trend card (design P2b) under a flag that has been outside the usual range 3 days running (web/projection.js).
    const p = r.signal && Projection.projection(state.rows, r.signal, state.flags);
    if (p) {
      const [text, meta] = Projection.lines(p, SIGNALS[r.signal]), card = document.createElement("li");
      card.className = "trend-card";
      card.append(monoNums(make("p", text)), make("p", meta, "meta"));
      list.append(card);
    }
  }
  $("flag-note").hidden = row.near_vision_ok !== false;
  put($("flag-note"), "You reported blurred near vision. No rule scores this yet; it goes into the summary for the flight surgeon.");
}

// ---------- screen 4: evidence card ----------

// Bold the evidence map's key_finding inside the study sentence, after the wording check passes.
function putBold(el, text, key) {
  put(el, text);
  const i = key ? text.indexOf(key) : -1;
  if (i < 0 || el.textContent !== text) return;
  const strong = document.createElement("strong");
  strong.textContent = key;
  el.replaceChildren(text.slice(0, i), strong, text.slice(i + key.length));
}

// "NTRS 1, Title, https://...; NTRS 2, Title, https://..." -> [{label: "NTRS 1", url}, ...].
// A part without a URL (for example "to be confirmed by research lead") stays plain text.
const sourceRefs = (src) => src.split(";").map((part) => {
  const url = part.match(/https:\/\/\S+/);
  return { label: url ? part.split(",")[0].trim() : part.trim(), url: url && url[0] };
});

// "Source: " then each reference as a link. Links open in a new tab and are never fetched by the page.
function putSources(el, refs) {
  const text = `Source: ${refs.map((s) => s.label).join("; ")}`;
  if (put(el, text).textContent !== text) return;
  el.replaceChildren("Source: ", ...refs.flatMap((s, i) => {
    const a = s.url ? Object.assign(document.createElement("a"), { href: s.url, target: "_blank", rel: "noopener noreferrer", textContent: s.label }) : s.label;
    return i ? ["; ", a] : [a];
  }));
}

function renderEvidence(r) {
  state.current = r;
  const e = state.evidence[r.rule] || {}, note = r.signal === "sleep_hours" && state.rows.at(-1).note;
  put($("ev-title"), title(r));
  put($("ev-plain"), plainWords(r));
  $("ev-note").hidden = !note;
  put($("ev-note"), note ? `Your note: ${note}` : "");

  const numbers = r.signal
    ? [
      ["Today", fmtZ(r, r.current)],
      [`Your usual (mean of ${r.window_days} days)`, fmtZ(r, r.baseline_mean)],
      ["Usual spread (1 SD)", fmtZ(r, r.baseline_sd)],
      ["How far", `${times(r.z)} your usual spread (flag at ${Rules.THRESHOLD}×)`],
      ["Status", plainStatus(r)],
    ]
    : [
      ["Window", `48 hours, days ${state.day - 1} and ${state.day}`],
      ["Readings", names(r)],
      ["Flags when", "2 or more readings are outside your usual range"],
      ["Status", plainStatus(r)],
    ];
  $("ev-numbers").classList.toggle("nums", !!r.signal); // today, usual and spread in the number font
  $("ev-numbers").replaceChildren(...numbers.flatMap(([k, v]) => [make("dt", k), make("dd", v)]));

  // A study is shown only with its id, title and URL; a step only with its source.
  const study = e.source_id != null && PREFIX[e.source_type] && e.title && e.url;
  $("ev-words").hidden = study && !e.plain_words;
  if (study) putBold($("ev-words"), e.plain_words || "", e.key_finding);
  else put($("ev-words"), "No matching study cached.");
  $("ev-study").hidden = !study;
  if (study) putSources($("ev-study"), [{ label: `${PREFIX[e.source_type]}${e.source_id} — ${e.title}`, url: e.url }]);

  const step = e.countermeasure && e.countermeasure_source;
  put($("ev-step"), step ? e.countermeasure : "No countermeasure step cached for this rule yet.");
  $("ev-step-source").hidden = !step;
  if (step) putSources($("ev-step-source"), sourceRefs(e.countermeasure_source));
  put($("ev-source"), sourceNote(r));
  put($("ev-rule"), `Rule: ${r.rule}`);
}

// ---------- screen 5: queue for flight surgeon ----------

$("queue-btn").addEventListener("click", () => {
  const row = state.rows.at(-1), lines = [`Crew member A, day ${state.day}. Telemetry is simulated.`];
  for (const r of flagsFor(state.day)) {
    lines.push(r.signal
      ? `${title(r)}: ${fmtZ(r, r.current)}, usual ${fmtZ(r, r.baseline_mean)} over ${r.window_days} days, z = ${signed(r.z)}, ${r.status === "confirmed" ? "flagged" : "watching"} (rule ${r.rule}).`
      : `${names(r)} moved together within 48 hours (rule ${r.rule}).`);
  }
  if (row.self_check) {
    lines.push(`Self-check: reaction ${fmt("reaction_ms", row.reaction_ms)} ${row.reaction_recorded ? "(recorded, simulated)" : "median of five"}, slept ${fmt("sleep_hours", row.sleep_hours)}, ` +
      `sleep quality ${row.sleep_quality_1to5} of 5, mood ${fmt("mood_1to5", row.mood_1to5)}, near vision ${row.near_vision_ok ? "clear" : "blurred"}.`);
    if (row.note) lines.push(`Sleep note: ${row.note}`); // own line, so a failed wording check withholds only the note
  }
  lines.push(ROUNDING_NOTE);
  $("message").replaceChildren(...lines.map((l) => make("p", l)));
  $("next-day").hidden = state.day === NEXT;
  show("queue");
});

$("next-day").addEventListener("click", () => {
  state.rows = [...state.rows, state.fixture.find((r) => r.day === NEXT)];
  recompute(NEXT);
  show("console");
});

// Reset in memory, not by reloading, so a phone that loaded the page once can run the demo again offline.
$("restart").addEventListener("click", () => {
  clearTimeout(rt.timer);
  rt.state = "idle";
  Object.assign(state, { rows: [], flags: {}, day: TODAY, trials: [], recorded: false, current: null });
  setRange(0); // back to 30 days
  rtShow("Tap here to start");
  rtStatus();
  $("rt-again").hidden = true;
  $("sleep").value = 7;
  $("note").value = "";
  for (const input of document.querySelectorAll('#today input[type="radio"]')) input.checked = false;
  $("missing").textContent = "";
  $("day-label").textContent = `Day ${TODAY}`;
  $("saved-line").textContent = "";
  renderSavedBox(); // the saved log is kept; only the demo state resets
  show("guide");
});

// ---------- start ----------

(async function init() {
  try {
    const [fixture, evidence, radiation] = await Promise.all(
      // no-store: a copy cached by an older server must never stand in for today's data
      ["data/crew_a_anomaly.json", "data/evidence_map.json", "data/radiation.json"].map((p) => fetch(p, { cache: "no-store" }).then((r) => r.json())));
    state.fixture = fixture.rows;
    state.evidence = evidence;
    state.radiation = radiation;
    renderRadiation();
    $("save").disabled = $("rt-recorded").disabled = $("saved-open").disabled = false; // all read the record; disabled in the HTML until it is here
    renderSavedBox();
  } catch (err) {
    put($("missing"), "The simulated record did not load. Start the page with: python -m baseline.serve");
    $("save").disabled = true;
    $("rt-recorded").disabled = true;
    $("saved-open").disabled = true;
    throw err;
  }
  await document.fonts.load('16px "Source Sans 3"');
  Chart.defaults.font = { family: '"Source Sans 3", system-ui, sans-serif', size: 12 };
  const blocked = Rules.blocksDiagnostic(document.body.textContent);
  if (blocked.length) console.error("Static page text fails the wording check:", blocked);
})();
