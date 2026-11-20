import glob, hashlib, json, math, os, re, shutil, sqlite3, subprocess, time, uuid
from datetime import date
from urllib.parse import urlsplit
from flask import Flask, request, g, abort, send_file, send_from_directory, jsonify

DATA = os.environ.get("DATA_DIR", "/data")
UPLOADS = os.path.join(DATA, "uploads")
VIDEO_CACHE = os.path.join(DATA, "video-cache")
THUMBS = os.path.join(DATA, "thumbs")
WEB_DIR = os.environ.get("WEB_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"))
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(VIDEO_CACHE, exist_ok=True)
os.makedirs(THUMBS, exist_ok=True)
ALLOWED = {".gif", ".webp", ".png", ".jpg", ".jpeg"}
MAX_SECONDS = 99 * 60 + 59
MIN_GIF_SECONDS = 0.25

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
    if "seconds" not in [row[1] for row in c.execute("pragma table_info(completions)")]:
        c.execute("alter table completions add column seconds integer not null default 0")
        c.execute("""update completions set seconds=coalesce(
            (select sum(s.seconds) from steps s where s.program_id=completions.program_id), 0)""")


# ---------- helpers ----------
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


# ---------- list thumbnails ----------
# A single small JPEG per media file. List views use it instead of the animated GIF so
# scrolling and opening a long workout does not decode dozens of full-size animations.
def thumb_path(rel):
    return os.path.join(THUMBS, hashlib.sha1(rel.encode("utf-8")).hexdigest() + ".jpg")


def drop_thumb(rel):
    if not rel:
        return
    try:
        os.remove(thumb_path(rel))
    except OSError:
        pass


def ensure_thumb(rel, src):
    """Return a cached thumbnail path for src, generating it on first use. None if unavailable."""
    if not (rel and src and os.path.isfile(src) and shutil.which("ffmpeg")):
        return None
    dst = thumb_path(rel)
    try:
        if os.path.getmtime(dst) >= os.path.getmtime(src):
            return dst
    except OSError:
        pass
    tmp = f"{dst}.{uuid.uuid4().hex}.jpg"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-vf", "thumbnail=10,scale=160:-2:flags=lanczos",
            "-frames:v", "1", "-q:v", "4", tmp,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        os.replace(tmp, dst)
        return dst
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        try:
            os.remove(tmp)
        except OSError:
            pass
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


def clean_video_cache(keep=None):
    cutoff = time.time() - 3600
    keep = keep if keep and re.fullmatch(r"[0-9a-f]{32}", keep) else None
    for path in glob.glob(os.path.join(VIDEO_CACHE, "*")):
        if keep and os.path.basename(path).startswith(keep):
            continue
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


def purge_video_cache():
    """Remove every cached video preview. Called whenever a page is opened."""
    for path in glob.glob(os.path.join(VIDEO_CACHE, "*")):
        try:
            os.remove(path)
        except OSError:
            pass


def release_video_cache(token):
    """Remove the cached files for one preview token, if it is valid."""
    if not re.fullmatch(r"[0-9a-f]{32}", token or ""):
        return
    for path in glob.glob(os.path.join(VIDEO_CACHE, token + "*")):
        try:
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
    """Resolve the category field: an existing id, "new" (+ new_category name) or empty."""
    sel = str(form.get("category") or "").strip()
    if sel == "new":
        return ensure_category(str(form.get("new_category") or "").strip())
    if sel.isdigit():
        row = db().execute("select id from categories where id=?", (int(sel),)).fetchone()
        return (row["id"], False) if row else (None, False)
    return None, False


def category_name(cid):
    if cid is None:
        return None
    row = db().execute("select name from categories where id=?", (cid,)).fetchone()
    return row["name"] if row else None


def normalized_crop(value):
    """Validate a {x,y,w,h} crop (0..1 of the frame) and return an ffmpeg filter."""
    if not value:
        return None
    if not isinstance(value, dict):
        raise ValueError
    try:
        x, y, w, h = (float(value[key]) for key in ("x", "y", "w", "h"))
    except (KeyError, TypeError, ValueError):
        raise ValueError
    if not all(math.isfinite(v) for v in (x, y, w, h)):
        raise ValueError
    if x < 0 or y < 0 or w < 0.01 or h < 0.01 or x + w > 1.001 or y + h > 1.001:
        raise ValueError
    if x <= 0.001 and y <= 0.001 and w >= 0.999 and h >= 0.999:
        return None   # the whole frame: nothing to crop
    return f"crop=iw*{w:.6f}:ih*{h:.6f}:iw*{x:.6f}:ih*{y:.6f}"


@app.post("/api/instagram/preview")
def instagram_preview():
    clean_video_cache()
    url = str((request.get_json(silent=True) or {}).get("url") or "").strip()
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
                       video_url=f"/api/instagram/video/{token}")
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


@app.get("/api/instagram/video/<token>")
def exercise_video_preview(token):
    return send_from_directory(VIDEO_CACHE, os.path.basename(video_cache_path(token, ".mp4")),
                               mimetype="video/mp4", max_age=0)


@app.post("/api/instagram/release")
def release_instagram_video():
    """Called by the page when it is left, so preview files do not linger."""
    release_video_cache(str((request.get_json(silent=True) or {}).get("token") or ""))
    return "", 204


@app.post("/api/instagram/save")
def save_instagram_gif():
    data = request.get_json(silent=True) or {}
    token = str(data.get("token") or "")
    clean_video_cache(keep=token)
    name = str(data.get("name") or "").strip()
    if not name or len(name) > 120:
        return jsonify(error="Enter an exercise name."), 400
    source = video_cache_path(token, ".mp4")
    metadata_path = video_cache_path(token, ".json")
    if not os.path.isfile(source) or not os.path.isfile(metadata_path):
        return jsonify(error="The video preview expired. Load the Instagram URL again."), 400
    try:
        with open(metadata_path, encoding="utf-8") as metadata:
            info = json.load(metadata)
        duration = float(info["duration"])
        fps = max(1.0, float(info.get("fps") or 30.0))
        start, end = float(data.get("start", "nan")), float(data.get("end", "nan"))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return jsonify(error="Choose valid start and end points."), 400
    if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end <= start or end > duration + 0.05 or end - start > 15.001:
        return jsonify(error="Choose a clip up to 15 seconds long within the video."), 400
    if end - start < max(MIN_GIF_SECONDS, 3 / fps):
        return jsonify(error="The clip is too short. Drag the sliders further apart and try again."), 400
    try:
        crop_filter = normalized_crop(data.get("crop"))
    except ValueError:
        return jsonify(error="Choose a valid crop area."), 400
    output = video_cache_path(token, f"-clip-{uuid.uuid4().hex}.gif")
    video_chain = "fps=12,scale=480:-2:flags=lanczos"
    if crop_filter:
        video_chain = crop_filter + "," + video_chain
    try:
        subprocess.run([
            "ffmpeg", "-y", "-ss", f"{start:.4f}", "-i", source, "-t", f"{end-start:.4f}",
            "-filter_complex",
            f"[0:v]{video_chain},split[main][pal];[pal]palettegen=max_colors=128[palette];[main][palette]paletteuse=dither=bayer",
            "-an", "-loop", "0", output,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        try:
            os.remove(output)
        except OSError:
            pass
        return jsonify(error="GIF creation failed. Try a shorter section of the video."), 422
    cid, created = category_from_form(data)
    cat_name = category_name(cid)
    folder = category_folder(cat_name)
    os.makedirs(folder, exist_ok=True)
    filename = unique_name(sanitize(name), ".gif", folder=folder)
    target = os.path.join(folder, filename)
    os.replace(output, target)
    new_id = db().execute("insert into exercises(name,gif,category_id) values(?,?,?)",
                          (name, rel_upload_path(target), cid)).lastrowid
    db().commit()
    # Keep the cached video and metadata so more GIFs can be cut from the same
    # preview. They are removed by the regular one-hour cache cleanup.
    now = time.time()
    for path in (source, metadata_path):
        try:
            os.utime(path, (now, now))
        except OSError:
            pass
    return jsonify(exercise_json(new_id))


@app.errorhandler(400)
@app.errorhandler(404)
def api_errors(e):
    """Keep API errors machine-readable; other paths get Flask's normal pages."""
    if request.path.startswith("/api/"):
        msg = "Check the values and try again." if e.code == 400 else "Not found."
        return jsonify(error=msg), e.code
    return e


# ---------- serializers ----------
def exercise_json(eid):
    r = db().execute("""select e.id, e.name, e.gif, e.category_id, c.name category from exercises e
        left join categories c on c.id=e.category_id where e.id=?""", (eid,)).fetchone()
    return dict(r) if r else None


def steps_json(pid):
    rows = db().execute("""select s.id, s.seconds, s.exercise_id, e.name, e.gif
        from steps s left join exercises e on e.id=s.exercise_id
        where s.program_id=? order by s.pos, s.id""", (pid,)).fetchall()
    return [{"id": r["id"], "seconds": r["seconds"], "exercise_id": r["exercise_id"],
             "name": r["name"] or "Rest", "gif": r["gif"],
             "kind": "ex" if r["exercise_id"] else "rest"} for r in rows]


def program_json(pid):
    p = db().execute("select id, name from programs where id=?", (pid,)).fetchone() or abort(404)
    return {"id": p["id"], "name": p["name"], "steps": steps_json(pid)}


def body():
    return request.get_json(silent=True) or {}


def seconds_from(value):
    try:
        secs = int(value)
    except (TypeError, ValueError):
        abort(400)
    if not 0 < secs <= MAX_SECONDS:
        abort(400)
    return secs


# ---------- workouts ----------
@app.get("/api/programs")
def api_programs():
    purge_video_cache()
    rows = db().execute("""select p.id, p.name, coalesce(sum(s.seconds),0) total, count(s.id) steps
        from programs p left join steps s on s.program_id=p.id group by p.id order by p.id""").fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/programs")
def api_add_program():
    name = str(body().get("name") or "").strip()
    if not name:
        return jsonify(error="Enter a workout name."), 400
    pid = db().execute("insert into programs(name) values(?)", (name,)).lastrowid
    db().commit()
    return jsonify(id=pid, name=name, steps=0, total=0), 201


@app.get("/api/programs/<int:pid>")
def api_program(pid):
    purge_video_cache()
    return jsonify(program_json(pid))


@app.patch("/api/programs/<int:pid>")
def api_rename_program(pid):
    name = str(body().get("name") or "").strip()
    if not name:
        return jsonify(error="Enter a workout name."), 400
    db().execute("update programs set name=? where id=?", (name, pid))
    db().commit()
    return jsonify(ok=True)


@app.delete("/api/programs/<int:pid>")
def api_del_program(pid):
    db().execute("delete from steps where program_id=?", (pid,))
    db().execute("delete from programs where id=?", (pid,))
    db().commit()
    return jsonify(ok=True)


@app.post("/api/programs/<int:pid>/steps")
def api_add_step(pid):
    data = body()
    secs = seconds_from(data.get("seconds"))
    ex_id = data.get("exercise_id")
    if ex_id is not None:
        if not db().execute("select 1 from exercises where id=?", (ex_id,)).fetchone():
            return jsonify(error="That exercise no longer exists."), 400
    pos = db().execute("select coalesce(max(pos),-1)+1 from steps where program_id=?", (pid,)).fetchone()[0]
    db().execute("insert into steps(program_id,pos,exercise_id,seconds) values(?,?,?,?)", (pid, pos, ex_id, secs))
    db().commit()
    return jsonify(program_json(pid))


@app.put("/api/programs/<int:pid>/order")
def api_reorder(pid):
    c = db()
    current = [r[0] for r in c.execute("select id from steps where program_id=? order by pos,id", (pid,))]
    try:
        ordered = [int(v) for v in body().get("ids", [])]
    except (TypeError, ValueError):
        abort(400)
    if len(ordered) != len(current) or set(ordered) != set(current):
        abort(400)
    for pos, sid in enumerate(ordered):
        c.execute("update steps set pos=? where id=? and program_id=?", (pos, sid, pid))
    c.commit()
    return jsonify(program_json(pid))


@app.patch("/api/steps/<int:sid>")
def api_edit_step(sid):
    db().execute("update steps set seconds=? where id=?", (seconds_from(body().get("seconds")), sid))
    db().commit()
    return jsonify(ok=True)


@app.delete("/api/steps/<int:sid>")
def api_del_step(sid):
    db().execute("delete from steps where id=?", (sid,))
    db().commit()
    return jsonify(ok=True)


# ---------- exercises ----------
@app.get("/api/exercises")
def api_exercises():
    rows = db().execute("""select e.id, e.name, e.gif, e.category_id, c.name category from exercises e
        left join categories c on c.id=e.category_id order by e.name collate nocase""").fetchall()
    cats = db().execute("select id, name from categories order by name collate nocase").fetchall()
    return jsonify(exercises=[dict(r) for r in rows], categories=[dict(r) for r in cats])


@app.post("/api/exercises")
def api_add_exercise():
    name = request.form.get("name", "").strip()
    if not name:
        return jsonify(error="Enter an exercise name."), 400
    cid, _ = category_from_form(request.form)
    gif = save_gif(request.files.get("gif"), name, category_name(cid))
    eid = db().execute("insert into exercises(name,gif,category_id) values(?,?,?)", (name, gif, cid)).lastrowid
    db().commit()
    return jsonify(exercise_json(eid)), 201


@app.patch("/api/exercises/<int:eid>")
def api_edit_exercise(eid):
    data = body()
    name = str(data.get("name") or "").strip()
    row = db().execute("select * from exercises where id=?", (eid,)).fetchone() or abort(404)
    if not name:
        return jsonify(error="Enter an exercise name."), 400
    cid, _ = category_from_form(data)
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
                drop_thumb(gif)
                gif = rel_upload_path(target)
    db().execute("update exercises set name=?, gif=?, category_id=? where id=?", (name, gif, cid, eid))
    db().commit()
    return jsonify(exercise_json(eid))


@app.delete("/api/exercises/<int:eid>")
def api_del_exercise(eid):
    r = db().execute("select gif from exercises where id=?", (eid,)).fetchone()
    if r and r["gif"]:
        try:
            os.remove(os.path.join(UPLOADS, r["gif"]))
        except OSError:
            pass
        drop_thumb(r["gif"])
    db().execute("delete from steps where exercise_id=?", (eid,))
    db().execute("delete from exercises where id=?", (eid,))
    db().commit()
    return jsonify(ok=True)


@app.post("/api/exercises/<int:eid>/crop")
def api_crop_exercise(eid):
    """Crop an exercise GIF/media in place, keeping its name and category."""
    row = db().execute("select gif from exercises where id=?", (eid,)).fetchone() or abort(404)
    if not row["gif"]:
        return jsonify(error="This exercise has no GIF to crop."), 400
    try:
        crop_filter = normalized_crop(body().get("crop"))
    except ValueError:
        return jsonify(error="Choose a valid crop area."), 400
    if not crop_filter:
        return jsonify(error="Drag the crop box to select a smaller area."), 400
    if not shutil.which("ffmpeg"):
        return jsonify(error="Cropping is unavailable because ffmpeg is not installed."), 503
    src = os.path.join(UPLOADS, row["gif"])
    uploads = os.path.realpath(UPLOADS)
    if os.path.commonpath([os.path.realpath(src), uploads]) != uploads or not os.path.isfile(src):
        return jsonify(error="The exercise file could not be found."), 404
    root, ext = os.path.splitext(src)
    if ext.lower() not in ALLOWED:
        return jsonify(error="This file type cannot be cropped."), 400
    tmp = f"{root}.crop-{uuid.uuid4().hex}{ext}"
    try:
        if ext.lower() == ".gif":
            cmd = [
                "ffmpeg", "-y", "-i", src, "-filter_complex",
                f"[0:v]{crop_filter},split[main][pal];[pal]palettegen=max_colors=128[palette];[main][palette]paletteuse=dither=bayer",
                "-loop", "0", tmp,
            ]
        else:
            cmd = ["ffmpeg", "-y", "-i", src, "-vf", crop_filter, tmp]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        os.replace(tmp, src)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        try:
            os.remove(tmp)
        except OSError:
            pass
        return jsonify(error="Cropping failed. Try a larger crop area."), 422
    return jsonify(exercise_json(eid))


@app.get("/media/<path:f>")
def media(f):
    if request.args.get("thumb"):
        src = os.path.join(UPLOADS, f)
        thumb = ensure_thumb(f, src)
        if thumb:
            # Revalidate every time (cheap 304) so a recropped GIF never shows a stale preview.
            return send_file(thumb, mimetype="image/jpeg", conditional=True, max_age=0)
    return send_from_directory(UPLOADS, f, max_age=0)


# ---------- calendar & completion ----------
@app.get("/api/calendar")
def api_calendar():
    purge_video_cache()
    rows = db().execute("select day, name, seconds from completions order by id").fetchall()
    done = {}
    for row in rows:
        done.setdefault(row["day"], []).append({"name": row["name"], "seconds": row["seconds"]})
    recent = db().execute("select day, name, seconds from completions order by id desc limit 10").fetchall()
    return jsonify(done=done, recent=[dict(r) for r in recent])


@app.post("/api/programs/<int:pid>/complete")
def api_complete(pid):
    """Called by the player only when a workout ran from start to finish."""
    p = db().execute("select name from programs where id=?", (pid,)).fetchone() or abort(404)
    try:
        day = date.fromisoformat(str(body().get("day") or "")).isoformat()
    except ValueError:
        abort(400)
    seconds = db().execute("select coalesce(sum(seconds),0) from steps where program_id=?", (pid,)).fetchone()[0]
    db().execute("insert into completions(program_id,name,day,ts,seconds) values(?,?,?,datetime('now'),?)",
                 (pid, p["name"], day, seconds))
    db().commit()
    return jsonify(ok=True)


# ---------- single-page app ----------
@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def spa(path):
    if path.startswith(("api/", "media/", "static/")):
        abort(404)
    if path and os.path.isfile(os.path.join(WEB_DIR, path)):
        hashed = path.startswith("assets/")
        return send_from_directory(WEB_DIR, path, max_age=31536000 if hashed else 0)
    if not os.path.isfile(os.path.join(WEB_DIR, "index.html")):
        return ("Frontend not built. Run `npm run build` in frontend/ (or use the Docker image).", 503)
    resp = send_from_directory(WEB_DIR, "index.html", max_age=0)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/manifest.webmanifest")
def manifest():
    return send_from_directory(app.static_folder, "manifest.webmanifest", mimetype="application/manifest+json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8088, debug=True)
