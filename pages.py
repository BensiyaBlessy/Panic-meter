from flask import render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
import calendar as cal
from app import app, get_db, login_required, load_tasks, get_trend

TYPES = ["Exam", "Assignment", "Record", "Project"]

# ---------- Calendar ----------
@app.route("/calendar")
@login_required
def calendar_page():
    today = date.today()
    try:
        y, m = map(int, request.args.get("m", "").split("-"))
        first = date(y, m, 1)
    except ValueError:
        first = today.replace(day=1)
    weeks = cal.Calendar(0).monthdatescalendar(first.year, first.month)
    by_day = {}
    for t in load_tasks(session["user_id"]):
        by_day.setdefault(t["deadline"], []).append(t)
    prev_m = (first - timedelta(days=1)).replace(day=1)
    next_m = (first + timedelta(days=32)).replace(day=1)
    return render_template("calendar.html", weeks=weeks, by_day=by_day, first=first, today=today,
                           prev=prev_m.strftime("%Y-%m"), nxt=next_m.strftime("%Y-%m"),
                           title=first.strftime("%B %Y"))

# ---------- Analytics ----------
@app.route("/analytics")
@login_required
def analytics():
    uid = session["user_id"]
    tasks = load_tasks(uid)
    by_type = {ty: 0 for ty in TYPES}
    for t in tasks:
        by_type[t["type"]] += 1
    shown = tasks[:10]
    data = {"types": by_type,
            "titles": [t["title"] for t in shown],
            "done": [t["hours_done"] for t in shown],
            "left": [t["remaining"] for t in shown]}
    trend = get_trend(uid)
    scores = trend["scores"]
    planned = round(sum(t["hours_needed"] for t in tasks), 1)
    done_h = round(sum(t["hours_done"] for t in tasks), 1)
    kpi = {"planned": planned, "done": done_h,
           "avg": round(sum(scores) / len(scores)) if scores else 0,
           "peak": max(scores) if scores else 0}
    return render_template("analytics.html", data=data, trend=trend, kpi=kpi)

# ---------- Profile ----------
@app.route("/profile")
@login_required
def profile():
    uid = session["user_id"]
    conn = get_db()
    u = conn.execute("SELECT name, email, daily_hours FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    tasks = load_tasks(uid)
    return render_template("profile.html", u=dict(u), total=len(tasks), done=sum(t["done"] for t in tasks))

@app.route("/profile/name", methods=["POST"])
@login_required
def profile_name():
    name = request.form["name"].strip()
    if not name:
        flash("Name cannot be empty.", "error")
    else:
        conn = get_db()
        conn.execute("UPDATE users SET name=? WHERE id=?", (name, session["user_id"]))
        conn.commit(); conn.close()
        session["name"] = name
        flash("Name updated.", "success")
    return redirect("/profile")

@app.route("/profile/password", methods=["POST"])
@login_required
def profile_password():
    f = request.form
    conn = get_db()
    u = conn.execute("SELECT password FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not check_password_hash(u["password"], f["current"]):
        flash("Current password is wrong.", "error")
    elif len(f["new"]) < 6:
        flash("New password must be at least 6 characters.", "error")
    else:
        conn.execute("UPDATE users SET password=? WHERE id=?",
                     (generate_password_hash(f["new"]), session["user_id"]))
        conn.commit()
        flash("Password changed.", "success")
    conn.close()
    return redirect("/profile")

@app.route("/profile/delete", methods=["POST"])
@login_required
def profile_delete():
    uid = session["user_id"]
    conn = get_db()
    for table, col in (("tasks", "user_id"), ("history", "user_id"), ("users", "id")):
        conn.execute("DELETE FROM " + table + " WHERE " + col + "=?", (uid,))
    conn.commit(); conn.close()
    session.clear()
    flash("Your account has been deleted.", "info")
    return redirect("/")