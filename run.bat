@echo off
title NoiseClear - Setting up...
color 0A

echo.
echo  ========================================
echo    NOISECLEAR - Auto Setup
echo  ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found!
    echo.
    echo  Please install Python from:
    echo  https://www.python.org/downloads/
    echo  
    echo  Make sure to check "Add Python to PATH"
    echo  during installation!
    echo.
    pause
    exit /b
)

echo  [1/5] Python found!

:: Install core deps silently
echo  [2/5] Installing core libraries...
python -m pip install soundfile noisereduce imageio-ffmpeg --quiet

echo  [3/5] Installing DeepFilterNet...
python -m pip install deepfilternet --quiet

:: Check if torch is present
python -c "import torch" >nul 2>&1
if errorlevel 1 (
    echo  [4/5] Installing PyTorch CPU (one-time ~230MB^)...
    python -m pip install torch==2.1.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cpu --quiet
) else (
    echo  [4/5] PyTorch already installed!
)

echo  [5/5] Launching NoiseClear...
echo.
python noise_canceller.py