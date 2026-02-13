# video_to_gift

## CI: Build macOS x86_64 artifact

This repo includes a GitHub Actions workflow `.github/workflows/build-macos-x86.yml` that builds an x86_64 macOS app (PyInstaller) and uploads a zip artifact. To run it:

- Push to `main` or use the "Run workflow" button in the Actions tab.
- The artifact `video_to_gif-macos-x86_64` will contain `dist/video_to_gif.app` (zipped) suitable for Intel macOS (Catalina).

Make sure to review and include ffmpeg licensing if you ship ffmpeg binaries.
