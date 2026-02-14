#!/usr/bin/env bash
# Build an x86_64 macOS bundle on Apple Silicon using Rosetta.
# Usage: run from repo root: ./build_x86_macos.sh
set -euo pipefail
cd "$(dirname "$0")"

# Check host arch
HOST_ARCH=$(uname -m)
if [ "$HOST_ARCH" != "arm64" ]; then
  echo "Host is not Apple Silicon (arch: $HOST_ARCH). You can run the normal build script instead." 
fi

# Ensure Rosetta is installed (only needed on Apple Silicon)
if [ "$HOST_ARCH" = "arm64" ]; then
  if /usr/bin/pgrep oahd >/dev/null 2>&1; then
    echo "Rosetta already installed."
  else
    echo "Rosetta not detected. Installing (requires sudo)..."
    sudo /usr/sbin/softwareupdate --install-rosetta --agree-to-license
  fi
fi

VENV_DIR=".venv_x86"
PYBIN="${PYTHON_BIN:-/usr/bin/python3}"

if [ -n "${PYTHON_BIN-}" ]; then
  echo "Using PYTHON_BIN=$PYTHON_BIN as Python interpreter for venv creation (use an x86_64 Python installer)."
fi

# Create x86_64 venv using Rosetta
if [ -d "$VENV_DIR" ]; then
  echo "Using existing venv: $VENV_DIR"
else
  echo "Creating x86_64 venv at $VENV_DIR (this uses Rosetta)" 
  arch -x86_64 "$PYBIN" -m venv "$VENV_DIR"
fi

# Activate venv
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# Upgrade pip and install build deps
python -m pip install --upgrade pip
python -m pip install pyinstaller pillow

# Ensure ffmpeg binaries exist and are x86_64
FF_DIR="ffmpeg_binaries/macos"
if [ -f "$FF_DIR/ffmpeg" ]; then
  echo "Found $FF_DIR/ffmpeg"
  file "$FF_DIR/ffmpeg"
  echo "If the ffmpeg binary is not x86_64, download an Intel (x86_64) build and place it at $FF_DIR/ffmpeg before building."
else
  echo "Warning: $FF_DIR/ffmpeg not found. Please populate ffmpeg_binaries/macos/ with ffmpeg and ffprobe x86_64 builds before building."
fi

# Run PyInstaller under Rosetta (x86_64)
echo "Running PyInstaller (x86_64)..."
# Force deployment target to macOS 10.15 so the produced binary is compatible with
# Catalina (10.15). Also export SDK/min version for extension builds.
export MACOSX_DEPLOYMENT_TARGET="10.15"
export CFLAGS="-mmacosx-version-min=${MACOSX_DEPLOYMENT_TARGET}"

arch -x86_64 python -m PyInstaller --noconfirm --windowed --name video_to_gif \
  --add-data "ffmpeg_binaries/macos:ffmpeg_binaries" video_to_gif_gui.py

# Inspect produced binary
OUT_BIN="dist/video_to_gif.app/Contents/MacOS/video_to_gif"
if [ -f "$OUT_BIN" ]; then
  echo "Build produced: $OUT_BIN"
  file "$OUT_BIN"
  echo "If file shows 'Mach-O 64-bit executable x86_64' you're good to test on Catalina." 
else
  echo "Build did not produce expected output. See PyInstaller logs above." 
fi

echo "Done. Test the produced app on the target macOS (Catalina)." 
