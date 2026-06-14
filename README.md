# V01D CONVERT PRIM3 v1.0

> Terminal-style all-in-one conversion suite for indie game developers.

```
▓▓ V01D CONVERT PRIM3 v1.0 ▓▓
MP4·GIF·WEB·EXE·APP
```

Single Python script. No installation. Just run it.

---

## What it does

| Tab | Input | Output | Use case |
|---|---|---|---|
| MP4→GIF | `.mp4 .mov .avi` | `.gif` | Showcase clips, trailers, itch.io previews |
| PY→WEB | Python game folder | Browser HTML build | itch.io free browser play |
| PY→EXE | `.py` | Linux/Windows binary | Direct download, Steam |
| MAC.APP | `.py` | macOS `.app` bundle | Mac distribution |
| INFO | — | — | Dependency status, guides, install commands |

---

## Requirements

Just Python 3.8+ and tkinter (included with Python).

Everything else — `ffmpeg`, `pygbag`, `PyInstaller` — is detected on launch and installed with one click.

---

## Run

```bash
python3 v01d_convert_prim3.py
```

On first launch a startup screen checks all dependencies and offers to install anything missing automatically.

---

## Features

- **Terminal aesthetic** — matrix green on black, `Courier New` throughout
- **Startup dependency checker** — detects ffmpeg, pygbag, PyInstaller; installs all missing with one click
- **Real progress bars** — percentage-tracked, not just spinners
  - MP4→GIF: parses `time=` from ffmpeg output vs total duration
  - PY→WEB: parses `[ n% ]` bracket output from pygbag
  - PY→EXE / MAC.APP: phase-estimated across collect → link → bundle
- **Global status bar** — always-visible bottom bar shows current job + session history of last 6 completed jobs
- **Mac .app — 3 ways**
  - Build Direct (if you're on a Mac)
  - Save `mac_build_user.py` — send to any Mac user, GUI does everything
  - Save GitHub Actions YAML — auto-builds `.app` on free Mac runners on every push
- **Cross-platform** — Linux, macOS, Windows; pip installs adapt per OS

---

## Platform notes

- **Linux** → EXE tab produces a Linux binary. For `.exe` build on Windows; for `.app` use the Mac tab.
- **macOS** → MAC.APP Build Direct tab works natively.
- **Windows** → EXE tab produces a `.exe`.
- PyInstaller always builds for the OS it runs on. Cross-platform builds require the Mac tab's User Script or GitHub Actions options.

---

## Dependencies (auto-installed)

| Tool | Used for | Auto-install method |
|---|---|---|
| `ffmpeg` | MP4→GIF conversion | `apt` / `brew` / `choco` |
| `pygbag` | Python→Web build | `pip` |
| `PyInstaller` | EXE + .app builds | `pip` |

---

## License

MIT — do whatever you want with it.

---

*Built for indie devs who just want to ship.*
