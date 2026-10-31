import os, re, sqlite3, uuid
from datetime import date
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, g, abort, send_from_directory

DATA = os.environ.get("DATA_DIR", "/data")
UPLOADS = os.path.join(DATA, "uploads")
os.makedirs(UPLOADS, exist_ok=True)
ALLOWED = {".gif", ".webp", ".png", ".jpg", ".jpeg"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024


def db():
    if "db" not in g:
        g.db = sqlite3.connect(os.path.join(DATA, "app.db"))
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    c = g.pop("db", None)
    if c:
        c.close()


with sqlite3.connect(os.path.join(DATA, "app.db")) as c:
    c.executescript("""
    create table if not exists exercises(id integer primary key, name text not null, gif text);
    create table if not exists programs(id integer primary key, name text not null);
    create table if not exists completions(id integer primary key, program_id integer, name text, day text not null, ts text);
    create table if not exists steps(id integer primary key, program_id integer not null,
        pos integer not null, exercise_id integer, seconds integer not null, label text);
    """)
    if "label" not in [row[1] for row in c.execute("pragma table_info(steps)")]:
        c.execute("alter table steps add column label text")


@app.template_filter("fmt")
def fmt(s):
    return f"{s // 60}:{s % 60:02d}"


# ---------- helpers ----------
def programs_partial():
    rows = db().execute("""select p.id, p.name, coalesce(sum(s.seconds),0) total, count(s.id) n
        from programs p left join steps s on s.program_id=p.id group by p.id order by p.id""").fetchall()
    return render_template("_programs.html", programs=rows)


def exercises_partial():
    rows = db().execute("select * from exercises order by name collate nocase").fetchall()
    return render_template("_exercises.html", exercises=rows)


def get_steps(pid):
    return db().execute("""select s.id, s.seconds, s.exercise_id, s.label, e.name, e.gif
        from steps s left join exercises e on e.id=s.exercise_id
        where s.program_id=? order by s.pos, s.id""", (pid,)).fetchall()


def steps_partial(pid):
    st = get_steps(pid)
    return render_template("_steps.html", steps=st, pid=pid, total=sum(s["seconds"] for s in st))


# ---------- workouts ----------
@app.get("/")
def index():
    return render_template("index.html", tab="w", partial=programs_partial())


@app.post("/programs")
def add_program():
    name = request.form.get("wk_title", "").strip()
    if name:
        db().execute("insert into programs(name) values(?)", (name,))
        db().commit()
    return programs_partial()


@app.get("/programs/<int:pid>")
def program(pid):
    p = db().execute("select * from programs where id=?", (pid,)).fetchone() or abort(404)
    ex = db().execute("select * from exercises order by name collate nocase").fetchall()
    return render_template("program.html", p=p, exercises=ex, partial=steps_partial(pid))


@app.delete("/programs/<int:pid>")
def del_program(pid):
    db().execute("delete from steps where program_id=?", (pid,))
    db().execute("delete from programs where id=?", (pid,))
    db().commit()
    return programs_partial()


def sanitize(name):
    """Exercise name -> safe file name (without extension)."""
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .")[:100] or "exercise"


def unique_name(base, ext, exclude=None):
    fn, n = base + ext, 2
    while os.path.exists(os.path.join(UPLOADS, fn)) and fn != exclude:
        fn = f"{base} ({n}){ext}"
        n += 1
    return fn


def save_gif(f, name):
    """Save the upload using the exercise name as the file name."""
    if f and f.filename:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ALLOWED:
            fn = unique_name(sanitize(name), ext)
            f.save(os.path.join(UPLOADS, fn))
            return fn
    return None


@app.post("/programs/<int:pid>/steps")
def add_step(pid):
    kind = request.form.get("kind", "workout")
    secs = int(request.form.get("min") or 0) * 60 + int(request.form.get("sec") or 0)
    ex_id = None
    if kind == "workout":
        sel = request.form.get("exercise", "")
        if sel == "new":
            name = request.form.get("ex_new_title", "").strip()
            if not name:
                return steps_partial(pid)
            cur = db().execute("insert into exercises(name,gif) values(?,?)",
                               (name, save_gif(request.files.get("gif"), name)))
            ex_id = cur.lastrowid
        elif sel.isdigit():
            ex_id = int(sel)
        else:
            return steps_partial(pid)
    if secs > 0:
        pos = db().execute("select coalesce(max(pos),-1)+1 from steps where program_id=?", (pid,)).fetchone()[0]
        db().execute("insert into steps(program_id,pos,exercise_id,seconds) values(?,?,?,?)",
                     (pid, pos, ex_id, secs))
    db().commit()
    return steps_partial(pid)


@app.post("/steps/<int:sid>/move/<d>")
def move_step(sid, d):
    c = db()
    pid = c.execute("select program_id from steps where id=?", (sid,)).fetchone()[0]
    ids = [r[0] for r in c.execute("select id from steps where program_id=? order by pos,id", (pid,))]
    i = ids.index(sid)
    j = i - 1 if d == "up" else i + 1
    if 0 <= j < len(ids):
        ids[i], ids[j] = ids[j], ids[i]
    for n, x in enumerate(ids):
        c.execute("update steps set pos=? where id=?", (n, x))
    c.commit()
    return steps_partial(pid)


@app.delete("/steps/<int:sid>")
def del_step(sid):
    pid = db().execute("select program_id from steps where id=?", (sid,)).fetchone()[0]
    db().execute("delete from steps where id=?", (sid,))
    db().commit()
    return steps_partial(pid)


@app.post("/programs/<int:pid>/rename")
def rename_program(pid):
    name = request.form.get("wk_rename", "").strip()
    if name:
        db().execute("update programs set name=? where id=?", (name, pid))
        db().commit()
    return "", 204


@app.post("/steps/<int:sid>")
def edit_step(sid):
    secs = int(request.form.get("min") or 0) * 60 + int(request.form.get("sec") or 0)
    if secs > 0:
        db().execute("update steps set seconds=? where id=?", (secs, sid))
        db().commit()
    return "", 204


# ---------- exercises ----------
@app.get("/exercises")
def exercises():
    return render_template("exercises.html", tab="e", partial=exercises_partial())


@app.post("/exercises")
def add_exercise():
    name = request.form.get("ex_title", "").strip()
    if name:
        db().execute("insert into exercises(name,gif) values(?,?)", (name, save_gif(request.files.get("gif"), name)))
        db().commit()
    return exercises_partial()


@app.post("/exercises/<int:eid>")
def rename_exercise(eid):
    name = request.form.get("ex_title", "").strip()
    row = db().execute("select gif from exercises where id=?", (eid,)).fetchone()
    if name and row:
        gif = row["gif"]
        if gif:   # keep the file name in step with the exercise name
            new = unique_name(sanitize(name), os.path.splitext(gif)[1], exclude=gif)
            if new != gif and os.path.exists(os.path.join(UPLOADS, gif)):
                os.rename(os.path.join(UPLOADS, gif), os.path.join(UPLOADS, new))
                gif = new
        db().execute("update exercises set name=?, gif=? where id=?", (name, gif, eid))
        db().commit()
    return exercises_partial()


@app.delete("/exercises/<int:eid>")
def del_exercise(eid):
    r = db().execute("select gif from exercises where id=?", (eid,)).fetchone()
    if r and r["gif"]:
        try:
            os.remove(os.path.join(UPLOADS, r["gif"]))
        except OSError:
            pass
    db().execute("delete from steps where exercise_id=?", (eid,))
    db().execute("delete from exercises where id=?", (eid,))
    db().commit()
    return exercises_partial()


@app.get("/media/<path:f>")
def media(f):
    return send_from_directory(UPLOADS, f, max_age=0)


@app.get("/manifest.webmanifest")
def manifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")


# ---------- calendar ----------
@app.get("/calendar")
def calendar():
    rows = db().execute("select day, name from completions order by id").fetchall()
    done = {}
    for row in rows:
        done.setdefault(row["day"], []).append(row["name"])
    recent = db().execute("select day, name from completions order by id desc limit 10").fetchall()
    return render_template("calendar.html", tab="c", done=done, recent=recent)


@app.post("/run/<int:pid>/complete")
def complete(pid):
    """Called by the player only when a workout ran from start to finish."""
    p = db().execute("select name from programs where id=?", (pid,)).fetchone() or abort(404)
    try:
        day = date.fromisoformat(request.form.get("day", "")).isoformat()
    except ValueError:
        abort(400)
    db().execute("insert into completions(program_id,name,day,ts) values(?,?,?,datetime('now'))", (pid, p["name"], day))
    db().commit()
    return "", 204


# ---------- player ----------
@app.get("/run/<int:pid>")
def run(pid):
    p = db().execute("select * from programs where id=?", (pid,)).fetchone() or abort(404)
    steps = [{"name": s["name"] or "Rest", "seconds": s["seconds"],
              "gif": "/media/" + quote(s["gif"]) if s["gif"] else None,
              "kind": "ex" if s["exercise_id"] else "rest"} for s in get_steps(pid)]
    return render_template("run.html", p=p, steps=steps)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8088, debug=True)
