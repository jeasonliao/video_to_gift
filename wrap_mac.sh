# from repo root (zsh)
APP_NAME="video_to_gif_custom"
APP_DIR="dist/$APP_NAME.app"
REAL_DIR="$APP_DIR/Contents/MacOS/_app"

rm -rf "$APP_DIR"
mkdir -p "$REAL_DIR" "$APP_DIR/Contents/Resources"

# copy built files (prefer build/video_to_gif)
cp -R build/video_to_gif/* "$REAL_DIR/" || cp -R dist/video_to_gif/* "$REAL_DIR/" || true
chmod +x "$REAL_DIR/video_to_gif" || true

# create launcher
cat > "$APP_DIR/Contents/MacOS/video_to_gif" <<'EOF'
#!/usr/bin/env bash
DIR="$(dirname "$0")/_app"
cd "$DIR"
exec ./video_to_gif "$@"
EOF
chmod +x "$APP_DIR/Contents/MacOS/video_to_gif"

# Info.plist
cat > "$APP_DIR/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>video_to_gif</string>
  <key>CFBundleExecutable</key><string>video_to_gif</string>
  <key>CFBundleIdentifier</key><string>com.example.video_to_gif</string>
  <key>CFBundleVersion</key><string>1.0</string>
</dict></plist>
EOF

# copy ffmpeg into Resources if you want it bundled (optional)
mkdir -p "$APP_DIR/Contents/Resources/ffmpeg_binaries/macos"
cp -R dist/video_to_gif.app/Contents/Resources/ffmpeg_binaries/macos/* "$APP_DIR/Contents/Resources/ffmpeg_binaries/macos/" 2>/dev/null || cp -R ffmpeg_binaries/macos/* "$APP_DIR/Contents/Resources/ffmpeg_binaries/macos/" 2>/dev/null || true
chmod -R a+rx "$APP_DIR/Contents/Resources/ffmpeg_binaries" || true

# create DMG (optional)
DMG="dist/${APP_NAME}.dmg"
rm -f "$DMG"
if command -v hdiutil >/dev/null 2>&1; then
  hdiutil create -volname "video_to_gif" -srcfolder "$APP_DIR" -ov -format UDZO "$DMG"
  echo "DMG created: $DMG"
else
  echo "Created app at: $APP_DIR (hdiutil not found, so no DMG created)"
fi