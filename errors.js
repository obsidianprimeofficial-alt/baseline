"use strict";
// Shows any uncaught script error at the top of the page (message, file, line), so it can be read on a
// phone with no developer tools. Loaded before every other script, and written for old browsers on purpose.
(function () {
  function show(text) {
    var el = document.getElementById("js-error");
    if (!el) return;
    el.hidden = false;
    el.textContent = el.textContent ? el.textContent + "\n" + text : text;
  }
  window.addEventListener("error", function (e) {
    var file = e.filename ? String(e.filename).split("/").pop().split("?")[0] : "unknown file";
    show("Script error: " + e.message + " (" + file + ", line " + e.lineno + (e.colno ? ", column " + e.colno : "") + ")");
  });
  window.addEventListener("unhandledrejection", function (e) {
    var r = e.reason;
    show("Script error: " + (r && r.message ? r.message : String(r)) + (r && r.stack ? " (" + String(r.stack).split("\n")[0] + ")" : ""));
  });
})();
