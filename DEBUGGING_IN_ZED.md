# Debugging in Zed

How to open the Kettlebell app in the Zed editor (for example on Omarchy), run it locally, debug it with breakpoints, and test the Docker image.

## 1. Set up the Python environment

The `import "flask" could not be resolved` error is not a missing extension. Zed includes Python support (Pyright) out of the box. The error means Flask is not installed in an environment Zed can see.

From the project folder:

```bash
python -m venv .venv
source .venv/bin/activate
pip install flask gunicorn debugpy yt-dlp
curl -L -o static/htmx.min.js https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js
```

`yt-dlp` and `ffmpeg` are needed to load Instagram videos and convert them into GIFs. Ensure `ffmpeg` is installed on your host system (e.g. `sudo pacman -S ffmpeg` on Arch/Omarchy).

The last command downloads htmx. The Dockerfile does this during the image build, but a local run outside Docker needs the file in place.

Create `pyrightconfig.json` in the project root so Zed finds the environment:

```json
{ "venvPath": ".", "venv": ".venv" }
```

Then restart the language server (command palette → `editor: restart language server`) or reopen the project. The warning on `flask` should disappear.

## 2. Run the app without the debugger

```bash
source .venv/bin/activate
DATA_DIR=./data FLASK_DEBUG=1 flask --app app run --host 0.0.0.0 --port 8088
```

Open http://localhost:8088. `DATA_DIR=./data` keeps the test database and GIFs inside the project instead of `/data`.

## 3. Debug with breakpoints

Zed's debugger uses debugpy for Python, so you need a recent Zed version.

Create `.zed/debug.json`:

```json
[
  {
    "label": "Flask app",
    "adapter": "Debugpy",
    "request": "launch",
    "module": "flask",
    "args": ["run", "--no-reload", "--host", "0.0.0.0", "--port", "8088"],
    "env": {
      "FLASK_APP": "app",
      "FLASK_DEBUG": "1",
      "DATA_DIR": "${ZED_WORKTREE_ROOT}/data"
    }
  }
]
```

Steps:

1. Open `app.py` and click in the gutter next to a line number to set a breakpoint, for example inside `add_step`.
2. Open the debug panel (or press `F4`) and start **Flask app**.
3. Open http://localhost:8088 in a browser and trigger the action. Zed pauses on the breakpoint.
4. Use the step controls to step over, step into or continue, and inspect variables in the panel.

`--no-reload` is required. Flask's auto-reloader starts a second process, and breakpoints become unreliable there.

Note: `--host 0.0.0.0` exposes Flask's interactive debugger to your network. That is fine at home. Remove the host flag on a shared network.

## 4. Run the Dockerfile locally

Install Docker on Omarchy (Arch based):

```bash
sudo pacman -S docker docker-buildx
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Log out and back in so the group change applies.

Add `.zed/tasks.json` to run Docker from Zed (command palette → `task: spawn`):

```json
[
  {
    "label": "docker build",
    "command": "docker build -t kettlebell .",
    "use_new_terminal": false
  },
  {
    "label": "docker run",
    "command": "docker run --rm -p 8088:8088 -v $ZED_WORKTREE_ROOT/data:/data kettlebell",
    "use_new_terminal": true
  }
]
```

Or in a terminal:

```bash
docker build -t kettlebell .
docker run --rm -p 8088:8088 -v "$(pwd)/data:/data" kettlebell
```

The `./data` folder is mounted as `/data`, the same way it will be on Unraid, so uploaded GIFs persist between runs. Stop the container with `Ctrl+C`.

## 5. Test how it looks

**Desktop browser**

1. Open http://localhost:8088 in Chromium.
2. Press `Ctrl+Shift+M` to open the device toolbar.
3. Pick an iPhone preset such as iPhone 15 Pro.

You will see the safe areas, tab bar and player at phone size.

**Real phone**

1. Connect the phone to the same Wi-Fi as your Omarchy machine.
2. Open `http://<omarchy-ip>:8088` in Safari. Find the IP with `ip a`.
3. If the page does not load, allow the port in the firewall: `sudo ufw allow 8088/tcp`.
4. Use **Share → Add to Home Screen** for the full-screen app look.

Sound works on the phone after the first tap. Keeping the screen awake needs HTTPS, so it will not work over plain HTTP.

## Troubleshooting

| Problem | Fix |
|---|---|
| `flask` import still unresolved | Check that `.venv` exists and `pyrightconfig.json` is in the project root, then restart the language server |
| Page loads but buttons do nothing | `static/htmx.min.js` is missing. Run the `curl` command in section 1 |
| Breakpoints are never hit | Make sure `--no-reload` is in the debug args and you started the debugger, not a normal run |
| Missing `yt-dlp` error on Instagram video load | Run `pip install yt-dlp` in your active `.venv` (or rebuild the Docker container) |
| Missing `ffmpeg` error | Install ffmpeg with `sudo pacman -S ffmpeg` (or your system's package manager) |
| `permission denied` from Docker | Add your user to the `docker` group and log out and back in |
| Port 8088 already in use | Stop the other process, or change the port in the run command and debug config |
| Phone cannot reach the app | Check both devices are on the same network and the firewall allows 8088 |
| GIFs missing after a rebuild | Run the container with the `-v ./data:/data` mount |
