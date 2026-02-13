#!/usr/bin/env python3
"""
video_to_gif_gui.py

A cross-platform single-file Python GUI utility (tkinter) to:
 - open a video file
 - choose start and end times (HH:MM:SS or seconds)
 - preview a single frame
 - export an animated GIF for the chosen range using ffmpeg
 - supports palette-based (best quality) and single-step (faster) methods
 - allows setting FPS and width and choosing output path
 - cleans up temporary files

Environment & setup
-------------------
Requires Python 3.10+.

Recommended: create and activate a virtual environment and install Pillow
(if you want preview functionality):

macOS / Linux:
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  python -m pip install pillow

Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  python -m pip install pillow

Install ffmpeg and ensure it is on PATH:
  macOS (Homebrew): brew install ffmpeg
  Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg
  Windows: use winget/choco or download from https://ffmpeg.org and add to PATH

Verify ffmpeg is installed:
  ffmpeg -version

Run:
  python video_to_gif_gui.py

Example ffmpeg snippets (used in this script)
- Palette (best quality):
  ffmpeg -ss {START} -to {END} -i "{INPUT}" -vf "fps={FPS},scale={WIDTH}:-1:flags=lanczos,palettegen" -y "{PALETTE}"
  ffmpeg -ss {START} -to {END} -i "{INPUT}" -i "{PALETTE}" -lavfi "fps={FPS},scale={WIDTH}:-1:flags=lanczos [x]; [x][1:v] paletteuse" -y "{OUTPUT}"
- Single-step (faster, lower quality):
  ffmpeg -ss {START} -to {END} -i "{INPUT}" -vf "fps={FPS},scale={WIDTH}:-1:flags=lanczos" -y "{OUTPUT}"

Notes
-----
 - This script uses subprocess.run with check=True and captures stdout/stderr for error reporting.
 - If Pillow is not installed, preview feature will be disabled (the rest of the functionality still works).
 - The GUI uses threading to run ffmpeg operations so the UI remains responsive.
"""

from __future__ import annotations
import os
import sys
import subprocess
import tempfile
import threading
import shlex
import math
from dataclasses import dataclass
from typing import Optional, Tuple

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception as e:
    print("tkinter is required but not available in this Python build.", file=sys.stderr)
    raise

# Pillow for preview (optional)
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

# Prefer bundled ffmpeg/ffprobe when present (next to executable or in ffmpeg_binaries/<platform>/)
def find_ffmpeg_binaries() -> tuple[str, str]:
    """Return (ffmpeg_cmd, ffprobe_cmd).

    Preference order:
    1. If running frozen (PyInstaller), look next to the executable for ffmpeg/ffprobe.
    2. Look in "ffmpeg_binaries/<platform>/" under the script directory for named binaries.
    3. Fall back to system commands "ffmpeg" and "ffprobe".
    """
    exe_dir = None
    try:
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(__file__)
    except Exception:
        exe_dir = os.path.abspath('.')

    # Platform specific names
    if sys.platform == "win32":
        ffmpeg_name = "ffmpeg.exe"
        ffprobe_name = "ffprobe.exe"
    else:
        ffmpeg_name = "ffmpeg"
        ffprobe_name = "ffprobe"

    # 1) check next to executable / script
    ff_local = os.path.join(exe_dir, ffmpeg_name)
    fp_local = os.path.join(exe_dir, ffprobe_name)
    if os.path.isfile(ff_local) and os.access(ff_local, os.X_OK) and os.path.isfile(fp_local) and os.access(fp_local, os.X_OK):
        return ff_local, fp_local

    # 2) check ffmpeg_binaries/<platform>/ in several likely locations. When
    # frozen, PyInstaller may place data in Resources or Frameworks inside the
    # .app bundle, or in a _internal folder for a --onedir build. Also check
    # sys._MEIPASS for one-file temp extraction.
    if sys.platform == "darwin":
        platform_sub = "macos"
    elif sys.platform == "win32":
        platform_sub = "windows"
    else:
        platform_sub = "linux"

    candidates = []
    # directly next to executable (e.g. when ffmpeg_binaries is placed alongside the binary)
    candidates.append(os.path.join(exe_dir, "ffmpeg_binaries"))
    # If frozen inside a .app bundle, exe_dir is likely the embedded _app directory
    # so climb to Contents and then to Resources/Frameworks where PyInstaller may store data
    app_contents = os.path.dirname(exe_dir)
    app_root = os.path.dirname(app_contents)
    candidates.append(os.path.join(app_root, "Resources", "ffmpeg_binaries"))
    candidates.append(os.path.join(app_root, "Frameworks", "ffmpeg_binaries"))
    # PyInstaller --onedir sometimes extracts internal data under an _internal dir
    candidates.append(os.path.join(os.path.dirname(parent), "_internal", "ffmpeg_binaries"))
    # sys._MEIPASS if onefile
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, "ffmpeg_binaries"))
    # also check relative to the source file (useful when running from source)
    try:
        src_dir = os.path.dirname(__file__)
        candidates.append(os.path.join(src_dir, "ffmpeg_binaries"))
    except Exception:
        pass

    for cand in candidates:
        platform_dir = os.path.join(cand, platform_sub)
        ff_local = os.path.join(platform_dir, ffmpeg_name)
        fp_local = os.path.join(platform_dir, ffprobe_name)
        if os.path.isfile(ff_local) and os.access(ff_local, os.X_OK) and os.path.isfile(fp_local) and os.access(fp_local, os.X_OK):
            return ff_local, fp_local

    # Fallback to system commands
    return ffmpeg_name, ffprobe_name

# Expose chosen commands
FFMPEG_CMD, FFPROBE_CMD = find_ffmpeg_binaries()


def check_ffmpeg_available() -> bool:
    """Return True if ffmpeg (and ffprobe) appear available on PATH or bundled."""
    for cmd in ((FFMPEG_CMD, "-version"), (FFPROBE_CMD, "-version")):
        try:
            subprocess.run([cmd[0], cmd[1]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            return False
    return True

def run_subprocess(cmd: list[str], capture: bool = True) -> Tuple[int, str, str]:
    """Run subprocess command and return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE if capture else None,
                              stderr=subprocess.PIPE if capture else None,
                              text=True, check=False)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        return proc.returncode, stdout, stderr
    except Exception as e:
        return 1, "", str(e)

def parse_time(t: str) -> Optional[float]:
    """
    Parse a time string in seconds or HH:MM:SS(.ms) format to seconds (float).
    Returns None on parse error.
    """
    if t is None:
        return None
    t = str(t).strip()
    if t == "":
        return None
    # Try plain float seconds
    try:
        return float(t)
    except ValueError:
        pass
    parts = t.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    if len(parts) == 1:
        return parts[0]
    # hh:mm:ss or mm:ss
    parts = list(reversed(parts))
    seconds = 0.0
    multiplier = 1.0
    for p in parts:
        seconds += p * multiplier
        multiplier *= 60.0
    return seconds

def format_time_seconds(s: float) -> str:
    """Format seconds as HH:MM:SS.mmm (no timezone)."""
    if s is None:
        return "Unknown"
    ms = int((s - math.floor(s)) * 1000)
    total = int(math.floor(s))
    sec = total % 60
    total //= 60
    minute = total % 60
    hour = total // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d}.{ms:03d}"

def get_video_duration(path: str) -> Optional[float]:
    """Get video duration in seconds using ffprobe, fallback to ffmpeg -i stderr parsing."""
    # Try ffprobe
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", path]
        rc, out, err = run_subprocess(cmd)
        if rc == 0 and out.strip():
            return float(out.strip())
    except Exception:
        pass
    # Fallback: ffmpeg -i outputs duration to stderr
    try:
        cmd = ["ffmpeg", "-i", path]
        rc, out, err = run_subprocess(cmd)
        text = out + err
        # search 'Duration: HH:MM:SS.xx'
        import re
        m = re.search(r"Duration: (\d+):(\d+):([\d\.]+)", text)
        if m:
            h, m_, s = m.groups()
            return float(h) * 3600.0 + float(m_) * 60.0 + float(s)
    except Exception:
        pass
    return None

@dataclass
class ExportOptions:
    fps: int = 10
    width: Optional[int] = None  # None means keep original width
    method: str = "palette"  # 'palette' or 'single'

# FFmpeg operations

def run_ffmpeg_palette(input_path: str, start: float, end: float, fps: int, width: Optional[int], output_path: str,
                       work_dir: str, progress_callback=None) -> Tuple[bool, str]:
    """
    Run palette-based two-pass ffmpeg GIF generation.
    Returns (success, message).
    """
    palette_path = os.path.join(work_dir, "palette.png")
    ss = format_time_seconds(start)
    to = format_time_seconds(end)
    scale = f"scale={width}:-1:flags=lanczos" if width else "scale=iw:-1:flags=lanczos"
    # Palette generation
    palette_cmd = [
        "ffmpeg", "-ss", ss, "-to", to, "-i", input_path,
        "-vf", f"fps={fps},{scale},palettegen",
        "-y", palette_path
    ]
    if progress_callback:
        progress_callback(f"Running palette generation:\n{' '.join(shlex.quote(x) for x in palette_cmd)}")
    rc, out, err = run_subprocess(palette_cmd)
    if rc != 0:
        return False, f"Palette generation failed: {err or out}"
    # Use palette to create gif
    gif_cmd = [
        "ffmpeg", "-ss", ss, "-to", to, "-i", input_path, "-i", palette_path,
        "-lavfi", f"fps={fps},{scale} [x]; [x][1:v] paletteuse",
        "-y", output_path
    ]
    if progress_callback:
        progress_callback(f"Running palette use:\n{' '.join(shlex.quote(x) for x in gif_cmd)}")
    rc2, out2, err2 = run_subprocess(gif_cmd)
    if rc2 != 0:
        return False, f"Palette-based gif creation failed: {err2 or out2}"
    return True, "GIF created successfully (palette method)."

def run_ffmpeg_single(input_path: str, start: float, end: float, fps: int, width: Optional[int], output_path: str,
                      progress_callback=None) -> Tuple[bool, str]:
    """Run single-step ffmpeg command to create gif (faster, lower quality)."""
    ss = format_time_seconds(start)
    to = format_time_seconds(end)
    scale = f"scale={width}:-1:flags=lanczos" if width else "scale=iw:-1:flags=lanczos"
    cmd = [
        "ffmpeg", "-ss", ss, "-to", to, "-i", input_path,
        "-vf", f"fps={fps},{scale}",
        "-y", output_path
    ]
    if progress_callback:
        progress_callback(f"Running single-step command:\n{' '.join(shlex.quote(x) for x in cmd)}")
    rc, out, err = run_subprocess(cmd)
    if rc != 0:
        return False, f"Single-step GIF creation failed: {err or out}"
    return True, "GIF created successfully (single-step method)."

# Preview frame

def extract_frame_to_file(input_path: str, time_sec: float, out_path: str) -> Tuple[bool, str]:
    """Extract a single frame at time_sec (seconds) to out_path using ffmpeg."""
    ss = format_time_seconds(time_sec)
    cmd = [
        "ffmpeg", "-ss", ss, "-i", input_path,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        out_path
    ]
    rc, out, err = run_subprocess(cmd)
    if rc != 0:
        return False, err or out
    return True, "Frame extracted."

# GUI

class VideoToGifGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Video -> GIF (ffmpeg)")
        self.input_path: Optional[str] = None
        self.duration: Optional[float] = None
        self.preview_image = None  # keep ref to avoid GC
        self.temp_dir_obj = None
        self._build_ui()
        self.ffmpeg_ok = check_ffmpeg_available()
        if not self.ffmpeg_ok:
            messagebox.showerror("ffmpeg not found", "ffmpeg or ffprobe not found on PATH. Please install ffmpeg and ensure ffmpeg and ffprobe are available.")
        self._lock = threading.Lock()

    def _build_ui(self):
        frm = ttk.Frame(self.root, padding=10)
        frm.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # File selection
        file_row = ttk.Frame(frm)
        file_row.grid(sticky="ew", pady=(0, 6))
        ttk.Label(file_row, text="Video:").grid(row=0, column=0, sticky="w")
        self.file_label = ttk.Label(file_row, text="(no file selected)", width=60)
        self.file_label.grid(row=0, column=1, sticky="w", padx=(6, 6))
        ttk.Button(file_row, text="Open...", command=self.choose_file).grid(row=0, column=2, sticky="e")

        # Duration
        dur_row = ttk.Frame(frm)
        dur_row.grid(sticky="ew", pady=(0, 6))
        ttk.Label(dur_row, text="Duration:").grid(row=0, column=0, sticky="w")
        self.duration_label = ttk.Label(dur_row, text="Unknown")
        self.duration_label.grid(row=0, column=1, sticky="w", padx=(6, 6))

        # Start / End inputs
        times_row = ttk.Frame(frm)
        times_row.grid(sticky="ew", pady=(0, 6))
        ttk.Label(times_row, text="Start (s or HH:MM:SS):").grid(row=0, column=0, sticky="w")
        self.start_var = tk.StringVar(value="0")
        self.start_entry = ttk.Entry(times_row, textvariable=self.start_var, width=20)
        self.start_entry.grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(times_row, text="End (s or HH:MM:SS):").grid(row=0, column=2, sticky="w")
        self.end_var = tk.StringVar(value="")
        self.end_entry = ttk.Entry(times_row, textvariable=self.end_var, width=20)
        self.end_entry.grid(row=0, column=3, sticky="w", padx=(6, 6))

        # FPS and width
        opts_row = ttk.Frame(frm)
        opts_row.grid(sticky="ew", pady=(0, 6))
        ttk.Label(opts_row, text="FPS:").grid(row=0, column=0, sticky="w")
        self.fps_var = tk.IntVar(value=10)
        ttk.Spinbox(opts_row, from_=1, to=60, textvariable=self.fps_var, width=6).grid(row=0, column=1, sticky="w", padx=(6, 12))
        ttk.Label(opts_row, text="Width (px, optional):").grid(row=0, column=2, sticky="w")
        self.width_var = tk.StringVar(value="")
        ttk.Entry(opts_row, textvariable=self.width_var, width=8).grid(row=0, column=3, sticky="w", padx=(6, 12))

        # Method choice
        method_row = ttk.Frame(frm)
        method_row.grid(sticky="ew", pady=(0, 6))
        ttk.Label(method_row, text="Method:").grid(row=0, column=0, sticky="w")
        self.method_var = tk.StringVar(value="palette")
        ttk.Radiobutton(method_row, text="Palette (best)", variable=self.method_var, value="palette").grid(row=0, column=1, sticky="w", padx=(6,6))
        ttk.Radiobutton(method_row, text="Single-step (faster)", variable=self.method_var, value="single").grid(row=0, column=2, sticky="w", padx=(6,6))

        # Preview and export buttons
        btn_row = ttk.Frame(frm)
        btn_row.grid(sticky="ew", pady=(0, 6))
        ttk.Button(btn_row, text="Preview Frame", command=self.on_preview).grid(row=0, column=0, sticky="w")
        ttk.Button(btn_row, text="Export GIF", command=self.on_export).grid(row=0, column=1, sticky="w", padx=(6,6))
        ttk.Button(btn_row, text="Choose Output...", command=self.choose_output).grid(row=0, column=2, sticky="w", padx=(6,6))

        # Output path
        out_row = ttk.Frame(frm)
        out_row.grid(sticky="ew", pady=(0, 6))
        ttk.Label(out_row, text="Output:").grid(row=0, column=0, sticky="w")
        self.output_var = tk.StringVar(value="")
        ttk.Entry(out_row, textvariable=self.output_var, width=60).grid(row=0, column=1, sticky="w", padx=(6,6))

        # Preview canvas / image
        preview_row = ttk.Frame(frm)
        preview_row.grid(sticky="ew", pady=(0, 6))
        self.canvas = tk.Canvas(preview_row, width=320, height=180, bg="#222")
        self.canvas.grid(row=0, column=0, sticky="w")
        self.canvas_text = self.canvas.create_text(160, 90, text="Preview\n(install Pillow for thumbnails)", fill="white", justify="center")

        # Status/log
        log_row = ttk.Frame(frm)
        log_row.grid(sticky="ew", pady=(6, 0))
        ttk.Label(log_row, text="Status:").grid(row=0, column=0, sticky="nw")
        self.log_text = tk.Text(log_row, height=8, width=80, wrap="word")
        self.log_text.grid(row=0, column=1, sticky="w")
        self.log_text.insert("end", "Ready.\n")
        self.log_text.configure(state="disabled")

    # UI helpers
    def log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def choose_file(self):
        # Use a permissive filetype filter and provide explicit common video type entries.
        # Putting 'All files' first helps macOS Open panel allow selecting files that
        # may not exactly match filter patterns used by the native dialog.
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose video file",
            initialdir=os.path.expanduser("~"),
            filetypes=[
                ("All files", "*.*"),
                ("MP4 files", "*.mp4"),
                ("MOV files", "*.mov"),
                ("MKV files", "*.mkv"),
                ("AVI files", "*.avi"),
                ("WEBM files", "*.webm"),
                ("Video files", ("*.mp4", "*.MP4", "*.mov", "*.MOV", "*.mkv", "*.MKV", "*.avi", "*.AVI", "*.webm", "*.WEBM")),
            ],
        )
        if not path:
            return
        self.input_path = path
        self.file_label.configure(text=path)
        self.log(f"Selected: {path}")
        self.duration = get_video_duration(path)
        if self.duration is not None:
            self.duration_label.configure(text=f"{format_time_seconds(self.duration)} ({self.duration:.2f} s)")
            self.log(f"Duration: {self.duration:.2f} seconds")
            # If end not set, default to duration
            if not self.end_var.get().strip():
                self.end_var.set(f"{self.duration:.3f}")
        else:
            self.duration_label.configure(text="Unknown")
            self.log("Duration: unknown")

    def choose_output(self):
        initial = ""
        if self.input_path:
            base = os.path.splitext(os.path.basename(self.input_path))[0]
            initial = base + ".gif"
        path = filedialog.asksaveasfilename(title="Choose output GIF", defaultextension=".gif", initialfile=initial, filetypes=[("GIF", "*.gif")])
        if path:
            self.output_var.set(path)
            self.log(f"Output set: {path}")

    def on_preview(self):
        if not PIL_AVAILABLE:
            messagebox.showwarning("Pillow not available", "Pillow not installed; preview disabled. Install with: pip install pillow")
            return
        if not self.input_path:
            messagebox.showwarning("No file", "Please choose a video file first.")
            return
        t = parse_time(self.start_var.get())
        if t is None:
            messagebox.showwarning("Invalid start", "Start time is invalid.")
            return
        # Extract frame to a temp file
        td = tempfile.TemporaryDirectory(prefix="v2g_preview_")
        frame_path = os.path.join(td.name, "preview.jpg")
        self.log(f"Extracting frame at {t} s ...")
        ok, msg = extract_frame_to_file(self.input_path, t, frame_path)
        if not ok:
            self.log(f"Preview failed: {msg}")
            td.cleanup()
            return
        try:
            img = Image.open(frame_path)
            # Resize to fit canvas
            canvas_w = int(self.canvas.cget("width"))
            canvas_h = int(self.canvas.cget("height"))
            img.thumbnail((canvas_w, canvas_h), Image.LANCZOS)
            self.preview_image = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_w//2, canvas_h//2, image=self.preview_image)
            self.log("Preview displayed.")
        except Exception as e:
            self.log(f"Preview error: {e}")
        finally:
            td.cleanup()

    def on_export(self):
        if not self.ffmpeg_ok:
            messagebox.showerror("ffmpeg missing", "ffmpeg or ffprobe not found. Install ffmpeg and try again.")
            return
        if not self.input_path:
            messagebox.showwarning("No file", "Please choose a video file first.")
            return
        start = parse_time(self.start_var.get())
        end = parse_time(self.end_var.get())
        if start is None:
            messagebox.showwarning("Invalid start", "Start time invalid.")
            return
        if end is None:
            # If end not provided but duration known, use duration
            if self.duration is not None:
                end = self.duration
                self.end_var.set(f"{end:.3f}")
            else:
                messagebox.showwarning("Invalid end", "End time invalid and video duration unknown.")
                return
        if end <= start:
            messagebox.showwarning("Invalid range", "End time must be greater than start time.")
            return
        # fps
        try:
            fps = int(self.fps_var.get())
            if not (1 <= fps <= 60):
                raise ValueError()
        except Exception:
            messagebox.showwarning("Invalid FPS", "FPS must be an integer between 1 and 60.")
            return
        # width
        width_val = self.width_var.get().strip()
        width = None
        if width_val:
            try:
                width = int(width_val)
                if width <= 0:
                    raise ValueError()
            except Exception:
                messagebox.showwarning("Invalid width", "Width must be a positive integer.")
                return
        out_path = self.output_var.get().strip()
        if not out_path:
            # ask user
            path = filedialog.asksaveasfilename(title="Choose output GIF", defaultextension=".gif", filetypes=[("GIF", "*.gif")])
            if not path:
                return
            out_path = path
            self.output_var.set(out_path)
        # Prepare options
        options = ExportOptions(fps=fps, width=width, method=self.method_var.get())
        # Create temporary working dir
        workdir = tempfile.mkdtemp(prefix="v2g_work_")
        self.log(f"Working directory: {workdir}")
        # Run ffmpeg in a separate thread
        thread = threading.Thread(target=self._export_worker, args=(self.input_path, start, end, options, out_path, workdir))
        thread.daemon = True
        thread.start()

    def _export_worker(self, input_path: str, start: float, end: float, opts: ExportOptions, out_path: str, workdir: str):
        # guard to ensure only one export at a time
        if not self._lock.acquire(blocking=False):
            self.log("Another export is in progress. Please wait.")
            return
        try:
            self.log(f"Starting export: {input_path} [{start} -> {end}] fps={opts.fps} width={opts.width} method={opts.method}")
            self._set_ui_busy(True)
            if opts.method == "palette":
                ok, msg = run_ffmpeg_palette(input_path, start, end, opts.fps, opts.width, out_path, workdir, progress_callback=self._thread_safe_log)
            else:
                ok, msg = run_ffmpeg_single(input_path, start, end, opts.fps, opts.width, out_path, progress_callback=self._thread_safe_log)
            if ok:
                self._thread_safe_log(f"Success: {msg}")
                self._thread_safe_log(f"Output saved to: {out_path}")
                messagebox.showinfo("Export complete", f"GIF exported to:\n{out_path}")
            else:
                self._thread_safe_log(f"Failed: {msg}")
                messagebox.showerror("Export failed", f"{msg}")
        finally:
            # cleanup workdir
            try:
                import shutil
                shutil.rmtree(workdir, ignore_errors=True)
                self._thread_safe_log("Cleaned temporary files.")
            except Exception:
                pass
            self._set_ui_busy(False)
            self._lock.release()

    def _set_ui_busy(self, busy: bool):
        def _set():
            if busy:
                self.root.config(cursor="watch")
            else:
                self.root.config(cursor="")
        try:
            self.root.after(0, _set)
        except Exception:
            pass

    def _thread_safe_log(self, msg: str):
        try:
            self.root.after(0, lambda m=msg: self.log(m))
        except Exception:
            # fallback
            self.log(msg)

def main():
    root = tk.Tk()
    app = VideoToGifGUI(root)
    root.geometry("820x560")
    root.mainloop()

if __name__ == "__main__":
    main()