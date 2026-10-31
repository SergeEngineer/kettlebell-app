# Kettlebell Timer

A small web app for building kettlebell workouts and running them with a countdown. It is designed to look and feel like a native iPhone training app, since it will mostly be opened from a phone. It runs as a Docker container (for example on Unraid).

## What it does

**Exercises**
- Save an exercise as a name plus a GIF showing the movement. The GIF file is stored under the exercise's name (for example `Kettlebell Swing.gif`) and renamed when you rename the exercise.
- Delete exercises you no longer need.

**Workouts**
- Create a workout and build it from steps. Each step is either an exercise or a rest, with a duration in minutes and seconds.
- Reorder steps with the up and down buttons, and remove steps you don't want.
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

1. Copy the project folder to `/mnt/user/appdata/kettlebell-src`.
2. In the Unraid terminal:
   ```bash
   cd /mnt/user/appdata/kettlebell-src
   docker build -t kettlebell .
   ```
3. In the Docker tab, choose **Add Container** and set:
   - **Repository:** `kettlebell`
   - **Port:** host `8088` to container `8088`
   - **Path:** `/mnt/user/appdata/kettlebell` mapped to `/data` (keeps your data between updates)
4. Open `http://UNRAID-IP:8088` on your phone.
5. In Safari, use **Share → Add to Home Screen** to get the full-screen app look.

To update after changing code: rebuild the image and recreate the container. Your data in `/data` is kept.

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
- **GIF uploads:** `.gif`, `.webp`, `.png` and `.jpg` files up to 30 MB.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATA_DIR` | `/data` | Where the database and uploads are stored |

For running and debugging locally, see [DEBUGGING_IN_ZED.md](DEBUGGING_IN_ZED.md).
