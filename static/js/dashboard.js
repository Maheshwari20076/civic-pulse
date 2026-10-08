/* Analytics charts. Every dataset comes from /admin/api/analytics. */
(function () {
  "use strict";

  var INK = "#0F2430", GRID = "#EDF2F4";
  var PALETTE = ["#14566B", "#E4930B", "#2F7A5B", "#B02B22", "#4F3FA8", "#C2571F",
                 "#6B8190", "#0E3F4F", "#B07A06", "#2E7D9B"];

  function base(extra) {
    return Object.assign({
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: INK, font: { family: "Public Sans", size: 12 } } } }
    }, extra || {});
  }

  function scales() {
    return {
      x: { ticks: { color: "#6B8190" }, grid: { display: false } },
      y: { ticks: { color: "#6B8190", precision: 0 }, grid: { color: GRID }, beginAtZero: true }
    };
  }

  function make(id, config) {
    var el = document.getElementById(id);
    if (!el) return;
    return new Chart(el.getContext("2d"), config);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof Chart === "undefined" || !document.getElementById("chart-category")) return;

    fetch("/admin/api/analytics")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var cat = d.by_category.filter(function (x) { return x.value > 0; });
        make("chart-category", {
          type: "doughnut",
          data: {
            labels: cat.map(function (x) { return x.label; }),
            datasets: [{ data: cat.map(function (x) { return x.value; }), backgroundColor: PALETTE,
                         borderWidth: 2, borderColor: "#fff" }]
          },
          options: base({ cutout: "58%", plugins: { legend: { position: "right",
            labels: { color: INK, boxWidth: 12, font: { family: "Public Sans", size: 12 } } } } })
        });

        make("chart-status", {
          type: "bar",
          data: {
            labels: d.by_status.map(function (x) { return x.label; }),
            datasets: [{ label: "Issues", data: d.by_status.map(function (x) { return x.value; }),
                         backgroundColor: "#14566B", borderRadius: 6 }]
          },
          options: base({ scales: scales(), plugins: { legend: { display: false } } })
        });

        make("chart-priority", {
          type: "bar",
          data: {
            labels: d.priority.map(function (x) { return x.label; }),
            datasets: [{ label: "Issues", data: d.priority.map(function (x) { return x.value; }),
                         backgroundColor: ["#2F7A5B", "#B07A06", "#C2571F", "#B02B22"], borderRadius: 6 }]
          },
          options: base({ scales: scales(), plugins: { legend: { display: false } } })
        });

        make("chart-reports", {
          type: "line",
          data: {
            labels: d.reports_over_time.labels,
            datasets: [{ label: "Citizen reports", data: d.reports_over_time.values,
                         borderColor: "#14566B", backgroundColor: "rgba(20,86,107,.12)",
                         fill: true, tension: .35, pointRadius: 2 }]
          },
          options: base({ scales: scales() })
        });

        make("chart-department", {
          type: "bar",
          data: {
            labels: d.by_department.map(function (x) { return x.label; }),
            datasets: [{ label: "Open issues", data: d.by_department.map(function (x) { return x.value; }),
                         backgroundColor: "#E4930B", borderRadius: 6 }]
          },
          options: base({ indexAxis: "y", scales: scales(), plugins: { legend: { display: false } } })
        });

        make("chart-resolution", {
          type: "line",
          data: {
            labels: d.resolution_trend.labels,
            datasets: [{ label: "Issues resolved", data: d.resolution_trend.values,
                         borderColor: "#2F7A5B", backgroundColor: "rgba(47,122,91,.12)",
                         fill: true, tension: .35, pointRadius: 2 }]
          },
          options: base({ scales: scales() })
        });
      })
      .catch(function () {
        document.querySelectorAll(".chart-box").forEach(function (b) {
          b.innerHTML = '<p class="muted small">Chart data could not be loaded.</p>';
        });
      });
  });
})();
