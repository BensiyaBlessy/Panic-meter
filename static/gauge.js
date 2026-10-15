function ringEmpty() {
  return document.documentElement.dataset.theme === "dark" ? "#2b3a55" : "#e3e8ef";
}

function drawGauge(id) {
  const el = document.getElementById(id);
  const score = Number(el.dataset.score);
  const color = score <= 30 ? "#2ecc71" : score <= 60 ? "#f1c40f" : score <= 80 ? "#e67e22" : "#e74c3c";
  el._chart = new Chart(el, {
    type: "doughnut",
    data: { datasets: [{ data: [score, 100 - score], backgroundColor: [color, ringEmpty()], borderWidth: 0 }] },
    options: { rotation: -90, circumference: 180, cutout: "76%",
      plugins: { legend: { display: false }, tooltip: { enabled: false } } }
  });
}

function drawTrend(id) {
  const el = document.getElementById(id);
  const raw = document.getElementById("trend-data");
  if (!el || !raw) return;
  const data = JSON.parse(raw.textContent);
  new Chart(el, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [{
        data: data.scores,
        borderColor: "#ff6b35",
        backgroundColor: "rgba(255,107,53,.15)",
        fill: true,
        tension: 0.3,
        pointRadius: 4,
        pointBackgroundColor: "#ff6b35"
      }]
    },
    options: {
      maintainAspectRatio: false,
      scales: {
        y: { min: 0, max: 100, ticks: { color: "#8a98ad" }, grid: { color: "rgba(138,152,173,.25)" } },
        x: { ticks: { color: "#8a98ad", maxRotation: 45 }, grid: { display: false } }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function drawForecast(id) {
  const el = document.getElementById(id);
  const raw = document.getElementById("forecast-data");
  if (!el || !raw) return;
  const d = JSON.parse(raw.textContent);
  new Chart(el, {
    type: "bar",
    data: {
      labels: d.labels,
      datasets: [
        {
          type: "bar",
          label: "Hours needed",
          data: d.hours,
          backgroundColor: d.hours.map(function (h) { return h > d.cap ? "#e74c3c" : "#ff6b35"; }),
          borderRadius: 6
        },
        {
          type: "line",
          label: "Hours available",
          data: d.labels.map(function () { return d.cap; }),
          borderColor: "#4c9aff",
          borderDash: [6, 4],
          borderWidth: 2,
          pointRadius: 0
        }
      ]
    },
    options: {
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, ticks: { color: "#8a98ad" }, grid: { color: "rgba(138,152,173,.25)" } },
        x: { ticks: { color: "#8a98ad" }, grid: { display: false } }
      },
      plugins: { legend: { labels: { color: "#8a98ad" } } }
    }
  });
}