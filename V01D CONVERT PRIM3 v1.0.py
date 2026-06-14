#!/usr/bin/env python3
"""
V01D CONVERT PRIM3 v1.0
MP4→GIF | Python→Web | Python→EXE | Mac .app
Terminal-style GUI. Auto-detects and installs dependencies.
stdlib only to launch. All else installed on demand.
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import subprocess, threading, os, sys, re, platform, shutil, datetime, time

# ══════════════════════════════════════════════════════════════════════════════
# THEME — terminal green on black
# ══════════════════════════════════════════════════════════════════════════════
BG      = "#0a0a0a"   # near-black
BG2     = "#111111"   # panel bg
BG3     = "#0d0d0d"   # log bg
TERM    = "#00ff41"   # matrix green
TERM2   = "#00cc33"   # dimmer green
TERM3   = "#005514"   # dark green (trough / inactive)
MUTED   = "#1a5c1a"   # very dim green
AMBER   = "#ffb000"   # warnings
RED     = "#ff2222"   # errors
WHITE   = "#cccccc"   # neutral text
FONT    = "Courier New"
FONT_SZ = 10
TITLE_F = (FONT, 13, "bold")
HEAD_F  = (FONT, 10, "bold")
BODY_F  = (FONT, 10)
SMALL_F = (FONT, 8)

OS_NAME = platform.system()   # Darwin | Linux | Windows

def smart_pip_cmd(pkg):
    """pip install command that works on Linux (PEP 668), Mac, and Windows."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", pkg]
    if OS_NAME == "Linux":
        cmd.append("--break-system-packages")
    return cmd

# ══════════════════════════════════════════════════════════════════════════════
# JOB HISTORY  (global, shared across all tabs)
# ══════════════════════════════════════════════════════════════════════════════
job_history = []   # list of dicts: {name, status, pct, time}
_history_callbacks = []

def history_subscribe(cb):
    _history_callbacks.append(cb)

def job_done(name, success):
    job_history.append({
        "name":   name,
        "status": "OK" if success else "FAIL",
        "pct":    100 if success else 0,
        "time":   datetime.datetime.now().strftime("%H:%M:%S"),
    })
    for cb in _history_callbacks:
        try: root.after(0, cb)
        except: pass

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL BOTTOM STATUS BAR
# ══════════════════════════════════════════════════════════════════════════════
class StatusBar:
    """Fixed bottom bar: current job progress + session history."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=BG3, bd=0)
        self.frame.pack(side="bottom", fill="x")

        # separator line
        tk.Frame(self.frame, bg=TERM3, height=1).pack(fill="x")

        top = tk.Frame(self.frame, bg=BG3)
        top.pack(fill="x", padx=10, pady=(4,2))

        # current job label + pct text
        self._job_var = tk.StringVar(value="IDLE")
        self._pct_var = tk.StringVar(value="")
        tk.Label(top, textvariable=self._job_var, bg=BG3, fg=TERM,
                 font=(FONT, 9, "bold"), anchor="w").pack(side="left")
        tk.Label(top, textvariable=self._pct_var, bg=BG3, fg=TERM2,
                 font=SMALL_F, anchor="e").pack(side="right")

        # progress canvas
        self._canvas = tk.Canvas(self.frame, height=12, bg=TERM3,
                                 highlightthickness=0)
        self._canvas.pack(fill="x", padx=10, pady=(0,4))
        self._w = 0
        self._canvas.bind("<Configure>", lambda e: setattr(self, "_w", e.width))
        self._pct  = 0
        self._anim = None
        self._spin_pos = 0
        self._spinning = False

        # history strip
        hist_frame = tk.Frame(self.frame, bg=BG3)
        hist_frame.pack(fill="x", padx=10, pady=(0,5))
        tk.Label(hist_frame, text="SESSION ▸ ", bg=BG3, fg=MUTED,
                 font=SMALL_F).pack(side="left")
        self._hist_lbl = tk.Label(hist_frame, text="no jobs yet",
                                   bg=BG3, fg=MUTED, font=SMALL_F, anchor="w")
        self._hist_lbl.pack(side="left", fill="x")

        history_subscribe(self._refresh_history)

    # ── public API ─────────────────────────────────────────────────────────
    def start(self, label):
        self._job_var.set(f"▶ {label}")
        self._pct_var.set("")
        self._pct = 0
        self._spinning = True
        self._spin_pos = 0
        self._tick()

    def set(self, pct, label=None):
        self._spinning = False
        if self._anim: root.after_cancel(self._anim); self._anim = None
        self._pct = max(0, min(100, pct))
        if label: self._job_var.set(f"▶ {label}")
        self._pct_var.set(f"{int(self._pct)}%")
        self._draw_bar(self._pct)

    def finish(self, label, success=True):
        self._spinning = False
        if self._anim: root.after_cancel(self._anim); self._anim = None
        self._pct = 100 if success else 0
        color = TERM if success else RED
        self._job_var.set(("✓" if success else "✗") + f" {label}")
        self._pct_var.set("100%" if success else "FAILED")
        self._draw_bar(self._pct, color=color)
        job_done(label, success)

    def idle(self):
        self._spinning = False
        if self._anim: root.after_cancel(self._anim); self._anim = None
        self._job_var.set("IDLE")
        self._pct_var.set("")
        self._draw_bar(0)

    # ── internal ───────────────────────────────────────────────────────────
    def _tick(self):
        if not self._spinning: return
        w = self._canvas.winfo_width() or 600
        self._spin_pos = (self._spin_pos + 4) % 110
        x1 = int(self._spin_pos / 110 * w)
        x2 = min(x1 + int(w * 0.25), w)
        c = self._canvas; c.delete("all")
        c.create_rectangle(0, 0, w, 12, fill=TERM3, outline="")
        c.create_rectangle(x1, 0, x2, 12, fill=TERM2, outline="")
        c.create_text(w//2, 6, text="PROCESSING…",
                      fill=BG, font=(FONT, 7, "bold"))
        self._anim = root.after(25, self._tick)

    def _draw_bar(self, pct, color=TERM):
        w = self._canvas.winfo_width() or 600
        fw = int(w * pct / 100)
        c = self._canvas; c.delete("all")
        c.create_rectangle(0, 0, w, 12, fill=TERM3, outline="")
        if fw > 0:
            c.create_rectangle(0, 0, fw, 12, fill=color, outline="")
        if pct > 0:
            c.create_text(w//2, 6, text=f"{int(pct)}%",
                          fill=BG if fw > w//2 else TERM,
                          font=(FONT, 7, "bold"))

    def _refresh_history(self):
        if not job_history:
            self._hist_lbl.config(text="no jobs yet")
            return
        parts = []
        for j in job_history[-6:]:   # show last 6
            icon = "✓" if j["status"] == "OK" else "✗"
            parts.append(f"{icon}{j['name']}@{j['time']}")
        self._hist_lbl.config(text="  |  ".join(parts), fg=TERM2)


# ══════════════════════════════════════════════════════════════════════════════
# STARTUP DEPENDENCY CHECKER
# ══════════════════════════════════════════════════════════════════════════════
class StartupChecker:
    """Full-screen checklist shown at launch. Installs everything with one click."""

    DEPS = [
        {"id": "ffmpeg",      "label": "ffmpeg",      "type": "binary",
         "apt": "ffmpeg",     "brew": "ffmpeg",       "choco": "ffmpeg"},
        {"id": "pygbag",      "label": "pygbag",      "type": "pip",    "pkg": "pygbag"},
        {"id": "pyinstaller", "label": "PyInstaller", "type": "pip",    "pkg": "pyinstaller"},
    ]

    def __init__(self, parent, on_done):
        self.parent   = parent
        self.on_done  = on_done
        self.statuses = {}   # id → "ok" | "missing" | "installing" | "error"

        self.frame = tk.Frame(parent, bg=BG)
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self._build_ui()
        self._check_all()

    def _build_ui(self):
        f = self.frame

        tk.Label(f, text="V01D CONVERT PRIM3 v1.0", bg=BG, fg=TERM,
                 font=(FONT, 16, "bold")).pack(pady=(36, 4))
        tk.Label(f, text="SYSTEM DEPENDENCY CHECK", bg=BG, fg=TERM2,
                 font=(FONT, 9)).pack(pady=(0, 28))

        self.rows = {}
        for dep in self.DEPS:
            row = tk.Frame(f, bg=BG2, padx=16, pady=10)
            row.pack(fill="x", padx=60, pady=4)
            tk.Label(row, text=dep["label"], bg=BG2, fg=WHITE,
                     font=HEAD_F, width=16, anchor="w").pack(side="left")
            status_lbl = tk.Label(row, text="CHECKING…", bg=BG2, fg=AMBER,
                                  font=HEAD_F, width=12, anchor="w")
            status_lbl.pack(side="left")
            note_lbl = tk.Label(row, text="", bg=BG2, fg=MUTED,
                                font=SMALL_F, anchor="w")
            note_lbl.pack(side="left", padx=12)
            self.rows[dep["id"]] = {"status": status_lbl, "note": note_lbl}

        # log
        self.log_box = scrolledtext.ScrolledText(
            f, height=7, bg=BG3, fg=TERM2, font=(FONT, 8),
            relief="flat", state="disabled")
        self.log_box.pack(fill="x", padx=60, pady=(20, 4))

        # buttons
        bf = tk.Frame(f, bg=BG)
        bf.pack(pady=16)
        self.btn_install = tk.Button(
            bf, text="[ INSTALL ALL MISSING ]", command=self._install_all,
            bg=TERM3, fg=TERM, font=HEAD_F, relief="flat",
            cursor="hand2", padx=20, pady=10,
            activebackground=TERM3, activeforeground=TERM)
        self.btn_install.pack(side="left", padx=8)
        self.btn_skip = tk.Button(
            bf, text="[ LAUNCH ANYWAY ]", command=self._launch,
            bg=BG2, fg=MUTED, font=HEAD_F, relief="flat",
            cursor="hand2", padx=20, pady=10,
            activebackground=BG2, activeforeground=WHITE)
        self.btn_skip.pack(side="left", padx=8)

    def _log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _check_all(self):
        def check():
            for dep in self.DEPS:
                if dep["type"] == "binary":
                    ok = shutil.which(dep["id"]) is not None
                else:
                    ok = subprocess.run(
                        [sys.executable, "-c", f"import {dep['pkg']}"],
                        capture_output=True).returncode == 0
                self.statuses[dep["id"]] = "ok" if ok else "missing"
                root.after(0, lambda d=dep, s=self.statuses[dep["id"]]: self._set_status(d["id"], s))
            root.after(0, self._after_check)
        threading.Thread(target=check, daemon=True).start()

    def _set_status(self, dep_id, status):
        row = self.rows[dep_id]
        if status == "ok":
            row["status"].config(text="✓  FOUND", fg=TERM)
            row["note"].config(text="")
        elif status == "missing":
            row["status"].config(text="✗  MISSING", fg=RED)
            row["note"].config(text="will install", fg=AMBER)
        elif status == "installing":
            row["status"].config(text="…  INSTALLING", fg=AMBER)
            row["note"].config(text="", fg=MUTED)
        elif status == "error":
            row["status"].config(text="✗  FAILED", fg=RED)
            row["note"].config(text="install manually", fg=RED)
        elif status == "done":
            row["status"].config(text="✓  INSTALLED", fg=TERM)
            row["note"].config(text="", fg=MUTED)

    def _after_check(self):
        missing = [d for d in self.DEPS if self.statuses.get(d["id"]) == "missing"]
        if not missing:
            self._log("All dependencies found. Ready to launch.\n")
            self.btn_install.config(text="[ ALL GOOD — LAUNCH ]",
                                    command=self._launch, bg=TERM3, fg=TERM)
        else:
            names = ", ".join(d["label"] for d in missing)
            self._log(f"Missing: {names}\nClick INSTALL ALL MISSING to auto-install.\n")

    def _install_all(self):
        missing = [d for d in self.DEPS if self.statuses.get(d["id"]) == "missing"]
        if not missing:
            self._launch(); return
        self.btn_install.config(state="disabled", text="[ INSTALLING… ]")
        self.btn_skip.config(state="disabled")
        threading.Thread(target=self._install_thread, args=(missing,), daemon=True).start()

    def _install_thread(self, deps):
        all_ok = True
        for dep in deps:
            root.after(0, lambda d=dep: self._set_status(d["id"], "installing"))
            self._log_r(f"\n>>> Installing {dep['label']}…\n")
            try:
                if dep["type"] == "pip":
                    cmd = smart_pip_cmd(dep["pkg"])
                elif dep["type"] == "binary":
                    if OS_NAME == "Linux":
                        cmd = ["sudo", "apt-get", "install", "-y", dep["apt"]]
                    elif OS_NAME == "Darwin":
                        cmd = ["brew", "install", dep["brew"]]
                    elif OS_NAME == "Windows":
                        cmd = ["choco", "install", "-y", dep["choco"]]
                    else:
                        self._log_r(f"Cannot auto-install {dep['label']} on {OS_NAME}.\n")
                        root.after(0, lambda d=dep: self._set_status(d["id"], "error"))
                        all_ok = False; continue

                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True)
                for line in proc.stdout:
                    self._log_r(line)
                proc.wait()
                if proc.returncode == 0:
                    self.statuses[dep["id"]] = "ok"
                    root.after(0, lambda d=dep: self._set_status(d["id"], "done"))
                else:
                    self.statuses[dep["id"]] = "error"
                    root.after(0, lambda d=dep: self._set_status(d["id"], "error"))
                    all_ok = False
            except Exception as e:
                self._log_r(f"Error: {e}\n")
                self.statuses[dep["id"]] = "error"
                root.after(0, lambda d=dep: self._set_status(d["id"], "error"))
                all_ok = False

        self._log_r("\n>>> Done.\n")
        root.after(0, lambda: self._install_finished(all_ok))

    def _log_r(self, text):
        root.after(0, lambda t=text: self._log(t))

    def _install_finished(self, all_ok):
        self.btn_skip.config(state="normal")
        if all_ok:
            self.btn_install.config(state="normal",
                text="[ ✓ ALL INSTALLED — LAUNCH ]", command=self._launch)
        else:
            self.btn_install.config(state="normal",
                text="[ RETRY ]", command=self._install_all)
            self._log("Some installs failed. Fix manually or Launch Anyway.\n")

    def _launch(self):
        self.frame.destroy()
        self.on_done()


# ══════════════════════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ══════════════════════════════════════════════════════════════════════════════
def run_cmd(cmd, cwd=None, on_line=None, on_done=None):
    def _go():
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, cwd=cwd)
            for line in proc.stdout:
                if on_line: root.after(0, lambda l=line: on_line(l))
            proc.wait()
            if on_done: root.after(0, lambda: on_done(proc.returncode))
        except FileNotFoundError as e:
            if on_line: root.after(0, lambda: on_line(f"ERROR: {e}\n"))
            if on_done: root.after(0, lambda: on_done(1))
    threading.Thread(target=_go, daemon=True).start()

def pip_install(pkg, log, on_done):
    log(f">>> pip install {pkg}\n")
    run_cmd(smart_pip_cmd(pkg), on_line=log, on_done=on_done)

def is_installed(mod):
    return subprocess.run([sys.executable, "-c", f"import {mod}"],
                          capture_output=True).returncode == 0

def has_bin(name):
    return shutil.which(name) is not None

def get_duration(path):
    try:
        r = subprocess.run(
            ["ffprobe","-v","error","-show_entries","format=duration",
             "-of","default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True)
        return float(r.stdout.strip())
    except: return None

def pyinstaller_progress(line, counters, update_pct):
    ll = line.lower()
    if "collecting" in ll or "copying" in ll:
        counters["pkgs"] += 1
        update_pct(min(60, counters["pkgs"] * 0.9))
        counters["phase"] = "collect"
    elif "building" in ll or "linking" in ll or "appending" in ll:
        if counters["phase"] != "link": counters["phase"] = "link"
        update_pct(min(90, counters.get("cur", 60) + 2))
    elif "completed" in ll or "app bundle" in ll or "onefile" in ll:
        update_pct(97)
    counters["cur"] = counters.get("cur", 0)


# ══════════════════════════════════════════════════════════════════════════════
# WIDGET HELPERS (terminal style)
# ══════════════════════════════════════════════════════════════════════════════
def t_label(parent, text, color=TERM, size=FONT_SZ, bold=False, bg=BG):
    return tk.Label(parent, text=text, bg=bg, fg=color,
                    font=(FONT, size, "bold" if bold else "normal"))

def t_entry(parent, var, width=46):
    e = tk.Entry(parent, textvariable=var, width=width,
                 bg=BG2, fg=TERM, insertbackground=TERM,
                 relief="flat", font=(FONT, FONT_SZ),
                 highlightthickness=1, highlightbackground=TERM3,
                 highlightcolor=TERM)
    return e

def t_btn(parent, text, cmd, color=TERM):
    return tk.Button(parent, text=text, command=cmd,
                     bg=TERM3, fg=color, font=(FONT, FONT_SZ, "bold"),
                     relief="flat", cursor="hand2", padx=12, pady=6,
                     activebackground=TERM3, activeforeground=TERM,
                     bd=1, highlightthickness=1,
                     highlightbackground=color, highlightcolor=color)

def t_ghost(parent, text, cmd):
    return tk.Button(parent, text=text, command=cmd,
                     bg=BG2, fg=TERM2, font=(FONT, FONT_SZ),
                     relief="flat", cursor="hand2", padx=10, pady=6,
                     activebackground=BG2, activeforeground=TERM,
                     bd=1, highlightthickness=1,
                     highlightbackground=TERM3, highlightcolor=TERM3)

def t_chk(parent, text, var):
    return tk.Checkbutton(parent, text=text, variable=var,
                          bg=BG, fg=TERM2, selectcolor=BG2,
                          activebackground=BG, activeforeground=TERM,
                          font=(FONT, FONT_SZ),
                          highlightthickness=0)

def rf(parent, bg=BG): return tk.Frame(parent, bg=bg)

def t_log(parent, height=10):
    box = scrolledtext.ScrolledText(
        parent, height=height, state="disabled",
        bg=BG3, fg=TERM2, font=(FONT, 8),
        relief="flat", insertbackground=TERM,
        selectbackground=TERM3, selectforeground=TERM)
    def write(t):
        box.configure(state="normal"); box.insert("end", t)
        box.see("end"); box.configure(state="disabled")
    def clear():
        box.configure(state="normal"); box.delete("1.0","end")
        box.configure(state="disabled")
    return box, write, clear

def t_section(parent, text):
    f = rf(parent)
    f.pack(fill="x", padx=20, pady=(14,4))
    tk.Label(f, text=f"┌─ {text} ", bg=BG, fg=TERM3,
             font=(FONT, 8)).pack(side="left")
    tk.Frame(f, bg=TERM3, height=1).pack(side="left", fill="x", expand=True, pady=8)
    return f

def t_input_row(parent, label, var, browse_fn=None, bg=BG):
    r = rf(parent, bg=bg); r.pack(fill="x", padx=20, pady=3)
    tk.Label(r, text=label, bg=bg, fg=TERM2,
             font=(FONT, FONT_SZ), width=18, anchor="w").pack(side="left")
    t_entry(r, var, width=38).pack(side="left", padx=6)
    if browse_fn:
        t_ghost(r, "[BROWSE]", browse_fn).pack(side="left")
    return r

def t_slider_row(parent, label, var, from_, to_, show_var=None):
    r = rf(parent); r.pack(fill="x", padx=20, pady=3)
    tk.Label(r, text=label, bg=BG, fg=TERM2,
             font=(FONT, FONT_SZ), width=18, anchor="w").pack(side="left")
    ttk.Scale(r, from_=from_, to=to_, orient="horizontal",
              variable=var, length=200).pack(side="left")
    sv = show_var or var
    tk.Label(r, textvariable=sv, bg=BG, fg=TERM,
             font=(FONT, FONT_SZ, "bold"), width=5).pack(side="left", padx=8)
    return r


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — MP4 → GIF
# ══════════════════════════════════════════════════════════════════════════════
def build_gif_tab(nb, sb):
    tab = tk.Frame(nb, bg=BG)
    nb.add(tab, text="  MP4→GIF  ")

    tk.Label(tab, text="[ MP4 → GIF CONVERTER ]", bg=BG, fg=TERM,
             font=(FONT, 12, "bold")).pack(pady=(18,2))
    tk.Label(tab, text="requires ffmpeg  ·  auto-installed on launch",
             bg=BG, fg=TERM3, font=SMALL_F).pack(pady=(0,8))

    t_section(tab, "INPUT / OUTPUT")
    inp_var = tk.StringVar(); out_var = tk.StringVar()
    fps_var = tk.IntVar(value=15); w_var = tk.IntVar(value=640)

    def browse_in():
        p = filedialog.askopenfilename(title="Select video",
            filetypes=[("Video","*.mp4 *.mov *.avi *.mkv"),("All","*.*")])
        if p: inp_var.set(p); out_var.set(os.path.splitext(p)[0]+".gif")

    def browse_out():
        p = filedialog.asksaveasfilename(title="Save GIF",
            defaultextension=".gif", filetypes=[("GIF","*.gif")])
        if p: out_var.set(p)

    t_input_row(tab, "INPUT  MP4 :", inp_var, browse_in)
    t_input_row(tab, "OUTPUT GIF :", out_var, browse_out)

    t_section(tab, "SETTINGS")
    t_slider_row(tab, "FRAMERATE (FPS) :", fps_var, 5, 30)
    t_slider_row(tab, "OUTPUT WIDTH px :", w_var,   200, 1280)

    log_box, log, log_clear = t_log(tab, height=8)

    def convert():
        inp = inp_var.get().strip(); out = out_var.get().strip()
        if not inp or not os.path.exists(inp):
            log_clear(); log("ERROR: select a valid input file.\n"); log_box.pack(padx=20,pady=4,fill="x"); return
        if not out:
            log_clear(); log("ERROR: set an output path.\n"); log_box.pack(padx=20,pady=4,fill="x"); return
        if not has_bin("ffmpeg"):
            log_clear(); log("ERROR: ffmpeg not found. Re-run and use INSTALL on startup screen.\n")
            log_box.pack(padx=20,pady=4,fill="x"); return

        conv_btn.config(state="disabled", text="[ CONVERTING… ]")
        log_clear(); log_box.pack(padx=20,pady=4,fill="x")
        log(f">>> SOURCE  : {os.path.basename(inp)}\n")
        log(f">>> FPS     : {fps_var.get()}\n>>> WIDTH   : {w_var.get()}px\n\n")
        sb.start("MP4→GIF")
        duration = get_duration(inp)
        tmp_pal  = out + ".pal.png"
        time_re  = re.compile(r"time=(\d+):(\d+):([\d.]+)")

        pass1 = ["ffmpeg","-y","-i",inp,
                 "-vf",f"fps={fps_var.get()},scale={w_var.get()}:-1:flags=lanczos,palettegen",
                 tmp_pal]
        pass2 = ["ffmpeg","-y","-i",inp,"-i",tmp_pal,
                 "-lavfi",f"fps={fps_var.get()},scale={w_var.get()}:-1:flags=lanczos[x];[x][1:v]paletteuse",
                 out]

        def parse(line, pn):
            m = time_re.search(line)
            if m and duration:
                s = int(m.group(1))*3600+int(m.group(2))*60+float(m.group(3))
                raw = s/duration*100
                sb.set(raw*0.45 if pn==1 else 45+raw*0.53, "MP4→GIF")

        def run_pass(cmd_list, pn, nxt):
            def _go():
                try:
                    proc = subprocess.Popen(cmd_list, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True)
                    for line in proc.stdout:
                        root.after(0, lambda l=line: log(l))
                        root.after(0, lambda l=line: parse(l, pn))
                    proc.wait()
                    root.after(0, lambda: nxt(proc.returncode))
                except Exception as e:
                    root.after(0, lambda: finish(1, str(e)))
            threading.Thread(target=_go, daemon=True).start()

        def after_p1(rc):
            if rc != 0: finish(rc, "Pass 1 failed"); return
            log("\n>>> PASS 2/2 — encoding GIF…\n\n")
            run_pass(pass2, 2, lambda rc2: finish(rc2))

        def finish(rc, err=""):
            conv_btn.config(state="normal", text="[ CONVERT ]")
            try: os.remove(tmp_pal)
            except: pass
            if rc == 0:
                mb = os.path.getsize(out)/1048576
                log(f"\n>>> DONE  {out}  ({mb:.1f} MB)\n")
                sb.finish("MP4→GIF", True)
            else:
                log(f"\n>>> FAILED  {err}\n")
                sb.finish("MP4→GIF", False)

        log(">>> PASS 1/2 — building palette…\n\n")
        run_pass(pass1, 1, after_p1)

    conv_btn = t_btn(tab, "[ CONVERT ]", convert)
    conv_btn.pack(pady=(10,4))
    log(">>> READY. Select input MP4 and press CONVERT.\n")
    log_box.pack(padx=20, pady=(4,16), fill="x")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Python → Web
# ══════════════════════════════════════════════════════════════════════════════
def build_web_tab(nb, sb):
    tab = tk.Frame(nb, bg=BG)
    nb.add(tab, text="  PY→WEB  ")

    tk.Label(tab, text="[ PYTHON → WEB BUILD ]", bg=BG, fg=TERM,
             font=(FONT, 12, "bold")).pack(pady=(18,2))
    tk.Label(tab, text="wraps pygame game into browser HTML via pygbag  ·  uploads to itch.io",
             bg=BG, fg=TERM3, font=SMALL_F).pack(pady=(0,8))

    t_section(tab, "GAME FILES")
    folder_var = tk.StringVar(); main_var = tk.StringVar()

    def browse_folder():
        p = filedialog.askdirectory(title="Select game folder")
        if p:
            folder_var.set(p)
            for f in os.listdir(p):
                if f.endswith(".py"): main_var.set(f); break

    def browse_main():
        init = folder_var.get() or os.path.expanduser("~")
        p = filedialog.askopenfilename(title="Select main .py",
            initialdir=init, filetypes=[("Python","*.py")])
        if p: folder_var.set(os.path.dirname(p)); main_var.set(os.path.basename(p))

    t_input_row(tab, "GAME FOLDER  :", folder_var, browse_folder)
    t_input_row(tab, "MAIN .PY     :", main_var,   browse_main)
    tk.Label(tab, text="  ↳ filename only e.g. main.py  (must live inside the game folder)",
             bg=BG, fg=TERM3, font=SMALL_F).pack(anchor="w", padx=20)

    log_box, log, log_clear = t_log(tab, height=9)
    pct_re = re.compile(r"\[\s*(\d+)%\s*\]")

    def install():
        btn_inst.config(state="disabled", text="[ INSTALLING… ]")
        log_clear(); log_box.pack(padx=20,pady=4,fill="x")
        sb.start("INSTALL pygbag")
        def done(rc):
            btn_inst.config(state="normal", text="[ INSTALL/UPDATE PYGBAG ]")
            sb.finish("INSTALL pygbag", rc==0)
            log("\n>>> pygbag ready.\n" if rc==0 else "\n>>> INSTALL FAILED.\n")
        pip_install("pygbag", log, done)

    def build():
        folder=folder_var.get().strip(); main=main_var.get().strip()
        if not folder or not os.path.isdir(folder):
            log_clear(); log("ERROR: select a valid game folder.\n")
            log_box.pack(padx=20,pady=4,fill="x"); return
        if not main:
            log_clear(); log("ERROR: specify main .py filename.\n")
            log_box.pack(padx=20,pady=4,fill="x"); return
        mp = os.path.join(folder, main)
        if not os.path.exists(mp):
            log_clear(); log(f"ERROR: not found: {mp}\n")
            log_box.pack(padx=20,pady=4,fill="x"); return
        if not is_installed("pygbag"):
            log_clear(); log("ERROR: pygbag not installed. Click INSTALL.\n")
            log_box.pack(padx=20,pady=4,fill="x"); return

        btn_build.config(state="disabled", text="[ BUILDING… ]")
        log_clear(); log_box.pack(padx=20,pady=4,fill="x")
        log(f">>> BUILDING  {main}\n>>> OUTPUT  → {folder}/build/web/\n\n")
        sb.start("PY→WEB")

        def on_line(line):
            log(line)
            m = pct_re.search(line)
            if m: sb.set(float(m.group(1)), "PY→WEB")

        def done(rc):
            btn_build.config(state="normal", text="[ BUILD WEB ]")
            web = os.path.join(folder,"build","web")
            if os.path.isdir(web):
                log(f"\n>>> DONE  zip and upload to itch.io:\n    {web}\n")
                sb.finish("PY→WEB", True)
            else:
                log("\n>>> BUILD FAILED — check log.\n")
                sb.finish("PY→WEB", False)

        run_cmd([sys.executable,"-m","pygbag","--build",mp],
                cwd=folder, on_line=on_line, on_done=done)

    bf = rf(tab); bf.pack(pady=(12,4))
    btn_inst  = t_ghost(bf, "[ INSTALL/UPDATE PYGBAG ]", install); btn_inst.pack(side="left",padx=6)
    btn_build = t_btn(bf,   "[ BUILD WEB ]",             build);   btn_build.pack(side="left",padx=6)

    log(">>> READY. Select game folder and main .py, then BUILD WEB.\n")
    log_box.pack(padx=20, pady=(4,16), fill="x")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Python → EXE
# ══════════════════════════════════════════════════════════════════════════════
def build_exe_tab(nb, sb):
    tab = tk.Frame(nb, bg=BG)
    nb.add(tab, text="  PY→EXE  ")

    tk.Label(tab, text="[ PYTHON → EXE BUILDER ]", bg=BG, fg=TERM,
             font=(FONT, 12, "bold")).pack(pady=(18,2))
    if OS_NAME == "Linux":
        note = f"running on Linux  ·  builds Linux binary  ·  run on Windows for .exe"
    elif OS_NAME == "Windows":
        note = "running on Windows  ·  builds .exe"
    else:
        note = f"running on {OS_NAME}"
    tk.Label(tab, text=note, bg=BG, fg=TERM3, font=SMALL_F).pack(pady=(0,8))

    t_section(tab, "TARGET")
    script_var = tk.StringVar(); name_var = tk.StringVar(); icon_var = tk.StringVar()
    onefile = tk.BooleanVar(value=True); noconsole = tk.BooleanVar(value=False)

    def browse_sc():
        p = filedialog.askopenfilename(title="Select main .py",
            filetypes=[("Python","*.py")])
        if p: script_var.set(p); name_var.set(os.path.splitext(os.path.basename(p))[0])

    def browse_ic():
        p = filedialog.askopenfilename(title="Select icon",
            filetypes=[("Icons","*.ico *.png"),("All","*.*")])
        if p: icon_var.set(p)

    t_input_row(tab, "MAIN .PY       :", script_var, browse_sc)
    t_input_row(tab, "APP NAME       :", name_var,   None)
    t_input_row(tab, "ICON (optional):", icon_var,   browse_ic)

    t_section(tab, "OPTIONS")
    of = rf(tab); of.pack(anchor="w", padx=20, pady=4)
    t_chk(of, "  --onefile       ", onefile).pack(side="left")
    t_chk(of, "  --noconsole (GUI/game)", noconsole).pack(side="left")

    log_box, log, log_clear = t_log(tab, height=8)

    def install():
        btn_inst.config(state="disabled", text="[ INSTALLING… ]")
        log_clear(); log_box.pack(padx=20,pady=4,fill="x")
        sb.start("INSTALL PyInstaller")
        def done(rc):
            btn_inst.config(state="normal", text="[ INSTALL/UPDATE PYINSTALLER ]")
            sb.finish("INSTALL PyInstaller", rc==0)
            log("\n>>> PyInstaller ready.\n" if rc==0 else "\n>>> INSTALL FAILED.\n")
        pip_install("pyinstaller", log, done)

    def build():
        script = script_var.get().strip()
        if not script or not os.path.exists(script):
            log_clear(); log("ERROR: select a valid .py file.\n")
            log_box.pack(padx=20,pady=4,fill="x"); return
        if not is_installed("PyInstaller"):
            log_clear(); log("ERROR: PyInstaller not installed. Click INSTALL.\n")
            log_box.pack(padx=20,pady=4,fill="x"); return

        cwd = os.path.dirname(script) or "."
        cmd = [sys.executable,"-m","PyInstaller"]
        if onefile.get():    cmd.append("--onefile")
        if noconsole.get():  cmd.append("--noconsole")
        n = name_var.get().strip()
        if n: cmd+=["--name",n]
        ic = icon_var.get().strip()
        if ic and os.path.exists(ic): cmd+=["--icon",ic]
        cmd.append(script)

        btn_build.config(state="disabled", text="[ BUILDING… ]")
        log_clear(); log_box.pack(padx=20,pady=4,fill="x")
        log(f">>> BUILDING  {os.path.basename(script)}\n>>> OUTPUT  → {cwd}/dist/\n\n")
        sb.start("PY→EXE")
        counters = {"pkgs":0,"phase":"collect","cur":0}

        def on_line(line):
            log(line)
            pyinstaller_progress(line, counters, lambda p: sb.set(p,"PY→EXE"))

        def done(rc):
            btn_build.config(state="normal", text="[ BUILD EXE ]")
            dist = os.path.join(cwd,"dist")
            if rc==0 and os.path.isdir(dist):
                log(f"\n>>> DONE  {dist}\n>>> NOTE: built for {OS_NAME} only.\n")
                sb.finish("PY→EXE", True)
            else:
                log("\n>>> BUILD FAILED — check log.\n")
                sb.finish("PY→EXE", False)

        run_cmd(cmd, cwd=cwd, on_line=on_line, on_done=done)

    bf = rf(tab); bf.pack(pady=(12,4))
    btn_inst  = t_ghost(bf,"[ INSTALL/UPDATE PYINSTALLER ]",install); btn_inst.pack(side="left",padx=6)
    btn_build = t_btn(bf,  "[ BUILD EXE ]",                  build);  btn_build.pack(side="left",padx=6)

    log(">>> READY. Select main .py and click BUILD EXE.\n")
    log_box.pack(padx=20, pady=(4,16), fill="x")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Mac .app
# ══════════════════════════════════════════════════════════════════════════════
def build_mac_tab(nb, sb):
    tab = tk.Frame(nb, bg=BG)
    nb.add(tab, text="  MAC.APP  ")

    tk.Label(tab, text="[ MAC .APP BUILDER ]", bg=BG, fg=TERM,
             font=(FONT, 12, "bold")).pack(pady=(18,2))
    if OS_NAME == "Darwin":
        note = "✓ running on macOS  ·  BUILD DIRECT available"
    else:
        note = f"running on {OS_NAME}  ·  use User Script or GitHub Actions tabs"
    tk.Label(tab, text=note, bg=BG, fg=TERM3, font=SMALL_F).pack(pady=(0,6))

    # inner sub-tabs
    s2 = ttk.Style()
    s2.configure("Mac.TNotebook",     background=BG2, borderwidth=0)
    s2.configure("Mac.TNotebook.Tab", background=BG3, foreground=TERM3,
                 font=(FONT,9), padding=(10,5))
    s2.map("Mac.TNotebook.Tab",
           background=[("selected",BG2)],
           foreground=[("selected",TERM)])

    inner = ttk.Notebook(tab, style="Mac.TNotebook")
    inner.pack(fill="both", expand=True, padx=12, pady=(6,12))

    # ── A: Build Direct ───────────────────────────────────────────────────────
    pA = tk.Frame(inner, bg=BG)
    inner.add(pA, text="  BUILD DIRECT  ")

    t_section(pA, "TARGET")
    scA=tk.StringVar(); nmA=tk.StringVar(); icA=tk.StringVar()
    ncA=tk.BooleanVar(value=True)

    def browse_scA():
        p=filedialog.askopenfilename(title="Select main .py",filetypes=[("Python","*.py")])
        if p: scA.set(p); nmA.set(os.path.splitext(os.path.basename(p))[0])
    def browse_icA():
        p=filedialog.askopenfilename(title="Select icon",
            filetypes=[("Icons","*.icns *.png"),("All","*.*")])
        if p: icA.set(p)

    t_input_row(pA,"MAIN .PY        :",scA,browse_scA)
    t_input_row(pA,"APP NAME        :",nmA,None)
    t_input_row(pA,"ICON (optional) :",icA,browse_icA)
    of=rf(pA); of.pack(anchor="w",padx=20,pady=4)
    t_chk(of,"  --windowed (no console)",ncA).pack(side="left")

    log_boxA,logA,log_clearA = t_log(pA, height=7)

    def installA():
        btn_iA.config(state="disabled",text="[ INSTALLING… ]")
        log_clearA(); log_boxA.pack(padx=20,pady=4,fill="x")
        sb.start("INSTALL PyInstaller")
        def done(rc):
            btn_iA.config(state="normal",text="[ INSTALL PYINSTALLER ]")
            sb.finish("INSTALL PyInstaller",rc==0)
            logA("\n>>> ready.\n" if rc==0 else "\n>>> FAILED.\n")
        pip_install("pyinstaller",logA,done)

    def buildA():
        if OS_NAME != "Darwin":
            log_clearA(); logA("ERROR: must run on macOS to build .app\n")
            log_boxA.pack(padx=20,pady=4,fill="x"); return
        script=scA.get().strip()
        if not script or not os.path.exists(script):
            log_clearA(); logA("ERROR: select a valid .py file.\n")
            log_boxA.pack(padx=20,pady=4,fill="x"); return
        if not is_installed("PyInstaller"):
            log_clearA(); logA("ERROR: install PyInstaller first.\n")
            log_boxA.pack(padx=20,pady=4,fill="x"); return

        cwd=os.path.dirname(script) or "."
        name=nmA.get().strip() or os.path.splitext(os.path.basename(script))[0]
        cmd=[sys.executable,"-m","PyInstaller","--onedir"]
        if ncA.get(): cmd.append("--windowed")
        cmd+=["--name",name]
        ic=icA.get().strip()
        if ic and os.path.exists(ic): cmd+=["--icon",ic]
        cmd.append(script)

        btn_bA.config(state="disabled",text="[ BUILDING… ]")
        log_clearA(); log_boxA.pack(padx=20,pady=4,fill="x")
        logA(f">>> BUILDING {name}.app\n>>> OUTPUT → {cwd}/dist/\n\n")
        sb.start("PY→.app")
        counters={"pkgs":0,"phase":"collect","cur":0}

        def on_line(line):
            logA(line)
            pyinstaller_progress(line,counters,lambda p: sb.set(p,"PY→.app"))

        def done(rc):
            btn_bA.config(state="normal",text="[ BUILD .APP ]")
            dist=os.path.join(cwd,"dist"); app=os.path.join(dist,f"{name}.app")
            if rc==0 and os.path.isdir(dist):
                logA(f"\n>>> DONE  {app}\n>>> Right-click → Open on first launch (Gatekeeper)\n")
                sb.finish("PY→.app",True)
                if OS_NAME=="Darwin": subprocess.run(["open","-R",app if os.path.isdir(app) else dist])
            else:
                logA("\n>>> FAILED — check log.\n"); sb.finish("PY→.app",False)

        run_cmd(cmd,cwd=cwd,on_line=on_line,on_done=done)

    bfA=rf(pA); bfA.pack(pady=(8,4))
    btn_iA=t_ghost(bfA,"[ INSTALL PYINSTALLER ]",installA); btn_iA.pack(side="left",padx=6)
    btn_bA=t_btn(bfA,  "[ BUILD .APP ]",          buildA);  btn_bA.pack(side="left",padx=6)
    logA(">>> BUILD DIRECT only works on macOS.\n")
    log_boxA.pack(padx=20,pady=(4,12),fill="x")

    # ── B: User Script ────────────────────────────────────────────────────────
    pB = tk.Frame(inner, bg=BG)
    inner.add(pB, text="  USER SCRIPT  ")

    tk.Label(pB,text="Ship mac_build_user.py to any Mac user.\nThey run it — no terminal needed. Builds .app with GUI + progress.",
             bg=BG,fg=TERM2,font=(FONT,9),justify="left").pack(padx=20,pady=(14,6),anchor="w")

    steps=[
        "1. Click SAVE below → save mac_build_user.py anywhere",
        "2. Send that file + your game folder to your Mac user",
        "3. They run:  python3 mac_build_user.py",
        "4. They browse to your .py, click Build, .app appears in Finder",
    ]
    for s in steps:
        tk.Label(pB,text=f"  {s}",bg=BG,fg=TERM3,font=(FONT,8)).pack(anchor="w",padx=20,pady=1)

    sv_B=tk.StringVar(value="")
    tk.Label(pB,textvariable=sv_B,bg=BG,fg=TERM,font=(FONT,9)).pack(pady=(10,2))

    MAC_SCRIPT=r'''#!/usr/bin/env python3
"""mac_build_user.py — Run on a Mac to build a .app from your Python game."""
import tkinter as tk
from tkinter import filedialog, scrolledtext
import subprocess, threading, os, sys, platform, shutil
if platform.system()!="Darwin":
    import tkinter.messagebox as mb; r=tk.Tk(); r.withdraw()
    mb.showerror("Wrong OS","Must run on macOS."); sys.exit(1)
BG,BG2,BG3="#0a0a0a","#111111","#0d0d0d"
TERM,TERM2,TERM3="#00ff41","#00cc33","#005514"
RED,AMBER,WHITE="#ff2222","#ffb000","#cccccc"
FONT="Courier New"
root=tk.Tk(); root.title("mac_build_user.py"); root.configure(bg=BG); root.resizable(False,False)
def lbl(p,t,c=TERM,s=10,b=False):
    return tk.Label(p,text=t,bg=p.cget("bg") if hasattr(p,"cget") else BG,fg=c,font=(FONT,s,"bold" if b else "normal"))
def ent(p,v,w=40):
    e=tk.Entry(p,textvariable=v,width=w,bg=BG2,fg=TERM,insertbackground=TERM,relief="flat",font=(FONT,10))
    e.configure(highlightthickness=1,highlightbackground=TERM3,highlightcolor=TERM); return e
def rf(p): return tk.Frame(p,bg=BG)
def run_cmd(cmd,cwd=None,on_line=None,on_done=None):
    def _go():
        try:
            proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,cwd=cwd)
            for line in proc.stdout:
                if on_line: root.after(0,lambda l=line:on_line(l))
            proc.wait()
            if on_done: root.after(0,lambda:on_done(proc.returncode))
        except Exception as e:
            if on_line: root.after(0,lambda:on_line(f"ERROR: {e}\n"))
            if on_done: root.after(0,lambda:on_done(1))
    threading.Thread(target=_go,daemon=True).start()
def is_inst(m): return subprocess.run([sys.executable,"-c",f"import {m}"],capture_output=True).returncode==0
tk.Label(root,text="[ MAC .APP BUILDER ]",bg=BG,fg=TERM,font=(FONT,13,"bold")).pack(pady=(20,4))
tk.Label(root,text=f"macOS {platform.mac_ver()[0]}  python {platform.python_version()}",bg=BG,fg=TERM3,font=(FONT,8)).pack(pady=(0,12))
body=rf(root); body.pack(padx=24,fill="x")
sc=tk.StringVar(); nm=tk.StringVar(); ic=tk.StringVar(); nc=tk.BooleanVar(value=True)
def bsc():
    p=filedialog.askopenfilename(title="Select main .py",filetypes=[("Python","*.py")])
    if p: sc.set(p); nm.set(os.path.splitext(os.path.basename(p))[0])
def bic():
    p=filedialog.askopenfilename(title="Select icon",filetypes=[("Icons","*.icns *.png"),("All","*.*")])
    if p: ic.set(p)
for (lt,v,bc) in [("MAIN .PY  :",sc,bsc),("APP NAME  :",nm,None),("ICON (opt):",ic,bic)]:
    r=rf(body); r.pack(fill="x",pady=3)
    tk.Label(r,text=lt,bg=BG,fg=TERM2,font=(FONT,10),width=12,anchor="w").pack(side="left")
    ent(r,v).pack(side="left",padx=6)
    if bc: tk.Button(r,text="[BROWSE]",command=bc,bg=BG2,fg=TERM2,font=(FONT,10),relief="flat",cursor="hand2",padx=8,pady=4).pack(side="left")
of=rf(body); of.pack(anchor="w",pady=6)
tk.Checkbutton(of,text="--windowed (no console)",variable=nc,bg=BG,fg=TERM2,selectcolor=BG2,activebackground=BG,font=(FONT,10)).pack(side="left")
st=tk.StringVar(value=">>> READY.")
tk.Label(root,textvariable=st,bg=BG,fg=TERM3,font=(FONT,8)).pack(pady=(6,0))
log_box=scrolledtext.ScrolledText(root,height=11,state="disabled",bg=BG3,fg=TERM2,font=(FONT,8),relief="flat")
def log(t): log_box.configure(state="normal"); log_box.insert("end",t); log_box.see("end"); log_box.configure(state="disabled")
def log_clear(): log_box.configure(state="normal"); log_box.delete("1.0","end"); log_box.configure(state="disabled")
def install():
    bi.config(state="disabled",text="[ INSTALLING… ]"); log_clear(); log_box.pack(padx=24,pady=(4,8),fill="x")
    def done(rc): bi.config(state="normal",text="[ INSTALL PYINSTALLER ]"); log("\n>>> ready.\n" if rc==0 else "\n>>> FAILED.\n")
    log(">>> installing pyinstaller…\n"); run_cmd([sys.executable,"-m","pip","install","--upgrade","pyinstaller"]+( ["--break-system-packages"] if __import__("platform").system()=="Linux" else []),on_line=log,on_done=done)
def build():
    script=sc.get().strip()
    if not script or not os.path.exists(script): st.set("ERROR: select a .py file"); return
    if not is_inst("PyInstaller"): log_clear(); log("ERROR: install PyInstaller first.\n"); log_box.pack(padx=24,pady=(4,8),fill="x"); return
    cwd=os.path.dirname(script) or "."; name=nm.get().strip() or os.path.splitext(os.path.basename(script))[0]
    cmd=[sys.executable,"-m","PyInstaller","--onedir"]
    if nc.get(): cmd.append("--windowed")
    cmd+=["--name",name]
    icv=ic.get().strip()
    if icv and os.path.exists(icv): cmd+=["--icon",icv]
    cmd.append(script)
    bb.config(state="disabled",text="[ BUILDING… ]"); log_clear(); log_box.pack(padx=24,pady=(4,8),fill="x")
    log(f">>> building {name}.app\n>>> output → {cwd}/dist/\n\n"); st.set(">>> BUILDING…")
    cnt={"p":0,"ph":"c","cur":0}
    def ol(line):
        log(line); ll=line.lower()
        if "collecting" in ll or "copying" in ll: cnt["p"]+=1
        elif "building" in ll or "linking" in ll: cnt["cur"]=cnt.get("cur",0)+2
    def done(rc):
        bb.config(state="normal",text="[ BUILD .APP ]")
        dist=os.path.join(cwd,"dist"); app=os.path.join(dist,f"{name}.app")
        if rc==0 and os.path.isdir(dist):
            st.set(">>> DONE"); log(f"\n>>> DONE  {app}\n>>> Right-click → Open on first launch.\n")
            subprocess.run(["open","-R",app if os.path.isdir(app) else dist])
        else: st.set(">>> FAILED"); log("\n>>> FAILED.\n")
    run_cmd(cmd,cwd=cwd,on_line=ol,on_done=done)
bf=rf(root); bf.pack(pady=(10,6))
bi=tk.Button(bf,text="[ INSTALL PYINSTALLER ]",command=install,bg=BG2,fg=TERM2,font=(FONT,10),relief="flat",cursor="hand2",padx=10,pady=6)
bi.pack(side="left",padx=6)
bb=tk.Button(bf,text="[ BUILD .APP ]",command=build,bg=TERM3,fg=TERM,font=(FONT,10,"bold"),relief="flat",cursor="hand2",padx=12,pady=6)
bb.pack(side="left",padx=6)
log(">>> select main .py and click BUILD .APP\n>>> install PyInstaller first on a fresh machine\n")
log_box.pack(padx=24,pady=(4,20),fill="x")
root.mainloop()
'''

    def save_B():
        p=filedialog.asksaveasfilename(title="Save mac_build_user.py",
            initialfile="mac_build_user.py",defaultextension=".py",
            filetypes=[("Python","*.py")])
        if p:
            with open(p,"w") as f: f.write(MAC_SCRIPT)
            sv_B.set(f">>> SAVED  {p}")

    t_btn(pB,"[ SAVE mac_build_user.py ]",save_B).pack(pady=(14,16))

    # ── C: GitHub Actions ─────────────────────────────────────────────────────
    pC = tk.Frame(inner, bg=BG)
    inner.add(pC, text="  GITHUB ACTIONS  ")

    tk.Label(pC,text="Auto-build .app on GitHub's free Mac runners on every push.",
             bg=BG,fg=TERM2,font=(FONT,9)).pack(padx=20,pady=(14,4),anchor="w")

    GH="""name: Build macOS .app
on:
  push:
    branches: [ main, master ]
  workflow_dispatch:
env:
  GAME_MAIN:  "main.py"    # ← your entry-point
  APP_NAME:   "MyGame"     # ← .app name
  PYTHON_VER: "3.11"
jobs:
  build-mac:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VER }}
      - run: |
          pip install --upgrade pip pyinstaller
          # pip install pygame
          # pip install -r requirements.txt
      - run: |
          pyinstaller --onedir --windowed \\
            --name "${{ env.APP_NAME }}" \\
            "${{ env.GAME_MAIN }}"
      - run: cd dist && zip -r "${{ env.APP_NAME }}-mac.zip" "${{ env.APP_NAME }}.app"
      - uses: actions/upload-artifact@v4
        with:
          name: ${{ env.APP_NAME }}-mac
          path: dist/${{ env.APP_NAME }}-mac.zip
          retention-days: 30
"""
    yb=scrolledtext.ScrolledText(pC,height=14,bg=BG3,fg=TERM2,font=(FONT,8),relief="flat")
    yb.insert("1.0",GH); yb.configure(state="disabled")
    yb.pack(padx=20,pady=(4,4),fill="x")

    sv_C=tk.StringVar(value="")
    tk.Label(pC,textvariable=sv_C,bg=BG,fg=TERM,font=(FONT,9)).pack(pady=(4,2))

    def save_C():
        p=filedialog.asksaveasfilename(title="Save YAML",initialfile="build-mac-app.yml",
            defaultextension=".yml",filetypes=[("YAML","*.yml")])
        if p:
            with open(p,"w") as f: f.write(GH)
            sv_C.set(f">>> SAVED  {p}")

    t_btn(pC,"[ SAVE build-mac-app.yml ]",save_C).pack(pady=(6,14))


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — INFO
# ══════════════════════════════════════════════════════════════════════════════
def build_info_tab(nb):
    tab = tk.Frame(nb, bg=BG)
    nb.add(tab, text="  INFO  ")

    canvas = tk.Canvas(tab, bg=BG, highlightthickness=0)
    scroll = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    inner = tk.Frame(canvas, bg=BG)
    canvas.create_window((0,0), window=inner, anchor="nw")
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    def section(text):
        tk.Frame(inner,bg=TERM3,height=1).pack(fill="x",padx=20,pady=(16,4))
        tk.Label(inner,text=f"  {text}",bg=BG,fg=TERM,font=(FONT,10,"bold")).pack(anchor="w",padx=20)

    def row(label, value, vc=TERM2):
        f=rf(inner); f.pack(fill="x",padx=30,pady=2)
        tk.Label(f,text=f"{label:<22}",bg=BG,fg=TERM3,font=(FONT,9)).pack(side="left")
        tk.Label(f,text=value,bg=BG,fg=vc,font=(FONT,9)).pack(side="left")

    def para(text):
        tk.Label(inner,text=text,bg=BG,fg=TERM2,font=(FONT,9),
                 justify="left",anchor="w",wraplength=560).pack(anchor="w",padx=30,pady=2)

    tk.Label(inner,text="V01D CONVERT PRIM3 v1.0",bg=BG,fg=TERM,
             font=(FONT,15,"bold")).pack(pady=(24,2))
    tk.Label(inner,text="MP4·GIF·WEB·EXE·APP  ·  terminal conversion suite",
             bg=BG,fg=TERM3,font=(FONT,9)).pack(pady=(0,8))

    # ── system ────────────────────────────────────────────────────────────────
    section("SYSTEM")
    row("OS",             f"{platform.system()} {platform.release()}")
    row("Python",         platform.python_version())
    row("Architecture",   platform.machine())
    row("Script location",sys.argv[0])

    # ── dependency status ─────────────────────────────────────────────────────
    section("DEPENDENCY STATUS")
    tk.Label(inner,text="  checking…",bg=BG,fg=AMBER,font=(FONT,9)).pack(anchor="w",padx=30)
    dep_frame = tk.Frame(inner,bg=BG); dep_frame.pack(fill="x",padx=30,pady=4)

    def check_deps_info():
        deps = [
            ("ffmpeg",       "binary", "ffmpeg"),
            ("ffprobe",      "binary", "ffprobe"),
            ("pygbag",       "pip",    "pygbag"),
            ("PyInstaller",  "pip",    "PyInstaller"),
        ]
        for child in dep_frame.winfo_children(): child.destroy()
        for (name,kind,check_id) in deps:
            if kind == "binary":
                ok = shutil.which(check_id) is not None
            else:
                ok = subprocess.run([sys.executable,"-c",f"import {check_id}"],
                                    capture_output=True).returncode==0
            color = TERM if ok else RED
            status = "FOUND" if ok else "NOT FOUND"
            f=rf(dep_frame); f.pack(fill="x",pady=1)
            tk.Label(f,text=f"{'  '+name:<18}",bg=BG,fg=TERM3,font=(FONT,9)).pack(side="left")
            tk.Label(f,text=status,bg=BG,fg=color,font=(FONT,9,"bold")).pack(side="left")

    t_btn(inner,"[ REFRESH DEPENDENCY STATUS ]",
          lambda: threading.Thread(target=check_deps_info,daemon=True).start(),
          color=TERM).pack(anchor="w",padx=30,pady=6)
    threading.Thread(target=check_deps_info, daemon=True).start()

    # ── how to use ────────────────────────────────────────────────────────────
    section("HOW TO USE")
    guides = [
        ("MP4 → GIF",
         "Select an MP4 video, set FPS and width, click CONVERT.\n"
         "Lower FPS = smaller file. 15fps is a good default for showcase GIFs."),
        ("Python → Web",
         "Select your game folder and main .py, click BUILD WEB.\n"
         "Zip the output build/web/ folder and upload to itch.io as an HTML build."),
        ("Python → EXE",
         "Select your main .py, set a name and optional icon, click BUILD EXE.\n"
         "Output goes to dist/. Builds for the current OS only."),
        ("Mac .app",
         "Three options: Build Direct (on a Mac), User Script (send to a Mac user),\n"
         "or GitHub Actions (auto-builds on every push — free)."),
    ]
    for (title,desc) in guides:
        tk.Label(inner,text=f"  ▸ {title}",bg=BG,fg=TERM,font=(FONT,9,"bold")).pack(anchor="w",padx=20,pady=(8,1))
        para(desc)

    # ── install commands ──────────────────────────────────────────────────────
    section("MANUAL INSTALL COMMANDS")
    cmds = [
        ("ffmpeg (Linux)",   "sudo apt install ffmpeg"),
        ("ffmpeg (Mac)",     "brew install ffmpeg"),
        ("ffmpeg (Windows)", "choco install ffmpeg"),
        ("pygbag",           "pip install pygbag"),
        ("PyInstaller",      "pip install pyinstaller"),
    ]
    for (label,cmd) in cmds:
        f=rf(inner); f.pack(fill="x",padx=30,pady=1)
        tk.Label(f,text=f"{label:<22}",bg=BG,fg=TERM3,font=(FONT,9)).pack(side="left")
        tk.Label(f,text=cmd,bg=BG,fg=TERM2,font=(FONT,9)).pack(side="left")

    section("NOTES")
    notes = [
        "• PyInstaller builds for the OS it runs on. Linux→Linux binary, Windows→.exe, Mac→.app.",
        "• For a Mac .app from Linux/Windows, use GitHub Actions or the User Script tab.",
        "• pygbag requires your game to use pygame and async-compatible code.",
        "• GIF quality uses 2-pass palettegen+paletteuse for best colour fidelity.",
        "• All builds output to a dist/ folder next to your source file.",
    ]
    for n in notes:
        tk.Label(inner,text=n,bg=BG,fg=TERM3,font=(FONT,8)).pack(anchor="w",padx=30,pady=1)

    tk.Frame(inner,bg=BG,height=20).pack()   # bottom padding


# ══════════════════════════════════════════════════════════════════════════════
# ROOT WINDOW + MAIN NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
root = tk.Tk()
root.title("V01D CONVERT PRIM3 v1.0")
root.configure(bg=BG)
root.resizable(True, True)
root.minsize(660, 540)

# title bar strip
title_bar = tk.Frame(root, bg=BG3, height=36)
title_bar.pack(fill="x", side="top")
tk.Label(title_bar, text="▓▓ V01D CONVERT PRIM3 v1.0 ▓▓",
         bg=BG3, fg=TERM, font=(FONT, 11, "bold")).pack(side="left", padx=14, pady=6)
tk.Label(title_bar, text=f"[ {OS_NAME} / Python {platform.python_version()} ]",
         bg=BG3, fg=TERM3, font=(FONT, 8)).pack(side="right", padx=14)

# ttk styles
s = ttk.Style()
s.theme_use("clam")
s.configure("TNotebook",     background=BG,  borderwidth=0)
s.configure("TNotebook.Tab", background=BG3, foreground=TERM3,
            font=(FONT, 9, "bold"), padding=(14,7))
s.map("TNotebook.Tab",
      background=[("selected", BG2)],
      foreground=[("selected", TERM)])
s.configure("TScale",       background=BG,  troughcolor=TERM3, sliderlength=14)
s.configure("Vertical.TScrollbar", background=BG2, troughcolor=BG3,
            arrowcolor=TERM3, bordercolor=BG3)

# status bar at the very bottom (before notebook so it anchors bottom)
sb = StatusBar(root)

# main notebook
nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True, padx=0, pady=0)

# ── build all tabs then launch startup checker ────────────────────────────────
def launch_main():
    build_gif_tab(nb, sb)
    build_web_tab(nb, sb)
    build_exe_tab(nb, sb)
    build_mac_tab(nb, sb)
    build_info_tab(nb)
    nb.pack(fill="both", expand=True)
    sb.idle()

StartupChecker(root, on_done=launch_main)

root.mainloop()
