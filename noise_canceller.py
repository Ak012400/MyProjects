import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import numpy as np

# ── dependency check ──────────────────────────────────────────────────────────
try:
    import soundfile as sf
    import noisereduce as nr
    import imageio_ffmpeg
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "noisereduce", "soundfile", "imageio-ffmpeg"])
    import soundfile as sf
    import noisereduce as nr
    import imageio_ffmpeg

# ─────────────────────────────────────────────────────────────────────────────
#  COLOUR PALETTE  (dark industrial)
# ─────────────────────────────────────────────────────────────────────────────
BG       = "#0f0f0f"
PANEL    = "#1a1a1a"
BORDER   = "#2a2a2a"
ACCENT   = "#00e5a0"       # mint-green
ACCENT2  = "#007a55"
TEXT     = "#e8e8e8"
SUBTEXT  = "#888888"
BTN_BG   = "#1f1f1f"

FONT_H   = ("Courier New", 18, "bold")
FONT_B   = ("Courier New", 11)
FONT_S   = ("Courier New", 9)


def reduce_noise(input_path, output_path, strength, prop_decrease, status_cb):
    """Core noise-reduction logic (runs on a background thread)."""
    import tempfile, subprocess as sp

    status_cb("Reading audio…")
    ext = os.path.splitext(input_path)[1].lower()

    # MP4 / M4A / MP3 / AAC → convert to WAV using imageio_ffmpeg directly
    tmp_wav = None
    if ext in (".mp4", ".m4a", ".mp3", ".aac"):
        status_cb("Converting to WAV…")
        tmp_wav = tempfile.mktemp(suffix=".wav")
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        sp.run(
            [ffmpeg_exe, "-y", "-i", input_path, tmp_wav],
            check=True, stdout=sp.DEVNULL, stderr=sp.DEVNULL
        )
        read_path = tmp_wav
    else:
        read_path = input_path

    data, sr = sf.read(read_path, always_2d=True)          # shape: (samples, channels)
    if tmp_wav and os.path.exists(tmp_wav):
        os.remove(tmp_wav)

    status_cb("Analysing noise profile…")
    results = []
    for ch in range(data.shape[1]):
        channel = data[:, ch]
        # Use first 0.5 s as noise sample (or full file if shorter)
        noise_sample = channel[:int(sr * 0.5)] if len(channel) > sr * 0.5 else channel
        cleaned = nr.reduce_noise(
            y=channel,
            sr=sr,
            y_noise=noise_sample,
            n_std_thresh_stationary=strength,
            prop_decrease=prop_decrease,
            stationary=False,
        )
        results.append(cleaned)

    status_cb("Writing output…")
    out_data = np.stack(results, axis=1)
    # Always save as WAV (most compatible)
    out_wav = os.path.splitext(output_path)[0] + ".wav"
    sf.write(out_wav, out_data, sr)
    status_cb(f"✔  Saved → {os.path.basename(out_wav)}")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────────────────────────────────────────
class NoiseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NoiseClear — Audio Noise Remover")
        self.geometry("560x520")
        self.resizable(False, False)
        self.configure(bg=BG)

        self.input_path  = tk.StringVar()
        self.output_path = tk.StringVar()
        self.strength    = tk.DoubleVar(value=1.5)   # std-dev threshold
        self.prop        = tk.DoubleVar(value=0.80)  # how much noise to subtract
        self.status_var  = tk.StringVar(value="Waiting for file…")

        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        # ── header ──
        hdr = tk.Frame(self, bg=ACCENT, height=4)
        hdr.pack(fill="x")

        title_frame = tk.Frame(self, bg=BG, pady=14)
        title_frame.pack(fill="x", padx=24)
        tk.Label(title_frame, text="NOISECLEAR", font=FONT_H,
                 bg=BG, fg=ACCENT).pack(anchor="w")
        tk.Label(title_frame, text="background noise removal · no internet required",
                 font=FONT_S, bg=BG, fg=SUBTEXT).pack(anchor="w")

        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x", padx=0)

        # ── file section ──
        self._section("INPUT FILE")
        f1 = tk.Frame(self, bg=PANEL, padx=10, pady=8)
        f1.pack(fill="x", padx=20)
        tk.Entry(f1, textvariable=self.input_path, width=44,
                 bg="#111", fg=TEXT, insertbackground=ACCENT,
                 relief="flat", font=FONT_S, bd=4).pack(side="left", expand=True, fill="x")
        tk.Button(f1, text="Browse", command=self._browse_input,
                  bg=BTN_BG, fg=ACCENT, relief="flat", font=FONT_S,
                  padx=8, cursor="hand2",
                  activebackground=ACCENT2, activeforeground="#000").pack(side="right", padx=(6,0))

        self._section("OUTPUT FILE")
        f2 = tk.Frame(self, bg=PANEL, padx=10, pady=8)
        f2.pack(fill="x", padx=20)
        tk.Entry(f2, textvariable=self.output_path, width=44,
                 bg="#111", fg=TEXT, insertbackground=ACCENT,
                 relief="flat", font=FONT_S, bd=4).pack(side="left", expand=True, fill="x")
        tk.Button(f2, text="Save As", command=self._browse_output,
                  bg=BTN_BG, fg=ACCENT, relief="flat", font=FONT_S,
                  padx=8, cursor="hand2",
                  activebackground=ACCENT2, activeforeground="#000").pack(side="right", padx=(6,0))

        # ── sliders ──
        self._section("NOISE REDUCTION SETTINGS")
        sliders = tk.Frame(self, bg=BG, padx=20)
        sliders.pack(fill="x")

        self._slider_row(sliders, "Sensitivity",
                         "Higher = more aggressive noise removal",
                         self.strength, 0.5, 3.0, row=0)
        self._slider_row(sliders, "Strength %",
                         "How much of the noise to subtract",
                         self.prop, 0.1, 1.0, row=1)

        # ── process button ──
        tk.Frame(self, bg=BG, height=12).pack()
        btn = tk.Button(self, text="⬡  REMOVE NOISE",
                        command=self._start,
                        bg=ACCENT, fg="#000",
                        font=("Courier New", 12, "bold"),
                        relief="flat", cursor="hand2",
                        padx=20, pady=10,
                        activebackground=ACCENT2, activeforeground="#000")
        btn.pack(padx=20, fill="x")
        self._btn = btn

        # ── progress & status ──
        tk.Frame(self, bg=BG, height=10).pack()
        self._pb = ttk.Progressbar(self, mode="indeterminate", length=520)
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TProgressbar", troughcolor=BORDER,
                        background=ACCENT, thickness=4)
        self._pb.pack(padx=20, fill="x")

        tk.Frame(self, bg=BG, height=8).pack()
        tk.Label(self, textvariable=self.status_var,
                 bg=BG, fg=SUBTEXT, font=FONT_S).pack(padx=20, anchor="w")

        tk.Frame(self, bg=BG, height=10).pack()
        tk.Label(self, text="Supports: WAV · FLAC · OGG · MP3 · MP4 · M4A · AAC",
                 bg=BG, fg="#444", font=FONT_S).pack()

    def _section(self, label):
        tk.Frame(self, bg=BG, height=12).pack()
        tk.Label(self, text=label, bg=BG, fg=SUBTEXT,
                 font=("Courier New", 8, "bold")).pack(anchor="w", padx=20)
        tk.Frame(self, bg=BG, height=2).pack()

    def _slider_row(self, parent, label, hint, var, lo, hi, row):
        tk.Label(parent, text=label, bg=BG, fg=TEXT,
                 font=FONT_S, width=14, anchor="w").grid(row=row, column=0, pady=4, sticky="w")

        val_label = tk.Label(parent, text=f"{var.get():.2f}",
                             bg=BG, fg=ACCENT, font=FONT_S, width=5)
        val_label.grid(row=row, column=2, padx=(6,0))

        sl = tk.Scale(parent, variable=var, from_=lo, to=hi,
                      resolution=0.05, orient="horizontal", length=280,
                      bg=BG, fg=TEXT, troughcolor=BORDER,
                      highlightthickness=0, sliderrelief="flat",
                      activebackground=ACCENT, showvalue=False,
                      command=lambda v, lbl=val_label: lbl.config(text=f"{float(v):.2f}"))
        sl.grid(row=row, column=1, padx=6)

        tk.Label(parent, text=hint, bg=BG, fg="#444",
                 font=("Courier New", 7)).grid(row=row+1, column=1, sticky="w", padx=6)

    # ── file dialogs ──────────────────────────────────────────────────────────
    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio files", "*.wav *.flac *.ogg *.mp3 *.mp4 *.m4a *.aac"),
                       ("All files", "*.*")])
        if path:
            self.input_path.set(path)
            # auto-suggest output
            base, ext = os.path.splitext(path)
            self.output_path.set(base + "_clean" + ext)
            self.status_var.set("File selected. Press REMOVE NOISE when ready.")

    def _browse_output(self):
        path = filedialog.asksaveasfilename(
            title="Save cleaned audio as",
            defaultextension=".wav",
            filetypes=[("WAV", "*.wav"), ("FLAC", "*.flac"),
                       ("OGG", "*.ogg"), ("All files", "*.*")])
        if path:
            self.output_path.set(path)

    # ── processing ────────────────────────────────────────────────────────────
    def _start(self):
        inp = self.input_path.get().strip()
        out = self.output_path.get().strip()

        if not inp:
            messagebox.showerror("Error", "Please select an input file.")
            return
        if not os.path.isfile(inp):
            messagebox.showerror("Error", "Input file not found.")
            return
        if not out:
            messagebox.showerror("Error", "Please set an output path.")
            return

        self._btn.config(state="disabled")
        self._pb.start(12)
        self.status_var.set("Processing…")

        def task():
            try:
                reduce_noise(inp, out,
                             strength=self.strength.get(),
                             prop_decrease=self.prop.get(),
                             status_cb=self._update_status)
            except Exception as e:
                self._update_status(f"✘  Error: {e}")
                messagebox.showerror("Processing Error", str(e))
            finally:
                self.after(0, self._done)

        threading.Thread(target=task, daemon=True).start()

    def _update_status(self, msg):
        self.after(0, lambda: self.status_var.set(msg))

    def _done(self):
        self._pb.stop()
        self._btn.config(state="normal")


if __name__ == "__main__":
    app = NoiseApp()
    app.mainloop()