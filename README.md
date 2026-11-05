# Kettlebell Timer

A small web app for building kettlebell workouts and running them with a countdown. It is designed to look and feel like a native iPhone training app, since it will mostly be opened from a phone. It runs as a Docker container (for example on Unraid).

## What it does

**Exercises**
- Save an exercise as a name, a category and a GIF showing the movement. Pick an existing category or create a new one while saving. Each category gets its own folder under `/data/uploads/` (for example `/data/uploads/Kettlebell/Kettlebell Swing.gif`); GIFs are renamed when you rename the exercise.
- Create a GIF from a public Instagram post or Reel by loading its URL, previewing the video, and choosing the start and end frames (up to 15 seconds).
- Change an exercise's category with ✎; its GIF moves to the new category folder.
- Delete exercises you no longer need.

**Workouts**
- Create a workout and build it from steps. Each step is either an exercise or a rest, with a duration in minutes and seconds.
- When adding an exercise step, filter the picker by category and choose from animated GIF thumbnails.
- Reorder steps by holding and dragging them, or use the up and down buttons; remove steps you don't want.
- See the total workout time.
- Rename a workout with the ✎ icon beside its title, and swipe a workout left on the home screen to delete it. Tap a step to expand it and change its time with iOS-style scroll wheels (saved automatically), and swipe a step left to delete it, like in iOS Mail. A step always shows its exercise's name, and exercises can be renamed in the Exercises tab.

Example workout:

| Step | Duration |
|---|---|
| Kettlebell Swing | 5 min |
| Rest | 1 min |
| Goblet Squat | 5 min |
| Rest | 1 min |
| Romanian Deadlift | 5 min |

**Player (START)**
- Full-screen dark view with a circular progress ring and a large countdown.
- Shows the exercise name and its looping GIF.
- During a rest, shows the upcoming exercise's GIF and name so you can get ready.
- Shows what is coming next, with pause, skip and back controls.
- A 5 second "Get ready" countdown runs before the first step.
- Beeps in the last 3 seconds and at every change. Vibrates on devices that support it.
- Keeps the screen awake while running (see notes below).

**Calendar**
- A contribution-style calendar (last 12 months). A day turns green when you finish a workout from start to finish; two or more finished workouts in a day show a brighter green.
- A workout only counts when its last step's timer runs out. Workouts you leave early, or skip through to the end, are not counted.
- Tap a day to see which workouts you completed. The tab also shows your totals and current streak.

## Tech stack

| Part | Choice |
|---|---|
| Backend | Python 3.12, Flask, gunicorn |
| Frontend | Server-rendered Jinja templates + HTMX |
| Timer | Plain JavaScript in the browser |
| Storage | SQLite + uploaded GIFs, both in the `/data` volume |
| Packaging | Docker |

## Project layout

```
kettlebell/
├── app.py                 Flask routes and database
├── templates/             Pages and HTMX partials
│   ├── base.html          Layout with the iOS style tab bar
│   ├── index.html         Workouts list
│   ├── program.html       Workout editor
│   ├── exercises.html     Exercise library
│   ├── run.html           Countdown player
│   └── _*.html            Partials swapped in by HTMX
├── static/
│   ├── app.css            iOS look and feel
│   └── htmx.min.js        Downloaded during the Docker build
├── Dockerfile
├── .dockerignore
├── docker-compose.yml
├── README.md
└── DEBUGGING_IN_ZED.md    Running and debugging locally
```

## Run with Docker

```bash
docker build -t kettlebell .
docker run --rm -p 8088:8088 -v "$(pwd)/data:/data" kettlebell
```

Open http://localhost:8088. Your database and GIFs are stored in `./data`.

Or with Compose:

```bash
docker compose up --build
```

## Deploy on Unraid

### 1. Place the source on Unraid

In the Unraid terminal:

```bash
git clone <repository-url> /mnt/user/appdata/kettlebell
```

*(Alternatively, copy the project folder to `/mnt/user/appdata/kettlebell` over your SMB appdata share).*

### 2. Choose a deployment method

#### Option A: Docker Compose (Fastest)

If you have Docker Compose or the **Docker Compose Manager** plugin installed on Unraid:

```bash
cd /mnt/user/appdata/kettlebell
docker compose up -d --build
```

`docker-compose.yml` is already preconfigured to map `/mnt/user/appdata/kettlebell` to `/data` and port `8088`.

---

#### Option B: Unraid Web UI (Standard)

Note if you updating the app to the latest version by replacing all files from repo, DON NOT DELETE `/data` folder as it contains the database and GIF files.

1. **Build the Docker image** in the Unraid terminal:
   ```bash
   cd /mnt/user/appdata/kettlebell
   docker build -t kettlebell .
   ```

2. **Add the container**:
   In the Unraid web interface, go to the **Docker** tab and click **Add Container** at the bottom:
   - **Name:** `kettlebell`
   - **Repository:** `kettlebell`
   - **Network Type:** `Bridge`
   - **WebUI:** `http://[IP]:[PORT:8088]/`

3. **Add Port mapping**:
   Click **+ Add another Path, Port, Variable, Device or Label**:
   - **Config Type:** `Port`
   - **Name:** `Web UI Port`
   - **Container Port:** `8088`
   - **Host Port:** `8088` (or another port if 8088 is already in use)
   - **Connection Type:** `TCP`
   - Click **Add**.

4. **Add Data Path mapping**:
   Click **+ Add another Path, Port, Variable, Device or Label**:
   - **Config Type:** `Path`
   - **Name:** `Appdata`
   - **Container Path:** `/data`
   - **Host Path:** `/mnt/user/appdata/kettlebell/data`
   - **Access Mode:** `Read/Write`
   - Click **Add**.

5. Click **Apply** to start the container.

---

### 3. Open on your devices

1. Open `http://<UNRAID-IP>:8088` in your browser.
2. On your iPhone, open the URL in Safari and tap **Share → Add to Home Screen** for the full-screen native app look.

### Updating after code changes

- **If using Compose:**
  ```bash
  cd /mnt/user/appdata/kettlebell-src
  git pull
  docker compose up -d --build
  ```
- **If using Unraid Web UI:**
  1. In the Unraid terminal:
     ```bash
     cd /mnt/user/appdata/kettlebell-src
     git pull
     docker build -t kettlebell .
     ```
  2. In the Unraid **Docker** tab, click the `kettlebell` container icon, select **Edit**, and click **Apply** at the bottom. Unraid will recreate the container using the new image while preserving all your exercises, workouts, and calendar history in `/mnt/user/appdata/kettlebell`.

## Notes

- **Screen stays on:** during a workout the app asks the iPhone to keep the screen awake (Wake Lock API) and also plays a tiny silent hidden video as a fallback. On iPhone this has limits you should know about:
  - The Wake Lock API only works over **HTTPS**. Over plain `http://` it is unavailable, and the video fallback is not reliable, especially in Home Screen apps on recent iOS versions.
  - In a **Home Screen app**, the Wake Lock API only works from iOS 18.4. In a normal Safari tab it works from iOS 16.4.
  - **Low Power Mode** shortens auto-lock to 30 seconds and can override this.
  - The guaranteed fallback is Settings → Display & Brightness → Auto-Lock → **Never** (switch it back afterwards).
  - To get HTTPS on Unraid, put the app behind Nginx Proxy Manager (Let's Encrypt), a Cloudflare tunnel, or Tailscale (`tailscale serve`, with HTTPS certificates enabled in the Tailscale admin console).
- **Full screen on iPhone:** Safari on iPhone does not allow websites to hide the address bar. For a true full-screen player, use **Share → Add to Home Screen** and open the app from the Home Screen icon. On Android, iPad and desktop, tapping "Tap to begin" enters full screen automatically, and "Done" exits it.
- **Sound on iPhone:** Safari only allows sound after a tap, so the player starts with a "Tap to begin" screen.
- **No login:** the app has no authentication. Keep it on your home network or behind a VPN.
- **GIF uploads:** `.gif`, `.webp`, `.png` and `.jpg` files up to 30 MB. Files are stored in `/data/uploads/<Category>/` and the folder is created automatically when you add a category.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATA_DIR` | `/data` | Where the database and uploads are stored |

For running and debugging locally, see [DEBUGGING_IN_ZED.md](DEBUGGING_IN_ZED.md).
