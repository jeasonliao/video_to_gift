@echo off
REM Build helper for Windows (Command Prompt).
REM Usage: run from the vedio_convert\ directory: build_windows.bat [--download-ffmpeg]
SETLOCAL ENABLEDELAYEDEXPANSION
cd /d %~dp0

SET DOWNLOAD_FFMPEG=false
IF "%1"=="--download-ffmpeg" SET DOWNLOAD_FFMPEG=true
IF "%DOWNLOAD_FFMPEG%"=="true" (
    call download_ffmpeg.sh windows
)
python -m venv .venv
call .\.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install pyinstaller pillow

REM PyInstaller expects add-data entries in the format src;dest on Windows
SET PY_ADD_DATA=ffmpeg_binaries;ffmpeg_binaries
pyinstaller --noconfirm --onefile --windowed --name video_to_gif.exe --add-data "%PY_ADD_DATA%" video_to_gif_gui.py

echo Build complete. Result: %~dp0dist\video_to_gif.exe
echo Note: ffmpeg is included in the bundle only if you placed ffmpeg/ffprobe into ffmpeg_binaries\windows before building, or used --download-ffmpeg.
PAUSE
