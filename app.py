from flask import Flask, render_template, request, redirect, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, date, timedelta
import sqlite3, csv, io

app = Flask(__name__)
app.secret_key = "change-this-to-any-random-text"
DB = "panic.db"

# ---------- Panic Score logic ----------
TYPE_WEIGHT = {"Exam": 1.5, "Record": 1.2, "Project": 1.2, "Assignment": 1.0}

def task_panic(t):
    days_left = max((t["deadline"] - date.today()).days, 0.5)
    remaining = max(t["hours_needed"] - t["hours_done"], 0)
    return (remaining / days_left) * TYPE_WEIGHT[t["type"]]

def total_panic(tasks):
    return min(round(sum(task_panic(t) for t in tasks if t["remaining"] > 0) * 10), 100)

def level(s):
    if s <= 30: return "Chill"
    if s <= 60: return "Careful"
    if s <= 80: return "Panic"
    return "Red Alert"

def message(s):
    if s <= 30: return "Relax, everything is under control."
    if s <= 60: return "Stay careful and plan your work."
    if s <= 80: return "Time to start working right now!"
    return "Red Alert! Drop everything and start now!"

# ---------- Database ----------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS tasks(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT, type TEXT, deadline TEXT,
        hours_needed REAL, hours_done REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, label TEXT, score INTEGER);""")
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)")]
    if "daily_hours" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN daily_hours REAL DEFAULT 4")
    conn.commit()
    conn.close()

def load_tasks(uid):
    conn = get_db()
    rows = conn.execute("SELECT * FROM tasks WHERE user_id=? ORDER BY deadline", (uid,)).fetchall()
    conn.close()
    tasks = []
    for r in rows:
        t = dict(r)
        t["deadline"] = datetime.strptime(r["deadline"], "%Y-%m-%d").date()
        t["remaining"] = max(t["hours_needed"] - t["hours_done"], 0)
        days = (t["deadline"] - date.today()).days
        t["days_left"] = days
        t["overdue"] = days < 0 and t["remaining"] > 0
        t["done"] = t["remaining"] == 0
        t["panic"] = round(task_panic(t), 1)
        t["per_day"] = round(t["remaining"] / max(days, 1), 1)
        tasks.append(t)
    return tasks

def record_score(uid, score):
    conn = get_db()
    last = conn.execute("SELECT score FROM history WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,)).fetchone()
    if last is None or last["score"] != score:
        conn.execute("INSERT INTO history(user_id,label,score) VALUES(?,?,?)",
                     (uid, datetime.now().strftime("%d %b %H:%M"), score))
        conn.commit()
    conn.close()

def get_trend(uid):
    conn = get_db()
    rows = conn.execute("SELECT label, score FROM history WHERE user_id=? ORDER BY id DESC LIMIT 12", (uid,)).fetchall()
    conn.close()
    rows = rows[::-1]
    return {"labels": [r["label"] for r in rows], "scores": [r["score"] for r in rows]}

def get_badges(score, stats):
    return [
        {"icon": "🚀", "name": "First step", "desc": "Add your first task", "on": stats["total"] >= 1},
        {"icon": "✅", "name": "Finisher", "desc": "Complete a task", "on": stats["done"] >= 1},
        {"icon": "🔥", "name": "Hat-trick", "desc": "Complete 3 tasks", "on": stats["done"] >= 3},
        {"icon": "⏰", "name": "On time", "desc": "Have no overdue tasks", "on": stats["total"] >= 1 and stats["overdue"] == 0},
        {"icon": "😎", "name": "Cool head", "desc": "Keep your score at 30 or below", "on": stats["total"] >= 1 and score <= 30},
    ]

def get_daily_hours(uid):
    conn = get_db()
    r = conn.execute("SELECT daily_hours FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return r["daily_hours"] if r and r["daily_hours"] else 4.0

def get_forecast(plan, cap):
    today = date.today()
    labels, hours = [], []
    for i in range(7):
        d = today + timedelta(days=i)
        total = 0
        for t in plan:
            if max(t["deadline"], today) >= d:
                total += t["remaining"] / max(t["days_left"], 1)
        labels.append(d.strftime("%a %d"))
        hours.append(round(total, 1))
    return {"labels": labels, "hours": hours, "cap": cap}

def login_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect("/login")
        return f(*a, **k)
    return wrapper

# ---------- Public pages ----------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        if len(pw) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")
        conn = get_db()
        try:
            cur = conn.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                               (name, email, generate_password_hash(pw)))
            conn.commit()
            session["user_id"], session["name"] = cur.lastrowid, name
            flash("Account created. Welcome, " + name.split()[0] + "!", "success")
            return redirect("/dashboard")
        except sqlite3.IntegrityError:
            flash("This email is already registered. Try logging in.", "error")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        conn = get_db()
        u = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if u and check_password_hash(u["password"], request.form["password"]):
            session["user_id"], session["name"] = u["id"], u["name"]
            flash("Welcome back, " + u["name"].split()[0] + "!", "success")
            return redirect("/dashboard")
        flash("Wrong email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect("/")

# ---------- Dashboard ----------
@app.route("/dashboard")
@login_required
def dashboard():
    tasks = load_tasks(session["user_id"])
    score = total_panic(tasks)
    plan = sorted([t for t in tasks if not t["done"]], key=lambda x: x["panic"], reverse=True)
    stats = {"total": len(tasks),
             "done": sum(t["done"] for t in tasks),
             "overdue": sum(t["overdue"] for t in tasks)}
    alerts = []
    for t in plan:
        if t["overdue"]:
            alerts.append(("red", f'{t["title"]} is overdue by {-t["days_left"]} day(s)!'))
        elif t["days_left"] == 0:
            alerts.append(("orange", f'{t["title"]} is due today!'))
        elif t["days_left"] == 1:
            alerts.append(("yellow", f'{t["title"]} is due tomorrow.'))
    uid = session["user_id"]
    record_score(uid, score)
    cap = get_daily_hours(uid)
    required = round(sum(t["remaining"] / max(t["days_left"], 1) for t in plan), 1)
    capacity = {"required": required, "available": cap, "over": required > cap, "gap": round(required - cap, 1)}
    return render_template("dashboard.html", tasks=tasks, plan=plan, score=score,
                           level=level(score), msg=message(score), stats=stats, alerts=alerts,
                           trend=get_trend(uid), badges=get_badges(score, stats),
                           capacity=capacity, forecast=get_forecast(plan, cap))

@app.route("/add", methods=["POST"])
@login_required
def add():
    f = request.form
    conn = get_db()
    conn.execute("INSERT INTO tasks(user_id,title,type,deadline,hours_needed) VALUES(?,?,?,?,?)",
                 (session["user_id"], f["title"], f["type"], f["deadline"], float(f["hours"])))
    conn.commit(); conn.close()
    flash('Task "' + f["title"] + '" added.', "success")
    return redirect("/dashboard")

@app.route("/progress/<int:tid>", methods=["POST"])
@login_required
def progress(tid):
    uid = session["user_id"]
    before = total_panic(load_tasks(uid))
    conn = get_db()
    conn.execute("UPDATE tasks SET hours_done=MIN(hours_done+?,hours_needed) WHERE id=? AND user_id=?",
                 (float(request.form["done_hours"]), tid, uid))
    conn.commit(); conn.close()
    tasks = load_tasks(uid)
    after = total_panic(tasks)
    t = next((x for x in tasks if x["id"] == tid), None)
    if t and t["done"]:
        flash('"' + t["title"] + '" completed! Panic score ' + str(before) + " → " + str(after), "celebrate")
    else:
        flash("Progress saved. Panic score " + str(before) + " → " + str(after), "success")
    return redirect("/dashboard")

@app.route("/complete/<int:tid>", methods=["POST"])
@login_required
def complete(tid):
    uid = session["user_id"]
    before = total_panic(load_tasks(uid))
    conn = get_db()
    conn.execute("UPDATE tasks SET hours_done=hours_needed WHERE id=? AND user_id=?", (tid, uid))
    conn.commit(); conn.close()
    after = total_panic(load_tasks(uid))
    flash("Task completed! Panic score " + str(before) + " → " + str(after), "celebrate")
    return redirect("/dashboard")

@app.route("/edit/<int:tid>", methods=["GET", "POST"])
@login_required
def edit(tid):
    uid = session["user_id"]
    conn = get_db()
    t = conn.execute("SELECT * FROM tasks WHERE id=? AND user_id=?", (tid, uid)).fetchone()
    if not t:
        conn.close()
        flash("Task not found.", "error")
        return redirect("/dashboard")
    if request.method == "POST":
        f = request.form
        hours = float(f["hours"])
        conn.execute("UPDATE tasks SET title=?, type=?, deadline=?, hours_needed=?, hours_done=MIN(hours_done,?) "
                     "WHERE id=? AND user_id=?", (f["title"], f["type"], f["deadline"], hours, hours, tid, uid))
        conn.commit(); conn.close()
        flash("Task updated.", "success")
        return redirect("/dashboard")
    conn.close()
    return render_template("edit.html", t=dict(t))

@app.route("/settings/hours", methods=["POST"])
@login_required
def set_hours():
    try:
        hrs = float(request.form["hours"])
    except ValueError:
        hrs = 4.0
    hrs = min(max(hrs, 0.5), 16)
    conn = get_db()
    conn.execute("UPDATE users SET daily_hours=? WHERE id=?", (hrs, session["user_id"]))
    conn.commit(); conn.close()
    flash("Daily study time set to {:g} hours.".format(hrs), "success")
    return redirect("/dashboard")

@app.route("/export")
@login_required
def export_csv():
    def safe(v):
        return "'" + v if isinstance(v, str) and v and v[0] in "=+-@" else v
    tasks = load_tasks(session["user_id"])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Task", "Type", "Deadline", "Hours needed", "Hours done", "Hours remaining", "Days left", "Status"])
    for t in tasks:
        status = "Done" if t["done"] else ("Overdue" if t["overdue"] else "Pending")
        w.writerow([safe(t["title"]), t["type"], t["deadline"], t["hours_needed"], t["hours_done"],
                    t["remaining"], t["days_left"], status])
    return Response("\ufeff" + buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=panic-meter-tasks.csv"})

@app.route("/delete/<int:tid>", methods=["POST"])
@login_required
def delete(tid):
    conn = get_db()
    conn.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (tid, session["user_id"]))
    conn.commit(); conn.close()
    flash("Task deleted.", "info")
    return redirect("/dashboard")

init_db()
if __name__ == "__main__":
    app.run(debug=True)