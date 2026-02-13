#!/usr/bin/env bash
# download_ffmpeg.sh
# Minimal script to download small static ffmpeg builds for macOS (x86_64 and arm64) and Windows.
# This script is not exhaustive and may need updates. It attempts to place platform binaries into ffmpeg_binaries/<platform>/
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p ffmpeg_binaries/macos ffmpeg_binaries/windows

# macOS (use johnvansickle builds or ffmpeg.zeranoe is gone). We'll try github.com/yt-dlp/ffmpeg-binaries or binares from evermeet.
# For simplicity, attempt to download an automatics build (intel/arm universal may not be available).

echo "Downloading macOS ffmpeg (universal)..."
MAC_URLS=(
    "https://evermeet.cx/ffmpeg/ffmpeg-6.0.zip" 
    "https://evermeet.cx/ffmpeg/ffmpeg-5.1.zip"
)

for url in "${MAC_URLS[@]}"; do
    echo "Trying $url"
    tmp="/tmp/ffmpeg_mac.zip"
    if curl -fsSL "$url" -o "$tmp"; then
        unzip -o "$tmp" -d /tmp/ffmpeg_mac_extract
        # evermeet provides ffmpeg and ffprobe at root
        if [ -f "/tmp/ffmpeg_mac_extract/ffmpeg" ]; then
            mkdir -p ffmpeg_binaries/macos
            mv /tmp/ffmpeg_mac_extract/ffmpeg ffmpeg_binaries/macos/ffmpeg
            if [ -f "/tmp/ffmpeg_mac_extract/ffprobe" ]; then
                mv /tmp/ffmpeg_mac_extract/ffprobe ffmpeg_binaries/macos/ffprobe
            fi
            chmod +x ffmpeg_binaries/macos/ffmpeg ffmpeg_binaries/macos/ffprobe || true
            rm -rf /tmp/ffmpeg_mac_extract "$tmp"
            echo "macOS ffmpeg downloaded to ffmpeg_binaries/macos/"
            break
        fi
    fi
done

# Windows static build (ffmpeg.zeranoe no longer available). Use gyan.dev builds
WIN_URL="https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

echo "Downloading Windows ffmpeg (release essentials)..."
if curl -fsSL "$WIN_URL" -o /tmp/ffmpeg_win.zip; then
    unzip -o /tmp/ffmpeg_win.zip -d /tmp/ffmpeg_win_extract
    # Find ffmpeg.exe and ffprobe.exe in extracted folders
    bin_dir=$(find /tmp/ffmpeg_win_extract -type f -iname ffmpeg.exe -printf '%h\n' | head -n1 || true)
    if [ -n "$bin_dir" ]; then
        mkdir -p ffmpeg_binaries/windows
        cp -f "$bin_dir/ffmpeg.exe" ffmpeg_binaries/windows/ffmpeg.exe
        cp -f "$bin_dir/ffprobe.exe" ffmpeg_binaries/windows/ffprobe.exe || true
        echo "Windows ffmpeg binaries copied to ffmpeg_binaries/windows/"
    else
        echo "Could not locate ffmpeg.exe in the downloaded archive."
    fi
    rm -rf /tmp/ffmpeg_win_extract /tmp/ffmpeg_win.zip || true
fi

echo "Download script finished. Please verify the binaries in ffmpeg_binaries/ and test them before distribution."
