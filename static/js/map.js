/* City intelligence map: Leaflet + OpenStreetMap, markers coloured by priority. */
(function () {
  "use strict";

  var COLORS = { critical: "#B02B22", high: "#C2571F", medium: "#B07A06", low: "#2F7A5B" };

  function pin(level, reports) {
    var color = COLORS[(level || "low").toLowerCase()] || COLORS.low;
    return L.divIcon({
      className: "",
      html: '<div class="marker-pin" style="background:' + color + '"><b>' + reports + "</b></div>",
      iconSize: [26, 26],
      iconAnchor: [13, 26],
      popupAnchor: [0, -24]
    });
  }

  function popup(issue) {
    return (
      '<div style="min-width:210px">' +
      '<div style="font-weight:700;margin-bottom:2px">' + escapeHtml(issue.title) + "</div>" +
      '<div style="font-size:12px;color:#6B8190;margin-bottom:6px">' +
        escapeHtml(issue.code) + " &middot; " + escapeHtml(issue.category || "Uncategorised") + "</div>" +
      '<div style="font-size:13px"><b>Priority ' + issue.priority + "</b> (" + issue.level + ")<br>" +
        issue.reports + " citizen report(s) &middot; " + issue.supports + " supporting<br>" +
        "Status: " + escapeHtml(issue.status) +
        (issue.department ? "<br>Dept: " + escapeHtml(issue.department) : "") + "</div>" +
      '<a style="display:inline-block;margin-top:8px;font-weight:600" href="' +
        window.CP_ISSUE_URL.replace("0", issue.id) + '">Open issue</a></div>'
    );
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function init() {
    var el = document.getElementById("map");
    if (!el || typeof L === "undefined") return;

    var map = L.map("map", { scrollWheelZoom: true }).setView(
      [window.CP_MAP_CENTER[0], window.CP_MAP_CENTER[1]], 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);

    var layer = L.layerGroup().addTo(map);
    var status = document.getElementById("map-status");

    function load() {
      var params = new URLSearchParams();
      document.querySelectorAll("[data-map-filter]").forEach(function (sel) {
        if (sel.value) params.set(sel.getAttribute("data-map-filter"), sel.value);
      });
      if (status) status.textContent = "Loading issues...";
      fetch("/api/issues?" + params.toString())
        .then(function (r) { return r.json(); })
        .then(function (rows) {
          layer.clearLayers();
          var bounds = [];
          rows.forEach(function (issue) {
            L.marker([issue.lat, issue.lng], { icon: pin(issue.level, issue.reports), title: issue.title })
              .bindPopup(popup(issue)).addTo(layer);
            bounds.push([issue.lat, issue.lng]);
          });
          if (bounds.length) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
          if (status) {
            status.textContent = rows.length
              ? rows.length + " issue" + (rows.length === 1 ? "" : "s") + " on the map"
              : "No issues match these filters yet.";
          }
        })
        .catch(function () { if (status) status.textContent = "Could not load map data."; });
    }

    document.querySelectorAll("[data-map-filter]").forEach(function (sel) {
      sel.addEventListener("change", load);
    });
    load();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
