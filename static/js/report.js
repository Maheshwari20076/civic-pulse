/* Report form: geolocation, draggable map pin, live duplicate check. */
(function () {
  "use strict";

  var map, marker, latInput, lngInput, addressInput, dupBox;

  function setPoint(lat, lng, zoom) {
    latInput.value = lat.toFixed(7);
    lngInput.value = lng.toFixed(7);
    if (marker) marker.setLatLng([lat, lng]);
    else marker = L.marker([lat, lng], { draggable: true }).addTo(map).on("dragend", function (e) {
      var p = e.target.getLatLng();
      setPoint(p.lat, p.lng);
      checkDuplicates();
    });
    if (zoom) map.setView([lat, lng], zoom);
    var readout = document.getElementById("coord-readout");
    if (readout) readout.textContent = lat.toFixed(5) + ", " + lng.toFixed(5);
    checkDuplicates();
  }

  function locate() {
    var btn = document.getElementById("use-location");
    var note = document.getElementById("geo-note");
    if (!navigator.geolocation) {
      note.textContent = "This browser cannot share a location. Tap the map to place the pin instead.";
      return;
    }
    btn.disabled = true;
    note.textContent = "Finding your location...";
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        btn.disabled = false;
        note.textContent = "Location set. Drag the pin if it is slightly off.";
        setPoint(pos.coords.latitude, pos.coords.longitude, 17);
      },
      function () {
        btn.disabled = false;
        note.textContent = "Location was not shared. Tap the map to place the pin instead.";
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  }

  var dupTimer;
  function checkDuplicates() {
    clearTimeout(dupTimer);
    dupTimer = setTimeout(runDuplicateCheck, 500);
  }

  function runDuplicateCheck() {
    if (!dupBox || !latInput.value || !lngInput.value) return;
    var description = document.getElementById("description").value;
    var title = document.getElementById("title").value;
    if ((title + description).trim().length < 8) return;

    fetch("/api/find-duplicates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: title,
        description: description,
        category: (document.querySelector("input[name=category]:checked") || {}).value || null,
        latitude: latInput.value,
        longitude: lngInput.value
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.matches || !data.matches.length) { dupBox.innerHTML = ""; return; }
        var top = data.matches[0];
        dupBox.innerHTML =
          '<div class="cp-card cp-card-pad" style="border-left:4px solid var(--amber)">' +
          '<div style="font-weight:700">' + data.count + " similar report" +
          (data.count === 1 ? "" : "s") + " already nearby</div>" +
          '<div class="small muted" style="margin-top:.2rem">Closest: ' + top.code + " &mdash; " +
          escapeHtml(top.title) + " (" + top.reports + " reports, " + top.distance_m + " m away)." +
          " Submitting will strengthen that issue instead of creating a duplicate.</div></div>";
      })
      .catch(function () { /* silent: this is an optional hint */ });
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function previewImage(input) {
    var box = document.getElementById("image-preview");
    if (!input.files || !input.files[0]) { box.innerHTML = ""; return; }
    var file = input.files[0];
    if (file.size > 5 * 1024 * 1024) {
      box.innerHTML = '<span class="text-danger small">That image is over 5 MB. Choose a smaller one.</span>';
      input.value = "";
      return;
    }
    var url = URL.createObjectURL(file);
    box.innerHTML = '<img src="' + url + '" alt="Selected photo preview" style="max-height:130px;border-radius:10px">';
  }

  document.addEventListener("DOMContentLoaded", function () {
    latInput = document.getElementById("latitude");
    lngInput = document.getElementById("longitude");
    addressInput = document.getElementById("address");
    dupBox = document.getElementById("duplicate-hint");
    var mapEl = document.getElementById("pick-map");
    if (!mapEl || typeof L === "undefined") return;

    map = L.map("pick-map").setView(window.CP_MAP_CENTER, 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    map.on("click", function (e) { setPoint(e.latlng.lat, e.latlng.lng); });

    if (latInput.value && lngInput.value) {
      setPoint(parseFloat(latInput.value), parseFloat(lngInput.value), 16);
    }

    document.getElementById("use-location").addEventListener("click", locate);
    ["title", "description"].forEach(function (id) {
      document.getElementById(id).addEventListener("input", checkDuplicates);
    });
    var image = document.getElementById("image");
    if (image) image.addEventListener("change", function () { previewImage(image); });

    var form = document.getElementById("report-form");
    form.addEventListener("submit", function () {
      var btn = document.getElementById("submit-btn");
      btn.disabled = true;
      btn.innerHTML = "Analysing report...";
    });
  });
})();
