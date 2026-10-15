from flask import render_template, session
from datetime import date, timedelta
from app import app, login_required, load_tasks, get_daily_hours

def build_schedule(tasks, cap, days=14):
    """Earliest-deadline-first: fill each day's study hours with the most urgent task."""
    today = date.today()
    pending = [dict(t, left=t["remaining"], eff=max(t["deadline"], today)) for t in tasks if not t["done"]]
    pending.sort(key=lambda t: (t["eff"], t["type"] != "Exam"))
    plan = []
    for i in range(days):
        d = today + timedelta(days=i)
        room = cap
        entries = []
        for t in pending:
            if room <= 0:
                break
            if t["left"] > 0 and t["eff"] >= d:
                h = min(room, t["left"])
                t["left"] -= h
                room -= h
                entries.append({"title": t["title"], "type": t["type"], "hours": round(h, 1)})
        plan.append({"date": d, "entries": entries, "total": round(cap - room, 1)})
    risk = [t for t in pending if t["left"] > 0.01 and t["eff"] < today + timedelta(days=days)]
    return plan, risk

@app.route("/schedule")
@login_required
def schedule_page():
    uid = session["user_id"]
    cap = get_daily_hours(uid)
    plan, risk = build_schedule(load_tasks(uid), cap)
    any_work = any(d["entries"] for d in plan)
    return render_template("schedule.html", plan=plan, risk=risk, cap=cap, today=date.today(), any_work=any_work)