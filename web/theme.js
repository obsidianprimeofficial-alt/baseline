"use strict";
// The page is dark only (Hrishin, 11 Nov 2026): web/tokens.css has one palette, so nothing here picks a theme,
// reads the device clock for it or reads a saved choice. What is left is the simulated crew schedule for the
// daily check prompt on the first screen.
(function (root) {
  // Simulated crew schedule, not a NASA figure: planned sleep window ends 06:00, device local time.
  const SLEEP_END_HOUR = 6;

  // The daily check prompt on the first screen, from the same schedule. saved: the checks on this device (Store.load()),
  // empty when storage is blocked. Local dates, because saved_at is in UTC. Worked out when the screen is drawn: no timer.
  function dailyLine(now, saved) {
    if (saved.some((e) => new Date(e.saved_at).toDateString() === now.toDateString())) return "Today's daily check is done.";
    if (now.getHours() < SLEEP_END_HOUR) return `Next daily check: ${String(SLEEP_END_HOUR).padStart(2, "0")}:00 (after the planned sleep window).`;
    return "Today's daily check is due now.";
  }

  const api = { SLEEP_END_HOUR, dailyLine };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Theme = api;
})(this);
