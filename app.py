import glob, json, math, os, re, shutil, sqlite3, subprocess, time, uuid
from datetime import date
from urllib.parse import quote, urlsplit
from flask import Flask, render_template, request, redirect, g, abort, send_from_directory, make_response, jsonify

DATA = os.environ.get("DATA_DIR", "/data")
UPLOADS = os.path.join(DATA, "uploads")
VIDEO_CACHE = os.path.join(DATA, "video-cache")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(VIDEO_CACHE, exist_ok=True)
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
    create table if not exists categories(id integer primary key, name text not null collate nocase unique);
    create table if not exists programs(id integer primary key, name text not null);
    create table if not exists completions(id integer primary key, program_id integer, name text, day text not null, ts text);
    create table if not exists steps(id integer primary key, program_id integer not null,
        pos integer not null, exercise_id integer, seconds integer not null, label text);
    """)
    if "label" not in [row[1] for row in c.execute("pragma table_info(steps)")]:
        c.execute("alter table steps add column label text")
    if "category_id" not in [row[1] for row in c.execute("pragma table_info(exercises)")]:
        c.execute("alter table exercises add column category_id integer")


@app.template_filter("fmt")
def fmt(s):
    return f"{s // 60}:{s % 60:02d}"


# ---------- helpers ----------
def programs_partial():
    rows = db().execute("""select p.id, p.name, coalesce(sum(s.seconds),0) total, count(s.id) n
        from programs p left join steps s on s.program_id=p.id group by p.id order by p.id""").fetchall()
    return render_template("_programs.html", programs=rows)


def exercises_partial():
    rows = db().execute("""select e.*, c.name category from exercises e
        left join categories c on c.id=e.category_id
        order by e.name collate nocase""").fetchall()
    cats = db().execute("select id, name from categories order by name collate nocase").fetchall()
    return render_template("_exercises.html", exercises=rows, categories=cats)


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
    ex = db().execute("""select e.*, c.name category from exercises e
        left join categories c on c.id=e.category_id
        order by e.name collate nocase""").fetchall()
    cats = db().execute("select id, name from categories order by name collate nocase").fetchall()
    uncategorized = db().execute("select exists(select 1 from exercises where category_id is null)").fetchone()[0]
    return render_template("program.html", p=p, exercises=ex, categories=cats, tab="w",
                           has_uncategorized=bool(uncategorized), partial=steps_partial(pid))


@app.delete("/programs/<int:pid>")
def del_program(pid):
    db().execute("delete from steps where program_id=?", (pid,))
    db().execute("delete from programs where id=?", (pid,))
    db().commit()
    return programs_partial()


def sanitize(name):
    """Exercise name -> safe file name (without extension)."""
    return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip(" .")[:100] or "exercise"


def category_folder(name):
    """Folder used to store a category's GIFs, e.g. data/uploads/Kettlebell/."""
    return os.path.join(UPLOADS, sanitize(name)) if name else UPLOADS


def rel_upload_path(path):
    return os.path.relpath(path, UPLOADS).replace(os.sep, "/")


def unique_name(base, ext, exclude=None, folder=None):
    folder = folder or UPLOADS
    fn, n = base + ext, 2
    while os.path.exists(os.path.join(folder, fn)) and os.path.join(folder, fn) != exclude:
        fn = f"{base} ({n}){ext}"
        n += 1
    return fn


def save_gif(f, name, category=None):
    """Save the upload in its category folder, using the exercise name as the file name."""
    if f and f.filename:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext in ALLOWED:
            folder = category_folder(category)
            os.makedirs(folder, exist_ok=True)
            fn = unique_name(sanitize(name), ext, folder=folder)
            f.save(os.path.join(folder, fn))
            return rel_upload_path(os.path.join(folder, fn))
    return None


def instagram_url(value):
    try:
        parsed = urlsplit(value.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return False
    return (parsed.scheme == "https" and port in (None, 443) and
            not parsed.username and not parsed.password and
            (host == "instagram.com" or host.endswith(".instagram.com") or host == "instagr.am"))


def clean_video_cache():
    cutoff = time.time() - 3600
    for path in glob.glob(os.path.join(VIDEO_CACHE, "*")):
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def video_cache_path(token, suffix):
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        abort(404)
    return os.path.join(VIDEO_CACHE, token + suffix)


def probe_video(path):
    """Return (duration, fps) for a video file using ffprobe, or (0.0, 30.0) on failure."""
    duration, fps = 0.0, 30.0
    if not (path and os.path.isfile(path) and shutil.which("ffprobe")):
        return duration, fps
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration:stream=r_frame_rate,avg_frame_rate",
            "-select_streams", "v:0",
            "-of", "json", path,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        data = json.loads(res.stdout) if res.stdout else {}
        format_duration = data.get("format", {}).get("duration")
        if format_duration:
            duration = float(format_duration)
        streams = data.get("streams", [])
        if streams:
            stream = streams[0]
            if not duration and stream.get("duration"):
                duration = float(stream["duration"])
            for key in ("r_frame_rate", "avg_frame_rate"):
                val = stream.get(key)
                if val and "/" in val:
                    num, den = val.split("/", 1)
                    if float(den) > 0:
                        calc_fps = float(num) / float(den)
                        if 1.0 <= calc_fps <= 240.0:
                            fps = calc_fps
                            break
                elif val:
                    try:
                        calc_fps = float(val)
                        if 1.0 <= calc_fps <= 240.0:
                            fps = calc_fps
                            break
                    except ValueError:
                        pass
    except Exception as exc:
        app.logger.warning("ffprobe failed for %s: %s", path, exc)
    return duration, fps


def ensure_category(name):
    """Find or create a category and make sure its upload folder exists."""
    name = " ".join(name.split())
    if not name:
        return None, False
    row = db().execute("select id, name from categories where name=? collate nocase", (name,)).fetchone()
    if row:
        cid, name, created = row["id"], row["name"], False
    else:
        cid, created = db().execute("insert into categories(name) values(?)", (name,)).lastrowid, True
    os.makedirs(category_folder(name), exist_ok=True)
    return cid, created


def category_from_form(form):
    """Resolve the category select (existing id or a new category name)."""
    sel = form.get("category", "").strip()
    if sel == "new":
        return ensure_category(form.get("ex_category_new", "").strip())
    if sel.isdigit():
        row = db().execute("select id from categories where id=?", (int(sel),)).fetchone()
        return (row["id"], False) if row else (None, False)
    return None, False


def category_name(cid):
    if cid is None:
        return None
    row = db().execute("select name from categories where id=?", (cid,)).fetchone()
    return row["name"] if row else None


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


@app.post("/steps/reorder/<int:pid>")
def reorder_steps(pid):
    c = db()
    current = [r[0] for r in c.execute("select id from steps where program_id=? order by pos,id", (pid,))]
    try:
        ordered = [int(value) for value in request.form.getlist("ids")]
    except ValueError:
        abort(400)
    if len(ordered) != len(current) or set(ordered) != set(current):
        abort(400)
    for pos, sid in enumerate(ordered):
        c.execute("update steps set pos=? where id=? and program_id=?", (pos, sid, pid))
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
    cats = db().execute("select id, name from categories order by name collate nocase").fetchall()
    return render_template("exercises.html", tab="e", partial=exercises_partial(), categories=cats)


@app.post("/exercises")
def add_exercise():
    name = request.form.get("ex_title", "").strip()
    if name:
        cid, created = category_from_form(request.form)
        gif = save_gif(request.files.get("gif"), name, category_name(cid))
        db().execute("insert into exercises(name,gif,category_id) values(?,?,?)", (name, gif, cid))
        db().commit()
        resp = make_response(exercises_partial())
        if created:   # refresh so the new category appears in the pickers outside #list
            resp.headers["HX-Refresh"] = "true"
        return resp
    return exercises_partial()


@app.post("/exercises/instagram/preview")
def instagram_preview():
    clean_video_cache()
    url = request.form.get("url", "").strip()
    if len(url) > 2048 or not instagram_url(url):
        return jsonify(error="Enter a valid Instagram post or Reel URL."), 400
    if not shutil.which("ffmpeg"):
        return jsonify(error="Video conversion is unavailable because ffmpeg is not installed."), 503
    try:
        import yt_dlp
        token = uuid.uuid4().hex
        outtmpl = os.path.join(VIDEO_CACHE, token + "-source.%(ext)s")
        options = {
            "format": "best[ext=mp4]/best", "noplaylist": True,
            "quiet": True, "no_warnings": True, "socket_timeout": 20,
            "retries": 2, "max_filesize": 100 * 1024 * 1024,
            "outtmpl": outtmpl,
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            media_info = info
            if info and (info.get("_type") == "playlist" or "entries" in info):
                entries = [e for e in (info.get("entries") or []) if e]
                if entries:
                    media_info = entries[0]
            known_duration = float(media_info.get("duration") or 0) if media_info else 0.0
            if known_duration > 180:
                return jsonify(error="The Instagram video must be between 1 second and 3 minutes long."), 400
            with yt_dlp.YoutubeDL(options) as downloader:
                downloader.download([url])
        sources = sorted(glob.glob(os.path.join(VIDEO_CACHE, token + "-source.*")))
        if not sources:
            raise RuntimeError("Download produced no video file")
        video_sources = [s for s in sources if s.lower().endswith((".mp4", ".mov", ".m4v", ".webm", ".mkv"))]
        source = video_sources[0] if video_sources else sources[0]
        probed_duration, probed_fps = probe_video(source)
        duration = probed_duration or known_duration
        fps = (float(media_info.get("fps") or 0) if media_info else 0.0) or probed_fps or 30.0
        if duration and (duration < 1 or duration > 180):
            for path in glob.glob(os.path.join(VIDEO_CACHE, token + "*")):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return jsonify(error="The Instagram video must be between 1 second and 3 minutes long."), 400
        preview = video_cache_path(token, ".mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", source, "-vf", "scale=720:-2:flags=lanczos",
            "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-movflags", "+faststart", preview,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=150)
        if not duration or duration < 1:
            duration, preview_fps = probe_video(preview)
            if preview_fps:
                fps = preview_fps
        if not duration or duration < 1 or duration > 180:
            for path in glob.glob(os.path.join(VIDEO_CACHE, token + "*")):
                try:
                    os.remove(path)
                except OSError:
                    pass
            return jsonify(error="The Instagram video must be between 1 second and 3 minutes long."), 400
        with open(video_cache_path(token, ".json"), "w", encoding="utf-8") as metadata:
            json.dump({"duration": duration, "fps": fps}, metadata)
        for s in sources:
            try:
                os.remove(s)
            except OSError:
                pass
        return jsonify(token=token, duration=duration, fps=fps,
                       video_url=f"/exercise-video-preview/{token}")
    except ModuleNotFoundError as exc:
        if exc.name in ("yt_dlp", "yt_dip"):
            return jsonify(error="yt-dlp is missing. Run 'pip install yt-dlp' in your environment or rebuild the container, then retry."), 503
        app.logger.exception("Instagram video preview dependency is missing")
        return jsonify(error="A video processing dependency is missing."), 503
    except Exception as exc:
        if "token" in locals():
            for path in glob.glob(os.path.join(VIDEO_CACHE, token + "*")):
                try:
                    os.remove(path)
                except OSError:
                    pass
        app.logger.exception("Instagram video preview failed")
        lines = str(exc).splitlines()
        raw_msg = lines[-1] if lines else type(exc).__name__
        clean_msg = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", raw_msg)
        detail = re.sub(r"https?://\S+", "[Instagram URL]", clean_msg)[:180]
        return jsonify(error=f"Could not load this Instagram video: {detail}. Check that the post is public and try again."), 422


@app.get("/exercise-video-preview/<token>")
def exercise_video_preview(token):
    return send_from_directory(VIDEO_CACHE, os.path.basename(video_cache_path(token, ".mp4")),
                               mimetype="video/mp4", max_age=0)


@app.post("/exercises/instagram/save")
def save_instagram_gif():
    clean_video_cache()
    name = request.form.get("ex_title", "").strip()
    token = request.form.get("token", "")
    if not name or len(name) > 120:
        return jsonify(error="Enter an exercise name."), 400
    source = video_cache_path(token, ".mp4")
    metadata_path = video_cache_path(token, ".json")
    if not os.path.isfile(source) or not os.path.isfile(metadata_path):
        return jsonify(error="The video preview expired. Load the Instagram URL again."), 400
    try:
        with open(metadata_path, encoding="utf-8") as metadata:
            duration = float(json.load(metadata)["duration"])
        start, end = float(request.form.get("start", "nan")), float(request.form.get("end", "nan"))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return jsonify(error="Choose valid start and end points."), 400
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or end > duration + 0.05 or end - start > 15:
        return jsonify(error="Choose a clip up to 15 seconds long within the video."), 400
    output = video_cache_path(token, "-clip.gif")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.4f}", "-i", source, "-t", f"{end-start:.4f}",
            "-filter_complex",
            "[0:v]fps=12,scale=480:-2:flags=lanczos,split[main][pal];[pal]palettegen=max_colors=128[palette];[main][palette]paletteuse=dither=bayer",
            "-an", "-loop", "0", output,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        try:
            os.remove(output)
        except OSError:
            pass
        return jsonify(error="GIF creation failed. Try a shorter section of the video."), 422
    cid, created = category_from_form(request.form)
    folder = category_folder(category_name(cid))
    os.makedirs(folder, exist_ok=True)
    filename = unique_name(sanitize(name), ".gif", folder=folder)
    target = os.path.join(folder, filename)
    os.replace(output, target)
    db().execute("insert into exercises(name,gif,category_id) values(?,?,?)",
                 (name, rel_upload_path(target), cid))
    db().commit()
    for path in (source, metadata_path, video_cache_path(token, ".mp4")):
        try:
            os.remove(path)
        except OSError:
            pass
    return jsonify(html=exercises_partial(), refresh=created)


@app.post("/exercises/<int:eid>")
def rename_exercise(eid):
    name = request.form.get("ex_title", "").strip()
    row = db().execute("select * from exercises where id=?", (eid,)).fetchone()
    if not (name and row):
        return exercises_partial()
    cid, created = category_from_form(request.form)
    gif = row["gif"]
    if gif:
        ext = os.path.splitext(gif)[1]
        old = os.path.join(UPLOADS, gif)
        folder = category_folder(category_name(cid))
        target = os.path.join(folder, sanitize(name) + ext)
        if os.path.normcase(os.path.normpath(old)) != os.path.normcase(os.path.normpath(target)):
            os.makedirs(folder, exist_ok=True)
            target = os.path.join(folder, unique_name(sanitize(name), ext, folder=folder))
            if os.path.exists(old):   # keep the GIF name in step with the exercise name and category
                os.replace(old, target)
                gif = rel_upload_path(target)
    db().execute("update exercises set name=?, gif=?, category_id=? where id=?", (name, gif, cid, eid))
    db().commit()
    resp = make_response(exercises_partial())
    if created:
        resp.headers["HX-Refresh"] = "true"
    return resp


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
