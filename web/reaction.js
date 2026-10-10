"use strict";
// Reaction-test timing, kept apart from the page so tests/test_web.py can run it in node.
// Both ends of a round use performance.now(): the page records shownAt in the animation frame after the
// circle is drawn (so it is on screen), and pressedAt on the first pointerdown or touchstart of a tap.
(function (root) {
  const ROUNDS = 5;
  const GUESS_MS = 100;    // faster than this is not a reaction to the circle: a false start
  const SAME_TAP_MS = 50;  // a pointerdown and the touchstart of the same tap arrive this close together

  // One input event in a round. s = { state, shownAt, lastDownAt }; returns what the event means:
  // "start" (first tap begins the test), "false-start" (before the circle, or too fast), "hit" with ms,
  // "duplicate" (second event of a tap already counted) or "ignore" (between rounds, after the test).
  function press(s, pressedAt) {
    if (pressedAt - s.lastDownAt < SAME_TAP_MS) return { kind: "duplicate" };
    if (s.state === "idle") return { kind: "start" };
    if (s.state === "waiting") return { kind: "false-start" };
    if (s.state !== "go") return { kind: "ignore" };
    const ms = Math.round(pressedAt - s.shownAt);
    return ms < GUESS_MS ? { kind: "false-start" } : { kind: "hit", ms };
  }

  const delayMs = (random) => 1000 + random * 2000; // 1 to 3 s before the circle
  const median = (xs) => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)];

  const api = { ROUNDS, GUESS_MS, SAME_TAP_MS, press, delayMs, median };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.Reaction = api;
})(this);
