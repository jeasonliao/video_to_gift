#!/usr/bin/env bash
# Build helper for macOS (zsh/bash).
# Usage: run this from the vedio_convert/ directory: ./build_mac.sh [--download-ffmpeg]
set -euo pipefail
cd "$(dirname "$0")"

DOWNLOAD_FFMPEG=false
if [ "${1-}" = "--download-ffmpeg" ]; then
    DOWNLOAD_FFMPEG=true
fi

if [ "$DOWNLOAD_FFMPEG" = true ]; then
    echo "Attempting to download ffmpeg binaries (may require internet access)..."
    ./download_ffmpeg.sh macos || echo "download_ffmpeg.sh failed; please populate ffmpeg_binaries/macos manually."
fi

# Create and activate virtualenv
python3 -m venv .venv
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install --upgrade pip
# Install build deps
python -m pip install pyinstaller pillow

# Build as macOS app bundle (.app). We include the ffmpeg_binaries directory as data so
# the produced bundle contains ffmpeg/ffprobe when present in that folder.
# Use --onedir to produce an app directory which is easier to bundle into a .app/.dmg.

# On macOS, PyInstaller expects add-data using ':' separator
PY_ADD_DATA="ffmpeg_binaries:ffmpeg_binaries"

# Ensure the ffmpeg_binaries directory exists so PyInstaller doesn't error when the
# directory is absent. If you want ffmpeg included, place ffmpeg/ffprobe into
# ffmpeg_binaries/macos or run the script with --download-ffmpeg.
mkdir -p ffmpeg_binaries

# If the macOS ffmpeg binaries are not present in ffmpeg_binaries, try to copy
# the system-installed ffmpeg/ffprobe into the folder so PyInstaller will bundle
# them. This lets users who have ffmpeg installed include it automatically.
mkdir -p ffmpeg_binaries/macos
if [ ! -x "ffmpeg_binaries/macos/ffmpeg" ]; then
    if command -v ffmpeg >/dev/null 2>&1; then
        echo "Found system ffmpeg — copying into ffmpeg_binaries/macos/ for bundling."
        SYS_FFMPEG=$(command -v ffmpeg)
        SYS_FFPROBE=$(command -v ffprobe || true)
        cp -f "$SYS_FFMPEG" ffmpeg_binaries/macos/ffmpeg || true
        if [ -n "$SYS_FFPROBE" ]; then
            cp -f "$SYS_FFPROBE" ffmpeg_binaries/macos/ffprobe || true
        fi
        chmod +x ffmpeg_binaries/macos/ffmpeg ffmpeg_binaries/macos/ffprobe || true
    else
        echo "Note: system ffmpeg not found. The built app will require ffmpeg on PATH at runtime unless you populate ffmpeg_binaries/macos/."
    fi
fi

pyinstaller --noconfirm --windowed --name video_to_gif --add-data "$PY_ADD_DATA" video_to_gif_gui.py

# On macOS PyInstaller will produce either a .app in dist/ or an executable directory.
APP_PATH="dist/video_to_gif.app"
if [ -d "$APP_PATH" ]; then
    echo "App bundle created at: $APP_PATH"
else
    # Some PyInstaller versions create a directory 'dist/video_to_gif' with an executable; create a minimal .app wrapper
    if [ -d "dist/video_to_gif" ]; then
        echo "Packaging dist/video_to_gif into .app wrapper..."
        rm -rf "dist/video_to_gif.app"
        mkdir -p "dist/video_to_gif.app/Contents/MacOS"
        cp -R "dist/video_to_gif"/* "dist/video_to_gif.app/Contents/MacOS/"
        # Minimal Info.plist
        cat > "dist/video_to_gif.app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>video_to_gif</string>
    <key>CFBundleExecutable</key>
    <string>video_to_gif</string>
    <key>CFBundleIdentifier</key>
    <string>com.example.video_to_gif</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
</dict>
</plist>
EOF
        echo "Created dist/video_to_gif.app"
        APP_PATH="dist/video_to_gif.app"
    else
        echo "Warning: build output not found in dist/. See PyInstaller output above."
    fi
fi

# Create a compressed DMG for distribution (requires hdiutil)
DMG_PATH="dist/video_to_gif.dmg"
if command -v hdiutil >/dev/null 2>&1 && [ -d "$APP_PATH" ]; then
    echo "Creating DMG: $DMG_PATH"
    rm -f "$DMG_PATH"
    hdiutil create -volname "video_to_gif" -srcfolder "$APP_PATH" -ov -format UDZO "$DMG_PATH"
    echo "DMG created: $DMG_PATH"
else
    echo "hdiutil not found or app bundle missing; skipping DMG creation. You can create a DMG manually."
fi

echo "Build complete. Result(s) in dist/"
echo "Note: ffmpeg is included in the bundle only if you placed ffmpeg/ffprobe into ffmpeg_binaries/macos before building, or used --download-ffmpeg."
