import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import sys
import subprocess
import numpy as np

# ── auto-install core deps ────────────────────────────────────────────────────
def _pip(*args):
    subprocess.check_call([sys.executable, "-m", "pip", "install", *args])

def _ensure(mod, pkg):
    try:
        __import__(mod)
    except ImportError:
        print(f"Installing {pkg}...")
        _pip(pkg)

_ensure("soundfile",      "soundfile")
_ensure("noisereduce",    "noisereduce")
_ensure("imageio_ffmpeg", "imageio-ffmpeg")

import soundfile as sf
import noisereduce as nr
import imageio_ffmpeg

# ── DeepFilterNet (advanced mode) ─────────────────────────────────────────────
def _try_df():
    global enhance, init_df, load_audio, save_audio
    try:
        from df.enhance import enhance, init_df, load_audio, save_audio
        return True
    except Exception:
        return False

# if deepfilternet installed but torch missing, auto-install compatible torch
if not _try_df():
    import importlib.util
    if importlib.util.find_spec("df") is not None:
        print("Installing torch 2.1.0 CPU + deepfilternet (one-time ~230MB)...")
        _pip("torch==2.1.0", "torchaudio==2.1.0",
             "--index-url", "https://download.pytorch.org/whl/cpu")
        _pip("deepfilternet")

DEEPFILTER_AVAILABLE = _try_df()

# ─────────────────────────────────────────────────────────────────────────────
BG      = "#0a0a0f"
PANEL   = "#12121a"
BORDER  = "#1e1e2e"
ACCENT  = "#00e5a0"
ACCENT2 = "#007a55"
WARN    = "#ff9f43"
TEXT    = "#e8e8e8"
SUBTEXT = "#666680"
BTN_BG  = "#1a1a2a"
FONT_H  = ("Courier New", 18, "bold")
FONT_S  = ("Courier New", 9)
FONT_XS = ("Courier New", 8)


# ── ffmpeg conversion helper ──────────────────────────────────────────────────
def convert_to_wav(input_path, tmp_wav, status_cb):
    status_cb("Converting to WAV...")
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run(
        [ffmpeg, "-y", "-i", input_path, tmp_wav],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


# ── DeepFilterNet engine ──────────────────────────────────────────────────────
def process_deepfilter(input_path, output_path, status_cb):
    import tempfile
    ext = os.path.splitext(input_path)[1].lower()
    tmp_wav = None
    if ext in (".mp4", ".m4a", ".mp3", ".aac"):
        tmp_wav = tempfile.mktemp(suffix=".wav")
        convert_to_wav(input_path, tmp_wav, status_cb)
        read_path = tmp_wav
    else:
        read_path = input_path

    status_cb("Loading DeepFilterNet model... (first run ~17MB download)")
    model, df_state, _ = init_df()
    status_cb("Loading audio...")
    audio, _ = load_audio(read_path, sr=df_state.sr())
    status_cb("Running neural noise filter...")
    enhanced = enhance(model, df_state, audio)
    out_wav = os.path.splitext(output_path)[0] + ".wav"
    status_cb("Saving output...")
    save_audio(out_wav, enhanced, df_state.sr())
    if tmp_wav and os.path.exists(tmp_wav):
        os.remove(tmp_wav)
    status_cb(f"Done! Saved: {os.path.basename(out_wav)}")


# ── Classic spectral engine ───────────────────────────────────────────────────
def process_classic(input_path, output_path, strength, prop_decrease, status_cb):
    import tempfile
    ext = os.path.splitext(input_path)[1].lower()
    tmp_wav = None
    if ext in (".mp4", ".m4a", ".mp3", ".aac"):
        tmp_wav = tempfile.mktemp(suffix=".wav")
        convert_to_wav(input_path, tmp_wav, status_cb)
        read_path = tmp_wav
    else:
        read_path = input_path

    status_cb("Reading audio...")
    data, rate = sf.read(read_path, always_2d=True)
    if tmp_wav and os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    status_cb("Analysing noise profile...")
    results = []
    for ch in range(data.shape[1]):
        channel = data[:, ch]
        noise_sample = channel[:int(rate * 0.5)] if len(channel) > rate * 0.5 else channel
        cleaned = nr.reduce_noise(
            y=channel, sr=rate,
            y_noise=noise_sample,
            n_std_thresh_stationary=strength,
            prop_decrease=prop_decrease,
            stationary=False,
        )
        results.append(cleaned)

    out_wav = os.path.splitext(output_path)[0] + ".wav"
    sf.write(out_wav, np.stack(results, axis=1), rate)
    status_cb(f"Done! Saved: {os.path.basename(out_wav)}")


# ── background installer ──────────────────────────────────────────────────────
def install_deepfilter(done_cb, log_cb):
    def task():
        try:
            log_cb("Installing DeepFilterNet... (~17MB, please wait)")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "deepfilternet"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            log_cb("Installed! Please restart the app.")
            done_cb(True)
        except Exception as e:
            log_cb(f"Install failed: {e}")
            done_cb(False)
    threading.Thread(target=task, daemon=True).start()


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class NoiseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NoiseClear Advanced")
        self.geometry("580x610")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.input_path  = tk.StringVar()
        self.output_path = tk.StringVar()
        self.strength    = tk.DoubleVar(value=1.5)
        self.prop        = tk.DoubleVar(value=0.85)
        self.mode        = tk.StringVar(value="deepfilter" if DEEPFILTER_AVAILABLE else "classic")
        self.status_var  = tk.StringVar(value="Waiting for file...")
        self._build_ui()

    def _build_ui(self):
        tk.Frame(self, bg=ACCENT, height=3).pack(fill="x")

        hf = tk.Frame(self, bg=BG, pady=12)
        hf.pack(fill="x", padx=24)
        tk.Label(hf, text="NOISECLEAR", font=FONT_H, bg=BG, fg=ACCENT).pack(anchor="w")
        tk.Label(hf, text="advanced neural noise removal  |  no internet required",
                 font=FONT_XS, bg=BG, fg=SUBTEXT).pack(anchor="w")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── ENGINE SELECTOR ──
        self._lbl("ENGINE")
        mf = tk.Frame(self, bg=PANEL, padx=12, pady=10)
        mf.pack(fill="x", padx=20)

        df_state = "normal" if DEEPFILTER_AVAILABLE else "disabled"
        df_color = ACCENT if DEEPFILTER_AVAILABLE else SUBTEXT
        tk.Radiobutton(
            mf, text="  Neural  |  DeepFilterNet  (best quality, ~17MB first run)",
            variable=self.mode, value="deepfilter",
            bg=PANEL, fg=df_color, selectcolor=BG,
            activebackground=PANEL, font=FONT_S, state=df_state,
            command=self._mode_changed
        ).pack(anchor="w")

        if not DEEPFILTER_AVAILABLE:
            row = tk.Frame(mf, bg=PANEL)
            row.pack(anchor="w", pady=(2,0))
            tk.Label(row, text="  not installed  ", bg=PANEL, fg=WARN, font=FONT_XS).pack(side="left")
            tk.Button(row, text="Install Now", command=self._do_install,
                      bg=WARN, fg="#000", font=FONT_XS,
                      relief="flat", padx=6, cursor="hand2").pack(side="left")

        tk.Frame(mf, bg=BORDER, height=1).pack(fill="x", pady=6)
        tk.Radiobutton(
            mf, text="  Classic  |  Spectral Gating  (no model, fast)",
            variable=self.mode, value="classic",
            bg=PANEL, fg=TEXT, selectcolor=BG,
            activebackground=PANEL, font=FONT_S,
            command=self._mode_changed
        ).pack(anchor="w")

        # ── FILES ──
        self._lbl("INPUT FILE")
        f1 = tk.Frame(self, bg=PANEL, padx=10, pady=8)
        f1.pack(fill="x", padx=20)
        tk.Entry(f1, textvariable=self.input_path, width=44,
                 bg="#0d0d14", fg=TEXT, insertbackground=ACCENT,
                 relief="flat", font=FONT_S, bd=4).pack(side="left", expand=True, fill="x")
        tk.Button(f1, text="Browse", command=self._browse_in,
                  bg=BTN_BG, fg=ACCENT, relief="flat", font=FONT_S,
                  padx=8, cursor="hand2").pack(side="right", padx=(6,0))

        self._lbl("OUTPUT FILE")
        f2 = tk.Frame(self, bg=PANEL, padx=10, pady=8)
        f2.pack(fill="x", padx=20)
        tk.Entry(f2, textvariable=self.output_path, width=44,
                 bg="#0d0d14", fg=TEXT, insertbackground=ACCENT,
                 relief="flat", font=FONT_S, bd=4).pack(side="left", expand=True, fill="x")
        tk.Button(f2, text="Save As", command=self._browse_out,
                  bg=BTN_BG, fg=ACCENT, relief="flat", font=FONT_S,
                  padx=8, cursor="hand2").pack(side="right", padx=(6,0))

        # ── classic sliders ──
        self._slider_frame = tk.Frame(self, bg=BG)
        self._lbl_in_frame = tk.Label(self._slider_frame, text="CLASSIC SETTINGS",
                                      bg=BG, fg=SUBTEXT, font=("Courier New", 8, "bold"))
        self._lbl_in_frame.pack(anchor="w", padx=20)
        sf2 = tk.Frame(self._slider_frame, bg=BG, padx=20)
        sf2.pack(fill="x")
        self._slider_row(sf2, "Sensitivity", "Higher = more aggressive", self.strength, 0.5, 3.0, 0)
        self._slider_row(sf2, "Strength %",  "How much noise to subtract", self.prop, 0.1, 1.0, 1)

        # ── run button ──
        tk.Frame(self, bg=BG, height=10).pack()
        self._btn = tk.Button(self, text="  REMOVE NOISE",
                              command=self._start,
                              bg=ACCENT, fg="#000",
                              font=("Courier New", 12, "bold"),
                              relief="flat", cursor="hand2",
                              padx=20, pady=10)
        self._btn.pack(padx=20, fill="x")

        tk.Frame(self, bg=BG, height=8).pack()
        self._pb = ttk.Progressbar(self, mode="indeterminate", length=540)
        s = ttk.Style(self); s.theme_use("default")
        s.configure("TProgressbar", troughcolor=BORDER, background=ACCENT, thickness=4)
        self._pb.pack(padx=20, fill="x")

        tk.Frame(self, bg=BG, height=6).pack()
        tk.Label(self, textvariable=self.status_var, bg=BG, fg=SUBTEXT, font=FONT_S).pack(padx=20, anchor="w")
        tk.Frame(self, bg=BG, height=8).pack()
        tk.Label(self, text="Supports: WAV  FLAC  OGG  MP3  MP4  M4A  AAC",
                 bg=BG, fg="#2a2a40", font=FONT_XS).pack()

        self._mode_changed()

    def _lbl(self, text):
        tk.Frame(self, bg=BG, height=10).pack()
        tk.Label(self, text=text, bg=BG, fg=SUBTEXT,
                 font=("Courier New", 8, "bold")).pack(anchor="w", padx=20)
        tk.Frame(self, bg=BG, height=2).pack()

    def _slider_row(self, parent, label, hint, var, lo, hi, row):
        tk.Label(parent, text=label, bg=BG, fg=TEXT,
                 font=FONT_S, width=14, anchor="w").grid(row=row*2, column=0, pady=2, sticky="w")
        vl = tk.Label(parent, text=f"{var.get():.2f}", bg=BG, fg=ACCENT, font=FONT_S, width=5)
        vl.grid(row=row*2, column=2, padx=(6,0))
        tk.Scale(parent, variable=var, from_=lo, to=hi, resolution=0.05,
                 orient="horizontal", length=280, bg=BG, fg=TEXT,
                 troughcolor=BORDER, highlightthickness=0, sliderrelief="flat",
                 activebackground=ACCENT, showvalue=False,
                 command=lambda v, l=vl: l.config(text=f"{float(v):.2f}")
                 ).grid(row=row*2, column=1, padx=6)
        tk.Label(parent, text=hint, bg=BG, fg="#2a2a40",
                 font=("Courier New", 7)).grid(row=row*2+1, column=1, sticky="w", padx=6)

    def _mode_changed(self):
        if self.mode.get() == "classic":
            self._slider_frame.pack(fill="x", before=self._btn)
        else:
            self._slider_frame.pack_forget()

    def _browse_in(self):
        p = filedialog.askopenfilename(
            filetypes=[("Audio", "*.wav *.flac *.ogg *.mp3 *.mp4 *.m4a *.aac"), ("All", "*.*")])
        if p:
            self.input_path.set(p)
            base, ext = os.path.splitext(p)
            self.output_path.set(base + "_clean" + ext)
            self.status_var.set("File selected. Press REMOVE NOISE.")

    def _browse_out(self):
        p = filedialog.asksaveasfilename(defaultextension=".wav",
            filetypes=[("WAV", "*.wav"), ("FLAC", "*.flac"), ("All", "*.*")])
        if p:
            self.output_path.set(p)

    def _do_install(self):
        self._btn.config(state="disabled")
        self._pb.start(12)
        install_deepfilter(
            done_cb=lambda ok: self.after(0, lambda: self._install_done(ok)),
            log_cb=lambda m: self.after(0, lambda: self.status_var.set(m))
        )

    def _install_done(self, ok):
        self._pb.stop()
        self._btn.config(state="normal")
        if ok:
            messagebox.showinfo("Installed!", "DeepFilterNet ready!\nPlease restart the app.")

    def _start(self):
        inp = self.input_path.get().strip()
        out = self.output_path.get().strip()
        if not inp or not os.path.isfile(inp):
            messagebox.showerror("Error", "Select a valid input file.")
            return
        if not out:
            messagebox.showerror("Error", "Set an output path.")
            return

        self._btn.config(state="disabled")
        self._pb.start(12)
        self.status_var.set("Starting...")

        def task():
            try:
                if self.mode.get() == "deepfilter" and DEEPFILTER_AVAILABLE:
                    process_deepfilter(inp, out, self._upd)
                else:
                    process_classic(inp, out, self.strength.get(), self.prop.get(), self._upd)
            except Exception as e:
                self._upd(f"Error: {e}")
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.after(0, self._done)

        threading.Thread(target=task, daemon=True).start()

    def _upd(self, msg):
        self.after(0, lambda: self.status_var.set(msg))

    def _done(self):
        self._pb.stop()
        self._btn.config(state="normal")


if __name__ == "__main__":
    app = NoiseApp()
    app.mainloop()