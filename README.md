# Kettlebell Timer

A small web app for building kettlebell workouts and running them with a countdown. It is designed to look and feel like a native iPhone training app, since it will mostly be opened from a phone. It runs as a Docker container (for example on Unraid).

## What it does

**Exercises**
- Save an exercise as a name plus a GIF showing the movement.
- Delete exercises you no longer need.

**Workouts**
- Create a workout and build it from steps. Each step is either an exercise or a rest, with a duration in minutes and seconds.
- Reorder steps with the up and down buttons, and remove steps you don't want.
- See the total workout time.

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
- Keeps the screen awake while running (needs HTTPS, see notes below).

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

- **HTTPS:** the "keep screen awake" feature only works over HTTPS. Without it the timer still runs, but the screen may dim. Put the app behind Nginx Proxy Manager, Tailscale or a Cloudflare tunnel to fix this.
- **Full screen on iPhone:** Safari on iPhone does not allow websites to hide the address bar. For a true full-screen player, use **Share → Add to Home Screen** and open the app from the Home Screen icon. On Android, iPad and desktop, tapping "Tap to begin" enters full screen automatically, and "Done" exits it.
- **Sound on iPhone:** Safari only allows sound after a tap, so the player starts with a "Tap to begin" screen.
- **No login:** the app has no authentication. Keep it on your home network or behind a VPN.
- **GIF uploads:** `.gif`, `.webp`, `.png` and `.jpg` files up to 30 MB.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATA_DIR` | `/data` | Where the database and uploads are stored |

For running and debugging locally, see [DEBUGGING_IN_ZED.md](DEBUGGING_IN_ZED.md).
