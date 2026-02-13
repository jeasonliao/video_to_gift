Packaging notes — video_to_gif_gui

This repository already contains a cross-platform Tkinter GUI script: `video_to_gif_gui.py`.

What I added
- `ffmpeg_binaries/` (empty placeholder) — place platform-specific ffmpeg / ffprobe binaries here before building to have them bundled into the app.
- `download_ffmpeg.sh` — (optional) helper script to attempt downloading static ffmpeg builds for macOS and Windows. This is best-effort and may require manual verification.
- `build_mac.sh` — macOS build helper; supports an optional `--download-ffmpeg` flag to try to download binaries before building. Produces a `.app` and optional DMG in `dist/`.
- `build_windows.bat` — Windows build helper; supports an optional `--download-ffmpeg` flag to try to download binaries before building. Produces `dist\video_to_gif.exe`.

Bundling ffmpeg
- If you want the built application to include ffmpeg/ffprobe, place platform binaries under `ffmpeg_binaries/macos/` or `ffmpeg_binaries/windows/` prior to running the build script, or run the build script with `--download-ffmpeg` (internet required).
- The GUI will prefer bundled copies of `ffmpeg` and `ffprobe` if found adjacent to the executable (PyInstaller) or inside the included `ffmpeg_binaries/<platform>/` folder.

PyInstaller tweaks
- `build_mac.sh` uses `--add-data` to include `ffmpeg_binaries` in the app bundle and attempts to create a `.app` wrapper and a compressed DMG using `hdiutil`.
- `build_windows.bat` uses `--add-data` in the Windows format.

Caveats
- The download helper attempts to fetch public ffmpeg builds; URLs may become stale. Always validate licenses and test binaries before distributing.
- The produced binaries do not embed system frameworks; for macOS distribution you may still need to code-sign and notarize.

Next steps
- I can add the actual binary files into the repo for testing if you want (I cannot download binaries into your repo without your confirmation).
- I can also modify the GUI to show which ffmpeg binary it is using at startup.

Important notes:
- ffmpeg/ffprobe are NOT bundled into the executable. You must install ffmpeg on the target system and ensure `ffmpeg` and `ffprobe` are on PATH.
- The generated binary contains the Python runtime and the script but external dependencies like system libraries and ffmpeg are external.
- On Windows, ensure you run `build_windows.bat` in Command Prompt (not PowerShell) or adapt activation commands for PowerShell.
- On macOS, code signing and notarization may be required to distribute an app to other users. The script uses PyInstaller to make a single-file executable; for an app bundle prefer `pyinstaller --windowed --name video_to_gif --onedir` or use `py2app`.

Usage (brief):
- macOS: open Terminal (zsh), cd to `vedio_convert/` and run `./build_mac.sh`.
- Windows: open Command Prompt, cd to `vedio_convert\` and run `build_windows.bat`.

If you want me to instead produce a cross-platform installer (DMG / .app, NSIS installer for Windows) or update the script to bundle ffmpeg using a bundled ffmpeg binary per platform, tell me which target platforms and I will add the required files and commands.
