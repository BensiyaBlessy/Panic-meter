from flask import request, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3
from app import app, get_db, load_tasks, total_panic, level

TYPES = ["Exam", "Assignment", "Record", "Project"]

def need_login():
    return jsonify(ok=False, error="Please log in first."), 401

@app.route("/api/register", methods=["POST"])
def api_register():
    d = request.get_json(silent=True) or {}
    name = str(d.get("name", "")).strip()
    email = str(d.get("email", "")).strip().lower()
    pw = str(d.get("password", ""))
    if not name or "@" not in email:
        return jsonify(ok=False, error="Enter your name and a valid email."), 400
    if len(pw) < 6:
        return jsonify(ok=False, error="Password must be at least 6 characters."), 400
    conn = get_db()
    try:
        cur = conn.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                           (name, email, generate_password_hash(pw)))
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify(ok=False, error="This email is already registered."), 409
    finally:
        conn.close()
    session["user_id"], session["name"] = cur.lastrowid, name
    flash("Account created. Welcome, " + name.split()[0] + "!", "success")
    return jsonify(ok=True, name=name), 201

@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.get_json(silent=True) or {}
    email = str(d.get("email", "")).strip().lower()
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()
    if u and check_password_hash(u["password"], str(d.get("password", ""))):
        session["user_id"], session["name"] = u["id"], u["name"]
        flash("Welcome back, " + u["name"].split()[0] + "!", "success")
        return jsonify(ok=True, name=u["name"])
    return jsonify(ok=False, error="Wrong email or password."), 401

@app.route("/api/me")
def api_me():
    if "user_id" not in session:
        return jsonify(logged_in=False)
    return jsonify(logged_in=True, name=session["name"])

@app.route("/api/tasks", methods=["GET"])
def api_tasks():
    if "user_id" not in session:
        return need_login()
    tasks = load_tasks(session["user_id"])
    score = total_panic(tasks)
    out = [{"id": t["id"], "title": t["title"], "type": t["type"],
            "deadline": t["deadline"].isoformat(), "hours_needed": t["hours_needed"],
            "hours_done": t["hours_done"], "days_left": t["days_left"],
            "done": t["done"], "overdue": t["overdue"]} for t in tasks]
    return jsonify(ok=True, score=score, level=level(score), tasks=out)

@app.route("/api/tasks", methods=["POST"])
def api_add_task():
    if "user_id" not in session:
        return need_login()
    d = request.get_json(silent=True) or {}
    title = str(d.get("title", "")).strip()
    try:
        datetime.strptime(str(d.get("deadline", "")), "%Y-%m-%d")
        hours = float(d.get("hours", 0))
    except ValueError:
        return jsonify(ok=False, error="Deadline must be YYYY-MM-DD and hours must be a number."), 400
    if not title or d.get("type") not in TYPES or hours <= 0:
        return jsonify(ok=False, error="Give a title, a valid type and hours above 0."), 400
    conn = get_db()
    cur = conn.execute("INSERT INTO tasks(user_id,title,type,deadline,hours_needed) VALUES(?,?,?,?,?)",
                       (session["user_id"], title, d["type"], d["deadline"], hours))
    conn.commit(); conn.close()
    return jsonify(ok=True, id=cur.lastrowid), 201