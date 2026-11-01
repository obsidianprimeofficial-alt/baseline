"use strict";
// Light/Dark theme. A choice saved on this device wins; with none, the page is dark during the crew's
// planned sleep window and light outside it. Loaded in <head> so the first paint is already in the right
// theme. Storage can be blocked (private mode, settings): then the choice lasts until the page closes.
(function (root) {
  // Simulated crew schedule, not a NASA figure: planned sleep window 22:00 to 06:00, device local time.
  const SLEEP_START_HOUR = 22, SLEEP_END_HOUR = 6;
  const KEY = "baseline-theme";

  const byClock = (date) => {
    const h = date.getHours();
    return h >= SLEEP_START_HOUR || h < SLEEP_END_HOUR ? "dark" : "light";
  };
  function saved() {
    try { const t = localStorage.getItem(KEY); return t === "light" || t === "dark" ? t : null; } catch (e) { return null; }
  }
  // The daily check prompt on the first screen, from the same schedule. saved: the checks on this device (Store.load()),
  // empty when storage is blocked. Local dates, because saved_at is in UTC. Worked out when the screen is drawn: no timer.
  function dailyLine(now, saved) {
    if (saved.some((e) => new Date(e.saved_at).toDateString() === now.toDateString())) return "Today's daily check is done.";
    if (now.getHours() < SLEEP_END_HOUR) return `Next daily check: ${String(SLEEP_END_HOUR).padStart(2, "0")}:00 (after the planned sleep window).`;
    return "Today's daily check is due now.";
  }
  const current = () => document.documentElement.getAttribute("data-theme");
  function set(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem(KEY, theme); } catch (e) { /* storage blocked: keep it for this visit only */ }
  }

  const api = { SLEEP_START_HOUR, SLEEP_END_HOUR, byClock, dailyLine, current, set };
  if (typeof module === "object" && module.exports) module.exports = api;
  else {
    root.Theme = api;
    document.documentElement.setAttribute("data-theme", saved() || byClock(new Date()));
  }
})(this);
