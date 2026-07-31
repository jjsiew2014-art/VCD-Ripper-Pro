"""
VCD Ripper Pro - A modern VCD video extraction tool for Windows
Uses FFmpeg to rip VCD videos with a premium dark UI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import os
import sys
import json
import time
import re
import shutil
import ctypes
import string
from pathlib import Path
from datetime import datetime


# ─────────────────────────────────────────────
#  Constants & Colour Palette
# ─────────────────────────────────────────────
APP_NAME = "VCD Ripper Pro"
APP_VERSION = "1.2.0"

COLORS = {
    "bg_dark":      "#0D0F14",
    "bg_panel":     "#141720",
    "bg_card":      "#1C2030",
    "bg_hover":     "#242840",
    "accent":       "#6C63FF",
    "accent_hover": "#8B84FF",
    "accent_dim":   "#3D3880",
    "success":      "#22C55E",
    "warning":      "#F59E0B",
    "error":        "#EF4444",
    "text_primary": "#F0F2FF",
    "text_secondary":"#8B93B0",
    "text_muted":   "#4A5270",
    "border":       "#252A40",
    "border_accent":"#4A44AA",
    "progress_bg":  "#1C2030",
    "dat_tag":      "#EC4899",
    "mpg_tag":      "#F59E0B",
    "mp4_tag":      "#22C55E",
    "mov_tag":      "#6C63FF",
}

FONTS = {
    "title":   ("Segoe UI", 26, "bold"),
    "heading": ("Segoe UI", 16, "bold"),
    "subhead": ("Segoe UI", 13, "bold"),
    "body":    ("Segoe UI", 12),
    "small":   ("Segoe UI", 11),
    "mono":    ("Consolas", 11),
    "badge":   ("Segoe UI", 10, "bold"),
}

VCD_DAT_PATHS = ["MPEGAV", "MPEG2"]   # folders inside VCD that hold .DAT files
VCD_MARKER    = "VCD"                  # label to detect VCD type drives

OUTPUT_FORMATS = {
    "DAT": {
        "ext": ".dat",
        "args": [],
        "desc": "Raw direct copy",
        "color": COLORS["dat_tag"],
    },
    "MPG": {
        "ext": ".mpg",
        "args": ["-c:v", "copy", "-c:a", "copy"],
        "desc": "MPEG-1/2 (native VCD stream)",
        "color": COLORS["mpg_tag"],
    },
    "MP4": {
        "ext": ".mp4",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "18",
                 "-c:a", "aac", "-b:a", "192k"],
        "desc": "H.264 + AAC (widely compatible)",
        "color": COLORS["mp4_tag"],
    },
    "MOV": {
        "ext": ".mov",
        "args": ["-c:v", "libx264", "-preset", "fast", "-crf", "18",
                 "-c:a", "aac", "-b:a", "192k"],
        "desc": "QuickTime / Apple compatible",
        "color": COLORS["mov_tag"],
    },
}

AUDIO_FORMATS = {
    "WAV": {
        "ext": ".wav",
        "args": ["-vn", "-acodec", "pcm_s16le", "-ar", "44100"],
        "desc": "Lossless PCM audio",
        "color": COLORS["success"],
    },
    "MP3": {
        "ext": ".mp3",
        "args": ["-vn", "-acodec", "libmp3lame", "-q:a", "2"],
        "desc": "High quality compressed audio",
        "color": COLORS["warning"],
    },
}


# ─────────────────────────────────────────────
#  FFmpeg / FFprobe discovery
# ─────────────────────────────────────────────
def find_ffmpeg():
    """Return paths to ffmpeg and ffprobe, or None if not found."""
    ffmpeg  = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")

    exe_dir = os.path.dirname(sys.executable)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    common = [
        os.path.join(exe_dir, "ffmpeg", "bin"),
        os.path.join(exe_dir, "ffmpeg"),
        exe_dir,
        os.path.join(script_dir, "ffmpeg", "bin"),
        os.path.join(script_dir, "ffmpeg"),
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
    ]
    for d in common:
        if not ffmpeg and os.path.isfile(os.path.join(d, "ffmpeg.exe")):
            ffmpeg = os.path.join(d, "ffmpeg.exe")
        if not ffprobe and os.path.isfile(os.path.join(d, "ffprobe.exe")):
            ffprobe = os.path.join(d, "ffprobe.exe")

    return ffmpeg, ffprobe


# ─────────────────────────────────────────────
#  VCD / Drive detection helpers
# ─────────────────────────────────────────────
def get_cd_drives():
    """Return list of optical drive letters on Windows."""
    drives = []
    try:
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive = f"{letter}:\\"
                dtype = ctypes.windll.kernel32.GetDriveTypeW(drive)
                if dtype == 5:          # DRIVE_CDROM = 5
                    drives.append(drive)
            bitmask >>= 1
    except Exception:
        pass
    return drives


def is_vcd_folder(path):
    """Return True if the given path looks like a VCD structure."""
    path = Path(path)
    # Classic VCD: has MPEGAV or MPEG2 folder with .DAT files
    for sub in VCD_DAT_PATHS:
        sub_path = path / sub
        if sub_path.is_dir():
            if list(sub_path.glob("*.DAT")) or list(sub_path.glob("*.dat")):
                return True
    # Also accept if the path itself contains .DAT files
    if list(path.glob("*.DAT")) or list(path.glob("*.dat")):
        return True
    return False


def find_dat_files(base_path):
    """Return list of unique .DAT file paths from a VCD directory."""
    base = Path(base_path)
    seen = set()
    found = []

    def add_file(p):
        try:
            real_p = p.resolve()
            key = str(real_p).lower()
            if key not in seen and real_p.is_file():
                seen.add(key)
                found.append(str(real_p))
        except Exception:
            pass

    for sub in VCD_DAT_PATHS:
        sub_path = base / sub
        if sub_path.is_dir():
            for p in sorted(sub_path.glob("*.[dD][aA][tT]")):
                add_file(p)
            for p in sorted(sub_path.glob("*.DAT")):
                add_file(p)

    if not found:
        for p in sorted(base.glob("*.[dD][aA][tT]")):
            add_file(p)
        for p in sorted(base.glob("*.DAT")):
            add_file(p)

    return found


def probe_video(ffprobe_path, file_path):
    """Use ffprobe to get video metadata. Returns dict or None."""
    try:
        cmd = [
            ffprobe_path, "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            file_path
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        data = json.loads(result.stdout)
        info = {
            "path":     file_path,
            "filename": Path(file_path).name,
            "size_mb":  round(os.path.getsize(file_path) / 1024**2, 1),
            "duration": 0,
            "width":    0,
            "height":   0,
            "codec":    "unknown",
            "fps":      "?",
            "bitrate":  "?",
        }
        fmt = data.get("format", {})
        if "duration" in fmt:
            info["duration"] = float(fmt["duration"])
        if "bit_rate" in fmt:
            br = int(fmt["bit_rate"])
            info["bitrate"] = f"{br // 1000} kbps"

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["codec"]  = stream.get("codec_name", "unknown").upper()
                info["width"]  = stream.get("width", 0)
                info["height"] = stream.get("height", 0)
                # fps
                fps_str = stream.get("r_frame_rate", "0/1")
                try:
                    n, d = fps_str.split("/")
                    info["fps"] = f"{int(n)//int(d)} fps" if int(d) else "?"
                except Exception:
                    info["fps"] = "?"
                break
        return info
    except Exception:
        return {
            "path":     file_path,
            "filename": Path(file_path).name,
            "size_mb":  round(os.path.getsize(file_path) / 1024**2, 1),
            "duration": 0, "width": 0, "height": 0,
            "codec": "VCD", "fps": "29 fps", "bitrate": "~1150 kbps",
        }


def format_duration(seconds):
    if not seconds:
        return "--:--"
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ─────────────────────────────────────────────
#  Tooltip helper
# ─────────────────────────────────────────────
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text   = text
        self.tip    = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        x, y, _, _ = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            self.tip, text=self.text,
            bg=COLORS["bg_hover"], fg=COLORS["text_primary"],
            font=FONTS["small"], padx=8, pady=4,
            relief="flat", bd=0
        )
        lbl.pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ─────────────────────────────────────────────
#  Animated progress ring canvas widget
# ─────────────────────────────────────────────
class ProgressRing(tk.Canvas):
    def __init__(self, parent, size=48, **kwargs):
        super().__init__(
            parent, width=size, height=size,
            bg=COLORS["bg_card"], highlightthickness=0, **kwargs
        )
        self._size  = size
        self._angle = 0
        self._running = False
        self._arc = None
        self._draw_base()

    def _draw_base(self):
        m = 4
        s = self._size
        self.create_oval(m, m, s - m, s - m,
                         outline=COLORS["accent_dim"], width=4, tags="base")
        self._arc = self.create_arc(
            m, m, s - m, s - m,
            start=90, extent=60,
            outline=COLORS["accent"], width=4,
            style="arc", tags="ring"
        )

    def start(self):
        self._running = True
        self._animate()

    def stop(self):
        self._running = False

    def _animate(self):
        if not self._running:
            return
        self._angle = (self._angle - 8) % 360
        self.itemconfig("ring", start=self._angle)
        self.after(20, self._animate)


# ─────────────────────────────────────────────
#  Flat styled button
# ─────────────────────────────────────────────
class FlatButton(tk.Frame):
    def __init__(self, parent, text, command=None, style="primary",
                 icon="", width=None, **kwargs):
        styles = {
            "primary":  (COLORS["accent"],       COLORS["accent_hover"],  COLORS["text_primary"]),
            "ghost":    (COLORS["bg_card"],       COLORS["bg_hover"],      COLORS["text_primary"]),
            "danger":   (COLORS["error"],         "#FF6666",               COLORS["text_primary"]),
            "success":  (COLORS["success"],       "#30D870",               COLORS["bg_dark"]),
        }
        bg, bg_h, fg = styles.get(style, styles["primary"])
        super().__init__(parent, bg=bg, cursor="hand2", **kwargs)
        self._bg   = bg
        self._bg_h = bg_h
        label_text = f"{icon}  {text}" if icon else text
        self._lbl = tk.Label(
            self, text=label_text, font=FONTS["subhead"],
            bg=bg, fg=fg, padx=16, pady=11
        )
        self._lbl.pack(fill="both", expand=True)
        if width:
            self.configure(width=width)

        for w in (self, self._lbl):
            w.bind("<Enter>",   self._on_enter)
            w.bind("<Leave>",   self._on_leave)
            w.bind("<Button-1>",self._on_click)
        self._command = command

    def _on_enter(self, _=None):
        self.configure(bg=self._bg_h)
        self._lbl.configure(bg=self._bg_h)

    def _on_leave(self, _=None):
        self.configure(bg=self._bg)
        self._lbl.configure(bg=self._bg)

    def _on_click(self, _=None):
        if self._command:
            self._command()

    def configure_state(self, enabled=True):
        if enabled:
            self._lbl.configure(fg=COLORS["text_primary"])
            for w in (self, self._lbl):
                w.bind("<Button-1>", self._on_click)
                w.configure(cursor="hand2")
        else:
            self._lbl.configure(fg=COLORS["text_muted"])
            for w in (self, self._lbl):
                w.unbind("<Button-1>")
                w.configure(cursor="")


# ─────────────────────────────────────────────
#  Video card widget (inside the file list)
# ─────────────────────────────────────────────
class VideoCard(tk.Frame):
    def __init__(self, parent, info, index, on_toggle, **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"],
                         highlightbackground=COLORS["border"],
                         highlightthickness=1, **kwargs)
        self.info      = info
        self.index     = index
        self.on_toggle = on_toggle
        self._selected = False
        self._build()
        self._bind_all()

    def _build(self):
        # Checkbox column
        chk_frame = tk.Frame(self, bg=COLORS["bg_card"], width=56)
        chk_frame.pack(side="left", fill="y")
        chk_frame.pack_propagate(False)
        self._chk_var = tk.BooleanVar(value=False)
        self._chk = tk.Checkbutton(
            chk_frame, variable=self._chk_var,
            bg=COLORS["bg_card"], activebackground=COLORS["bg_hover"],
            fg=COLORS["accent"], selectcolor=COLORS["bg_dark"],
            command=self._toggle, cursor="hand2",
            relief="flat", bd=0
        )
        self._chk.place(relx=0.5, rely=0.5, anchor="center")

        # Content
        content = tk.Frame(self, bg=COLORS["bg_card"], padx=14, pady=14)
        content.pack(side="left", fill="both", expand=True)

        # Row 1: filename + size badge
        row1 = tk.Frame(content, bg=COLORS["bg_card"])
        row1.pack(fill="x")
        self._filename_lbl = tk.Label(
            row1, text=f"📼  {self.info['filename']}",
            font=FONTS["subhead"], bg=COLORS["bg_card"],
            fg=COLORS["text_primary"]
        )
        self._filename_lbl.pack(side="left")
        size_lbl = tk.Label(
            row1, text=f"{self.info['size_mb']} MB",
            font=FONTS["badge"], bg=COLORS["accent_dim"],
            fg=COLORS["text_primary"], padx=8, pady=3
        )
        size_lbl.pack(side="right", padx=(0, 4))

        # Row 2: metadata
        row2 = tk.Frame(content, bg=COLORS["bg_card"])
        row2.pack(fill="x", pady=(6, 0))
        meta = (
            f"⏱  {format_duration(self.info['duration'])}     "
            f"📐 {self.info['width']}×{self.info['height']}     "
            f"🎬 {self.info['codec']}     "
            f"🎞 {self.info['fps']}     "
            f"📊 {self.info['bitrate']}"
        )
        tk.Label(row2, text=meta, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(side="left")

        # Rename button (right side) — larger, visible accent color
        self._rename_btn = tk.Button(
            self, text="✏",
            font=("Segoe UI", 18, "bold"), bg=COLORS["bg_card"],
            fg="#38BDF8", relief="flat", bd=0,
            cursor="hand2", activebackground=COLORS["bg_hover"],
            activeforeground="#7DD3FC",
            command=self._on_rename
        )
        self._rename_btn.pack(side="right", padx=(0, 14), pady=0)

    def _bind_all(self):
        for w in self.winfo_children():
            if w is not self._rename_btn:
                w.bind("<Enter>", self._hover_on)
                w.bind("<Leave>", self._hover_off)
        self.bind("<Enter>", self._hover_on)
        self.bind("<Leave>", self._hover_off)

    def _hover_on(self, _=None):
        if not self._selected:
            self.configure(bg=COLORS["bg_hover"],
                           highlightbackground=COLORS["border_accent"])

    def _hover_off(self, _=None):
        if not self._selected:
            self.configure(bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"])

    def _toggle(self):
        self._selected = self._chk_var.get()
        if self._selected:
            self.configure(highlightbackground=COLORS["accent"])
        else:
            self.configure(highlightbackground=COLORS["border"])
        self.on_toggle(self.index, self._selected)

    def set_selected(self, val: bool):
        self._chk_var.set(val)
        self._selected = val
        self.configure(highlightbackground=COLORS["accent"] if val else COLORS["border"])

    def _on_rename(self):
        """Inline rename dialog — let user pick a new output stem for this file."""
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title("Rename file")
        dlg.configure(bg=COLORS["bg_panel"])
        dlg.resizable(False, False)
        dlg.grab_set()

        stem = Path(self.info["filename"]).stem
        tk.Label(
            dlg, text="Output filename (without extension):",
            font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_secondary"]
        ).pack(padx=24, pady=(20, 6), anchor="w")

        entry_var = tk.StringVar(value=stem)
        entry = tk.Entry(
            dlg, textvariable=entry_var,
            font=FONTS["body"], width=36,
            bg=COLORS["bg_card"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], relief="flat",
            bd=6
        )
        entry.pack(padx=24, pady=(0, 4))
        entry.select_range(0, "end")
        entry.focus_set()

        btn_row = tk.Frame(dlg, bg=COLORS["bg_panel"])
        btn_row.pack(padx=24, pady=(8, 20), fill="x")

        def apply():
            new_stem = entry_var.get().strip()
            if new_stem:
                self.info["custom_stem"] = new_stem
                self._filename_lbl.configure(text=f"📼  {new_stem}  ✏")
            dlg.destroy()

        tk.Button(
            btn_row, text="Apply",
            font=FONTS["body"], bg=COLORS["accent"],
            fg=COLORS["text_primary"], relief="flat", bd=0,
            padx=20, pady=6, cursor="hand2",
            command=apply
        ).pack(side="left", padx=(0, 8))
        tk.Button(
            btn_row, text="Cancel",
            font=FONTS["body"], bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], relief="flat", bd=0,
            padx=20, pady=6, cursor="hand2",
            command=dlg.destroy
        ).pack(side="left")

        dlg.bind("<Return>", lambda e: apply())
        dlg.bind("<Escape>", lambda e: dlg.destroy())

    @property
    def selected(self):
        return self._chk_var.get()


# ─────────────────────────────────────────────
#  Log console widget
# ─────────────────────────────────────────────
class LogConsole(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], **kwargs)
        self._text = tk.Text(
            self, bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            font=FONTS["mono"], relief="flat", bd=0,
            state="disabled", wrap="word", height=3,
            insertbackground=COLORS["accent"]
        )
        sb = ttk.Scrollbar(self, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._text.pack(fill="both", expand=True)

        # Tag colours
        self._text.tag_configure("info",    foreground=COLORS["text_secondary"])
        self._text.tag_configure("success", foreground=COLORS["success"])
        self._text.tag_configure("warning", foreground=COLORS["warning"])
        self._text.tag_configure("error",   foreground=COLORS["error"])
        self._text.tag_configure("accent",  foreground=COLORS["accent"])

    def log(self, message, level="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        icons = {"info": "●", "success": "✓", "warning": "⚠", "error": "✗", "accent": "►"}
        icon = icons.get(level, "●")
        line = f"[{ts}]  {icon}  {message}\n"
        self._text.configure(state="normal")
        self._text.insert("end", line, level)
        self._text.see("end")
        self._text.configure(state="disabled")

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


# ─────────────────────────────────────────────
#  Main Application Window
# ─────────────────────────────────────────────
class VCDRipperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.configure(bg=COLORS["bg_dark"])
        self.geometry("1360x920")
        self.minsize(1100, 750)

        # DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # State
        self._videos: list[dict] = []
        self._cards:  list[VideoCard] = []
        self._selected_indices: set[int] = set()
        self._output_folder    = tk.StringVar(value="")
        self._output_format    = tk.StringVar(value="DAT")
        self._output_mode      = tk.StringVar(value="video")   # "video" or "audio"
        self._audio_format     = tk.StringVar(value="WAV")     # "WAV" or "MP3"
        self._vcd_path         = tk.StringVar(value="")
        self._dat_rename_mp4   = tk.BooleanVar(value=True)   # DAT sub-option: rename to .mp4
        self._use_1080p        = tk.BooleanVar(value=False)  # MP4/MOV resolution: False=original
        self._auto_open_folder = tk.BooleanVar(value=True)   # Auto open folder after rip
        self._ripping          = False
        self._poll_job         = None
        self._sash_initialized = False
        self._cancel_requested = False
        self._current_proc     = None

        # FFmpeg
        self._ffmpeg, self._ffprobe = find_ffmpeg()

        self._build_ui()
        self._apply_ttk_styles()
        self._start_drive_poll()

        # App icon — works for both plain Python and PyInstaller onedir
        try:
            _base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
            _ico  = os.path.join(_base, "CompactDisc.ico")
            if os.path.isfile(_ico):
                self.iconbitmap(_ico)
        except Exception:
            pass

        if not self._ffmpeg:
            self._show_ffmpeg_warning()

    # ── UI Construction ──────────────────────
    def _build_ui(self):
        # Bind configure to position sash reliably on first render
        self.bind("<Configure>", self._on_window_configure)

        # ── Header bar ──────────────────────
        header = tk.Frame(self, bg=COLORS["bg_panel"], height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header, text="VCD Ripper Pro",
            font=FONTS["title"], bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"]
        ).pack(side="left", padx=28, pady=0)

        tk.Label(
            header, text=f"v{APP_VERSION}",
            font=FONTS["body"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        ).pack(side="left", pady=(16, 0))

        # Settings / About button (replaces FFmpeg badge)
        self._about_btn = tk.Button(
            header, text="⚙  About",
            font=FONTS["badge"],
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["accent"],
            relief="flat", bd=0, padx=14, pady=6,
            cursor="hand2",
            command=self._show_about
        )
        self._about_btn.pack(side="right", padx=20)

        # Drive status indicator
        self._drive_lbl = tk.Label(
            header, text="⏺  No disc detected",
            font=FONTS["body"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        )
        self._drive_lbl.pack(side="right", padx=20)

        # ── Main paned layout ────────────────
        self._paned = tk.PanedWindow(
            self, orient="vertical",
            bg=COLORS["bg_dark"], sashwidth=6,
            sashrelief="flat"
        )
        self._paned.pack(fill="both", expand=True, padx=0, pady=0)

        top_frame = tk.Frame(self._paned, bg=COLORS["bg_dark"])
        bot_frame = tk.Frame(self._paned, bg=COLORS["bg_dark"])
        self._paned.add(top_frame, stretch="always", minsize=400)
        self._paned.add(bot_frame, stretch="never", minsize=100)

        # ── Left sidebar (Source & Selection) ──
        left_sidebar = tk.Frame(top_frame, bg=COLORS["bg_panel"], width=280)
        left_sidebar.pack(side="left", fill="y")
        left_sidebar.pack_propagate(False)

        left_scroll_area = tk.Frame(left_sidebar, bg=COLORS["bg_panel"])
        left_scroll_area.pack(fill="both", expand=True)

        left_canvas = tk.Canvas(left_scroll_area, bg=COLORS["bg_panel"], highlightthickness=0)
        left_vsb = ttk.Scrollbar(left_scroll_area, orient="vertical", command=left_canvas.yview)
        left_canvas.configure(yscrollcommand=left_vsb.set)
        left_vsb.pack(side="right", fill="y")

        left_content = tk.Frame(left_canvas, bg=COLORS["bg_panel"])
        left_window = left_canvas.create_window((0, 0), window=left_content, anchor="nw")

        left_content.bind("<Configure>", lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        left_canvas.bind("<Configure>", lambda e: left_canvas.itemconfig(left_window, width=e.width))

        def _on_left_mousewheel(event):
            left_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        left_canvas.bind_all("<MouseWheel>", lambda e: _on_left_mousewheel(e) if "canvas" in str(e.widget).lower() or "frame" in str(e.widget).lower() else None)

        left_canvas.pack(side="left", fill="both", expand=True)
        self._build_left_sidebar(left_content)

        # ── Center content area (VCD Tracks) ──
        content = tk.Frame(top_frame, bg=COLORS["bg_dark"])
        content.pack(side="left", fill="both", expand=True)
        self._build_content(content)

        # ── Right sidebar (Output Format, Output Folder, Rip Controls) ──
        right_sidebar = tk.Frame(top_frame, bg=COLORS["bg_panel"], width=420)
        right_sidebar.pack(side="right", fill="y")
        right_sidebar.pack_propagate(False)

        # Fixed bottom container for "Start Ripping" and "Stop Ripping" buttons
        right_bottom_frame = tk.Frame(right_sidebar, bg=COLORS["bg_panel"])
        right_bottom_frame.pack(side="bottom", fill="x", padx=16, pady=16)

        self._rip_btn = FlatButton(
            right_bottom_frame, text="Start Ripping", icon="⚡",
            style="primary", command=self._start_rip
        )
        self._rip_btn.pack(fill="x", pady=(0, 8))

        self._stop_btn = FlatButton(
            right_bottom_frame, text="Stop Ripping", icon="⏹",
            style="danger", command=self._stop_rip
        )
        self._stop_btn.pack(fill="x")
        self._stop_btn.configure_state(False)

        # Scrollable container for Output Format & Output Folder
        right_scroll_area = tk.Frame(right_sidebar, bg=COLORS["bg_panel"])
        right_scroll_area.pack(side="top", fill="both", expand=True)

        right_canvas = tk.Canvas(right_scroll_area, bg=COLORS["bg_panel"], highlightthickness=0)
        right_vsb = ttk.Scrollbar(right_scroll_area, orient="vertical", command=right_canvas.yview)
        right_canvas.configure(yscrollcommand=right_vsb.set)
        right_vsb.pack(side="right", fill="y")

        right_content = tk.Frame(right_canvas, bg=COLORS["bg_panel"])
        right_window = right_canvas.create_window((0, 0), window=right_content, anchor="nw")

        right_content.bind("<Configure>", lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all")))
        right_canvas.bind("<Configure>", lambda e: right_canvas.itemconfig(right_window, width=e.width))

        def _on_right_mousewheel(event):
            right_canvas.yview_scroll(-1 * (event.delta // 120), "units")
        right_canvas.bind_all("<MouseWheel>", lambda e: _on_right_mousewheel(e) if "canvas" in str(e.widget).lower() or "frame" in str(e.widget).lower() else None)

        right_canvas.pack(side="left", fill="both", expand=True)
        self._build_right_sidebar(right_content)

        # ── Bottom log console ───────────────
        log_header = tk.Frame(bot_frame, bg=COLORS["bg_panel"], height=32)
        log_header.pack(fill="x")
        log_header.pack_propagate(False)
        tk.Label(
            log_header, text="  📋  Console Log",
            font=FONTS["subhead"], bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        ).pack(side="left", pady=6)
        tk.Button(
            log_header, text="Clear",
            font=FONTS["small"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"], bd=0, cursor="hand2",
            activebackground=COLORS["bg_panel"],
            command=lambda: self._log.clear()
        ).pack(side="right", padx=16)

        self._log = LogConsole(bot_frame)
        self._log.pack(fill="both", expand=True)

    def _on_window_configure(self, event):
        if not self._sash_initialized and event.widget == self:
            h = self.winfo_height()
            if h > 300:
                self.after(50, lambda: self._set_initial_sash(h))
                self._sash_initialized = True

    def _set_initial_sash(self, h):
        try:
            curr_h = self.winfo_height() or h
            self._paned.sash_place(0, 0, curr_h - 135)
        except Exception:
            pass

    def _build_left_sidebar(self, parent):
        pad = {"padx": 20}

        # ── Source section ───────────────────
        self._section_label(parent, "SOURCE")

        # Auto-detect display
        detect_card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        detect_card.pack(fill="x", padx=20, pady=(6, 0))

        self._detect_icon = tk.Label(
            detect_card, text="💿", font=("Segoe UI Emoji", 32),
            bg=COLORS["bg_card"]
        )
        self._detect_icon.pack(pady=(14, 0))

        self._detect_label = tk.Label(
            detect_card, text="Insert a VCD disc\nor click Browse",
            font=FONTS["body"], bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], justify="center"
        )
        self._detect_label.pack(pady=(6, 0))

        self._detected_drive_lbl = tk.Label(
            detect_card, text="",
            font=FONTS["subhead"], bg=COLORS["bg_card"],
            fg=COLORS["accent"]
        )
        self._detected_drive_lbl.pack(pady=(4, 12))

        # Manual browse button
        browse_btn = FlatButton(
            parent, text="Browse Folder", icon="📁",
            style="ghost", command=self._browse_source
        )
        browse_btn.pack(fill="x", padx=20, pady=(10, 0))

        # Scan button
        self._scan_btn = FlatButton(
            parent, text="Scan VCD", icon="🔍",
            style="primary", command=self._scan_vcd
        )
        self._scan_btn.pack(fill="x", padx=20, pady=(8, 0))

        # Path display
        self._path_lbl = tk.Label(
            parent, textvariable=self._vcd_path,
            font=FONTS["mono"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"], wraplength=240,
            justify="left"
        )
        self._path_lbl.pack(fill="x", padx=20, pady=(6, 0))

        # ── Separator ───────────────────────
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(
            fill="x", padx=20, pady=12
        )

        # ── Selection section ────────────────
        self._section_label(parent, "SELECTION")

        sel_row = tk.Frame(parent, bg=COLORS["bg_panel"])
        sel_row.pack(fill="x", padx=20, pady=(6, 0))

        FlatButton(
            sel_row, text="All", icon="☑",
            style="ghost", command=self._select_all
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        FlatButton(
            sel_row, text="None", icon="☐",
            style="ghost", command=self._select_none
        ).pack(side="left", fill="x", expand=True)

        self._sel_count_lbl = tk.Label(
            parent, text="0 of 0 selected",
            font=FONTS["body"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        )
        self._sel_count_lbl.pack(padx=20, pady=(6, 12))

    def _build_right_sidebar(self, parent):
        # ── Output section ───────────────────
        self._section_label(parent, "OUTPUT FORMAT")

        # ── Mode toggle: Video / Audio Only (boxed 2-line card) ──
        mode_card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        mode_card.pack(fill="x", padx=20, pady=(8, 0))

        for mode_val, mode_txt, mode_col in [
            ("video", "🎬  Video",      COLORS["accent"]),
            ("audio", "🎵  Audio Only", COLORS["success"]),
        ]:
            tk.Radiobutton(
                mode_card, text=mode_txt,
                variable=self._output_mode, value=mode_val,
                font=("Segoe UI", 11, "bold"),
                bg=COLORS["bg_card"], fg=mode_col,
                selectcolor=COLORS["bg_dark"],
                activebackground=COLORS["bg_card"],
                activeforeground=mode_col,
                cursor="hand2",
                command=self._on_mode_change
            ).pack(anchor="w", padx=16, pady=8)

        # ── Format options container (holds video_panel & audio_panel) ──
        self._fmt_container = tk.Frame(parent, bg=COLORS["bg_panel"])
        self._fmt_container.pack(fill="x", padx=0, pady=(4, 0))

        # ── Video sub-panel ─────────────────
        self._video_panel = tk.Frame(self._fmt_container, bg=COLORS["bg_panel"])
        self._video_panel.pack(fill="x", padx=0, pady=0)

        tk.Label(
            self._video_panel, text="Video Format:",
            font=("Segoe UI", 11, "bold"), bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        ).pack(anchor="w", padx=20, pady=(8, 4))

        fmt_card = tk.Frame(
            self._video_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        fmt_card.pack(fill="x", padx=20, pady=(0, 4))

        for idx, (fmt, info) in enumerate(OUTPUT_FORMATS.items()):
            item_frame = tk.Frame(fmt_card, bg=COLORS["bg_card"])
            item_frame.pack(fill="x", padx=14, pady=(6 if idx == 0 else 4, 6))

            rb = tk.Radiobutton(
                item_frame, text=fmt,
                variable=self._output_format, value=fmt,
                font=("Segoe UI", 12, "bold"),
                bg=COLORS["bg_card"],
                fg=info["color"],
                selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg_card"],
                activeforeground=info["color"],
                cursor="hand2",
                command=self._on_format_change
            )
            rb.pack(anchor="w")

            desc_lbl = tk.Label(
                item_frame, text=info["desc"],
                font=("Segoe UI", 10), bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"], justify="left"
            )
            desc_lbl.pack(anchor="w", padx=(28, 0), pady=(1, 0))

        # DAT sub-option
        self._dat_suboption_frame = tk.Frame(self._video_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"], highlightthickness=1)
        self._dat_suboption_frame.pack(fill="x", padx=20, pady=(6, 0))

        tk.Label(
            self._dat_suboption_frame, text="DAT Output Mode:",
            font=("Segoe UI", 11, "bold"), bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"]
        ).pack(anchor="w", padx=14, pady=(8, 4))

        rb_row = tk.Frame(self._dat_suboption_frame, bg=COLORS["bg_card"])
        rb_row.pack(fill="x", padx=14, pady=(0, 8))

        tk.Radiobutton(
            rb_row, text="Raw .dat  (no changes)",
            variable=self._dat_rename_mp4, value=False,
            font=("Segoe UI", 11), bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        ).pack(anchor="w")

        tk.Radiobutton(
            rb_row, text="Rename to .mp4",
            variable=self._dat_rename_mp4, value=True,
            font=("Segoe UI", 11), bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        ).pack(anchor="w", pady=(4, 0))

        # ── MP4 / MOV resolution sub-panel ──────
        self._res_suboption_frame = tk.Frame(self._video_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"], highlightthickness=1)
        # hidden by default (only shown for MP4/MOV)

        tk.Label(
            self._res_suboption_frame, text="Export Resolution:",
            font=("Segoe UI", 11, "bold"), bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"]
        ).pack(anchor="w", padx=14, pady=(8, 4))

        res_rb_row = tk.Frame(self._res_suboption_frame, bg=COLORS["bg_card"])
        res_rb_row.pack(fill="x", padx=14, pady=(0, 8))

        tk.Radiobutton(
            res_rb_row, text="Original Quality",
            variable=self._use_1080p, value=False,
            font=("Segoe UI", 11, "bold"), bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        ).pack(anchor="w")

        tk.Radiobutton(
            res_rb_row, text="1440×1080  (upscale to 1080p, 4:3)",
            variable=self._use_1080p, value=True,
            font=("Segoe UI", 11, "bold"), bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        ).pack(anchor="w", pady=(6, 0))

        # ── Audio Only sub-panel ─────────────
        self._audio_panel = tk.Frame(self._fmt_container, bg=COLORS["bg_panel"])
        # not packed by default (video is active)

        tk.Label(
            self._audio_panel, text="Audio Format:",
            font=("Segoe UI", 11, "bold"), bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        ).pack(anchor="w", padx=20, pady=(8, 4))

        audio_fmt_card = tk.Frame(
            self._audio_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        audio_fmt_card.pack(fill="x", padx=20, pady=(0, 4))

        for idx, (afmt, ainfo) in enumerate(AUDIO_FORMATS.items()):
            aitem_frame = tk.Frame(audio_fmt_card, bg=COLORS["bg_card"])
            aitem_frame.pack(fill="x", padx=14, pady=(6 if idx == 0 else 4, 6))

            arb = tk.Radiobutton(
                aitem_frame, text=afmt,
                variable=self._audio_format, value=afmt,
                font=("Segoe UI", 12, "bold"),
                bg=COLORS["bg_card"],
                fg=ainfo["color"],
                selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg_card"],
                activeforeground=ainfo["color"],
                cursor="hand2",
                command=self._on_audio_format_change
            )
            arb.pack(anchor="w")

            adesc_lbl = tk.Label(
                aitem_frame, text=ainfo["desc"],
                font=("Segoe UI", 10), bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"], justify="left"
            )
            adesc_lbl.pack(anchor="w", padx=(28, 0), pady=(1, 0))

        # ── Separator ───────────────────────
        tk.Frame(parent, bg=COLORS["border"], height=1).pack(
            fill="x", padx=20, pady=12
        )

        # ── Output folder section ────────────
        self._section_label(parent, "OUTPUT FOLDER")

        out_btn = FlatButton(
            parent, text="Choose Output Folder", icon="💾",
            style="ghost", command=self._choose_output
        )
        out_btn.pack(fill="x", padx=20, pady=(10, 0))

        self._out_lbl = tk.Label(
            parent, textvariable=self._output_folder,
            font=FONTS["mono"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"], wraplength=360,
            justify="left"
        )
        self._out_lbl.pack(fill="x", padx=20, pady=(6, 4))

        tk.Checkbutton(
            parent, text="Open output folder after ripped",
            variable=self._auto_open_folder,
            font=("Segoe UI", 11), bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_panel"],
            cursor="hand2", relief="flat", bd=0
        ).pack(anchor="w", padx=20, pady=(4, 12))

    def _build_content(self, parent):
        # ── Title bar ───────────────────────
        title_bar = tk.Frame(parent, bg=COLORS["bg_dark"], height=56)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        self._content_title = tk.Label(
            title_bar, text="Video Files",
            font=FONTS["heading"], bg=COLORS["bg_dark"],
            fg=COLORS["text_primary"]
        )
        self._content_title.pack(side="left", padx=20, pady=14)

        self._video_count_badge = tk.Label(
            title_bar, text="",
            font=FONTS["badge"], bg=COLORS["accent_dim"],
            fg=COLORS["text_primary"], padx=10, pady=4
        )
        self._video_count_badge.pack(side="left", pady=16)

        # ── Scrollable video list ─────────────
        list_container = tk.Frame(parent, bg=COLORS["bg_dark"])
        list_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._canvas = tk.Canvas(
            list_container, bg=COLORS["bg_dark"],
            highlightthickness=0
        )
        self._vsb = ttk.Scrollbar(
            list_container, orient="vertical",
            command=self._canvas.yview
        )
        self._canvas.configure(yscrollcommand=self._vsb.set)
        self._vsb.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._list_frame = tk.Frame(self._canvas, bg=COLORS["bg_dark"])
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw"
        )
        self._list_frame.bind("<Configure>", self._on_list_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Empty state
        self._empty_frame = tk.Frame(self._list_frame, bg=COLORS["bg_dark"])
        self._empty_frame.pack(fill="both", expand=True, pady=100)
        tk.Label(
            self._empty_frame, text="💿",
            font=("Segoe UI Emoji", 64),
            bg=COLORS["bg_dark"]
        ).pack()
        tk.Label(
            self._empty_frame,
            text="No VCD loaded",
            font=FONTS["heading"], bg=COLORS["bg_dark"],
            fg=COLORS["text_secondary"], justify="center"
        ).pack(pady=(12, 0))
        tk.Label(
            self._empty_frame,
            text="Insert a disc or browse to a VCD folder, then click Scan VCD",
            font=FONTS["body"], bg=COLORS["bg_dark"],
            fg=COLORS["text_muted"], justify="center"
        ).pack(pady=(6, 0))

        # ── Progress bar (hidden initially) ──
        self._progress_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        self._progress_frame.pack(fill="x", padx=8, pady=(0, 4))

        self._progress_lbl = tk.Label(
            self._progress_frame, text="",
            font=FONTS["body"], bg=COLORS["bg_dark"],
            fg=COLORS["text_secondary"]
        )
        self._progress_lbl.pack(side="left", padx=(8, 0))

        self._progress_pct = tk.Label(
            self._progress_frame, text="",
            font=FONTS["body"], bg=COLORS["bg_dark"],
            fg=COLORS["accent"]
        )
        self._progress_pct.pack(side="right", padx=(0, 8))

        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(
            parent, variable=self._progress_var,
            style="Custom.Horizontal.TProgressbar"
        )
        self._progress_bar.pack(fill="x", padx=8, pady=(0, 8))
        self._progress_bar.pack_forget()

    def _section_label(self, parent, text):
        lbl = tk.Label(
            parent, text=text,
            font=FONTS["badge"], bg=COLORS["bg_panel"],
            fg=COLORS["accent"], padx=20
        )
        lbl.pack(fill="x", pady=(18, 0))

    # ── TTK Styles ───────────────────────────
    def _apply_ttk_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor=COLORS["progress_bg"],
            background=COLORS["accent"],
            lightcolor=COLORS["accent"],
            darkcolor=COLORS["accent"],
            bordercolor=COLORS["bg_dark"],
            thickness=8
        )
        style.configure(
            "TScrollbar",
            troughcolor=COLORS["bg_dark"],
            background=COLORS["bg_card"],
            bordercolor=COLORS["bg_dark"],
            arrowcolor=COLORS["text_muted"]
        )

    # ── Drive polling ─────────────────────────
    def _start_drive_poll(self):
        self._poll_drives()

    def _poll_drives(self):
        drives = get_cd_drives()
        if drives:
            detected = []
            for d in drives:
                if is_vcd_folder(d):
                    detected.append(d)
            if detected:
                drive = detected[0]
                if self._vcd_path.get() != drive:
                    self._vcd_path.set(drive)
                    self._detected_drive_lbl.configure(text=f"Drive  {drive[0]}:")
                    self._detect_label.configure(
                        text="VCD detected!", fg=COLORS["success"]
                    )
                    self._drive_lbl.configure(
                        text=f"💿  VCD on {drive[0]}:",
                        fg=COLORS["success"]
                    )
                    self._log.log(f"VCD disc auto-detected at {drive}", "success")
            else:
                if drives:
                    self._drive_lbl.configure(
                        text=f"💿  Drive {drives[0][0]}: (no VCD)",
                        fg=COLORS["warning"]
                    )
        else:
            self._drive_lbl.configure(text="⏺  No disc detected", fg=COLORS["text_muted"])

        self._poll_job = self.after(3000, self._poll_drives)

    # ── Actions ───────────────────────────────
    def _show_about(self):
        """Open the About / Settings dialog."""
        dlg = tk.Toplevel(self)
        dlg.title("About VCD Ripper Pro")
        dlg.configure(bg=COLORS["bg_panel"])
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.geometry("420x480")

        # Center the dialog over the main window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 420) // 2
        y = self.winfo_y() + (self.winfo_height() - 480) // 2
        dlg.geometry(f"420x480+{x}+{y}")

        # ── Logo area ──────────────────────────
        logo_frame = tk.Frame(dlg, bg=COLORS["bg_dark"], height=140)
        logo_frame.pack(fill="x")
        logo_frame.pack_propagate(False)

        try:
            from PIL import Image, ImageTk
            _base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
            _png  = os.path.join(_base, "CompactDisc.png")
            if not os.path.isfile(_png):
                _png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CompactDisc.png")
            if os.path.isfile(_png):
                img = Image.open(_png).convert("RGBA").resize((96, 96), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(logo_frame, image=photo, bg=COLORS["bg_dark"])
                lbl_img.image = photo   # keep reference
                lbl_img.pack(pady=(20, 4))
        except Exception:
            tk.Label(
                logo_frame, text="💿", font=("Segoe UI Emoji", 52),
                bg=COLORS["bg_dark"]
            ).pack(pady=(20, 4))

        # ── Info rows ─────────────────────────
        info_frame = tk.Frame(dlg, bg=COLORS["bg_panel"])
        info_frame.pack(fill="x", padx=32, pady=(16, 0))

        def _row(label, value, val_color=None):
            row = tk.Frame(info_frame, bg=COLORS["bg_panel"])
            row.pack(fill="x", pady=5)
            tk.Label(row, text=label, font=FONTS["small"],
                     bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
                     width=16, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=FONTS["body"],
                     bg=COLORS["bg_panel"],
                     fg=val_color or COLORS["text_primary"]).pack(side="left")

        _row("Application",  APP_NAME)
        _row("Version",      f"v{APP_VERSION}", COLORS["accent"])
        _row("Developer",    "jjsiew2014-art")

        # FFmpeg status row
        ffmpeg_text  = "✓  Ready" if self._ffmpeg else "✗  Not Found"
        ffmpeg_color = COLORS["success"] if self._ffmpeg else COLORS["error"]
        _row("FFmpeg",       ffmpeg_text, ffmpeg_color)

        if self._ffmpeg:
            _row("FFmpeg path", os.path.basename(self._ffmpeg),
                 COLORS["text_secondary"])

        # ── Separator ─────────────────────────
        tk.Frame(dlg, bg=COLORS["border"], height=1).pack(
            fill="x", padx=32, pady=(16, 0)
        )

        # ── Footer ────────────────────────────
        tk.Label(
            dlg, text="MIT License  •  Free to use & distribute",
            font=FONTS["small"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        ).pack(pady=(10, 0))

        # ── Close button ──────────────────────
        tk.Button(
            dlg, text="Close",
            font=FONTS["body"], bg=COLORS["accent"],
            fg=COLORS["text_primary"], relief="flat", bd=0,
            padx=32, pady=8, cursor="hand2",
            activebackground=COLORS["accent_hover"],
            activeforeground=COLORS["text_primary"],
            command=dlg.destroy
        ).pack(pady=(12, 24))

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.bind("<Return>", lambda e: dlg.destroy())

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Select VCD folder")
        if folder:
            self._vcd_path.set(folder)
            if is_vcd_folder(folder):
                self._log.log(f"VCD structure found at {folder}", "success")
                self._detect_label.configure(text="VCD folder selected", fg=COLORS["success"])
            else:
                self._log.log(
                    "Selected folder may not be a standard VCD (no .DAT files found). "
                    "Scanning anyway...", "warning"
                )

    def _scan_vcd(self):
        path = self._vcd_path.get().strip()
        if not path:
            messagebox.showwarning("No source", "Please insert a VCD or browse to a VCD folder first.")
            return
        if not os.path.isdir(path):
            messagebox.showerror("Invalid path", f"Path does not exist:\n{path}")
            return

        self._videos.clear()
        self._clear_list()
        self._log.log(f"Scanning {path} …", "accent")

        def do_scan():
            files = find_dat_files(path)
            if not files:
                # Fallback: look for any video-like files
                exts = [".dat", ".mpg", ".mpeg", ".vob", ".mp4", ".avi"]
                for ext in exts:
                    files.extend(
                        str(p) for p in Path(path).rglob(f"*{ext}")
                    )
            return files

        def after_scan(files):
            if not files:
                self._log.log("No video files found in selected path.", "warning")
                messagebox.showinfo(
                    "No files found",
                    "No VCD video files (.DAT) were found.\n"
                    "Make sure you selected the root of a VCD disc or folder."
                )
                return

            self._log.log(f"Found {len(files)} file(s). Reading metadata…", "info")
            self._video_count_badge.configure(text=f"  {len(files)}  ")

            def probe_all():
                infos = []
                for f in files:
                    if self._ffprobe:
                        info = probe_video(self._ffprobe, f)
                    else:
                        info = {
                            "path":     f,
                            "filename": Path(f).name,
                            "size_mb":  round(os.path.getsize(f) / 1024**2, 1),
                            "duration": 0, "width": 352, "height": 240,
                            "codec": "MPEG1", "fps": "29 fps", "bitrate": "~1150 kbps",
                        }
                    infos.append(info)
                    self.after(0, lambda i=info: self._log.log(
                        f"  {i['filename']}  —  {i['size_mb']} MB  {format_duration(i['duration'])}", "info"
                    ))
                self.after(0, lambda: self._populate_list(infos))

            threading.Thread(target=probe_all, daemon=True).start()

        threading.Thread(
            target=lambda: self.after(0, lambda: after_scan(do_scan())),
            daemon=True
        ).start()

    def _populate_list(self, infos):
        self._videos = infos
        self._cards.clear()
        self._selected_indices.clear()
        self._clear_list()

        if self._empty_frame.winfo_exists():
            self._empty_frame.pack_forget()

        for i, info in enumerate(infos):
            card = VideoCard(
                self._list_frame, info, i,
                on_toggle=self._on_card_toggle
            )
            card.pack(fill="x", padx=4, pady=3)
            self._cards.append(card)

        # Auto-select all videos by default
        self._select_all()
        self._log.log(f"Loaded {len(infos)} video(s) from VCD. All selected.", "success")

    def _clear_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()

    def _on_card_toggle(self, index, selected):
        if selected:
            self._selected_indices.add(index)
        else:
            self._selected_indices.discard(index)
        self._update_sel_count()

    def _select_all(self):
        for i, card in enumerate(self._cards):
            card.set_selected(True)
            self._selected_indices.add(i)
        self._update_sel_count()

    def _select_none(self):
        for card in self._cards:
            card.set_selected(False)
        self._selected_indices.clear()
        self._update_sel_count()

    def _update_sel_count(self):
        n = len(self._selected_indices)
        total = len(self._videos)
        self._sel_count_lbl.configure(
            text=f"{n} of {total} selected",
            fg=COLORS["accent"] if n else COLORS["text_muted"]
        )

    def _choose_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self._output_folder.set(folder)
            self._log.log(f"Output folder set: {folder}", "info")

    def _on_format_change(self):
        fmt = self._output_format.get()
        if fmt == "DAT":
            self._dat_suboption_frame.pack(fill="x", padx=20, pady=(6, 0))
        else:
            self._dat_suboption_frame.pack_forget()
        # Show resolution panel only for MP4 and MOV
        if fmt in ("MP4", "MOV"):
            self._res_suboption_frame.pack(fill="x", padx=20, pady=(6, 0))
        else:
            self._res_suboption_frame.pack_forget()

    def _on_audio_format_change(self):
        pass

    def _on_mode_change(self):
        mode = self._output_mode.get()
        if mode == "video":
            self._audio_panel.pack_forget()
            self._video_panel.pack(fill="x", padx=0, pady=0)
        else:
            self._video_panel.pack_forget()
            self._audio_panel.pack(fill="x", padx=0, pady=0)

    # ── Ripping logic ─────────────────────────
    def _stop_rip(self):
        if not self._ripping:
            return
        self._cancel_requested = True
        self._log.log("Cancellation requested by user… Stopping process.", "warning")
        if self._current_proc and self._current_proc.poll() is None:
            try:
                self._current_proc.terminate()
            except Exception:
                pass
        self._stop_btn.configure_state(False)

    def _start_rip(self):
        if self._ripping:
            return

        mode = self._output_mode.get()
        if mode == "audio":
            fmt     = self._audio_format.get()
            fmt_cfg = AUDIO_FORMATS[fmt]
        else:
            fmt     = self._output_format.get()
            fmt_cfg = OUTPUT_FORMATS[fmt]

        needs_ffmpeg = (mode == "audio") or (fmt not in ("DAT",))
        if needs_ffmpeg and not self._ffmpeg:
            messagebox.showerror(
                "FFmpeg not found",
                "FFmpeg is required for audio extraction and video conversion.\n\n"
                "Download from https://ffmpeg.org/download.html and ensure\n"
                "ffmpeg.exe is in your PATH or in a 'ffmpeg/bin' folder next to this script.\n\n"
                "Tip: Select 'DAT' video format to extract raw files without FFmpeg."
            )
            return

        selected = sorted(self._selected_indices)
        if not selected:
            if self._videos:
                if messagebox.askyesno(
                    "No selection",
                    "No videos selected. Rip all videos?"
                ):
                    self._select_all()
                    selected = list(range(len(self._videos)))
                else:
                    return
            else:
                messagebox.showwarning("No videos", "Please scan a VCD first.")
                return

        out_folder = self._output_folder.get().strip()
        if not out_folder:
            out_folder = filedialog.askdirectory(title="Select output folder")
            if not out_folder:
                return
            self._output_folder.set(out_folder)

        os.makedirs(out_folder, exist_ok=True)
        videos_to_rip = [self._videos[i] for i in selected]

        self._ripping = True
        self._cancel_requested = False
        self._current_proc = None

        self._rip_btn.configure_state(False)
        self._stop_btn.configure_state(True)
        self._progress_bar.pack(fill="x", padx=8, pady=(0, 8))
        self._progress_var.set(0)
        self._log.log(
            f"Starting extraction of {len(videos_to_rip)} file(s) → {fmt} format…",
            "accent"
        )

        threading.Thread(
            target=self._rip_thread,
            args=(videos_to_rip, out_folder, fmt, fmt_cfg, self._use_1080p.get()),
            daemon=True
        ).start()

    def _rip_thread(self, videos, out_folder, fmt, fmt_cfg, use_1080p=False):
        total   = len(videos)
        success = 0
        errors  = 0
        was_cancelled = False

        for i, video in enumerate(videos):
            if self._cancel_requested:
                was_cancelled = True
                break

            raw_stem = Path(video["filename"]).stem
            stem = video.get("custom_stem") or raw_stem
            # For DAT video: use .dat or .mp4 based on user sub-option
            if fmt == "DAT" and self._output_mode.get() == "video":
                out_ext = ".mp4" if self._dat_rename_mp4.get() else ".dat"
            else:
                out_ext = fmt_cfg["ext"]
            out_name = f"{stem}{out_ext}"
            out_path = os.path.join(out_folder, out_name)

            # Avoid overwriting
            if os.path.exists(out_path):
                base, ext = os.path.splitext(out_path)
                out_path  = f"{base}_{int(time.time())}{ext}"

            self.after(0, lambda v=video, idx=i: (
                self._progress_lbl.configure(
                    text=f"Processing {idx+1}/{total}: {v['filename']}"
                ),
                self._progress_pct.configure(text=f"{int((idx/total)*100)}%"),
                self._progress_var.set((idx / total) * 100)
            ))
            self.after(0, lambda v=video: self._log.log(
                f"Extracting: {v['filename']} → {os.path.basename(out_path)}", "info"
            ))

            if fmt == "DAT" and self._output_mode.get() == "video":
                # Direct binary file copy without FFmpeg
                try:
                    src_path = video["path"]
                    chunk_size = 1024 * 1024  # 1MB chunk
                    file_cancelled = False
                    with open(src_path, "rb") as fsrc, open(out_path, "wb") as fdst:
                        while True:
                            if self._cancel_requested:
                                file_cancelled = True
                                break
                            buf = fsrc.read(chunk_size)
                            if not buf:
                                break
                            fdst.write(buf)

                    if file_cancelled or self._cancel_requested:
                        was_cancelled = True
                        if os.path.exists(out_path):
                            try:
                                os.remove(out_path)
                            except Exception:
                                pass
                        break

                    size = round(os.path.getsize(out_path) / 1024**2, 1)
                    success += 1
                    self.after(0, lambda n=out_name, s=size: self._log.log(
                        f"✓  Extracted raw DAT → Saved as: {n}  ({s} MB)", "success"
                    ))
                except Exception as e:
                    errors += 1
                    self.after(0, lambda err=str(e): self._log.log(
                        f"Direct copy error: {err}", "error"
                    ))
            else:
                # Use FFmpeg to convert/rip video
                # Build args — optionally inject 1080p downscale filter
                ffmpeg_args = list(fmt_cfg["args"])
                if use_1080p and fmt in ("MP4", "MOV"):
                    # Upscale VCD (352x240 / 352x288) to 1440x1080 (4:3 at 1080p)
                    # using Lanczos for sharpest quality upscale
                    ffmpeg_args = ["-vf", "scale=1440:1080:flags=lanczos"] + ffmpeg_args
                cmd = [
                    self._ffmpeg,
                    "-i", video["path"],
                    *ffmpeg_args,
                    "-y",
                    out_path
                ]

                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self._current_proc = proc

                    # Stream FFmpeg output
                    for line in proc.stdout:
                        if self._cancel_requested:
                            try:
                                proc.terminate()
                            except Exception:
                                pass
                            break
                        line = line.strip()
                        if line and ("frame=" in line or "speed=" in line):
                            self.after(0, lambda l=line: self._log.log(l, "info"))

                    proc.wait()
                    self._current_proc = None

                    if self._cancel_requested:
                        was_cancelled = True
                        if os.path.exists(out_path):
                            try:
                                os.remove(out_path)
                            except Exception:
                                pass
                        break

                    if proc.returncode == 0:
                        size = round(os.path.getsize(out_path) / 1024**2, 1)
                        success += 1
                        self.after(0, lambda n=out_name, s=size: self._log.log(
                            f"✓  Saved: {n}  ({s} MB)", "success"
                        ))
                    else:
                        errors += 1
                        self.after(0, lambda v=video: self._log.log(
                            f"FFmpeg error processing: {v['filename']}", "error"
                        ))

                except Exception as e:
                    errors += 1
                    self.after(0, lambda err=str(e): self._log.log(
                        f"Exception: {err}", "error"
                    ))

        # Done
        self.after(0, lambda: self._rip_done(total, success, errors, out_folder, was_cancelled or self._cancel_requested))

    def _rip_done(self, total, success, errors, out_folder, cancelled=False):
        self._ripping = False
        self._current_proc = None
        self._rip_btn.configure_state(True)
        self._stop_btn.configure_state(False)

        if cancelled:
            self._progress_lbl.configure(text=f"Stopped: {success}/{total} files saved")
            self._log.log(f"Extraction stopped by user. {success} file(s) completed.", "warning")
            messagebox.showinfo(
                "Task Stopped",
                f"Ripping task was stopped by user.\n\n{success} video(s) were saved to:\n{out_folder}"
            )
        elif errors == 0:
            self._progress_var.set(100)
            self._progress_lbl.configure(text=f"Completed: {success}/{total} files ripped")
            self._progress_pct.configure(text="100%")
            self._log.log(
                f"All {success} file(s) ripped successfully! Output: {out_folder}",
                "success"
            )
            # Auto-open output folder if checked
            if self._auto_open_folder.get():
                try:
                    os.startfile(out_folder)
                except Exception as e:
                    self._log.log(f"Could not open output folder: {e}", "warning")

            # Only prompt to eject disc
            if messagebox.askyesno(
                "Eject Disc?",
                f"Successfully ripped {success} file(s)!\n\nWould you like to eject the disc now?"
            ):
                self._eject_drive_f()
        else:
            self._log.log(
                f"Completed with {errors} error(s). {success} file(s) saved to {out_folder}",
                "warning"
            )
            messagebox.showwarning(
                "Completed with errors",
                f"Ripped {success} file(s) successfully.\n"
                f"{errors} file(s) had errors — check the console log."
            )

    # ── Canvas scroll helpers ─────────────────
    def _on_list_configure(self, _):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # ── Drive eject & Reset ───────────────────
    def _clear_disc_info(self):
        """Reset and clear all scanned disc tracks and drive info UI."""
        self._videos.clear()
        self._cards.clear()
        self._selected_indices.clear()
        self._vcd_path.set("")

        self._clear_list()
        if hasattr(self, "_empty_frame") and self._empty_frame.winfo_exists():
            self._empty_frame.pack(expand=True, pady=80)

        self._drive_lbl.configure(text="⏺  No disc detected", fg=COLORS["text_muted"])
        self._detect_icon.configure(text="💿")
        self._detect_label.configure(text="Insert a VCD disc\nor click Browse", fg=COLORS["text_muted"])
        self._detected_drive_lbl.configure(text="")
        self._video_count_badge.configure(text="0 tracks detected")
        self._sel_count_lbl.configure(text="0 of 0 selected")

        self._log.log("Disc information cleared.", "info")

    def _eject_drive_f(self):
        """Eject the optical disc in drive F: using Windows Shell COM API and clear disc info."""
        try:
            ps_cmd = (
                "(New-Object -ComObject Shell.Application)"
                ".Namespace(17).ParseName('F:').InvokeVerb('Eject')"
            )
            subprocess.Popen(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-Command", ps_cmd],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            self._log.log("Eject command sent to drive F:", "info")
        except Exception as e:
            self._log.log(f"Eject failed: {e}", "error")
            messagebox.showwarning(
                "Eject failed",
                f"Could not eject drive F:\n{e}"
            )
        finally:
            # Auto clear disc information UI
            self._clear_disc_info()

    # ── FFmpeg warning ────────────────────────
    def _show_ffmpeg_warning(self):
        self._log.log(
            "FFmpeg not found! Download from https://ffmpeg.org and add to PATH.", "error"
        )
        self._log.log(
            "Or place ffmpeg.exe in a 'ffmpeg/bin' subfolder next to this script.", "warning"
        )

    def on_close(self):
        if self._poll_job:
            self.after_cancel(self._poll_job)
        self.destroy()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = VCDRipperApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
