from flask import render_template, session, redirect, flash
from functools import wraps
from app import app, get_db, load_tasks, total_panic, level

# Leave empty to make the FIRST registered account the admin.
# Or write your login email here, for example: ADMIN_EMAIL = "bensiya@gmail.com"
ADMIN_EMAIL = ""

def admin_id():
    conn = get_db()
    if ADMIN_EMAIL:
        r = conn.execute("SELECT id FROM users WHERE email=?", (ADMIN_EMAIL.strip().lower(),)).fetchone()
    else:
        r = conn.execute("SELECT MIN(id) AS id FROM users").fetchone()
    conn.close()
    return r["id"] if r and r["id"] else None

def is_admin():
    return "user_id" in session and session["user_id"] == admin_id()

@app.context_processor
def inject_admin():
    return {"is_admin": is_admin()}

def admin_required(f):
    @wraps(f)
    def wrapper(*a, **k):
        if not is_admin():
            flash("This page is for the admin only.", "error")
            return redirect("/dashboard" if "user_id" in session else "/")
        return f(*a, **k)
    return wrapper

@app.route("/admin")
@admin_required
def admin_page():
    conn = get_db()
    users = conn.execute("SELECT id, name, email FROM users ORDER BY id").fetchall()
    conn.close()
    rows, scores, total_tasks, total_done = [], [], 0, 0
    for u in users:
        tasks = load_tasks(u["id"])
        s = total_panic(tasks)
        done = sum(t["done"] for t in tasks)
        rows.append({"id": u["id"], "name": u["name"], "email": u["email"],
                     "tasks": len(tasks), "done": done, "score": s, "level": level(s)})
        scores.append(s)
        total_tasks += len(tasks)
        total_done += done
    kpi = {"users": len(rows), "tasks": total_tasks, "done": total_done,
           "avg": round(sum(scores) / len(scores)) if scores else 0}
    return render_template("admin.html", rows=rows, kpi=kpi)

@app.route("/admin/delete/<int:uid>", methods=["POST"])
@admin_required
def admin_delete(uid):
    if uid == session["user_id"]:
        flash("You cannot delete your own account here.", "error")
        return redirect("/admin")
    conn = get_db()
    for table, col in (("tasks", "user_id"), ("history", "user_id"), ("users", "id")):
        conn.execute("DELETE FROM " + table + " WHERE " + col + "=?", (uid,))
    conn.commit(); conn.close()
    flash("User deleted.", "info")
    return redirect("/admin")