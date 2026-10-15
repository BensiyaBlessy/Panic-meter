// ---------- Toast popup ----------
function toast(msg, type, ms) {
  type = type || "info";
  ms = ms || 3800;
  const box = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = "toast " + type;
  el.textContent = msg;
  el.onclick = () => el.remove();
  box.appendChild(el);
  setTimeout(() => {
    el.classList.add("hide");
    setTimeout(() => el.remove(), 350);
  }, ms);
}

// ---------- Confetti ----------
function confetti() {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const c = document.createElement("canvas");
  c.id = "confetti";
  document.body.appendChild(c);
  const ctx = c.getContext("2d");
  c.width = window.innerWidth;
  c.height = window.innerHeight;
  const colors = ["#ff6b35", "#2ecc71", "#f1c40f", "#4c9aff", "#e74c3c"];
  const bits = Array.from({ length: 140 }, () => ({
    x: Math.random() * c.width,
    y: -20 - Math.random() * c.height * 0.5,
    w: 5 + Math.random() * 5,
    vx: -2 + Math.random() * 4,
    vy: 3 + Math.random() * 4,
    col: colors[Math.floor(Math.random() * colors.length)]
  }));
  let frame = 0;
  (function draw() {
    ctx.clearRect(0, 0, c.width, c.height);
    bits.forEach(b => {
      b.x += b.vx;
      b.y += b.vy;
      ctx.fillStyle = b.col;
      ctx.fillRect(b.x, b.y, b.w, b.w * 1.6);
    });
    frame++;
    if (frame < 150) requestAnimationFrame(draw);
    else c.remove();
  })();
}

// ---------- Run on page load ----------
document.addEventListener("DOMContentLoaded", function () {
  // messages sent from Flask
  const data = document.getElementById("flash-data");
  if (data) {
    JSON.parse(data.textContent).forEach(function (item) {
      const cat = item[0], msg = item[1];
      toast(msg, cat === "celebrate" ? "success" : cat);
      if (cat === "celebrate") confetti();
    });
  }

  // urgent deadline popup: shows every time the dashboard opens
  const ad = document.getElementById("alert-data");
  if (ad && Number(ad.dataset.count) > 0) {
    setTimeout(function () {
      toast("⚠️ You have " + ad.dataset.count + " urgent task(s). Check the alerts on this page.", "warn", 6000);
    }, 800);
  }
});

// ---------- Dark mode ----------
function updateThemeIcon() {
  const b = document.getElementById("theme-btn");
  if (b) b.textContent = document.documentElement.dataset.theme === "dark" ? "☀️" : "🌙";
}

function toggleTheme() {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) {}
  updateThemeIcon();
  document.querySelectorAll("canvas[data-score]").forEach(function (c) {
    if (c._chart) {
      c._chart.data.datasets[0].backgroundColor[1] = ringEmpty();
      c._chart.update();
    }
  });
}

document.addEventListener("DOMContentLoaded", function () {
  updateThemeIcon();
  const btn = document.getElementById("theme-btn");
  if (btn) btn.onclick = toggleTheme;
});

// ---------- Task filter and search ----------
document.addEventListener("DOMContentLoaded", function () {
  const tasks = document.querySelectorAll(".task");
  const search = document.getElementById("search");
  if (!tasks.length || !search) return;
  let filter = "all";

  function apply() {
    const q = search.value.trim().toLowerCase();
    let shown = 0;
    tasks.forEach(function (t) {
      const okFilter =
        filter === "all" ||
        (filter === "pending" && t.dataset.done === "0") ||
        (filter === "done" && t.dataset.done === "1") ||
        (filter === "overdue" && t.dataset.overdue === "1");
      const okSearch = t.dataset.title.includes(q);
      t.style.display = okFilter && okSearch ? "" : "none";
      if (okFilter && okSearch) shown++;
    });
    document.getElementById("no-match").hidden = shown > 0;
  }

  document.querySelectorAll(".chip").forEach(function (chip) {
    chip.onclick = function () {
      document.querySelectorAll(".chip").forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      filter = chip.dataset.filter;
      apply();
    };
  });
  search.oninput = apply;
});

// ---------- Focus timer ----------
document.addEventListener("DOMContentLoaded", function () {
  const box = document.getElementById("focus");
  if (!box) return;
  const display = document.getElementById("focus-time");
  const taskSel = document.getElementById("focus-task");
  const minSel = document.getElementById("focus-min");
  const startBtn = document.getElementById("focus-start");
  const resetBtn = document.getElementById("focus-reset");
  const doneBox = document.getElementById("focus-done");
  const doneMsg = document.getElementById("focus-done-msg");
  const logBtn = document.getElementById("focus-log-btn");
  const logForm = document.getElementById("focus-log");
  const hoursInput = document.getElementById("focus-hours");
  const pageTitle = document.title;

  let total = Number(minSel.value) * 60;
  let left = total;
  let timer = null;
  let hours = 0;

  function fmt(s) {
    const m = Math.floor(s / 60), r = s % 60;
    return String(m).padStart(2, "0") + ":" + String(r).padStart(2, "0");
  }

  function paint() {
    display.textContent = fmt(left);
    document.title = timer ? fmt(left) + " · Focus" : pageTitle;
  }

  function beep() {
    try {
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      const o = ac.createOscillator();
      o.connect(ac.destination);
      o.frequency.value = 880;
      o.start();
      setTimeout(function () { o.stop(); ac.close(); }, 600);
    } catch (e) {}
  }

  function stop() {
    clearInterval(timer);
    timer = null;
    startBtn.textContent = "Start";
  }

  function finish() {
    stop();
    left = 0;
    paint();
    hours = Math.round((total / 3600) * 100) / 100;
    beep();
    toast("Focus session complete! Great work.", "success", 5000);
    confetti();
    const name = taskSel.options[taskSel.selectedIndex].text;
    doneMsg.textContent = "You focused for " + (total / 60) + " min on " + name + ".";
    logBtn.textContent = "Log " + hours + "h";
    doneBox.hidden = false;
  }

  startBtn.onclick = function () {
    if (timer) { stop(); paint(); return; }       // pause
    if (!taskSel.value) { toast("Add a pending task first.", "warn"); return; }
    if (left <= 0) left = total;
    doneBox.hidden = true;
    startBtn.textContent = "Pause";
    timer = setInterval(function () {
      left--;
      paint();
      if (left <= 0) finish();
    }, 1000);
    paint();
  };

  resetBtn.onclick = function () {
    stop();
    total = Number(minSel.value) * 60;
    left = total;
    doneBox.hidden = true;
    paint();
  };
  minSel.onchange = resetBtn.onclick;

  logBtn.onclick = function () {
    logForm.action = "/progress/" + taskSel.value;
    hoursInput.value = hours;
    logForm.submit();
  };

  paint();
});

// ---------- Login / Sign up popup (talks to the JSON API) ----------
document.addEventListener("DOMContentLoaded", function () {
  const dlg = document.getElementById("auth-dlg");
  if (!dlg) return;
  const form = document.getElementById("auth-form");
  const err = document.getElementById("auth-err");
  const nameRow = dlg.querySelector(".f-name");
  const submit = document.getElementById("auth-submit");
  const nameIn = document.getElementById("a-name");
  const emailIn = document.getElementById("a-email");
  const passIn = document.getElementById("a-pass");
  let mode = "login";

  function setMode(m) {
    mode = m;
    dlg.querySelectorAll(".tab").forEach(function (t) {
      t.classList.toggle("active", t.dataset.tab === m);
    });
    nameRow.hidden = m !== "register";
    submit.textContent = m === "login" ? "Log in" : "Create account";
    passIn.autocomplete = m === "login" ? "current-password" : "new-password";
    err.hidden = true;
  }

  function openAuth(m) {
    setMode(m);
    dlg.showModal();
    (m === "register" ? nameIn : emailIn).focus();
  }

  // any Log in / Sign up link opens the popup instead of a new page
  document.addEventListener("click", function (e) {
    const a = e.target.closest('a[href="/login"], a[href="/register"]');
    if (!a) return;
    if (location.pathname === "/login" || location.pathname === "/register") return;
    e.preventDefault();
    openAuth(a.getAttribute("href") === "/login" ? "login" : "register");
  });

  dlg.querySelectorAll(".tab").forEach(function (t) {
    t.onclick = function () { setMode(t.dataset.tab); };
  });
  document.getElementById("auth-close").onclick = function () { dlg.close(); };

  // send the form to the backend as JSON
  form.addEventListener("submit", async function (ev) {
    ev.preventDefault();
    err.hidden = true;
    submit.disabled = true;
    const body = { email: emailIn.value, password: passIn.value };
    if (mode === "register") body.name = nameIn.value;
    try {
      const res = await fetch("/api/" + mode, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.ok) {
        window.location.href = "/dashboard";
        return;
      }
      err.textContent = data.error;
      err.hidden = false;
    } catch (e) {
      err.textContent = "Cannot reach the server. Please try again.";
      err.hidden = false;
    }
    submit.disabled = false;
  });
});
    