# 🎙️ NoiseClear — Audio Noise Remover

> Remove background noise from WhatsApp, call recordings, and any audio file — **no internet required, runs fully offline.**

---

## ✨ Features

- 🧠 **Neural Mode** — DeepFilterNet (state-of-the-art speech enhancement)
- ⚗️ **Classic Mode** — Spectral Gating (fast, no model needed)
- 🎵 Supports **MP4, WAV, FLAC, OGG, MP3, M4A, AAC**
- 🖥️ Simple desktop GUI — no technical knowledge required
- 📦 Auto-installs all dependencies on first run

---

## 🚀 Quick Start (Non-Technical Users)

### Step 1 — Install Python (one time only)
Download from 👉 [python.org/downloads](https://www.python.org/downloads/)

> ⚠️ During install, make sure to check **"Add Python to PATH"**

### Step 2 — Download the app
Go to [**Releases**](../../releases) → Download `NoiseClear.zip` → Extract it

### Step 3 — Run
Double-click **`run.bat`**

That's it! Everything installs automatically on first run (~230MB, one time only).

---

## 🛠️ For Developers

```bash
git clone https://github.com/Ak012400/NoiceCancellation-App
cd NoiseClear-App

pip install deepfilternet torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu
python noise_canceller.py
```

---

## 📸 Screenshot

<!-- Add screenshot here after first run -->
> _Screenshot coming soon_

---

## 🔬 How It Works

| Mode | Algorithm | Quality | Speed |
|------|-----------|---------|-------|
| Neural | DeepFilterNet (RNNoise-based deep learning) | ⭐⭐⭐⭐⭐ | Medium |
| Classic | Spectral Gating (noisereduce) | ⭐⭐⭐ | Fast |

**Neural mode** uses a pretrained deep learning model (~17MB) specifically trained on speech data — perfect for WhatsApp voice notes and call recordings.

---

## 📋 Requirements

- Windows 10/11
- Python 3.10+
- ~500MB disk space (for PyTorch, one time)

---

## 📄 License

MIT License — free to use and modify.

---

<p align="center">Made with ❤️ by <a href="https://github.com/Ak012400">Arun Kumar</a></p>