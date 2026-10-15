from flask import render_template, session, redirect, request
from datetime import date, timedelta
from app import app, load_tasks, total_panic, level


def to_date(d):
    if isinstance(d, date):
        return d
    return date.fromisoformat(str(d))


@app.route("/whatif", methods=["GET", "POST"])
def whatif_page():
    if "user_id" not in session:
        return redirect("/")

    tasks = [t for t in load_tasks(session["user_id"]) if not t.get("done")]
    before = total_panic(tasks)
    result = None

    if request.method == "POST":
        sim = []
        for t in tasks:
            tid = str(t["id"])
            if request.form.get("complete_" + tid):
                continue  # task finished in the simulation
            try:
                extra_h = float(request.form.get("hours_" + tid) or 0)
                extra_d = int(request.form.get("days_" + tid) or 0)
            except ValueError:
                extra_h, extra_d = 0, 0
            c = dict(t)
            c["hours_done"] = min(c["hours_done"] + max(extra_h, 0), c["hours_needed"])
            c["deadline"] = to_date(c["deadline"]) + timedelta(days=max(extra_d, 0))
            sim.append(c)
        after = total_panic(sim)
        result = {"before": before, "after": after,
                  "diff": before - after,
                  "level_before": level(before), "level_after": level(after)}

    return render_template("whatif.html", tasks=tasks, result=result, before=before)