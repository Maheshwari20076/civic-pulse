/* Shared behaviour: icons, flash auto-dismiss, sidebar, animated counters. */
(function () {
  "use strict";

  function icons() {
    if (window.lucide && window.lucide.createIcons) window.lucide.createIcons();
  }

  function flashes() {
    document.querySelectorAll(".cp-flash .alert").forEach(function (el, i) {
      setTimeout(function () {
        el.classList.add("fade");
        setTimeout(function () { el.remove(); }, 300);
      }, 5000 + i * 400);
    });
  }

  function sidebar() {
    var toggle = document.querySelector(".sidebar-toggle");
    var bar = document.querySelector(".sidebar");
    var backdrop = document.querySelector(".sidebar-backdrop");
    if (!toggle || !bar) return;
    function close() { bar.classList.remove("open"); if (backdrop) backdrop.classList.remove("show"); }
    toggle.addEventListener("click", function () {
      bar.classList.toggle("open");
      if (backdrop) backdrop.classList.toggle("show");
    });
    if (backdrop) backdrop.addEventListener("click", close);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
  }

  /* Counters animate once on load; respects reduced-motion. */
  function counters() {
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var target = parseFloat(el.getAttribute("data-count")) || 0;
      var suffix = el.getAttribute("data-suffix") || "";
      if (reduce) { el.textContent = Math.round(target).toLocaleString() + suffix; return; }
      var start = performance.now(), dur = 900;
      function tick(now) {
        var p = Math.min(1, (now - start) / dur);
        var eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased).toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    icons(); flashes(); sidebar(); counters();
  });

  window.CivicPulse = { icons: icons };
})();
