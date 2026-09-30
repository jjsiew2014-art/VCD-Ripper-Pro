"""
VCD Ripper Pro - A modern VCD video extraction tool for Windows
Uses FFmpeg to rip VCD videos with a premium dark UI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
import queue
import atexit
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
APP_VERSION = "1.3.0"

THEME_DARK = {
    "bg_dark":        "#0D0F14",
    "bg_panel":       "#141720",
    "bg_card":        "#1C2030",
    "bg_hover":       "#242840",
    "accent":         "#6C63FF",
    "accent_hover":   "#8B84FF",
    "accent_dim":     "#3D3880",
    "success":        "#22C55E",
    "warning":        "#F59E0B",
    "error":          "#EF4444",
    "cyan":           "#06B6D4",
    "text_primary":   "#F0F2FF",
    "text_secondary": "#8B93B0",
    "text_muted":     "#4A5270",
    "border":         "#252A40",
    "border_accent":  "#4A44AA",
    "progress_bg":    "#1C2030",
    "dat_tag":        "#EC4899",
    "mpg_tag":        "#F59E0B",
    "mp4_tag":        "#22C55E",
    "mov_tag":        "#6C63FF",
    "btn_primary_fg": "#F0F2FF",
    "badge_fg":       "#F0F2FF",
    "rename_btn":     "#38BDF8",
    "rename_btn_hover": "#7DD3FC",
}

THEME_LIGHT = {
    "bg_dark":        "#F1F5F9",
    "bg_panel":       "#FFFFFF",
    "bg_card":        "#F8FAFC",
    "bg_hover":       "#E2E8F0",
    "accent":         "#5B50E5",
    "accent_hover":   "#4B40D4",
    "accent_dim":     "#EEF2FF",
    "success":        "#16A34A",
    "warning":        "#D97706",
    "error":          "#DC2626",
    "cyan":           "#0891B2",
    "text_primary":   "#0F172A",
    "text_secondary": "#475569",
    "text_muted":     "#94A3B8",
    "border":         "#E2E8F0",
    "border_accent":  "#A5B4FC",
    "progress_bg":    "#E2E8F0",
    "dat_tag":        "#DB2777",
    "mpg_tag":        "#D97706",
    "mp4_tag":        "#16A34A",
    "mov_tag":        "#5B50E5",
    "btn_primary_fg": "#FFFFFF",
    "badge_fg":       "#4338CA",
    "rename_btn":     "#0284C7",
    "rename_btn_hover": "#0369A1",
}

COLORS = dict(THEME_DARK)

def get_windows_theme():
    """Detects whether Windows system app theme is light or dark using registry."""
    if sys.platform != "win32":
        return "dark"
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if val == 1 else "dark"
    except Exception:
        return "dark"

def set_window_dark_mode(hwnd, dark=True):
    """Sets the Windows DWM immersive dark mode attribute for the window title bar."""
    if sys.platform != "win32" or not hwnd:
        return False
    try:
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        val = ctypes.c_int(1 if dark else 0)
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(val),
            ctypes.sizeof(val)
        )
        if res != 0:
            # Fallback for Windows 10 builds before 19041 (1809~1909)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                19,
                ctypes.byref(val),
                ctypes.sizeof(val)
            )
        return True
    except Exception:
        return False

def apply_theme_palette(theme_name):
    palette = THEME_LIGHT if theme_name == "light" else THEME_DARK
    COLORS.update(palette)
    for fmt, key in [("DAT", "dat_tag"), ("MPG", "mpg_tag"), ("MP4", "mp4_tag"), ("MOV", "mov_tag")]:
        if fmt in OUTPUT_FORMATS:
            OUTPUT_FORMATS[fmt]["color"] = COLORS[key]
    if "WAV" in AUDIO_FORMATS:
        AUDIO_FORMATS["WAV"]["color"] = COLORS["success"]
    if "MP3" in AUDIO_FORMATS:
        AUDIO_FORMATS["MP3"]["color"] = COLORS["warning"]

BASE_FONTS = {
    "title":       ("Segoe UI", 26, "bold"),
    "heading":     ("Segoe UI", 16, "bold"),
    "subhead":     ("Segoe UI", 13, "bold"),
    "body":        ("Segoe UI", 12, "normal"),
    "body_bold":   ("Segoe UI", 12, "bold"),
    "small":       ("Segoe UI", 11, "normal"),
    "small_bold":  ("Segoe UI", 11, "bold"),
    "mono":        ("Consolas", 11, "normal"),
    "badge":       ("Segoe UI", 10, "bold"),
    "tiny":        ("Segoe UI", 10, "normal"),
    "rename_btn":  ("Segoe UI", 18, "bold"),
    "emoji_32":    ("Segoe UI Emoji", 32, "normal"),
    "emoji_38":    ("Segoe UI Emoji", 38, "normal"),
    "emoji_64":    ("Segoe UI Emoji", 64, "normal"),
}

FONTS = {k: (spec[0], spec[1], spec[2] if len(spec) > 2 else "normal") for k, spec in BASE_FONTS.items()}

def scale_val(val, scale=None):
    if scale is None:
        try:
            scale = i18n.get_scale_factor()
        except Exception:
            scale = 1.0
    return max(1, int(round(val * scale)))

def apply_font_scale(root, scale=1.0):
    import tkinter.font as tkFont
    for k, spec in BASE_FONTS.items():
        fam, size = spec[0], spec[1]
        weight = spec[2] if len(spec) > 2 else "normal"
        scaled_size = max(8, int(round(size * scale)))
        if k in FONTS and isinstance(FONTS[k], tkFont.Font):
            try:
                FONTS[k].configure(size=scaled_size)
            except Exception:
                pass
        else:
            try:
                FONTS[k] = tkFont.Font(root, family=fam, size=scaled_size, weight=weight)
            except Exception:
                FONTS[k] = (fam, scaled_size, weight)


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
#  I18n System
# ─────────────────────────────────────────────
TRANSLATIONS = {
    "en": {
        "header": {
            "title": "VCD Ripper Pro",
            "console": "📋  Console",
            "clear_all": "🗑  Clear All",
            "clear_all_tip": "Clear loaded video files and progress",
            "about": "⚙  Setting",
            "batch_rename": "✏  Batch Rename",
            "eject_disc": "⏏  Eject Disc",
            "no_disc": "⏺  No disc detected",
            "vcd_on": "💿  VCD on {drive}:",
            "drive_no_vcd": "💿  Drive {drive}: (no VCD)",
        },
        "drive": {
            "detect_vcd": "VCD detected!",
            "insert_vcd": "Insert a VCD disc\nor click Browse",
            "folder_selected": "VCD folder selected",
            "drive_label": "Drive  {drive}:",
        },
        "source": {
            "title": "SOURCE",
            "browse": "Browse Folder",
            "scan": "Scan VCD",
        },
        "selection": {
            "title": "SELECTION",
            "all": "All",
            "none": "None",
            "count": "{n} of {total} selected",
        },
        "format": {
            "title": "OUTPUT FORMAT",
            "video_mode": "🎬  Video",
            "audio_mode": "🎵  Audio Only",
            "video_lbl": "Video Format:",
            "dat_desc": "Raw direct copy",
            "mpg_desc": "MPEG-1/2 (native VCD stream)",
            "mp4_desc": "H.264 + AAC (widely compatible)",
            "mov_desc": "QuickTime / Apple compatible",
            "dat_mode_lbl": "DAT Output Mode:",
            "dat_raw": "Raw .dat  (no changes)",
            "dat_mp4": "Rename to .mp4",
            "res_title": "Export Resolution:",
            "res_orig": "Original Quality",
            "res_1080p": "1440×1080  (upscale to 1080p, 4:3)",
            "audio_lbl": "Audio Format:",
            "wav_desc": "Lossless PCM audio",
            "mp3_desc": "High quality compressed audio",
        },
        "output": {
            "title": "OUTPUT FOLDER",
            "choose": "Choose Output Folder",
            "auto_open": "Open output folder after ripped",
        },
        "rip": {
            "start": "Start Ripping",
            "stop": "Stop Ripping",
        },
        "content": {
            "title": "Video Files",
            "badge": "  {n}  ",
            "badge_empty": "0 tracks detected",
            "empty_title": "No VCD loaded",
            "empty_sub": "Insert a disc or browse to a VCD folder, then click Scan VCD",
            "scan_prog_folder": "Scanning folder: {name}...",
            "scan_prog_read": "Reading metadata ({idx}/{total}): {name}",
            "rip_prog_proc": "Processing {idx}/{total}: {name}",
            "rip_prog_stop": "Stopped: {success}/{total} files saved",
            "rip_prog_done": "Completed: {success}/{total} files ripped",
        },
        "console": {
            "title": "  📋  Console Log",
            "clear": "Clear",
        },
        "about": {
            "title": "Setting",
            "app": "Application",
            "version": "Version",
            "dev": "Developer",
            "ffmpeg": "FFmpeg status",
            "ffmpeg_path": "FFmpeg path",
            "ready": "✓  Ready",
            "not_found": "✗  Not Found",
            "license": "MIT License",
            "close": "Close",
        },
        "language": {
            "title": "Language",
            "en": "English",
            "zh": "中文",
        },
        "appearance": {
            "title": "Appearance",
            "system": "System",
            "light": "Light Mode",
            "dark": "Dark Mode",
        },
        "scale": {
            "title": "Scale",
            "100": "100%",
            "125": "125%",
            "150": "150%",
            "100%": "100%",
            "125%": "125%",
            "150%": "150%",
        },
        "rename": {
            "title": "Rename file",
            "inst": "Output filename (without extension):",
            "apply": "Apply",
            "cancel": "Cancel",
        },
        "batch": {
            "title": "Batch Rename",
            "header": "Batch Rename Files",
            "inst": "Edit output filenames below (without extension):",
            "track": "Track {n}:",
            "apply_all": "Apply All",
            "cancel": "Cancel",
            "no_files_title": "No Files",
            "no_files_msg": "No files to rename. Please scan a VCD first.",
            "seq_enable": "Enable Sequential Numbering",
            "seq_base": "Base Name:",
            "seq_start": "Start Index:",
            "seq_suffix": "Suffix:",
            "seq_preview": "Preview:",
        },
        "messageboxes": {
            "no_source_title": "No source",
            "no_source_msg": "Please insert a VCD or browse to a VCD folder first.",
            "invalid_path_title": "Invalid path",
            "invalid_path_msg": "Path does not exist:\n{path}",
            "no_files_title": "No files found",
            "no_files_msg": "No VCD video files (.DAT) were found.\nMake sure you selected the root of a VCD disc or folder.",
            "ffmpeg_req_title": "FFmpeg not found",
            "ffmpeg_req_msg": "FFmpeg is required for audio extraction and video conversion.\n\nDownload from https://ffmpeg.org/download.html and ensure\nffmpeg.exe is in your PATH or in a 'ffmpeg/bin' folder next to this script.\n\nTip: Select 'DAT' video format to extract raw files without FFmpeg.",
            "no_sel_title": "No selection",
            "no_sel_msg": "No videos selected. Rip all videos?",
            "no_vid_title": "No videos",
            "no_vid_msg": "Please scan a VCD first.",
            "stop_title": "Task Stopped",
            "stop_msg": "Ripping task was stopped by user.\n\n{success} video(s) were saved to:\n{folder}",
            "eject_title": "Eject Disc?",
            "eject_msg": "Successfully ripped {success} file(s)!\n\nWould you like to eject the disc now?",
            "err_title": "Completed with errors",
            "err_msg": "Ripped {success} file(s) successfully.\n{errors} file(s) had errors — check the console log.",
            "no_drive_title": "No Disc Drive",
            "no_drive_msg": "No optical disc drive was detected.",
            "eject_fail_title": "Eject Failed",
            "eject_fail_msg": "Could not eject drive {drive}:\n{err}",
            "ejecting": "Ejecting disc from drive {drive}:...",
            "unsupported_disc_title": "Unsupported Disc Format",
            "unsupported_disc_msg": "The detected optical disc is not a valid VCD (e.g., Audio CD or DVD). This app is specifically designed for VCD ripping.",
            "timeout_title": "Disc Read Timeout",
            "timeout_msg": "Ripping was stopped due to severely damaged disc sectors or read timeout. Partial video has been saved.",
            "btn_ok": "OK",
            "btn_eject": "Eject Disc",
        },
        "log": {
            "non_vcd_blocked": "Disc detected in drive {drive}, type: {type}, blocking process.",
            "vcd_auto": "VCD disc auto-detected at {drive}",
            "vcd_found": "VCD structure found at {folder}",
            "vcd_not_std": "Selected folder may not be a standard VCD (no .DAT files found). Scanning anyway...",
            "scan_dir": "Scanning {path} …",
            "no_vid": "No video files found in selected path.",
            "found_files": "Found {total} file(s). Reading metadata…",
            "loaded": "Loaded {total} video(s) from VCD. All selected.",
            "out_set": "Output folder set: {folder}",
            "cancel_req": "Cancellation requested by user… Stopping process.",
            "start_ext": "Starting extraction of {total} file(s) → {fmt} format…",
            "extracting": "Extracting: {name} → {out}",
            "raw_dat_ok": "✓  Extracted raw DAT → Saved as: {name}  ({size} MB)",
            "copy_err": "Direct copy error: {err}",
            "saved_ok": "✓  Saved: {name}  ({size} MB)",
            "saved_partial": "⚠  Preserved partial video: {name}  ({size} MB)",
            "read_timeout": "Disc read timed out on {name} ({timeout}s without data). Terminating process.",
            "ffmpeg_err": "FFmpeg error processing: {name}",
            "exc": "Exception: {err}",
            "stop_sum": "Extraction stopped by user. {success} file(s) completed.",
            "done_ok": "All {success} file(s) ripped successfully! Output: {folder}",
            "open_err": "Could not open output folder: {err}",
            "done_err": "Completed with {errors} error(s). {success} file(s) saved to {folder}",
            "cleared": "Disc information cleared.",
            "cleared_all": "Cleared video files and progress.",
            "eject_win32": "Disc ejected from drive {drive}: (DeviceIoControl)",
            "eject_win32_fail": "DeviceIoControl eject failed: {err}",
            "eject_ps": "Eject command sent to drive {drive}: (PowerShell)",
            "eject_ps_fail": "PowerShell eject also failed: {err}",
            "batch_renamed": "Batch renamed {total} file(s).",
            "ffmpeg_dl": "FFmpeg not found! Download from https://ffmpeg.org and add to PATH.",
            "ffmpeg_hint": "Or place ffmpeg.exe in a 'ffmpeg/bin' subfolder next to this script.",
        }
    },
    "zh_CN": {
        "header": {
            "title": "VCD Ripper Pro",
            "console": "📋  控制台",
            "clear_all": "🗑  清空",
            "clear_all_tip": "清空已加载的影片列表与进度",
            "about": "⚙  设置",
            "batch_rename": "✏  批量重命名",
            "eject_disc": "⏏  弹出光盘",
            "no_disc": "⏺  未检测到光盘",
            "vcd_on": "💿  VCD 位于 {drive}:",
            "drive_no_vcd": "💿  驱动器 {drive}: (无 VCD)",
        },
        "drive": {
            "detect_vcd": "检测到 VCD！",
            "insert_vcd": "插入 VCD 光盘\n或点击浏览",
            "folder_selected": "已选择 VCD 文件夹",
            "drive_label": "驱动器  {drive}:",
        },
        "source": {
            "title": "来源",
            "browse": "浏览文件夹",
            "scan": "扫描 VCD",
        },
        "selection": {
            "title": "选择",
            "all": "全选",
            "none": "取消全选",
            "count": "已选择 {n} / {total}",
        },
        "format": {
            "title": "输出格式",
            "video_mode": "🎬  视频",
            "audio_mode": "🎵  仅音频",
            "video_lbl": "视频格式：",
            "dat_desc": "原始档案",
            "mpg_desc": "MPEG-1/2 (原生 VCD)",
            "mp4_desc": "H.264 + AAC (广泛兼容)",
            "mov_desc": "QuickTime / 苹果兼容",
            "dat_mode_lbl": "DAT 输出模式：",
            "dat_raw": "原始 .dat",
            "dat_mp4": "重命名为 .mp4",
            "res_title": "导出分辨率：",
            "res_orig": "原始画质",
            "res_1080p": "1440×1080 (拉伸至 1080p, 4:3)",
            "audio_lbl": "音频格式：",
            "wav_desc": "无损 PCM 音频",
            "mp3_desc": "高品质压缩音频",
        },
        "output": {
            "title": "输出",
            "choose": "选择文件夹",
            "auto_open": "提取完成后打开输出文件夹",
        },
        "rip": {
            "start": "开始提取",
            "stop": "停止提取",
        },
        "content": {
            "title": "视频文件",
            "badge": "  {n}  ",
            "badge_empty": "检测到 0 个轨道",
            "empty_title": "未加载 VCD",
            "empty_sub": "插入光盘或浏览至 VCD 文件夹，然后点击扫描 VCD",
            "scan_prog_folder": "正在扫描文件夹：{name}...",
            "scan_prog_read": "正在读取元数据 ({idx}/{total})：{name}",
            "rip_prog_proc": "正在处理 ({idx}/{total})：{name}",
            "rip_prog_stop": "已停止：成功保存 {success}/{total} 个文件",
            "rip_prog_done": "已完成：成功提取 {success}/{total} 个文件",
        },
        "console": {
            "title": "  📋  控制台日志",
            "clear": "清除",
        },
        "about": {
            "title": "设置",
            "app": "应用程序",
            "version": "版本",
            "dev": "开发者",
            "ffmpeg": "FFmpeg 状态",
            "ffmpeg_path": "FFmpeg 路径",
            "ready": "✓  就绪",
            "not_found": "✗  未找到",
            "license": "MIT 许可证",
            "close": "关闭",
        },
        "language": {
            "title": "语言",
            "en": "English",
            "zh": "中文",
        },
        "appearance": {
            "title": "外观",
            "system": "跟随系统",
            "light": "浅色模式",
            "dark": "深色模式",
        },
        "scale": {
            "title": "界面缩放",
            "100": "100%",
            "125": "125%",
            "150": "150%",
            "100%": "100%",
            "125%": "125%",
            "150%": "150%",
        },
        "rename": {
            "title": "重命名文件",
            "inst": "输出文件名 (不含扩展名)：",
            "apply": "应用",
            "cancel": "取消",
        },
        "batch": {
            "title": "批量重命名",
            "header": "批量重命名文件",
            "inst": "在下方编辑输出文件名 (不含扩展名)：",
            "track": "轨道 {n}:",
            "apply_all": "全部应用",
            "cancel": "取消",
            "no_files_title": "没有文件",
            "no_files_msg": "没有可以重命名的文件。请先扫描 VCD。",
            "seq_enable": "启用顺序编号",
            "seq_base": "基础名称：",
            "seq_start": "起始序号：",
            "seq_suffix": "后缀：",
            "seq_preview": "预览：",
        },
        "messageboxes": {
            "no_source_title": "没有来源",
            "no_source_msg": "请先插入 VCD 或浏览至 VCD 文件夹。",
            "invalid_path_title": "路径无效",
            "invalid_path_msg": "路径不存在：\n{path}",
            "no_files_title": "未找到文件",
            "no_files_msg": "未找到 VCD 视频文件 (.DAT)。\n请确保选择了 VCD 光盘或文件夹的根目录。",
            "ffmpeg_req_title": "未找到 FFmpeg",
            "ffmpeg_req_msg": "音频提取和视频转换需要 FFmpeg。\n\n请从 https://ffmpeg.org/download.html 下载，并确保\nffmpeg.exe 位于您的 PATH 环境变量中，或者与本脚本同级的 'ffmpeg/bin' 文件夹中。\n\n提示：选择 'DAT' 视频格式可以直接提取原始文件而无需 FFmpeg。",
            "no_sel_title": "未选择",
            "no_sel_msg": "未选择任何视频。要提取所有视频吗？",
            "no_vid_title": "没有视频",
            "no_vid_msg": "请先扫描 VCD。",
            "stop_title": "任务已停止",
            "stop_msg": "提取任务已被用户停止。\n\n{success} 个视频已保存至：\n{folder}",
            "eject_title": "弹出光盘？",
            "eject_msg": "已成功提取 {success} 个文件！\n\n您想现在弹出光盘吗？",
            "err_title": "完成但有错误",
            "err_msg": "成功提取了 {success} 个文件。\n{errors} 个文件出现错误 — 请查看控制台日志。",
            "no_drive_title": "没有光盘驱动器",
            "no_drive_msg": "未检测到光盘驱动器。",
            "eject_fail_title": "弹出失败",
            "eject_fail_msg": "无法弹出驱动器 {drive}:\n{err}",
            "ejecting": "正在从驱动器 {drive} 弹出光盘:...",
            "unsupported_disc_title": "不支持的光盘格式",
            "unsupported_disc_msg": "侦测到非 VCD 光盘（如音乐 CD 或 DVD）。本软件仅专门用于 VCD 光盘抓取与转换。",
            "timeout_title": "光碟读取超时",
            "timeout_msg": "由于光盘严重划伤或坏道导致读取超时，已停止提取。已为您保留已完成抓取的视频片段。",
            "btn_ok": "确定",
            "btn_eject": "弹出光碟",
        },
        "log": {
            "non_vcd_blocked": "在驱动器 {drive} 检测到光盘，类型: {type}，已拦截处理流程。",
            "vcd_auto": "自动检测到 VCD 光盘于 {drive}",
            "vcd_found": "在 {folder} 找到 VCD 结构",
            "vcd_not_std": "所选文件夹可能不是标准 VCD (未找到 .DAT 文件)。仍将扫描...",
            "scan_dir": "正在扫描 {path} …",
            "no_vid": "在所选路径中未找到视频文件。",
            "found_files": "找到 {total} 个文件。正在读取元数据…",
            "loaded": "已从 VCD 加载 {total} 个视频。已全选。",
            "out_set": "输出文件夹设置为：{folder}",
            "cancel_req": "用户请求取消… 正在停止进程。",
            "start_ext": "开始提取 {total} 个文件 → {fmt} 格式…",
            "extracting": "正在提取：{name} → {out}",
            "raw_dat_ok": "✓  已提取原始 DAT → 保存为：{name}  ({size} MB)",
            "copy_err": "直接复制错误：{err}",
            "saved_ok": "✓  已保存：{name}  ({size} MB)",
            "saved_partial": "⚠  已保留部分视频片段：{name}  ({size} MB)",
            "read_timeout": "读取光盘 {name} 超时（已停滞 {timeout} 秒）。正在终止进程。",
            "ffmpeg_err": "FFmpeg 处理错误：{name}",
            "exc": "异常：{err}",
            "stop_sum": "提取被用户停止。已完成 {success} 个文件。",
            "done_ok": "所有 {success} 个文件提取成功！输出至：{folder}",
            "open_err": "无法打开输出文件夹：{err}",
            "done_err": "完成，共有 {errors} 个错误。{success} 个文件保存至 {folder}",
            "cleared": "光盘信息已清除。",
            "cleared_all": "已清空影片列表与进度。",
            "eject_win32": "光盘已从驱动器 {drive} 弹出：(DeviceIoControl)",
            "eject_win32_fail": "DeviceIoControl 弹出失败：{err}",
            "eject_ps": "弹出命令已发送至驱动器 {drive}：(PowerShell)",
            "eject_ps_fail": "PowerShell 弹出也失败：{err}",
            "batch_renamed": "已批量重命名 {total} 个文件。",
            "ffmpeg_dl": "未找到 FFmpeg！请从 https://ffmpeg.org 下载并添加到 PATH。",
            "ffmpeg_hint": "或者将 ffmpeg.exe 放在本脚本旁边的 'ffmpeg/bin' 子文件夹中。",
        }
    }
}

class I18n:
    def __init__(self):
        self.lang = "en"
        self.theme = "system"
        self.scale = "100%"
        self._refresh_cb = None
        self._theme_cb = None
        self._scale_cb = None
        self._load_config()

    def _load_config(self):
        try:
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            # Allow external json translation files (en.json, zh-CN.json) to override/extend translations
            for lang_code, fname in (("en", "en.json"), ("zh_CN", "zh-CN.json"), ("zh_CN", "zh_CN.json")):
                l_path = os.path.join(exe_dir, fname)
                if os.path.exists(l_path):
                    try:
                        with open(l_path, "r", encoding="utf-8") as lf:
                            loaded = json.load(lf)
                            if lang_code in TRANSLATIONS and isinstance(loaded, dict):
                                for section, s_data in loaded.items():
                                    if isinstance(s_data, dict) and section in TRANSLATIONS[lang_code]:
                                        TRANSLATIONS[lang_code][section].update(s_data)
                                    else:
                                        TRANSLATIONS[lang_code][section] = s_data
                    except Exception:
                        pass

            cfg_path = os.path.join(exe_dir, "config.json")
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "lang" in data and data["lang"] in TRANSLATIONS:
                        self.lang = data["lang"]
                    if "theme" in data and data["theme"] in ("system", "light", "dark"):
                        self.theme = data["theme"]
                    if "scale" in data and data["scale"] in ("100%", "125%", "150%"):
                        self.scale = data["scale"]
        except Exception:
            pass

    def _save_config(self):
        try:
            exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            cfg_path = os.path.join(exe_dir, "config.json")
            data = {"lang": self.lang, "theme": self.theme, "scale": self.scale}
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def t(self, key, **kwargs):
        keys = key.split('.')
        val = TRANSLATIONS.get(self.lang, TRANSLATIONS["en"])
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return key
        if kwargs and isinstance(val, str):
            try:
                return val.format(**kwargs)
            except Exception:
                pass
        return val

    def switch(self, lang):
        if lang in TRANSLATIONS:
            self.lang = lang
            self._save_config()
            if self._refresh_cb:
                self._refresh_cb()

    def switch_theme(self, theme):
        if theme in ("system", "light", "dark"):
            self.theme = theme
            self._save_config()
            effective = self.get_effective_theme()
            apply_theme_palette(effective)
            if self._theme_cb:
                self._theme_cb()

    def get_scale_factor(self):
        factors = {"100%": 1.0, "125%": 1.25, "150%": 1.5}
        return factors.get(self.scale, 1.0)

    def switch_scale(self, scale):
        if scale in ("100%", "125%", "150%"):
            self.scale = scale
            self._save_config()
            if self._scale_cb:
                self._scale_cb(self.get_scale_factor())

    def get_effective_theme(self):
        if self.theme == "system":
            return get_windows_theme()
        return self.theme

    def set_refresh_callback(self, cb):
        self._refresh_cb = cb

    def set_theme_callback(self, cb):
        self._theme_cb = cb

    def set_scale_callback(self, cb):
        self._scale_cb = cb

i18n = I18n()
apply_theme_palette(i18n.get_effective_theme())

def t(key, **kwargs):
    return i18n.t(key, **kwargs)

_APP_ICON_PHOTO = None
_APP_ICON_ICO_PATH = None
_HEADER_ICONS = {}

def get_header_icon(size=64):
    if size not in _HEADER_ICONS:
        try:
            from PIL import Image, ImageTk
            _base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
            _png = os.path.join(_base, "CompactDisc.png")
            if not os.path.isfile(_png):
                _png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CompactDisc.png")
            if os.path.isfile(_png):
                img = Image.open(_png).convert("RGBA").resize((size, size), Image.LANCZOS)
                _HEADER_ICONS[size] = ImageTk.PhotoImage(img)
            else:
                _HEADER_ICONS[size] = False
        except Exception:
            _HEADER_ICONS[size] = False
    return _HEADER_ICONS.get(size) if _HEADER_ICONS.get(size) else None

def _get_header_icon_64():
    return get_header_icon(scale_val(64))



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
#  Process Priority & Watchdog / Kill helpers
# ─────────────────────────────────────────────
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
IDLE_PRIORITY_CLASS         = 0x00000040
DISC_READ_TIMEOUT_SECONDS   = 20.0  # Trigger timeout if no progress for 20s
GRACEFUL_TERMINATE_TIMEOUT  = 3.0   # Wait up to 3s for graceful exit before force kill

def set_low_process_priority(proc):
    """Set CPU priority to Below Normal and I/O priority to Low for a subprocess on Windows."""
    if not proc or not hasattr(proc, "_handle"):
        return
    try:
        ctypes.windll.kernel32.SetPriorityClass(int(proc._handle), BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass
    try:
        # ProcessIoPriority = 0x21 (33). Values: 0 = Very Low, 1 = Low, 2 = Normal
        io_priority = ctypes.c_ulong(1)  # Low I/O Priority
        ctypes.windll.ntdll.NtSetInformationProcess(
            int(proc._handle), 33, ctypes.byref(io_priority), ctypes.sizeof(io_priority)
        )
    except Exception:
        pass

def kill_process_tree(proc, force=False):
    """Terminate or force kill a subprocess and its entire process tree on Windows."""
    if not proc or proc.poll() is not None:
        return
    pid = getattr(proc, "pid", None)
    if not force:
        try:
            proc.terminate()
        except Exception:
            pass
    else:
        if pid:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            except Exception:
                pass
        try:
            proc.kill()
        except Exception:
            pass

def terminate_and_kill(proc, graceful_timeout=3.0):
    """Gracefully terminate with SIGTERM/terminate, then force kill after graceful_timeout seconds."""
    if not proc or proc.poll() is not None:
        return
    try:
        proc.terminate()
    except Exception:
        pass

    deadline = time.time() + graceful_timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.1)

    if proc.poll() is None:
        kill_process_tree(proc, force=True)


# ─────────────────────────────────────────────
#  Single-Instance Lock & Window Activation helpers
# ─────────────────────────────────────────────
SINGLE_INSTANCE_MUTEX_NAME = "Global\\VCD_Ripper_Pro_Unique_Mutex_Lock"
_APP_MUTEX_HANDLE = None

def acquire_single_instance_lock(name=SINGLE_INSTANCE_MUTEX_NAME):
    """
    Attempt to acquire a system-level named mutex lock on Windows.
    Returns True if this is the first/only running instance.
    Returns False if another instance is already running.
    """
    global _APP_MUTEX_HANDLE
    if sys.platform != "win32":
        return True

    ERROR_ALREADY_EXISTS = 183
    ERROR_ACCESS_DENIED = 5

    try:
        # Try Global\ namespace first
        handle = ctypes.windll.kernel32.CreateMutexW(None, True, name)
        err = ctypes.windll.kernel32.GetLastError()

        # Fallback to Local\ namespace if permissions restrict Global\
        if not handle and err == ERROR_ACCESS_DENIED:
            fallback_name = "Local\\" + name.replace("Global\\", "")
            handle = ctypes.windll.kernel32.CreateMutexW(None, True, fallback_name)
            err = ctypes.windll.kernel32.GetLastError()

        if err == ERROR_ALREADY_EXISTS:
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
            return False  # An instance is already running

        _APP_MUTEX_HANDLE = handle
        return True
    except Exception:
        # If mutex creation fails for unexpected OS reasons, do not block app startup
        return True

def release_single_instance_lock():
    """Release and close the named mutex handle upon application termination."""
    global _APP_MUTEX_HANDLE
    if _APP_MUTEX_HANDLE:
        try:
            ctypes.windll.kernel32.ReleaseMutex(_APP_MUTEX_HANDLE)
        except Exception:
            pass
        try:
            ctypes.windll.kernel32.CloseHandle(_APP_MUTEX_HANDLE)
        except Exception:
            pass
        _APP_MUTEX_HANDLE = None

atexit.register(release_single_instance_lock)

def find_existing_window():
    """Find the HWND of the currently running VCD Ripper Pro main window."""
    if sys.platform != "win32":
        return None

    user32 = ctypes.windll.user32
    found_hwnd = [None]
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def enum_cb(hwnd, lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            # Match top-level main window whose title starts with APP_NAME ("VCD Ripper Pro")
            if title.startswith(APP_NAME):
                owner = user32.GetWindow(hwnd, 4)  # GW_OWNER = 4
                if owner == 0 or not user32.IsWindow(owner):
                    found_hwnd[0] = hwnd
                    return False
        return True

    proc = WNDENUMPROC(enum_cb)
    # Retry briefly up to 1 second in case the primary window is still being rendered
    for _ in range(10):
        user32.EnumWindows(proc, 0)
        if found_hwnd[0]:
            break
        time.sleep(0.1)

    return found_hwnd[0]

def activate_existing_window(hwnd=None):
    """Restore if minimized and bring existing window to the foreground."""
    if sys.platform != "win32":
        return False

    if not hwnd:
        hwnd = find_existing_window()
    if not hwnd:
        return False

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    SW_SHOWNORMAL = 1
    SW_RESTORE = 9

    # If window is minimized (iconic), restore it
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    else:
        user32.ShowWindow(hwnd, SW_SHOWNORMAL)

    # Bring to foreground reliably using AttachThreadInput
    try:
        foreground_hwnd = user32.GetForegroundWindow()
        foreground_thread_id = user32.GetWindowThreadProcessId(foreground_hwnd, None)
        current_thread_id = kernel32.GetCurrentThreadId()

        if foreground_thread_id != current_thread_id:
            user32.AttachThreadInput(foreground_thread_id, current_thread_id, True)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(foreground_thread_id, current_thread_id, False)
        else:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
    except Exception:
        try:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    return True


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


class DiscCheckResult:
    """Represents disc type inspection result with dual tuple / bool support."""
    def __init__(self, is_vcd: bool, disc_type: str, details: str = ""):
        self.is_vcd = bool(is_vcd)
        self.disc_type = str(disc_type)
        self.details = str(details)

    def __bool__(self):
        return self.is_vcd

    def __iter__(self):
        return iter((self.is_vcd, self.disc_type))

    def __getitem__(self, index):
        return (self.is_vcd, self.disc_type)[index]

    def __repr__(self):
        return f"DiscCheckResult(is_vcd={self.is_vcd}, disc_type={self.disc_type!r}, details={self.details!r})"


def is_vcd_disc(drive_path) -> DiscCheckResult:
    """
    Robust, fast check if the given path/drive contains a valid VCD disc.
    Prioritizes checking standard MPEGAV/VCD directories and .DAT files
    without deep file tree scanning to avoid optical drive IO blocking.
    Returns DiscCheckResult(is_vcd: bool, disc_type: str).
    """
    if not drive_path:
        return DiscCheckResult(False, "No Disc", "Empty path")

    try:
        p = Path(drive_path)
        if not p.exists() or not p.is_dir():
            return DiscCheckResult(False, "No Disc", "Path does not exist or is not a directory")

        # Fast shallow inspection of root entries only - avoids recursive tree traversal
        try:
            root_entries = list(p.iterdir())
        except (PermissionError, OSError):
            return DiscCheckResult(False, "Unreadable Disc", "Cannot read root directory")

        if not root_entries:
            return DiscCheckResult(False, "Empty Disc", "No files found on drive")

        # Map uppercase entry names for case-insensitive lookup
        names_map = {e.name.upper(): e for e in root_entries}

        # 1. Primary VCD check: MPEGAV or MPEG2 directories
        for vcd_dir in ("MPEGAV", "MPEG2"):
            if vcd_dir in names_map and names_map[vcd_dir].is_dir():
                try:
                    for item in names_map[vcd_dir].iterdir():
                        if item.is_file() and item.suffix.upper() == ".DAT":
                            return DiscCheckResult(True, "VCD", f"Found {item.name} in {vcd_dir}")
                except (PermissionError, OSError):
                    pass
                return DiscCheckResult(True, "VCD", f"Found {vcd_dir} directory")

        # Check standard VCD metadata directory (White Book specification)
        if "VCD" in names_map and names_map["VCD"].is_dir():
            try:
                sub_names = {item.name.upper() for item in names_map["VCD"].iterdir() if item.is_file()}
                if any(vcd_meta in sub_names for vcd_meta in ("INFO.VCD", "ENTRIES.VCD", "LOT.VCD", "PSD.VCD")):
                    return DiscCheckResult(True, "VCD", "Found standard VCD metadata directory")
            except (PermissionError, OSError):
                pass
            return DiscCheckResult(True, "VCD", "Found VCD directory")

        # Check for .DAT video/audio tracks directly in root
        for e in root_entries:
            try:
                if e.is_file() and e.suffix.upper() == ".DAT":
                    return DiscCheckResult(True, "VCD", f"Found root DAT file: {e.name}")
            except (PermissionError, OSError):
                pass

        # Check other VCD markers from VCD_DAT_PATHS (e.g. SEGMENT)
        for sub in VCD_DAT_PATHS:
            sub_u = sub.upper()
            if sub_u in names_map and names_map[sub_u].is_dir():
                try:
                    for item in names_map[sub_u].iterdir():
                        if item.is_file() and item.suffix.upper() == ".DAT":
                            return DiscCheckResult(True, "VCD", f"Found DAT file in {sub}")
                except (PermissionError, OSError):
                    pass

        # 2. Identify common non-VCD optical disc formats
        # DVD-Video (VIDEO_TS / AUDIO_TS)
        if "VIDEO_TS" in names_map or "AUDIO_TS" in names_map:
            return DiscCheckResult(False, "DVD-Video", "Found DVD-Video structure (VIDEO_TS)")

        # Blu-ray (BDMV / CERTIFICATE)
        if "BDMV" in names_map or "CERTIFICATE" in names_map:
            return DiscCheckResult(False, "Blu-ray", "Found Blu-ray structure (BDMV)")

        # Audio CD (CD-DA tracks mapped as .cda files on Windows)
        cda_files = [e for e in root_entries if e.is_file() and e.suffix.lower() == ".cda"]
        if cda_files:
            return DiscCheckResult(False, "Audio CD", f"Found {len(cda_files)} Audio CD track(s)")

        # 3. Non-VCD Data Disc
        return DiscCheckResult(False, "Data CD/DVD", "No VCD directory structure or .DAT files found")

    except Exception as exc:
        return DiscCheckResult(False, "Unknown Disc", f"Inspection error: {exc}")


def is_vcd_folder(path):
    """Return True if the given path looks like a VCD structure."""
    return bool(is_vcd_disc(path))


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


def get_subprocess_env():
    """Return a copy of os.environ with UTF-8 encoding configured for child processes."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def sanitize_filename(name: str, fallback: str = "track") -> str:
    """
    Sanitize a filename or track/label string for safe filesystem usage on Windows/cross-platform.
    Removes or replaces invalid characters (< > : " / \\ | ? * and control chars),
    strips trailing dots and spaces, handles reserved Windows names, and falls back if empty.
    """
    if not name or not isinstance(name, str):
        return fallback

    # Replace colons and slashes with clean separators
    s = name.replace(":", " - ").replace("/", "_").replace("\\", "_")
    # Replace Windows illegal characters: < > : " / \ | ? * and ASCII control characters 0x00-0x1F, 0x7F
    s = re.sub(r'[\<\>\:"/\\\|\?\*\x00-\x1f\x7f]', '_', s)
    # Remove unicode replacement char or undefined characters
    s = s.replace("\ufffd", "_")
    # Collapse multiple consecutive underscores or spaces
    s = re.sub(r'_+', '_', s)
    s = re.sub(r'\s+', ' ', s)
    # Strip leading/trailing spaces and dots (forbidden by Windows filesystem)
    s = s.strip(" .")

    if not s:
        return fallback

    # Check for reserved Windows filenames (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    p = Path(s)
    stem_upper = p.stem.upper()
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10))
    }
    if stem_upper in reserved_names:
        s = f"{p.stem}_file{p.suffix}"

    # Avoid overly long filenames (max 200 chars for safety)
    if len(s) > 200:
        s = s[:200].rstrip(" .")

    return s if s else fallback


def sanitize_path(path_str: str) -> str:
    """Sanitize a full file path by normalizing directory and sanitizing filename."""
    if not path_str:
        return ""
    try:
        p = Path(path_str)
        safe_name = sanitize_filename(p.name)
        if p.parent and str(p.parent) != ".":
            return str(p.parent / safe_name)
        return safe_name
    except Exception:
        return path_str


def get_volume_label(path: str) -> str:
    """Return the sanitized volume label of a drive or directory on Windows, or empty string."""
    try:
        drive = os.path.splitdrive(os.path.abspath(path))[0]
        if drive:
            if not drive.endswith("\\"):
                drive += "\\"
            vol_buf = ctypes.create_unicode_buffer(261)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(drive),
                vol_buf,
                len(vol_buf),
                None, None, None, None, 0
            )
            if ok and vol_buf.value:
                return sanitize_filename(vol_buf.value.strip())
    except Exception:
        pass
    return ""


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
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=get_subprocess_env(),
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS
        )
        data = json.loads(result.stdout) if (result.stdout and result.stdout.strip()) else {}
        clean_filename = sanitize_filename(Path(file_path).name, fallback="track")
        info = {
            "path":     file_path,
            "filename": clean_filename,
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
            try:
                info["duration"] = float(fmt["duration"])
            except (ValueError, TypeError):
                info["duration"] = 0
        if "bit_rate" in fmt:
            try:
                br = int(fmt["bit_rate"])
                info["bitrate"] = f"{br // 1000} kbps"
            except (ValueError, TypeError):
                pass

        # Extract and sanitize title/metadata tags if available
        tags = fmt.get("tags", {}) if isinstance(fmt, dict) else {}
        for k in ("title", "TITLE", "Title"):
            if k in tags and tags[k]:
                clean_title = sanitize_filename(str(tags[k]).strip())
                if clean_title:
                    info["title"] = clean_title
                    break

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
        safe_name = sanitize_filename(Path(file_path).name, fallback="track")
        size = 0.0
        try:
            size = round(os.path.getsize(file_path) / 1024**2, 1)
        except Exception:
            pass
        return {
            "path":     file_path,
            "filename": safe_name,
            "size_mb":  size,
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
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _=None):
        if self.tip or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 10
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
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
        except Exception:
            pass

    def hide(self, _=None):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
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
            "primary":  (COLORS["accent"],       COLORS["accent_hover"],  COLORS.get("btn_primary_fg", "#FFFFFF")),
            "ghost":    (COLORS["bg_card"],       COLORS["bg_hover"],      COLORS["text_primary"]),
            "danger":   (COLORS["error"],         "#FF6666",               "#FFFFFF"),
            "success":  (COLORS["success"],       "#30D870",               COLORS["bg_dark"]),
        }
        bg, bg_h, fg = styles.get(style, styles["primary"])
        super().__init__(parent, bg=bg, cursor="hand2", **kwargs)
        self._style = style
        self._fg   = fg
        self._bg   = bg
        self._bg_h = bg_h
        label_text = f"{icon}  {text}" if icon else text
        self._lbl = tk.Label(
            self, text=label_text, font=FONTS["subhead"],
            bg=bg, fg=fg, padx=scale_val(16), pady=scale_val(11)
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
            self._lbl.configure(fg=self._fg)
            for w in (self, self._lbl):
                w.bind("<Button-1>", self._on_click)
                w.configure(cursor="hand2")
        else:
            self._lbl.configure(fg=COLORS["text_muted"])
            for w in (self, self._lbl):
                w.unbind("<Button-1>")
                w.configure(cursor="")

    def set_text(self, text, icon=""):
        label_text = f"{icon}  {text}" if icon else text
        self._lbl.configure(text=label_text)

    def apply_theme(self):
        styles = {
            "primary":  (COLORS["accent"],       COLORS["accent_hover"],  COLORS.get("btn_primary_fg", "#FFFFFF")),
            "ghost":    (COLORS["bg_card"],       COLORS["bg_hover"],      COLORS["text_primary"]),
            "danger":   (COLORS["error"],         "#FF6666",               "#FFFFFF"),
            "success":  (COLORS["success"],       "#30D870",               COLORS["bg_dark"]),
        }
        bg, bg_h, fg = styles.get(self._style, styles["primary"])
        self._bg = bg
        self._bg_h = bg_h
        self._fg = fg
        self.configure(bg=bg)
        self._lbl.configure(bg=bg, fg=fg)


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
        self._chk_frame = tk.Frame(self, bg=COLORS["bg_card"], width=scale_val(56))
        self._chk_frame.pack(side="left", fill="y")
        self._chk_frame.pack_propagate(False)
        self._chk_var = tk.BooleanVar(value=False)
        self._chk = tk.Checkbutton(
            self._chk_frame, variable=self._chk_var,
            bg=COLORS["bg_card"], activebackground=COLORS["bg_hover"],
            fg=COLORS["accent"], selectcolor=COLORS["bg_card"],
            command=self._toggle, cursor="hand2",
            relief="flat", bd=0
        )
        self._chk.place(relx=0.5, rely=0.5, anchor="center")

        # Content
        self._content_frame = tk.Frame(self, bg=COLORS["bg_card"], padx=scale_val(14), pady=scale_val(14))
        self._content_frame.pack(side="left", fill="both", expand=True)

        # Row 1: filename + size badge
        self._row1 = tk.Frame(self._content_frame, bg=COLORS["bg_card"])
        self._row1.pack(fill="x")
        self._filename_lbl = tk.Label(
            self._row1, text=f"📼  {self.info['filename']}",
            font=FONTS["subhead"], bg=COLORS["bg_card"],
            fg=COLORS["text_primary"]
        )
        self._filename_lbl.pack(side="left")
        self._size_lbl = tk.Label(
            self._row1, text=f"{self.info['size_mb']} MB",
            font=FONTS["badge"], bg=COLORS["accent_dim"],
            fg=COLORS.get("badge_fg", COLORS["text_primary"]), padx=scale_val(8), pady=scale_val(3)
        )
        self._size_lbl.pack(side="right", padx=(0, scale_val(4)))

        # Row 2: metadata
        self._row2 = tk.Frame(self._content_frame, bg=COLORS["bg_card"])
        self._row2.pack(fill="x", pady=(scale_val(6), 0))
        meta = (
            f"⏱  {format_duration(self.info['duration'])}     "
            f"📐 {self.info['width']}×{self.info['height']}     "
            f"🎬 {self.info['codec']}     "
            f"🎞 {self.info['fps']}     "
            f"📊 {self.info['bitrate']}"
        )
        self._meta_lbl = tk.Label(self._row2, text=meta, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        self._meta_lbl.pack(side="left")

        # Rename button (right side) — larger, visible accent color
        self._rename_btn = tk.Button(
            self, text="✏",
            font=FONTS["rename_btn"], bg=COLORS["bg_card"],
            fg=COLORS.get("rename_btn", "#38BDF8"), relief="flat", bd=0,
            cursor="hand2", activebackground=COLORS["bg_hover"],
            activeforeground=COLORS.get("rename_btn_hover", "#7DD3FC"),
            command=self._on_rename
        )
        self._rename_btn.pack(side="right", padx=(0, scale_val(14)), pady=0)

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

    def apply_theme(self):
        border_color = COLORS["accent"] if self._selected else COLORS["border"]
        self.configure(bg=COLORS["bg_card"], highlightbackground=border_color)
        if hasattr(self, "_chk_frame"):
            self._chk_frame.configure(bg=COLORS["bg_card"])
        if hasattr(self, "_chk"):
            self._chk.configure(
                bg=COLORS["bg_card"], activebackground=COLORS["bg_hover"],
                fg=COLORS["accent"], selectcolor=COLORS["bg_card"]
            )
        if hasattr(self, "_content_frame"):
            self._content_frame.configure(bg=COLORS["bg_card"])
        if hasattr(self, "_row1"):
            self._row1.configure(bg=COLORS["bg_card"])
        if hasattr(self, "_filename_lbl"):
            self._filename_lbl.configure(bg=COLORS["bg_card"], fg=COLORS["text_primary"])
        if hasattr(self, "_size_lbl"):
            self._size_lbl.configure(
                bg=COLORS["accent_dim"],
                fg=COLORS.get("badge_fg", COLORS["text_primary"])
            )
        if hasattr(self, "_row2"):
            self._row2.configure(bg=COLORS["bg_card"])
        if hasattr(self, "_meta_lbl"):
            self._meta_lbl.configure(bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        if hasattr(self, "_rename_btn"):
            self._rename_btn.configure(
                bg=COLORS["bg_card"],
                fg=COLORS.get("rename_btn", "#38BDF8"),
                activebackground=COLORS["bg_hover"],
                activeforeground=COLORS.get("rename_btn_hover", "#7DD3FC")
            )

    def _on_rename(self):
        """Inline rename dialog — let user pick a new output stem for this file."""
        dlg = tk.Toplevel(self.winfo_toplevel())
        dlg.title(t("rename.title"))
        dlg.configure(bg=COLORS["bg_panel"])
        dlg.resizable(False, False)
        dlg.grab_set()

        stem = Path(self.info["filename"]).stem
        self._rename_inst_lbl = tk.Label(
            dlg, text=t("rename.inst"),
            font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_secondary"]
        )
        self._rename_inst_lbl.pack(padx=24, pady=(20, 6), anchor="w")

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
                clean_stem = sanitize_filename(new_stem, fallback=stem)
                self.info["custom_stem"] = clean_stem
                self._filename_lbl.configure(text=f"📼  {clean_stem}")
            dlg.destroy()

        self._rename_apply_btn = tk.Button(
            btn_row, text=t("rename.apply"),
            font=FONTS["body"], bg=COLORS["accent"],
            fg=COLORS["text_primary"], relief="flat", bd=0,
            padx=20, pady=6, cursor="hand2",
            command=apply
        )
        self._rename_apply_btn.pack(side="left", padx=(0, 8))
        self._rename_cancel_btn = tk.Button(
            btn_row, text=t("rename.cancel"),
            font=FONTS["body"], bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], relief="flat", bd=0,
            padx=20, pady=6, cursor="hand2",
            command=dlg.destroy
        )
        self._rename_cancel_btn.pack(side="left")

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

    def apply_theme(self):
        self.configure(bg=COLORS["bg_dark"])
        self._text.configure(
            bg=COLORS["bg_dark"], fg=COLORS["text_secondary"],
            insertbackground=COLORS["accent"]
        )
        self._text.tag_configure("info",    foreground=COLORS["text_secondary"])
        self._text.tag_configure("success", foreground=COLORS["success"])
        self._text.tag_configure("warning", foreground=COLORS["warning"])
        self._text.tag_configure("error",   foreground=COLORS["error"])
        self._text.tag_configure("accent",  foreground=COLORS["accent"])

    def log(self, message, level="info"):
        ts = datetime.now().strftime("%H:%M:%S")
        icons = {"info": "●", "success": "✓", "warning": "⚠", "error": "✗", "accent": "►"}
        icon = icons.get(level, "●")
        # Ensure message is safely encoded/decoded with UTF-8 and errors replaced
        safe_msg = str(message).encode("utf-8", errors="replace").decode("utf-8")
        line = f"[{ts}]  {icon}  {safe_msg}\n"
        try:
            self._text.configure(state="normal")
            self._text.insert("end", line, level)
            self._text.see("end")
            self._text.configure(state="disabled")
        except Exception:
            pass

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


# ─────────────────────────────────────────────
#  Windows Taskbar Progress Helper (ITaskbarList3)
# ─────────────────────────────────────────────
class WindowsTaskbarProgress:
    """Controls the Windows Taskbar button progress indicator using ITaskbarList3 COM interface."""
    TBPF_NOPROGRESS    = 0x00000000
    TBPF_INDETERMINATE = 0x00000001
    TBPF_NORMAL        = 0x00000002
    TBPF_ERROR         = 0x00000004
    TBPF_PAUSED        = 0x00000008

    def __init__(self, root_widget):
        self._root = root_widget
        self._taskbar = None
        self._set_progress_val_fn = None
        self._set_progress_state_fn = None
        self._hwnd = None
        self._supported = False
        self._init_taskbar()

    def _init_taskbar(self):
        if sys.platform != "win32":
            return
        try:
            from ctypes import (
                wintypes, Structure, c_byte, c_ushort, c_ulong,
                POINTER, c_void_p, c_ulonglong, c_int, WINFUNCTYPE, c_long
            )

            class GUID(Structure):
                _fields_ = [
                    ("Data1", c_ulong),
                    ("Data2", c_ushort),
                    ("Data3", c_ushort),
                    ("Data4", c_byte * 8)
                ]

            CLSID_TaskbarList = GUID(
                0x56FDF344, 0xFD6D, 0x11D0,
                (c_byte * 8)(0x95, 0x8A, 0x00, 0x60, 0x97, 0xC9, 0xA0, 0x90)
            )
            IID_ITaskbarList3 = GUID(
                0xEA1AFB91, 0x9E28, 0x4B86,
                (c_byte * 8)(0x90, 0xE9, 0x9E, 0x9F, 0x8A, 0x5E, 0xEF, 0xAF)
            )

            ctypes.windll.ole32.CoInitialize(None)
            taskbar = c_void_p()
            hr = ctypes.windll.ole32.CoCreateInstance(
                ctypes.byref(CLSID_TaskbarList),
                None,
                1,  # CLSCTX_INPROC_SERVER
                ctypes.byref(IID_ITaskbarList3),
                ctypes.byref(taskbar)
            )
            if hr != 0 or not taskbar.value:
                return

            vtable = ctypes.cast(taskbar.value, POINTER(POINTER(c_void_p))).contents
            self._taskbar = taskbar
            # slot 9: SetProgressValue(this, hwnd, completed, total)
            self._set_progress_val_fn = WINFUNCTYPE(
                c_long, c_void_p, wintypes.HWND, c_ulonglong, c_ulonglong
            )(vtable[9])
            # slot 10: SetProgressState(this, hwnd, flags)
            self._set_progress_state_fn = WINFUNCTYPE(
                c_long, c_void_p, wintypes.HWND, c_int
            )(vtable[10])
            self._supported = True
        except Exception:
            self._supported = False

    def _get_hwnd(self):
        if not self._supported:
            return None
        if self._hwnd:
            return self._hwnd
        try:
            client_hwnd = self._root.winfo_id()
            if client_hwnd:
                # GA_ROOT = 2: retrieves the root window by walking the chain of parent windows
                hwnd = ctypes.windll.user32.GetAncestor(client_hwnd, 2)
                self._hwnd = hwnd if hwnd else client_hwnd
        except Exception:
            pass
        return self._hwnd

    def set_state(self, state):
        hwnd = self._get_hwnd()
        if not hwnd or not self._supported:
            return
        try:
            self._set_progress_state_fn(self._taskbar, hwnd, state)
        except Exception:
            pass

    def set_value(self, completed, total=100):
        hwnd = self._get_hwnd()
        if not hwnd or not self._supported:
            return
        try:
            if total <= 0:
                total = 100
            completed = max(0, min(int(completed), int(total)))
            self._set_progress_state_fn(self._taskbar, hwnd, self.TBPF_NORMAL)
            self._set_progress_val_fn(self._taskbar, hwnd, completed, int(total))
        except Exception:
            pass

    def set_error(self):
        self.set_state(self.TBPF_ERROR)

    def set_paused(self):
        self.set_state(self.TBPF_PAUSED)

    def reset(self):
        self.set_state(self.TBPF_NOPROGRESS)


# ─────────────────────────────────────────────
#  Main Application Window
# ─────────────────────────────────────────────
class VCDRipperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(t('header.title'))
        self.configure(bg=COLORS["bg_dark"])

        # DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # Explicit AppUserModelID so Windows taskbar uses CompactDisc.ico
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jjsiew.vcdripperpro.1.3.0")
        except Exception:
            pass

        # Apply fonts and window scale
        apply_font_scale(self, i18n.get_scale_factor())
        self._apply_window_scale()

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
        self._cancel_requested = False
        self._current_proc     = None
        
        # Batch rename session memory
        self._batch_seq_enabled = False
        self._batch_base_name   = "Track"
        self._batch_start_index = "1"
        
        # Windows taskbar progress
        self._taskbar_progress = WindowsTaskbarProgress(self)
        self._about_dialog     = None
        self._last_non_vcd_drive = None
        self._unsupported_dlg_open = False

        i18n.set_refresh_callback(self._refresh_ui)
        i18n.set_theme_callback(self._on_theme_changed)
        i18n.set_scale_callback(self._on_scale_changed)

        # FFmpeg
        self._ffmpeg, self._ffprobe = find_ffmpeg()

        self._build_ui()
        self._apply_ttk_styles()
        self._start_drive_poll()

        # App icon — multi-resolution CompactDisc.ico
        self._set_window_icon(self)

        # Global MouseWheel scroll dispatcher
        self.bind_all("<MouseWheel>", self._on_global_mousewheel)

        if not self._ffmpeg:
            self._show_ffmpeg_warning()

    def _apply_window_scale(self):
        s = i18n.get_scale_factor()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        target_w = min(int(round(1360 * s)), screen_w - 40)
        target_h = min(int(round(920 * s)), screen_h - 80)
        min_w = min(int(round(1100 * s)), screen_w - 60)
        min_h = min(int(round(750 * s)), screen_h - 100)
        self.minsize(min_w, min_h)
        self.geometry(f"{target_w}x{target_h}")

    def _on_scale_changed(self, scale_factor):
        apply_font_scale(self, scale_factor)
        self._apply_window_scale()
        self._rebuild_ui()

        # App icon — works for both plain Python and PyInstaller onedir
        self._set_window_icon(self)

        # Global MouseWheel scroll dispatcher
        self.bind_all("<MouseWheel>", self._on_global_mousewheel)

        if not self._ffmpeg:
            self._show_ffmpeg_warning()

    def _on_theme_changed(self):
        self._apply_theme()

    def _apply_theme(self):
        # 1. Root window & Title bar
        self.configure(bg=COLORS["bg_dark"])
        try:
            hwnd = ctypes.windll.user32.GetAncestor(self.winfo_id(), 2) or self.winfo_id()
            set_window_dark_mode(hwnd, i18n.get_effective_theme() == "dark")
        except Exception:
            pass

        # 2. TTK styles (progressbars, scrollbars)
        self._apply_ttk_styles()

        # 3. Header bar
        if hasattr(self, "_header"):
            self._header.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_title_lbl"):
            self._title_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_primary"])
        if hasattr(self, "_version_lbl"):
            self._version_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
        if hasattr(self, "_clear_all_btn"):
            self._clear_all_btn.configure(
                bg=COLORS["bg_card"],
                fg=COLORS["text_muted"] if self._ripping else COLORS["text_secondary"],
                activebackground=COLORS["bg_hover"],
                activeforeground=COLORS["accent"]
            )
        if hasattr(self, "_console_btn"):
            self._console_btn.configure(
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                activebackground=COLORS["bg_hover"], activeforeground=COLORS["accent"]
            )
        if hasattr(self, "_about_btn"):
            self._about_btn.configure(
                bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                activebackground=COLORS["bg_hover"], activeforeground=COLORS["accent"]
            )
        if hasattr(self, "_batch_rename_btn"):
            self._batch_rename_btn.configure(
                bg=COLORS["bg_card"], fg=COLORS["accent"],
                activebackground=COLORS["bg_hover"], activeforeground=COLORS["accent_hover"]
            )
        if hasattr(self, "_eject_btn"):
            self._eject_btn.configure(
                bg=COLORS["bg_card"], fg=COLORS["warning"],
                activebackground=COLORS["bg_hover"], activeforeground=COLORS["warning"]
            )
        if hasattr(self, "_drive_lbl"):
            d = self._vcd_path.get()
            self._drive_lbl.configure(
                bg=COLORS["bg_panel"],
                fg=COLORS["text_secondary"] if d else COLORS["text_muted"]
            )

        # 4. Left sidebar
        if hasattr(self, "_top_frame"):
            self._top_frame.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_left_sidebar"):
            self._left_sidebar.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_left_scroll_area"):
            self._left_scroll_area.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_left_canvas"):
            self._left_canvas.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_left_content"):
            self._left_content.configure(bg=COLORS["bg_panel"])

        if hasattr(self, "_source_section_lbl"):
            self._source_section_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["accent"])
        if hasattr(self, "_detect_card"):
            self._detect_card.configure(bg=COLORS["bg_card"], highlightbackground=COLORS["border"])
        if hasattr(self, "_detect_icon"):
            self._detect_icon.configure(bg=COLORS["bg_card"])
        if hasattr(self, "_detect_label"):
            d = self._vcd_path.get()
            self._detect_label.configure(
                bg=COLORS["bg_card"],
                fg=COLORS["success"] if (d and is_vcd_folder(d)) else COLORS["text_muted"]
            )
        if hasattr(self, "_detected_drive_lbl"):
            self._detected_drive_lbl.configure(bg=COLORS["bg_card"], fg=COLORS["accent"])

        if hasattr(self, "_browse_btn"):
            self._browse_btn.apply_theme()
        if hasattr(self, "_scan_btn"):
            self._scan_btn.apply_theme()
        if hasattr(self, "_path_lbl"):
            self._path_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
        if hasattr(self, "_left_sep"):
            self._left_sep.configure(bg=COLORS["border"])

        if hasattr(self, "_sel_section_lbl"):
            self._sel_section_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["accent"])
        if hasattr(self, "_sel_row"):
            self._sel_row.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_sel_all_btn"):
            self._sel_all_btn.apply_theme()
        if hasattr(self, "_sel_none_btn"):
            self._sel_none_btn.apply_theme()
        if hasattr(self, "_sel_count_lbl"):
            self._sel_count_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])

        # 5. Right sidebar
        if hasattr(self, "_right_sidebar"):
            self._right_sidebar.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_right_bottom_frame"):
            self._right_bottom_frame.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_rip_btn"):
            self._rip_btn.apply_theme()
        if hasattr(self, "_stop_btn"):
            self._stop_btn.apply_theme()
        if hasattr(self, "_right_scroll_area"):
            self._right_scroll_area.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_right_canvas"):
            self._right_canvas.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_right_content"):
            self._right_content.configure(bg=COLORS["bg_panel"])

        if hasattr(self, "_format_section_lbl"):
            self._format_section_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["accent"])
        if hasattr(self, "_mode_card"):
            self._mode_card.configure(bg=COLORS["bg_card"], highlightbackground=COLORS["border"])
        if hasattr(self, "_video_mode_rb"):
            self._video_mode_rb.configure(
                bg=COLORS["bg_card"], fg=COLORS["accent"],
                selectcolor=COLORS["bg_dark"], activebackground=COLORS["bg_card"],
                activeforeground=COLORS["accent"]
            )
        if hasattr(self, "_audio_mode_rb"):
            self._audio_mode_rb.configure(
                bg=COLORS["bg_card"], fg=COLORS["success"],
                selectcolor=COLORS["bg_dark"], activebackground=COLORS["bg_card"],
                activeforeground=COLORS["success"]
            )

        if hasattr(self, "_fmt_container"):
            self._fmt_container.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_video_panel"):
            self._video_panel.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_video_fmt_lbl"):
            self._video_fmt_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_secondary"])
        if hasattr(self, "_fmt_card"):
            self._fmt_card.configure(bg=COLORS["bg_card"], highlightbackground=COLORS["border"])
        for item in getattr(self, "_fmt_items", []):
            item["frame"].configure(bg=COLORS["bg_card"])
            item["rb"].configure(
                bg=COLORS["bg_card"], selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg_card"]
            )
            item["lbl"].configure(bg=COLORS["bg_card"], fg=COLORS["text_secondary"])

        if hasattr(self, "_dat_suboption_frame"):
            self._dat_suboption_frame.configure(bg=COLORS["bg_card"], highlightbackground=COLORS["border"])
        if hasattr(self, "_dat_mode_lbl"):
            self._dat_mode_lbl.configure(bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        if hasattr(self, "_rb_row"):
            self._rb_row.configure(bg=COLORS["bg_card"])
        if hasattr(self, "_dat_raw_rb"):
            self._dat_raw_rb.configure(
                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_panel"], activebackground=COLORS["bg_card"]
            )
        if hasattr(self, "_dat_mp4_rb"):
            self._dat_mp4_rb.configure(
                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_panel"], activebackground=COLORS["bg_card"]
            )

        if hasattr(self, "_res_suboption_frame"):
            self._res_suboption_frame.configure(bg=COLORS["bg_card"], highlightbackground=COLORS["border"])
        if hasattr(self, "_res_title_lbl"):
            self._res_title_lbl.configure(bg=COLORS["bg_card"], fg=COLORS["text_secondary"])
        if hasattr(self, "_res_rb_row"):
            self._res_rb_row.configure(bg=COLORS["bg_card"])
        if hasattr(self, "_res_orig_rb"):
            self._res_orig_rb.configure(
                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_panel"], activebackground=COLORS["bg_card"]
            )
        if hasattr(self, "_res_1080p_rb"):
            self._res_1080p_rb.configure(
                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_panel"], activebackground=COLORS["bg_card"]
            )

        if hasattr(self, "_audio_panel"):
            self._audio_panel.configure(bg=COLORS["bg_panel"])
        if hasattr(self, "_audio_fmt_lbl"):
            self._audio_fmt_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_secondary"])
        if hasattr(self, "_audio_fmt_card"):
            self._audio_fmt_card.configure(bg=COLORS["bg_card"], highlightbackground=COLORS["border"])
        for item in getattr(self, "_audio_items", []):
            item["frame"].configure(bg=COLORS["bg_card"])
            item["rb"].configure(
                bg=COLORS["bg_card"], selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg_card"]
            )
            item["lbl"].configure(bg=COLORS["bg_card"], fg=COLORS["text_secondary"])

        if hasattr(self, "_right_sep"):
            self._right_sep.configure(bg=COLORS["border"])
        if hasattr(self, "_output_section_lbl"):
            self._output_section_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["accent"])
        if hasattr(self, "_choose_folder_btn"):
            self._choose_folder_btn.apply_theme()
        if hasattr(self, "_out_lbl"):
            self._out_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
        if hasattr(self, "_auto_open_chk"):
            self._auto_open_chk.configure(
                bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_dark"], activebackground=COLORS["bg_panel"]
            )

        # 6. Center Content (Video List & Empty State)
        if hasattr(self, "_content_container"):
            self._content_container.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_content_title_bar"):
            self._content_title_bar.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_content_title"):
            self._content_title.configure(bg=COLORS["bg_dark"], fg=COLORS["text_primary"])
        if hasattr(self, "_video_count_badge"):
            self._video_count_badge.configure(bg=COLORS["accent_dim"], fg=COLORS["text_primary"])
        if hasattr(self, "_list_container"):
            self._list_container.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_canvas"):
            self._canvas.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_list_frame"):
            self._list_frame.configure(bg=COLORS["bg_dark"])

        if hasattr(self, "_empty_frame"):
            self._empty_frame.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_empty_icon_lbl"):
            self._empty_icon_lbl.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_empty_title_lbl"):
            self._empty_title_lbl.configure(bg=COLORS["bg_dark"], fg=COLORS["text_secondary"])
        if hasattr(self, "_empty_sub_lbl"):
            self._empty_sub_lbl.configure(bg=COLORS["bg_dark"], fg=COLORS["text_muted"])

        for card in self._cards:
            card.apply_theme()

        # Progress bars
        if hasattr(self, "_scan_progress_frame"):
            self._scan_progress_frame.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_scan_progress_lbl"):
            self._scan_progress_lbl.configure(bg=COLORS["bg_dark"], fg=COLORS["text_secondary"])
        if hasattr(self, "_scan_progress_pct"):
            self._scan_progress_pct.configure(bg=COLORS["bg_dark"], fg=COLORS["cyan"])
        if hasattr(self, "_progress_frame"):
            self._progress_frame.configure(bg=COLORS["bg_dark"])
        if hasattr(self, "_progress_lbl"):
            self._progress_lbl.configure(bg=COLORS["bg_dark"], fg=COLORS["text_secondary"])
        if hasattr(self, "_progress_pct"):
            self._progress_pct.configure(bg=COLORS["bg_dark"], fg=COLORS["accent"])

        # 7. Log Window
        if hasattr(self, "_log_window") and self._log_window.winfo_exists():
            self._log_window.configure(bg=COLORS["bg_dark"])
            if hasattr(self, "_log_header"):
                self._log_header.configure(bg=COLORS["bg_panel"])
            if hasattr(self, "_console_title_lbl"):
                self._console_title_lbl.configure(bg=COLORS["bg_panel"], fg=COLORS["text_secondary"])
            if hasattr(self, "_console_clear_btn"):
                self._console_clear_btn.configure(
                    bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
                    activebackground=COLORS["bg_panel"]
                )
            if hasattr(self, "_log"):
                self._log.apply_theme()
            try:
                log_hwnd = ctypes.windll.user32.GetAncestor(self._log_window.winfo_id(), 2) or self._log_window.winfo_id()
                set_window_dark_mode(log_hwnd, i18n.get_effective_theme() == "dark")
            except Exception:
                pass

        # 8. Settings Dialog (if open)
        if hasattr(self, "_about_dialog") and self._about_dialog and self._about_dialog.winfo_exists():
            if hasattr(self._about_dialog, "update_theme"):
                self._about_dialog.update_theme()

    def _rebuild_ui(self):
        # Save log contents
        log_text = ""
        if hasattr(self, '_log') and hasattr(self._log, '_text'):
            try:
                log_text = self._log._text.get("1.0", "end")
            except Exception:
                pass

        # Destroy old log window so it gets recreated with new theme
        log_shown = False
        if hasattr(self, '_log_window') and self._log_window.winfo_exists():
            log_shown = (self._log_window.state() != "withdrawn" and self._log_window.state() != "iconic")
            self._log_window.destroy()

        # Destroy all direct child widgets of root (preserving _about_dialog if open)
        for child in self.winfo_children():
            if hasattr(self, "_about_dialog") and self._about_dialog and child == self._about_dialog:
                continue
            child.destroy()

        # Set root window background
        self.configure(bg=COLORS["bg_dark"])

        # Re-build UI
        self._build_ui()
        self._apply_ttk_styles()

        # Restore log
        if log_text.strip():
            self._log._text.configure(state="normal")
            self._log._text.delete("1.0", "end")
            self._log._text.insert("1.0", log_text.rstrip("\n") + "\n")
            self._log._text.see("end")
            self._log._text.configure(state="disabled")
        if log_shown:
            self._log_window.deiconify()

        # Restore video tracks if any
        if self._videos:
            saved_selected = set(self._selected_indices)
            self._cards.clear()
            self._selected_indices.clear()
            self._clear_list()
            if hasattr(self, "_empty_frame") and self._empty_frame.winfo_exists():
                self._empty_frame.pack_forget()

            for i, info in enumerate(self._videos):
                card = VideoCard(
                    self._list_frame, info, i,
                    on_toggle=self._on_card_toggle
                )
                card.pack(fill="x", padx=4, pady=3)
                self._cards.append(card)

            for idx in saved_selected:
                if idx < len(self._cards):
                    self._cards[idx].set_selected(True)
                    self._selected_indices.add(idx)
            self._update_sel_count()
        else:
            self._clear_list()
            if hasattr(self, "_empty_frame") and self._empty_frame.winfo_exists():
                self._empty_frame.pack(fill="both", expand=True, pady=100)

        # Refresh all localized text & drive status
        self._refresh_ui()

        # Update about dialog scale if open
        if hasattr(self, "_about_dialog") and self._about_dialog and self._about_dialog.winfo_exists():
            if hasattr(self._about_dialog, "update_scale"):
                self._about_dialog.update_scale()
            self._about_dialog.lift()

    # ── UI Construction ──────────────────────
    def _build_ui(self):
        # ── Header bar ──────────────────────
        self._header = tk.Frame(self, bg=COLORS["bg_panel"], height=scale_val(68))
        self._header.pack(fill="x", side="top")
        self._header.pack_propagate(False)
        header = self._header

        self._title_lbl = tk.Label(
            header, text=t('header.title'),
            font=FONTS["title"], bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"]
        )
        self._title_lbl.pack(side="left", padx=scale_val(28), pady=0)

        self._version_lbl = tk.Label(
            header, text=f"v{APP_VERSION}",
            font=FONTS["body"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        )
        self._version_lbl.pack(side="left", pady=(scale_val(16), 0))

        # Clear All button (Far Right, immediately right of Console Log)
        self._clear_all_btn = tk.Button(
            header, text=t('header.clear_all'),
            font=FONTS["badge"],
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["accent"],
            relief="flat", bd=0, padx=scale_val(14), pady=scale_val(6),
            cursor="hand2",
            command=self._clear_all_action
        )
        self._clear_all_btn.pack(side="right", padx=(scale_val(6), scale_val(24)))
        self._clear_all_tip = Tooltip(self._clear_all_btn, t('header.clear_all_tip'))

        # Console Log button (Immediately left of Clear All)
        self._console_btn = tk.Button(
            header, text=t('header.console'),
            font=FONTS["badge"],
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["accent"],
            relief="flat", bd=0, padx=scale_val(14), pady=scale_val(6),
            cursor="hand2",
            command=self._toggle_console
        )
        self._console_btn.pack(side="right", padx=scale_val(6))

        # Setting button
        self._about_btn = tk.Button(
            header, text=t('header.about'),
            font=FONTS["badge"],
            bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["accent"],
            relief="flat", bd=0, padx=scale_val(14), pady=scale_val(6),
            cursor="hand2",
            command=self._show_about
        )
        self._about_btn.pack(side="right", padx=scale_val(6))

        # Batch Rename button
        self._batch_rename_btn = tk.Button(
            header, text=t('header.batch_rename'),
            font=FONTS["badge"],
            bg=COLORS["bg_card"], fg=COLORS["accent"],
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["accent_hover"],
            relief="flat", bd=0, padx=scale_val(14), pady=scale_val(6),
            cursor="hand2",
            command=self._batch_rename
        )
        self._batch_rename_btn.pack(side="right", padx=scale_val(6))

        # Eject Disc button
        self._eject_btn = tk.Button(
            header, text=t('header.eject_disc'),
            font=FONTS["badge"],
            bg=COLORS["bg_card"], fg=COLORS["warning"],
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["warning"],
            relief="flat", bd=0, padx=scale_val(14), pady=scale_val(6),
            cursor="hand2",
            command=self._eject_disc
        )
        self._eject_btn.pack(side="right", padx=scale_val(6))

        # Drive status indicator
        self._drive_lbl = tk.Label(
            header, text=t('header.no_disc'),
            font=FONTS["badge"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        )
        self._drive_lbl.pack(side="right", padx=(scale_val(20), scale_val(6)))

        # ── Main layout (full height) ────────────────
        self._top_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        self._top_frame.pack(fill="both", expand=True)
        top_frame = self._top_frame

        # ── Left sidebar (Source & Selection) ──
        self._left_sidebar = tk.Frame(top_frame, bg=COLORS["bg_panel"], width=scale_val(280))
        self._left_sidebar.pack(side="left", fill="y")
        self._left_sidebar.pack_propagate(False)
        left_sidebar = self._left_sidebar

        self._left_scroll_area = tk.Frame(left_sidebar, bg=COLORS["bg_panel"])
        self._left_scroll_area.pack(fill="both", expand=True)

        self._left_canvas = tk.Canvas(self._left_scroll_area, bg=COLORS["bg_panel"], highlightthickness=0)
        left_vsb = ttk.Scrollbar(self._left_scroll_area, orient="vertical", command=self._left_canvas.yview)
        self._left_canvas.configure(yscrollcommand=left_vsb.set)
        left_vsb.pack(side="right", fill="y")

        self._left_content = tk.Frame(self._left_canvas, bg=COLORS["bg_panel"])
        left_window = self._left_canvas.create_window((0, 0), window=self._left_content, anchor="nw")

        self._left_content.bind("<Configure>", lambda e: self._left_canvas.configure(scrollregion=self._left_canvas.bbox("all")))
        self._left_canvas.bind("<Configure>", lambda e: self._left_canvas.itemconfig(left_window, width=e.width))
        self._left_canvas._can_scroll = True
        self._left_canvas.pack(side="left", fill="both", expand=True)
        self._build_left_sidebar(self._left_content)

        # ── Center content area (VCD Tracks) ──
        self._content_container = tk.Frame(top_frame, bg=COLORS["bg_dark"])
        self._content_container.pack(side="left", fill="both", expand=True)
        self._build_content(self._content_container)

        # ── Right sidebar (Output Format, Output Folder, Rip Controls) ──
        self._right_sidebar = tk.Frame(top_frame, bg=COLORS["bg_panel"], width=scale_val(420))
        self._right_sidebar.pack(side="right", fill="y")
        self._right_sidebar.pack_propagate(False)
        right_sidebar = self._right_sidebar

        # Fixed bottom container for "Start Ripping" and "Stop Ripping" buttons
        self._right_bottom_frame = tk.Frame(right_sidebar, bg=COLORS["bg_panel"])
        self._right_bottom_frame.pack(side="bottom", fill="x", padx=scale_val(16), pady=scale_val(16))

        self._rip_btn = FlatButton(
            self._right_bottom_frame, text=t('rip.start'), icon="⚡",
            style="primary", command=self._start_rip
        )
        self._rip_btn.pack(fill="x", pady=(0, 8))

        self._stop_btn = FlatButton(
            self._right_bottom_frame, text=t('rip.stop'), icon="⏹",
            style="danger", command=self._stop_rip
        )
        self._stop_btn.pack(fill="x")
        self._stop_btn.configure_state(False)

        # Scrollable container for Output Format & Output Folder
        self._right_scroll_area = tk.Frame(right_sidebar, bg=COLORS["bg_panel"])
        self._right_scroll_area.pack(side="top", fill="both", expand=True)

        self._right_canvas = tk.Canvas(self._right_scroll_area, bg=COLORS["bg_panel"], highlightthickness=0)
        right_vsb = ttk.Scrollbar(self._right_scroll_area, orient="vertical", command=self._right_canvas.yview)
        self._right_canvas.configure(yscrollcommand=right_vsb.set)
        right_vsb.pack(side="right", fill="y")

        self._right_content = tk.Frame(self._right_canvas, bg=COLORS["bg_panel"])
        right_window = self._right_canvas.create_window((0, 0), window=self._right_content, anchor="nw")

        self._right_content.bind("<Configure>", lambda e: self._right_canvas.configure(scrollregion=self._right_canvas.bbox("all")))
        self._right_canvas.bind("<Configure>", lambda e: self._right_canvas.itemconfig(right_window, width=e.width))
        self._right_canvas._can_scroll = True
        self._right_canvas.pack(side="left", fill="both", expand=True)
        self._build_right_sidebar(self._right_content)

        # ── Console Log (popup window) ───────────────
        self._log_window = tk.Toplevel(self)
        self._log_window.title("Console Log — VCD Ripper Pro")
        self._log_window.configure(bg=COLORS["bg_dark"])
        self._log_window.geometry(f"{scale_val(700)}x{scale_val(400)}")
        self._log_window.protocol("WM_DELETE_WINDOW", self._log_window.withdraw)
        self._log_window.withdraw()  # Start hidden

        # Set icon on log window
        self._set_window_icon(self._log_window)

        self._log_header = tk.Frame(self._log_window, bg=COLORS["bg_panel"], height=scale_val(36))
        self._log_header.pack(fill="x")
        self._log_header.pack_propagate(False)
        self._console_title_lbl = tk.Label(
            self._log_header, text=t('console.title'),
            font=FONTS["subhead"], bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        )
        self._console_title_lbl.pack(side="left", pady=6)
        self._console_clear_btn = tk.Button(
            self._log_header, text=t('console.clear'),
            font=FONTS["small"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"], bd=0, cursor="hand2",
            activebackground=COLORS["bg_panel"],
            command=lambda: self._log.clear()
        )
        self._console_clear_btn.pack(side="right", padx=16)

        self._log = LogConsole(self._log_window)
        self._log.pack(fill="both", expand=True)

    def _build_left_sidebar(self, parent):
        pad = {"padx": 20}

        # ── Source section ───────────────────
        self._source_section_lbl = self._section_label(parent, t('source.title'))

        # Auto-detect display
        self._detect_card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        self._detect_card.pack(fill="x", padx=20, pady=(6, 0))
        detect_card = self._detect_card

        self._detect_icon = tk.Label(
            detect_card, text="💿", font=FONTS["emoji_32"],
            bg=COLORS["bg_card"]
        )
        self._detect_icon.pack(pady=(14, 0))

        self._detect_label = tk.Label(
            detect_card, text=t('drive.insert_vcd'),
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
        self._browse_btn = FlatButton(
            parent, text=t('source.browse'),
            icon="📁",
            style="ghost", command=self._browse_source
        )
        self._browse_btn.pack(fill="x", padx=20, pady=(10, 0))

        # Scan button
        self._scan_btn = FlatButton(
            parent, text=t('source.scan'),
            icon="🔍",
            style="primary", command=self._scan_vcd
        )
        self._scan_btn.pack(fill="x", padx=20, pady=(8, 0))

        # Path display
        self._path_lbl = tk.Label(
            parent, textvariable=self._vcd_path,
            font=FONTS["mono"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"], wraplength=scale_val(240),
            justify="left"
        )
        self._path_lbl.pack(fill="x", padx=20, pady=(6, 0))

        # ── Separator ───────────────────────
        self._left_sep = tk.Frame(parent, bg=COLORS["border"], height=1)
        self._left_sep.pack(fill="x", padx=20, pady=12)

        # ── Selection section ────────────────
        self._sel_section_lbl = self._section_label(parent, t('selection.title'))

        self._sel_row = tk.Frame(parent, bg=COLORS["bg_panel"])
        self._sel_row.pack(fill="x", padx=20, pady=(6, 0))
        sel_row = self._sel_row

        self._sel_all_btn = FlatButton(
            sel_row, text=t('selection.all'),
            icon="☑",
            style="ghost", command=self._select_all
        )
        self._sel_all_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self._sel_none_btn = FlatButton(
            sel_row, text=t('selection.none'),
            icon="☐",
            style="ghost", command=self._select_none
        )
        self._sel_none_btn.pack(side="left", fill="x", expand=True)

        self._sel_count_lbl = tk.Label(
            parent, text=t('selection.count').format(n=0, total=0),
            font=FONTS["body"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        )
        self._sel_count_lbl.pack(padx=20, pady=(6, 12))

    def _build_right_sidebar(self, parent):
        # ── Output section ───────────────────
        self._format_section_lbl = self._section_label(parent, t('format.title'))

        # ── Mode toggle: Video / Audio Only (boxed 2-line card) ──
        self._mode_card = tk.Frame(
            parent, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        self._mode_card.pack(fill="x", padx=20, pady=(8, 0))
        mode_card = self._mode_card

        self._video_mode_rb = tk.Radiobutton(
            mode_card, text=t('format.video_mode'),
            variable=self._output_mode, value="video",
            font=FONTS["small_bold"],
            bg=COLORS["bg_card"], fg=COLORS["accent"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["accent"],
            cursor="hand2",
            command=self._on_mode_change
        )
        self._video_mode_rb.pack(anchor="w", padx=16, pady=8)

        self._audio_mode_rb = tk.Radiobutton(
            mode_card, text=t('format.audio_mode'),
            variable=self._output_mode, value="audio",
            font=FONTS["small_bold"],
            bg=COLORS["bg_card"], fg=COLORS["success"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_card"],
            activeforeground=COLORS["success"],
            cursor="hand2",
            command=self._on_mode_change
        )
        self._audio_mode_rb.pack(anchor="w", padx=16, pady=(0, 8))

        # ── Format options container (holds video_panel & audio_panel) ──
        self._fmt_container = tk.Frame(parent, bg=COLORS["bg_panel"])
        self._fmt_container.pack(fill="x", padx=0, pady=(4, 0))

        # ── Video sub-panel ─────────────────
        self._video_panel = tk.Frame(self._fmt_container, bg=COLORS["bg_panel"])
        self._video_panel.pack(fill="x", padx=0, pady=0)

        self._video_fmt_lbl = tk.Label(
            self._video_panel, text=t('format.video_lbl'),
            font=FONTS["small_bold"], bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        )
        self._video_fmt_lbl.pack(anchor="w", padx=20, pady=(8, 4))

        self._fmt_card = tk.Frame(
            self._video_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        self._fmt_card.pack(fill="x", padx=20, pady=(0, 4))
        fmt_card = self._fmt_card

        self._fmt_desc_lbls = {}
        self._fmt_items = []
        for idx, (fmt, info) in enumerate(OUTPUT_FORMATS.items()):
            item_frame = tk.Frame(fmt_card, bg=COLORS["bg_card"])
            item_frame.pack(fill="x", padx=14, pady=(6 if idx == 0 else 4, 6))

            rb = tk.Radiobutton(
                item_frame, text=fmt,
                variable=self._output_format, value=fmt,
                font=FONTS["body_bold"],
                bg=COLORS["bg_card"],
                fg=info["color"],
                selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg_card"],
                activeforeground=info["color"],
                cursor="hand2",
                command=self._on_format_change
            )
            rb.pack(anchor="w")

            desc_key = f"format.{fmt.lower()}_desc"
            desc_lbl = tk.Label(
                item_frame, text=t(desc_key),
                font=FONTS["tiny"], bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"], justify="left"
            )
            desc_lbl.pack(anchor="w", padx=(28, 0), pady=(1, 0))
            self._fmt_desc_lbls[fmt] = desc_lbl
            self._fmt_items.append({"frame": item_frame, "rb": rb, "lbl": desc_lbl})

        # DAT sub-option
        self._dat_suboption_frame = tk.Frame(self._video_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"], highlightthickness=1)
        self._dat_suboption_frame.pack(fill="x", padx=20, pady=(6, 0))

        self._dat_mode_lbl = tk.Label(
            self._dat_suboption_frame, text=t('format.dat_mode_lbl'),
            font=FONTS["small_bold"], bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"]
        )
        self._dat_mode_lbl.pack(anchor="w", padx=14, pady=(8, 4))

        self._rb_row = tk.Frame(self._dat_suboption_frame, bg=COLORS["bg_card"])
        self._rb_row.pack(fill="x", padx=14, pady=(0, 8))
        rb_row = self._rb_row

        self._dat_raw_rb = tk.Radiobutton(
            rb_row, text=t('format.dat_raw'),
            variable=self._dat_rename_mp4, value=False,
            font=FONTS["small"], bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        )
        self._dat_raw_rb.pack(anchor="w")

        self._dat_mp4_rb = tk.Radiobutton(
            rb_row, text=t('format.dat_mp4'),
            variable=self._dat_rename_mp4, value=True,
            font=FONTS["small"], bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        )
        self._dat_mp4_rb.pack(anchor="w", pady=(4, 0))

        # ── MP4 / MOV resolution sub-panel ──────
        self._res_suboption_frame = tk.Frame(self._video_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"], highlightthickness=1)
        # hidden by default (only shown for MP4/MOV)

        self._res_title_lbl = tk.Label(
            self._res_suboption_frame, text=t('format.res_title'),
            font=FONTS["small_bold"], bg=COLORS["bg_card"],
            fg=COLORS["text_secondary"]
        )
        self._res_title_lbl.pack(anchor="w", padx=14, pady=(8, 4))

        self._res_rb_row = tk.Frame(self._res_suboption_frame, bg=COLORS["bg_card"])
        self._res_rb_row.pack(fill="x", padx=14, pady=(0, 8))
        res_rb_row = self._res_rb_row

        self._res_orig_rb = tk.Radiobutton(
            res_rb_row, text=t('format.res_orig'),
            variable=self._use_1080p, value=False,
            font=FONTS["small_bold"], bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        )
        self._res_orig_rb.pack(anchor="w")

        self._res_1080p_rb = tk.Radiobutton(
            res_rb_row, text=t('format.res_1080p'),
            variable=self._use_1080p, value=True,
            font=FONTS["small_bold"], bg=COLORS["bg_card"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_panel"],
            activebackground=COLORS["bg_card"],
            cursor="hand2"
        )
        self._res_1080p_rb.pack(anchor="w", pady=(6, 0))

        # ── Audio Only sub-panel ─────────────
        self._audio_panel = tk.Frame(self._fmt_container, bg=COLORS["bg_panel"])
        # not packed by default (video is active)

        self._audio_fmt_lbl = tk.Label(
            self._audio_panel, text=t('format.audio_lbl'),
            font=FONTS["small_bold"], bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        )
        self._audio_fmt_lbl.pack(anchor="w", padx=20, pady=(8, 4))

        self._audio_fmt_card = tk.Frame(
            self._audio_panel, bg=COLORS["bg_card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        self._audio_fmt_card.pack(fill="x", padx=20, pady=(0, 4))
        audio_fmt_card = self._audio_fmt_card

        self._audio_desc_lbls = {}
        self._audio_items = []
        for idx, (afmt, ainfo) in enumerate(AUDIO_FORMATS.items()):
            aitem_frame = tk.Frame(audio_fmt_card, bg=COLORS["bg_card"])
            aitem_frame.pack(fill="x", padx=14, pady=(6 if idx == 0 else 4, 6))

            arb = tk.Radiobutton(
                aitem_frame, text=afmt,
                variable=self._audio_format, value=afmt,
                font=FONTS["body_bold"],
                bg=COLORS["bg_card"],
                fg=ainfo["color"],
                selectcolor=COLORS["bg_panel"],
                activebackground=COLORS["bg_card"],
                activeforeground=ainfo["color"],
                cursor="hand2",
                command=self._on_audio_format_change
            )
            arb.pack(anchor="w")

            desc_key = f"format.{afmt.lower()}_desc"
            adesc_lbl = tk.Label(
                aitem_frame, text=t(desc_key),
                font=FONTS["tiny"], bg=COLORS["bg_card"],
                fg=COLORS["text_secondary"], justify="left"
            )
            adesc_lbl.pack(anchor="w", padx=(28, 0), pady=(1, 0))
            self._audio_desc_lbls[afmt] = adesc_lbl
            self._audio_items.append({"frame": aitem_frame, "rb": arb, "lbl": adesc_lbl})

        # ── Separator ───────────────────────
        self._right_sep = tk.Frame(parent, bg=COLORS["border"], height=1)
        self._right_sep.pack(fill="x", padx=20, pady=12)

        # ── Output folder section ────────────
        self._output_section_lbl = self._section_label(parent, t('output.title'))

        self._choose_folder_btn = FlatButton(
            parent, text=t('output.choose'),
            icon="💾",
            style="ghost", command=self._choose_output
        )
        self._choose_folder_btn.pack(fill="x", padx=20, pady=(10, 0))

        self._out_lbl = tk.Label(
            parent, textvariable=self._output_folder,
            font=FONTS["mono"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"], wraplength=scale_val(360),
            justify="left"
        )
        self._out_lbl.pack(fill="x", padx=20, pady=(6, 4))

        self._auto_open_chk = tk.Checkbutton(
            parent, text=t('output.auto_open'),
            variable=self._auto_open_folder,
            font=FONTS["small"], bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_dark"],
            activebackground=COLORS["bg_panel"],
            cursor="hand2", relief="flat", bd=0
        )
        self._auto_open_chk.pack(anchor="w", padx=20, pady=(4, 12))

    def _build_content(self, parent):
        # ── Title bar ───────────────────────
        self._content_title_bar = tk.Frame(parent, bg=COLORS["bg_dark"], height=scale_val(56))
        self._content_title_bar.pack(fill="x")
        self._content_title_bar.pack_propagate(False)
        title_bar = self._content_title_bar

        self._content_title = tk.Label(
            title_bar, text=t('content.title'),
            font=FONTS["heading"], bg=COLORS["bg_dark"],
            fg=COLORS["text_primary"]
        )
        self._content_title.pack(side="left", padx=20, pady=14)

        self._video_count_badge = tk.Label(
            title_bar, text=t('content.badge_empty'),
            font=FONTS["badge"], bg=COLORS["accent_dim"],
            fg=COLORS["text_primary"], padx=10, pady=4
        )
        self._video_count_badge.pack(side="left", pady=16)

        # ── Scrollable video list ─────────────
        self._list_container = tk.Frame(parent, bg=COLORS["bg_dark"])
        self._list_container.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        list_container = self._list_container

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
        self._canvas._can_scroll = True

        # Empty state
        self._empty_frame = tk.Frame(self._list_frame, bg=COLORS["bg_dark"])
        self._empty_frame.pack(fill="both", expand=True, pady=100)
        self._empty_icon_lbl = tk.Label(
            self._empty_frame, text="💿",
            font=FONTS["emoji_64"],
            bg=COLORS["bg_dark"]
        )
        self._empty_icon_lbl.pack()
        self._empty_title_lbl = tk.Label(
            self._empty_frame,
            text=t('content.empty_title'),
            font=FONTS["heading"], bg=COLORS["bg_dark"],
            fg=COLORS["text_secondary"], justify="center"
        )
        self._empty_title_lbl.pack(pady=(12, 0))
        self._empty_sub_lbl = tk.Label(
            self._empty_frame,
            text=t('content.empty_sub'),
            font=FONTS["body"], bg=COLORS["bg_dark"],
            fg=COLORS["text_muted"], justify="center"
        )
        self._empty_sub_lbl.pack(pady=(6, 0))

        # ── Scan progress bar (cyan, hidden initially) ──
        self._scan_progress_frame = tk.Frame(parent, bg=COLORS["bg_dark"])
        self._scan_progress_frame.pack(fill="x", padx=8, pady=(0, 4))
        self._scan_progress_frame.pack_forget()

        self._scan_progress_lbl = tk.Label(
            self._scan_progress_frame, text="",
            font=FONTS["body"], bg=COLORS["bg_dark"],
            fg=COLORS["text_secondary"]
        )
        self._scan_progress_lbl.pack(side="left", padx=(8, 0))

        self._scan_progress_pct = tk.Label(
            self._scan_progress_frame, text="",
            font=FONTS["body"], bg=COLORS["bg_dark"],
            fg=COLORS["cyan"]
        )
        self._scan_progress_pct.pack(side="right", padx=(0, 8))

        self._scan_progress_var = tk.DoubleVar(value=0)
        self._scan_progress_bar = ttk.Progressbar(
            parent, variable=self._scan_progress_var,
            style="Scan.Horizontal.TProgressbar"
        )
        self._scan_progress_bar.pack(fill="x", padx=8, pady=(0, 8))
        self._scan_progress_bar.pack_forget()

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
        return lbl

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
            "Scan.Horizontal.TProgressbar",
            troughcolor=COLORS["progress_bg"],
            background=COLORS["cyan"],
            lightcolor=COLORS["cyan"],
            darkcolor=COLORS["cyan"],
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
        self._poll_in_flight = False
        self._poll_drives()

    def _poll_drives(self):
        if self._poll_job:
            try:
                self.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

        if getattr(self, "_poll_in_flight", False) or self._ripping:
            self._poll_job = self.after(3000, self._poll_drives)
            return

        self._poll_in_flight = True

        def _bg_poll():
            try:
                drives = get_cd_drives()
                vcd_drives = []
                non_vcd_drives = []
                if drives:
                    for d in drives:
                        check = is_vcd_disc(d)
                        if check.is_vcd:
                            vcd_drives.append((d, check))
                        elif check.disc_type not in ("No Disc", "Empty Disc", "Unreadable Disc"):
                            non_vcd_drives.append((d, check))

                theme_changed = False
                current_effective = None
                if i18n.theme == "system" and not self._ripping:
                    current_effective = i18n.get_effective_theme()
                    expected_bg = THEME_LIGHT["bg_dark"] if current_effective == "light" else THEME_DARK["bg_dark"]
                    if COLORS["bg_dark"] != expected_bg:
                        theme_changed = True

                self.after(0, lambda: self._apply_poll_results(drives, vcd_drives, non_vcd_drives, theme_changed, current_effective))
            except Exception:
                pass
            finally:
                self._poll_in_flight = False
                self.after(0, lambda: setattr(self, "_poll_job", self.after(3000, self._poll_drives)))

        threading.Thread(target=_bg_poll, daemon=True).start()

    def _apply_poll_results(self, drives, vcd_drives, non_vcd_drives, theme_changed, current_effective):
        if self._ripping:
            return

        if vcd_drives:
            drive, check = vcd_drives[0]
            self._last_non_vcd_drive = None
            if self._vcd_path.get() != drive:
                self._vcd_path.set(drive)
                vol_name = get_volume_label(drive)
                if vol_name:
                    self._batch_base_name = vol_name
                self._detected_drive_lbl.configure(text=t('drive.drive_label').format(drive=drive[0]))
                self._detect_label.configure(
                    text=t('drive.detect_vcd'), fg=COLORS["success"]
                )
                self._drive_lbl.configure(
                    text=t('header.vcd_on').format(drive=drive[0]),
                    fg=COLORS["success"]
                )
                log_text = f"{drive} [{vol_name}]" if vol_name else drive
                self._log.log(t('log.vcd_auto').format(drive=log_text), "success")
                self.after(500, self._scan_vcd)  # Auto-scan after short delay
        elif non_vcd_drives:
            drive, check = non_vcd_drives[0]
            self._drive_lbl.configure(
                text=f"💿  {drive[0]}: ({check.disc_type})",
                fg=COLORS["warning"]
            )
            self._detected_drive_lbl.configure(text=t('drive.drive_label').format(drive=drive[0]))
            self._detect_label.configure(
                text=f"{check.disc_type}", fg=COLORS["warning"]
            )
            if self._last_non_vcd_drive != drive:
                self._last_non_vcd_drive = drive
                self._vcd_path.set(drive)
                log_msg = t('log.non_vcd_blocked').format(drive=drive, type=check.disc_type)
                if log_msg == 'log.non_vcd_blocked':
                    log_msg = f"Disc detected in drive {drive}, type: {check.disc_type}, blocking process."
                self._log.log(log_msg, "warning")
                self._show_unsupported_disc_dialog(drive, check.disc_type)
        else:
            self._last_non_vcd_drive = None
            if drives:
                self._drive_lbl.configure(
                    text=t('header.drive_no_vcd').format(drive=drives[0][0]),
                    fg=COLORS["warning"]
                )
            else:
                self._drive_lbl.configure(text=t('header.no_disc'), fg=COLORS["text_muted"])
            current_p = self._vcd_path.get()
            if current_p and any(current_p.upper().startswith(d[0].upper()) for d in drives):
                if not self._ripping:
                    self._clear_disc_info()

        # Auto-detect Windows theme changes in system mode
        if theme_changed and current_effective:
            apply_theme_palette(current_effective)
            self._on_theme_changed()

    # ── Actions ───────────────────────────────
    def _show_about(self):
        """Open the About / Settings dialog."""
        if hasattr(self, "_about_dialog") and self._about_dialog and self._about_dialog.winfo_exists():
            self._about_dialog.lift()
            self._about_dialog.focus_force()
            return

        dlg = tk.Toplevel(self)
        self._about_dialog = dlg

        def _on_destroy(event):
            if event.widget == dlg:
                self._about_dialog = None
        dlg.bind("<Destroy>", _on_destroy)

        dlg.title(t('about.title'))
        dlg.configure(bg=COLORS["bg_panel"])
        dlg.resizable(False, False)
        self._set_window_icon(dlg)
        dlg.grab_set()
        dlg_w, dlg_h = scale_val(540), scale_val(490)
        dlg.geometry(f"{dlg_w}x{dlg_h}")

        # Center the dialog over the main window
        self.update_idletasks()
        x = max(0, self.winfo_x() + (self.winfo_width()  - dlg_w) // 2)
        y = max(0, self.winfo_y() + (self.winfo_height() - dlg_h) // 2)
        dlg.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")

        try:
            dlg_hwnd = ctypes.windll.user32.GetAncestor(dlg.winfo_id(), 2) or dlg.winfo_id()
            set_window_dark_mode(dlg_hwnd, i18n.get_effective_theme() == "dark")
        except Exception:
            pass

        # ── Header Banner ─────────────────────
        header_frame = tk.Frame(dlg, bg=COLORS["bg_dark"])
        header_frame.pack(fill="x")

        header_inner = tk.Frame(header_frame, bg=COLORS["bg_dark"])
        header_inner.pack(fill="x", padx=scale_val(32), pady=scale_val(20))

        # 1. Software icon on the left
        header_icon = _get_header_icon_64()
        if header_icon:
            lbl_img = tk.Label(header_inner, image=header_icon, bg=COLORS["bg_dark"])
            lbl_img.image = header_icon
            lbl_img.pack(side="left", padx=(0, scale_val(16)))
        else:
            lbl_img = tk.Label(
                header_inner, text="💿", font=FONTS["emoji_38"],
                bg=COLORS["bg_dark"]
            )
            lbl_img.pack(side="left", padx=(0, scale_val(16)))

        # Right side of icon: text container
        header_text = tk.Frame(header_inner, bg=COLORS["bg_dark"])
        header_text.pack(side="left", fill="y")

        # 2 & 3. Main title (app name) + Version number (smaller font) to its right
        title_row = tk.Frame(header_text, bg=COLORS["bg_dark"])
        title_row.pack(anchor="w")

        lbl_app_name = tk.Label(
            title_row, text=APP_NAME,
            font=FONTS["heading"],
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"]
        )
        lbl_app_name.pack(side="left")

        lbl_version = tk.Label(
            title_row, text=f"v{APP_VERSION}",
            font=FONTS["small"],
            bg=COLORS["bg_dark"], fg=COLORS["accent"]
        )
        lbl_version.pack(side="left", padx=(8, 0), pady=(4, 0))

        # 4. Subtitle below app name: Developed by jjsiew2014-art
        lbl_author = tk.Label(
            header_text, text="Developed by jjsiew2014-art",
            font=FONTS["small"],
            bg=COLORS["bg_dark"], fg=COLORS["text_muted"]
        )
        lbl_author.pack(anchor="w", pady=(3, 0))

        # Header separator
        header_sep = tk.Frame(dlg, bg=COLORS["border"], height=1)
        header_sep.pack(fill="x")

        # ── Body rows ─────────────────────────
        body_frame = tk.Frame(dlg, bg=COLORS["bg_panel"])
        body_frame.pack(fill="x", padx=32, pady=(18, 0))

        # 1. Appearance row
        row_appearance = tk.Frame(body_frame, bg=COLORS["bg_panel"])
        row_appearance.pack(fill="x", pady=6)

        lbl_appearance_title = tk.Label(
            row_appearance, text=t('appearance.title'), font=FONTS["small"],
            bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
            width=16, anchor="w"
        )
        lbl_appearance_title.pack(side="left")

        theme_btn_frame = tk.Frame(row_appearance, bg=COLORS["bg_panel"])
        theme_btn_frame.pack(side="left")

        theme_buttons = {}
        modes = [
            ("system", t('appearance.system')),
            ("light",  t('appearance.light')),
            ("dark",   t('appearance.dark')),
        ]
        for idx, (m_key, m_label) in enumerate(modes):
            is_active = (i18n.theme == m_key)
            m_bg = COLORS["accent"] if is_active else COLORS["bg_card"]
            m_fg = COLORS.get("btn_primary_fg", "#FFFFFF") if is_active else COLORS["text_secondary"]
            btn = tk.Button(
                theme_btn_frame, text=m_label, font=FONTS["small"],
                width=11,
                bg=m_bg, fg=m_fg,
                relief="flat", bd=0, padx=2, pady=3,
                cursor="hand2" if not self._ripping else "",
                state="normal" if not self._ripping else "disabled",
                command=lambda m=m_key: set_appearance(m)
            )
            btn.pack(side="left", padx=(0, 6 if idx < len(modes) - 1 else 0))
            theme_buttons[m_key] = btn

        # 2. Scale row (placed right below Appearance)
        row_scale = tk.Frame(body_frame, bg=COLORS["bg_panel"])
        row_scale.pack(fill="x", pady=6)

        lbl_scale_title = tk.Label(
            row_scale, text=t('scale.title'), font=FONTS["small"],
            bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
            width=16, anchor="w"
        )
        lbl_scale_title.pack(side="left")

        scale_btn_frame = tk.Frame(row_scale, bg=COLORS["bg_panel"])
        scale_btn_frame.pack(side="left")

        scale_buttons = {}
        scales = [
            ("100%", t('scale.100')),
            ("125%", t('scale.125')),
            ("150%", t('scale.150')),
        ]
        for idx, (s_key, s_label) in enumerate(scales):
            is_active = (i18n.scale == s_key)
            s_bg = COLORS["accent"] if is_active else COLORS["bg_card"]
            s_fg = COLORS.get("btn_primary_fg", "#FFFFFF") if is_active else COLORS["text_secondary"]
            btn = tk.Button(
                scale_btn_frame, text=s_label, font=FONTS["small"],
                width=11,
                bg=s_bg, fg=s_fg,
                relief="flat", bd=0, padx=2, pady=3,
                cursor="hand2" if not self._ripping else "",
                state="normal" if not self._ripping else "disabled",
                command=lambda sk=s_key: set_scale(sk)
            )
            btn.pack(side="left", padx=(0, 6 if idx < len(scales) - 1 else 0))
            scale_buttons[s_key] = btn

        # 3. Language row
        row_language = tk.Frame(body_frame, bg=COLORS["bg_panel"])
        row_language.pack(fill="x", pady=6)

        lbl_lang_title = tk.Label(
            row_language, text=t('language.title'), font=FONTS["small"],
            bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
            width=16, anchor="w"
        )
        lbl_lang_title.pack(side="left")

        btn_lang_frame = tk.Frame(row_language, bg=COLORS["bg_panel"])
        btn_lang_frame.pack(side="left")

        en_active = (i18n.lang == "en")
        zh_active = (i18n.lang == "zh_CN")
        en_bg = COLORS["accent"] if en_active else COLORS["bg_card"]
        zh_bg = COLORS["accent"] if zh_active else COLORS["bg_card"]
        en_fg = COLORS.get("btn_primary_fg", "#FFFFFF") if en_active else COLORS["text_secondary"]
        zh_fg = COLORS.get("btn_primary_fg", "#FFFFFF") if zh_active else COLORS["text_secondary"]

        btn_en = tk.Button(
            btn_lang_frame, text="EN", font=FONTS["small"],
            width=5, bg=en_bg, fg=en_fg,
            relief="flat", bd=0, pady=3, cursor="hand2",
            command=lambda: set_lang("en")
        )
        btn_en.pack(side="left", padx=(0, 6))

        btn_zh = tk.Button(
            btn_lang_frame, text="中", font=FONTS["small"],
            width=5, bg=zh_bg, fg=zh_fg,
            relief="flat", bd=0, pady=3, cursor="hand2",
            command=lambda: set_lang("zh_CN")
        )
        btn_zh.pack(side="left")

        # 3. FFmpeg status row
        row_ffmpeg = tk.Frame(body_frame, bg=COLORS["bg_panel"])
        row_ffmpeg.pack(fill="x", pady=6)

        lbl_ffmpeg_title = tk.Label(
            row_ffmpeg, text=t('about.ffmpeg'), font=FONTS["small"],
            bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
            width=16, anchor="w"
        )
        lbl_ffmpeg_title.pack(side="left")

        ffmpeg_text  = t('about.ready') if self._ffmpeg else t('about.not_found')
        ffmpeg_color = COLORS["success"] if self._ffmpeg else COLORS["error"]
        lbl_ffmpeg_status = tk.Label(
            row_ffmpeg, text=ffmpeg_text, font=FONTS["body"],
            bg=COLORS["bg_panel"], fg=ffmpeg_color
        )
        lbl_ffmpeg_status.pack(side="left")

        # 4. FFmpeg path row
        row_ffmpeg_path = tk.Frame(body_frame, bg=COLORS["bg_panel"])
        row_ffmpeg_path.pack(fill="x", pady=6)

        lbl_ffmpeg_path_title = tk.Label(
            row_ffmpeg_path, text=t('about.ffmpeg_path'), font=FONTS["small"],
            bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
            width=16, anchor="w"
        )
        lbl_ffmpeg_path_title.pack(side="left")

        path_text = os.path.basename(self._ffmpeg) if self._ffmpeg else "—"
        path_color = COLORS["text_secondary"] if self._ffmpeg else COLORS["text_muted"]
        lbl_path = tk.Label(
            row_ffmpeg_path, text=path_text, font=FONTS["body"],
            bg=COLORS["bg_panel"], fg=path_color
        )
        lbl_path.pack(side="left")
        if self._ffmpeg:
            Tooltip(lbl_path, self._ffmpeg)

        # ── Separator ─────────────────────────
        body_sep = tk.Frame(dlg, bg=COLORS["border"], height=1)
        body_sep.pack(fill="x", padx=32, pady=(18, 0))

        # ── Footer ────────────────────────────
        lbl_license = tk.Label(
            dlg, text=t('about.license'),
            font=FONTS["small"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"]
        )
        lbl_license.pack(pady=(12, 0))

        # ── Close button ──────────────────────
        btn_close = tk.Button(
            dlg, text=t('about.close'),
            font=FONTS["body"], bg=COLORS["accent"],
            fg=COLORS.get("btn_primary_fg", "#FFFFFF"), relief="flat", bd=0,
            padx=32, pady=7, cursor="hand2",
            activebackground=COLORS["accent_hover"],
            activeforeground=COLORS.get("btn_primary_fg", "#FFFFFF"),
            command=dlg.destroy
        )
        btn_close.pack(pady=(12, 20))

        def update_dlg_lang():
            dlg.title(t('about.title'))
            lbl_appearance_title.configure(text=t('appearance.title'))
            theme_buttons["system"].configure(text=t('appearance.system'))
            theme_buttons["light"].configure(text=t('appearance.light'))
            theme_buttons["dark"].configure(text=t('appearance.dark'))
            lbl_scale_title.configure(text=t('scale.title'))
            scale_buttons["100%"].configure(text=t('scale.100'))
            scale_buttons["125%"].configure(text=t('scale.125'))
            scale_buttons["150%"].configure(text=t('scale.150'))
            lbl_lang_title.configure(text=t('language.title'))
            lbl_ffmpeg_title.configure(text=t('about.ffmpeg'))
            lbl_ffmpeg_status.configure(text=t('about.ready') if self._ffmpeg else t('about.not_found'))
            lbl_ffmpeg_path_title.configure(text=t('about.ffmpeg_path'))
            lbl_license.configure(text=t('about.license'))
            btn_close.configure(text=t('about.close'))

            en_act = (i18n.lang == "en")
            zh_act = (i18n.lang == "zh_CN")
            btn_en.configure(
                bg=COLORS["accent"] if en_act else COLORS["bg_card"],
                fg=COLORS.get("btn_primary_fg", "#FFFFFF") if en_act else COLORS["text_secondary"]
            )
            btn_zh.configure(
                bg=COLORS["accent"] if zh_act else COLORS["bg_card"],
                fg=COLORS.get("btn_primary_fg", "#FFFFFF") if zh_act else COLORS["text_secondary"]
            )

        def update_dlg_theme():
            dlg.configure(bg=COLORS["bg_panel"])
            try:
                d_hwnd = ctypes.windll.user32.GetAncestor(dlg.winfo_id(), 2) or dlg.winfo_id()
                set_window_dark_mode(d_hwnd, i18n.get_effective_theme() == "dark")
            except Exception:
                pass
            header_frame.configure(bg=COLORS["bg_dark"])
            header_inner.configure(bg=COLORS["bg_dark"])
            lbl_img.configure(bg=COLORS["bg_dark"])
            header_text.configure(bg=COLORS["bg_dark"])
            title_row.configure(bg=COLORS["bg_dark"])
            lbl_app_name.configure(bg=COLORS["bg_dark"], fg=COLORS["text_primary"])
            lbl_version.configure(bg=COLORS["bg_dark"], fg=COLORS["accent"])
            lbl_author.configure(bg=COLORS["bg_dark"], fg=COLORS["text_muted"])
            header_sep.configure(bg=COLORS["border"])

            body_frame.configure(bg=COLORS["bg_panel"])
            row_appearance.configure(bg=COLORS["bg_panel"])
            lbl_appearance_title.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
            theme_btn_frame.configure(bg=COLORS["bg_panel"])

            for m_key, btn in theme_buttons.items():
                is_act = (i18n.theme == m_key)
                m_bg = COLORS["accent"] if is_act else COLORS["bg_card"]
                m_fg = COLORS.get("btn_primary_fg", "#FFFFFF") if is_act else COLORS["text_secondary"]
                btn.configure(
                    bg=m_bg, fg=m_fg,
                    activebackground=COLORS["accent_hover"] if is_act else COLORS["bg_hover"],
                    activeforeground=m_fg
                )

            row_scale.configure(bg=COLORS["bg_panel"])
            lbl_scale_title.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
            scale_btn_frame.configure(bg=COLORS["bg_panel"])

            for sk, btn in scale_buttons.items():
                is_act = (i18n.scale == sk)
                s_bg = COLORS["accent"] if is_act else COLORS["bg_card"]
                s_fg = COLORS.get("btn_primary_fg", "#FFFFFF") if is_act else COLORS["text_secondary"]
                btn.configure(
                    bg=s_bg, fg=s_fg,
                    activebackground=COLORS["accent_hover"] if is_act else COLORS["bg_hover"],
                    activeforeground=s_fg
                )

            row_language.configure(bg=COLORS["bg_panel"])
            lbl_lang_title.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
            btn_lang_frame.configure(bg=COLORS["bg_panel"])
            en_act = (i18n.lang == "en")
            zh_act = (i18n.lang == "zh_CN")
            btn_en.configure(
                bg=COLORS["accent"] if en_act else COLORS["bg_card"],
                fg=COLORS.get("btn_primary_fg", "#FFFFFF") if en_act else COLORS["text_secondary"],
                activebackground=COLORS["accent_hover"] if en_act else COLORS["bg_hover"]
            )
            btn_zh.configure(
                bg=COLORS["accent"] if zh_act else COLORS["bg_card"],
                fg=COLORS.get("btn_primary_fg", "#FFFFFF") if zh_act else COLORS["text_secondary"],
                activebackground=COLORS["accent_hover"] if zh_act else COLORS["bg_hover"]
            )

            row_ffmpeg.configure(bg=COLORS["bg_panel"])
            lbl_ffmpeg_title.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
            lbl_ffmpeg_status.configure(
                bg=COLORS["bg_panel"],
                fg=COLORS["success"] if self._ffmpeg else COLORS["error"]
            )
            row_ffmpeg_path.configure(bg=COLORS["bg_panel"])
            lbl_ffmpeg_path_title.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
            lbl_path.configure(
                bg=COLORS["bg_panel"],
                fg=COLORS["text_secondary"] if self._ffmpeg else COLORS["text_muted"]
            )
            body_sep.configure(bg=COLORS["border"])
            lbl_license.configure(bg=COLORS["bg_panel"], fg=COLORS["text_muted"])
            btn_close.configure(
                bg=COLORS["accent"],
                fg=COLORS.get("btn_primary_fg", "#FFFFFF"),
                activebackground=COLORS["accent_hover"],
                activeforeground=COLORS.get("btn_primary_fg", "#FFFFFF")
            )

        def update_dlg_scale():
            dlg.update_idletasks()
            dw = scale_val(540)
            dh = scale_val(490)
            rx = self.winfo_x()
            ry = self.winfo_y()
            rw = self.winfo_width()
            rh = self.winfo_height()
            nx = max(0, rx + (rw - dw) // 2)
            ny = max(0, ry + (rh - dh) // 2)
            dlg.geometry(f"{dw}x{dh}+{nx}+{ny}")

            new_icon = _get_header_icon_64()
            if new_icon:
                lbl_img.configure(image=new_icon)
                lbl_img.image = new_icon

            for sk, btn in scale_buttons.items():
                is_act = (i18n.scale == sk)
                s_bg = COLORS["accent"] if is_act else COLORS["bg_card"]
                s_fg = COLORS.get("btn_primary_fg", "#FFFFFF") if is_act else COLORS["text_secondary"]
                btn.configure(
                    bg=s_bg, fg=s_fg,
                    activebackground=COLORS["accent_hover"] if is_act else COLORS["bg_hover"],
                    activeforeground=s_fg
                )

        dlg.update_theme = update_dlg_theme
        dlg.update_lang = update_dlg_lang
        dlg.update_scale = update_dlg_scale

        def set_appearance(mode):
            if self._ripping:
                return
            i18n.switch_theme(mode)
            update_dlg_theme()

        def set_scale(sk):
            if self._ripping:
                return
            i18n.switch_scale(sk)
            update_dlg_scale()

        def set_lang(l):
            i18n.switch(l)
            update_dlg_lang()

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.bind("<Return>", lambda e: dlg.destroy())

    def _browse_source(self):
        folder = filedialog.askdirectory(title="Select VCD folder")
        if not folder:
            return
        self._vcd_path.set(folder)
        self._detect_label.configure(text=t('drive.detecting'), fg=COLORS["accent"])
        def check_bg():
            check = is_vcd_disc(folder)
            self.after(0, lambda: self._apply_browse_check(folder, check))
        threading.Thread(target=check_bg, daemon=True).start()

    def _apply_browse_check(self, folder, check):
        if check.is_vcd:
            self._last_non_vcd_drive = None
            self._log.log(t('log.vcd_found').format(folder=folder), "success")
            self._detect_label.configure(text=t('drive.folder_selected'), fg=COLORS["success"])
        else:
            log_msg = t('log.non_vcd_blocked').format(drive=folder, type=check.disc_type)
            if log_msg == 'log.non_vcd_blocked':
                log_msg = f"Disc detected in drive {folder}, type: {check.disc_type}, blocking process."
            self._log.log(log_msg, "warning")
            self._detect_label.configure(text=f"{check.disc_type}", fg=COLORS["warning"])
            self._show_unsupported_disc_dialog(folder, check.disc_type)

    def _scan_vcd(self):
        path = self._vcd_path.get().strip()
        if not path:
            messagebox.showwarning(t('messageboxes.no_source_title'), t('messageboxes.no_source_msg'))
            return

        self._videos.clear()
        self._clear_list()
        self._log.log(t('log.scan_dir').format(path=path), "accent")

        # Show scan progress bar
        self._scan_progress_lbl.configure(text=t('content.scan_prog_folder').format(name=path))
        self._scan_progress_pct.configure(text="0%")
        self._scan_progress_var.set(0)
        self._scan_progress_frame.pack(fill="x", padx=8, pady=(0, 4))
        self._scan_progress_bar.pack(fill="x", padx=8, pady=(0, 8))

        def after_scan(files):
            if not files:
                self._scan_progress_frame.pack_forget()
                self._scan_progress_bar.pack_forget()
                self._log.log(t('log.no_vid'), "warning")
                messagebox.showinfo(
                    t('messageboxes.no_files_title'),
                    t('messageboxes.no_files_msg')
                )
                return

            total = len(files)
            self._log.log(t('log.found_files').format(total=total), "info")
            self._video_count_badge.configure(text=t('content.badge').format(n=total))

            def probe_all():
                infos = []
                for i, f in enumerate(files):
                    fname = Path(f).name
                    pct = int((i / total) * 100)
                    self.after(0, lambda idx=i, fn=fname, p=pct: (
                        self._scan_progress_lbl.configure(text=t('content.scan_prog_read').format(idx=idx+1, total=total, name=fn)),
                        self._scan_progress_pct.configure(text=f"{p}%"),
                        self._scan_progress_var.set(p)
                    ))
                    if self._ffprobe:
                        info = probe_video(self._ffprobe, f)
                    else:
                        info = {
                            "path":     f,
                            "filename": sanitize_filename(fname),
                            "size_mb":  round(os.path.getsize(f) / 1024**2, 1),
                            "duration": 0, "width": 352, "height": 240,
                            "codec": "MPEG1", "fps": "29 fps", "bitrate": "~1150 kbps",
                        }
                    infos.append(info)
                    self.after(0, lambda info_item=info: self._log.log(
                        f"  {info_item['filename']}  —  {info_item['size_mb']} MB  {format_duration(info_item['duration'])}", "info"
                    ))

                # Finish scan progress
                self.after(0, lambda: (
                    self._scan_progress_var.set(100),
                    self._scan_progress_pct.configure(text="100%"),
                    self._populate_list(infos),
                    self.after(600, lambda: (
                        self._scan_progress_frame.pack_forget(),
                        self._scan_progress_bar.pack_forget()
                    ))
                ))

            threading.Thread(target=probe_all, daemon=True).start()

        def do_scan_bg():
            if not os.path.isdir(path):
                self.after(0, lambda: (
                    self._scan_progress_frame.pack_forget(),
                    self._scan_progress_bar.pack_forget(),
                    messagebox.showerror(t('messageboxes.invalid_path_title'), t('messageboxes.invalid_path_msg').format(path=path))
                ))
                return

            folder_display = get_volume_label(path) or Path(path).name or path
            self.after(0, lambda: self._scan_progress_lbl.configure(
                text=t('content.scan_prog_folder').format(name=folder_display)
            ))

            # Validate disc format - intercept non-VCD discs
            check = is_vcd_disc(path)
            if not check.is_vcd:
                def handle_non_vcd():
                    self._scan_progress_frame.pack_forget()
                    self._scan_progress_bar.pack_forget()
                    log_msg = t('log.non_vcd_blocked').format(drive=path, type=check.disc_type)
                    if log_msg == 'log.non_vcd_blocked':
                        log_msg = f"Disc detected in drive {path}, type: {check.disc_type}, blocking process."
                    self._log.log(log_msg, "warning")
                    self._show_unsupported_disc_dialog(path, check.disc_type)
                self.after(0, handle_non_vcd)
                return

            files = find_dat_files(path)
            if not files:
                # Fallback: look for any video-like files
                exts = [".dat", ".mpg", ".mpeg", ".vob", ".mp4", ".avi"]
                for ext in exts:
                    try:
                        files.extend(str(p) for p in Path(path).rglob(f"*{ext}"))
                    except Exception:
                        pass
            self.after(0, lambda: after_scan(files))

        threading.Thread(target=do_scan_bg, daemon=True).start()

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
        self._log.log(t('log.loaded').format(total=len(infos)), "success")

    def _clear_list(self):
        for w in self._list_frame.winfo_children():
            if not hasattr(self, "_empty_frame") or w is not self._empty_frame:
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
            text=t('selection.count').format(n=n, total=total),
            fg=COLORS["accent"] if n else COLORS["text_muted"]
        )

    def _choose_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self._output_folder.set(folder)
            self._log.log(t('log.out_set').format(folder=folder), "info")

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
        self._taskbar_progress.set_paused()
        self._log.log(t('log.cancel_req'), "warning")
        if self._current_proc and self._current_proc.poll() is None:
            try:
                kill_process_tree(self._current_proc, force=True)
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
                t('messageboxes.ffmpeg_req_title'),
                t('messageboxes.ffmpeg_req_msg')
            )
            return

        selected = sorted(self._selected_indices)
        if not selected:
            if self._videos:
                if messagebox.askyesno(
                    t('messageboxes.no_sel_title'),
                    t('messageboxes.no_sel_msg')
                ):
                    self._select_all()
                    selected = list(range(len(self._videos)))
                else:
                    return
            else:
                messagebox.showwarning(t('messageboxes.no_vid_title'), t('messageboxes.no_vid_msg'))
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
        if hasattr(self, "_clear_all_btn"):
            self._clear_all_btn.configure(
                state="disabled",
                fg=COLORS["text_muted"],
                cursor=""
            )
        self._progress_bar.pack(fill="x", padx=8, pady=(0, 8))
        self._progress_var.set(0)
        self._taskbar_progress.set_value(0, 100)
        self._log.log(
            t('log.start_ext').format(total=len(videos_to_rip), fmt=fmt),
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
        was_timed_out = False

        # Ensure destination directory exists
        try:
            os.makedirs(out_folder, exist_ok=True)
        except Exception:
            pass

        # Calculate total duration for time-based progress
        total_duration = sum(v.get("duration", 0) for v in videos)
        completed_duration = 0.0

        for i, video in enumerate(videos):
            if self._cancel_requested:
                was_cancelled = True
                break

            raw_stem = Path(video["filename"]).stem
            stem = video.get("custom_stem") or raw_stem
            stem = sanitize_filename(stem, fallback=f"track_{i+1}")
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
                out_name  = os.path.basename(out_path)

            # Update progress label with current file info
            if total_duration > 0:
                overall_pct = (completed_duration / total_duration) * 100
            else:
                overall_pct = (i / total) * 100
            self.after(0, lambda v=video, idx=i, pct=overall_pct: (
                self._progress_lbl.configure(
                    text=t('content.rip_prog_proc').format(idx=idx+1, total=total, name=v['filename'])
                ),
                self._progress_pct.configure(text=f"{int(pct)}%"),
                self._progress_var.set(pct),
                self._taskbar_progress.set_value(int(pct), 100)
            ))
            self.after(0, lambda v=video: self._log.log(
                t('log.extracting').format(name=v['filename'], out=os.path.basename(out_path)), "info"
            ))

            if fmt == "DAT" and self._output_mode.get() == "video":
                # Direct binary file copy without FFmpeg (with watchdog & queue)
                try:
                    src_path = video["path"]
                    chunk_size = 1024 * 1024  # 1MB chunk
                    file_cancelled = False
                    dat_timed_out = False
                    src_size = os.path.getsize(src_path)
                    video_dur = video.get("duration", 0)
                    bytes_copied = 0

                    chunk_queue = queue.Queue(maxsize=8)
                    stop_reader = threading.Event()

                    def dat_reader():
                        try:
                            with open(src_path, "rb") as fsrc:
                                while not stop_reader.is_set():
                                    buf = fsrc.read(chunk_size)
                                    if not buf:
                                        chunk_queue.put(None)
                                        break
                                    chunk_queue.put(buf)
                        except Exception as read_ex:
                            chunk_queue.put(read_ex)

                    reader_t = threading.Thread(target=dat_reader, daemon=True)
                    reader_t.start()

                    last_heartbeat = time.time()
                    with open(out_path, "wb") as fdst:
                        while True:
                            if self._cancel_requested:
                                stop_reader.set()
                                file_cancelled = True
                                break

                            try:
                                item = chunk_queue.get(timeout=0.2)
                            except queue.Empty:
                                if time.time() - last_heartbeat > DISC_READ_TIMEOUT_SECONDS:
                                    stop_reader.set()
                                    dat_timed_out = True
                                    was_timed_out = True
                                    self.after(0, lambda v=video: self._log.log(
                                        t('log.read_timeout').format(name=v['filename'], timeout=int(DISC_READ_TIMEOUT_SECONDS)),
                                        "warning"
                                    ))
                                    break
                                continue

                            if item is None:
                                break
                            if isinstance(item, Exception):
                                raise item

                            last_heartbeat = time.time()
                            fdst.write(item)
                            bytes_copied += len(item)
                            if src_size > 0 and total_duration > 0:
                                file_progress = (bytes_copied / src_size) * video_dur
                                overall = (completed_duration + file_progress) / total_duration * 100
                                self.after(0, lambda p=overall, idx=i: (
                                    self._progress_var.set(p),
                                    self._progress_pct.configure(text=f"{int(p)}%"),
                                    self._taskbar_progress.set_value(int(p), 100)
                                ))

                    if file_cancelled or self._cancel_requested:
                        was_cancelled = True
                        if os.path.exists(out_path):
                            try:
                                os.remove(out_path)
                            except Exception:
                                pass
                        break

                    if dat_timed_out:
                        # Keep partial file for damaged disc
                        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                            part_size = round(os.path.getsize(out_path) / 1024**2, 1)
                            self.after(0, lambda n=out_name, s=part_size: self._log.log(
                                t('log.saved_partial').format(name=n, size=s), "warning"
                            ))
                        break

                    size = round(os.path.getsize(out_path) / 1024**2, 1)
                    success += 1
                    completed_duration += video.get("duration", 0)
                    self.after(0, lambda n=out_name, s=size: self._log.log(
                        t('log.raw_dat_ok').format(name=n, size=s), "success"
                    ))
                except Exception as e:
                    errors += 1
                    self.after(0, lambda err=str(e): self._log.log(
                        t('log.copy_err').format(err=err), "error"
                    ))
            else:
                # Use FFmpeg to convert/rip video with error tolerance and low priority
                ffmpeg_args = list(fmt_cfg["args"])
                if use_1080p and fmt in ("MP4", "MOV"):
                    # Upscale VCD (352x240 / 352x288) to 1440x1080 (4:3 at 1080p)
                    # using Lanczos for sharpest quality upscale
                    ffmpeg_args = ["-vf", "scale=1440:1080:flags=lanczos"] + ffmpeg_args
                cmd = [
                    self._ffmpeg,
                    "-nostdin",
                    "-err_detect", "ignore_err",
                    "-fflags", "+discardcorrupt",
                    "-i", video["path"],
                    *ffmpeg_args,
                    "-max_error_rate", "1.0",
                    "-y",
                    out_path
                ]

                try:
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=get_subprocess_env(),
                        creationflags=subprocess.CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS
                    )
                    self._current_proc = proc
                    set_low_process_priority(proc)

                    video_dur = video.get("duration", 0)
                    line_queue = queue.Queue()

                    def read_stdout():
                        try:
                            for line in iter(proc.stdout.readline, ''):
                                line_queue.put(line)
                        except Exception:
                            pass
                        finally:
                            try:
                                proc.stdout.close()
                            except Exception:
                                pass
                            line_queue.put(None)

                    reader_t = threading.Thread(target=read_stdout, daemon=True)
                    reader_t.start()

                    last_heartbeat = time.time()
                    proc_timed_out = False

                    while True:
                        if self._cancel_requested:
                            kill_process_tree(proc, force=True)
                            break

                        try:
                            line = line_queue.get(timeout=0.2)
                        except queue.Empty:
                            if proc.poll() is not None:
                                while not line_queue.empty():
                                    rem = line_queue.get_nowait()
                                    if rem is None:
                                        break
                                break

                            if (time.time() - last_heartbeat) > DISC_READ_TIMEOUT_SECONDS:
                                proc_timed_out = True
                                was_timed_out = True
                                self.after(0, lambda v=video: self._log.log(
                                    t('log.read_timeout').format(name=v['filename'], timeout=int(DISC_READ_TIMEOUT_SECONDS)),
                                    "warning"
                                ))
                                terminate_and_kill(proc, graceful_timeout=GRACEFUL_TERMINATE_TIMEOUT)
                                break
                            continue

                        if line is None:
                            break

                        last_heartbeat = time.time()
                        line = line.strip()
                        if line and ("frame=" in line or "speed=" in line):
                            self.after(0, lambda l=line: self._log.log(l, "info"))
                            # Parse time= for fine-grained progress
                            time_match = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line)
                            if time_match and video_dur > 0 and total_duration > 0:
                                h, m, s = time_match.groups()
                                current_secs = int(h) * 3600 + int(m) * 60 + float(s)
                                file_progress = min(current_secs, video_dur)
                                overall = (completed_duration + file_progress) / total_duration * 100
                                overall = min(overall, 99.9)  # Don't hit 100% until truly done
                                self.after(0, lambda p=overall: (
                                    self._progress_var.set(p),
                                    self._progress_pct.configure(text=f"{int(p)}%"),
                                    self._taskbar_progress.set_value(int(p), 100)
                                ))
                        elif any(err_kw in line.lower() for err_kw in ("error", "corrupt", "invalid")):
                            self.after(0, lambda l=line: self._log.log(l, "warning"))

                    try:
                        proc.wait(timeout=2)
                    except Exception:
                        pass
                    self._current_proc = None

                    if self._cancel_requested:
                        was_cancelled = True
                        if os.path.exists(out_path):
                            try:
                                os.remove(out_path)
                            except Exception:
                                pass
                        break

                    if proc_timed_out:
                        # Preserve partially recovered video file
                        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                            part_size = round(os.path.getsize(out_path) / 1024**2, 1)
                            self.after(0, lambda n=out_name, s=part_size: self._log.log(
                                t('log.saved_partial').format(name=n, size=s), "warning"
                            ))
                        break

                    if proc.returncode == 0:
                        size = round(os.path.getsize(out_path) / 1024**2, 1)
                        success += 1
                        completed_duration += video.get("duration", 0)
                        self.after(0, lambda n=out_name, s=size: self._log.log(
                            t('log.saved_ok').format(name=n, size=s), "success"
                        ))
                    else:
                        errors += 1
                        completed_duration += video.get("duration", 0)
                        self.after(0, lambda v=video: self._log.log(
                            t('log.ffmpeg_err').format(name=v['filename']), "error"
                        ))

                except Exception as e:
                    errors += 1
                    self.after(0, lambda err=str(e): self._log.log(
                        t('log.exc').format(err=err), "error"
                    ))

        # Done
        self.after(0, lambda: self._rip_done(
            total, success, errors, out_folder,
            cancelled=(was_cancelled or self._cancel_requested),
            timed_out=was_timed_out
        ))

    def _rip_done(self, total, success, errors, out_folder, cancelled=False, timed_out=False):
        self._ripping = False
        self._current_proc = None
        self._rip_btn.configure_state(True)
        self._stop_btn.configure_state(False)
        if hasattr(self, "_clear_all_btn"):
            self._clear_all_btn.configure(
                state="normal",
                fg=COLORS["text_secondary"],
                cursor="hand2"
            )

        if timed_out:
            self._taskbar_progress.set_paused()
            self._progress_lbl.configure(text=t('messageboxes.timeout_title'))
            self._log.log(t('messageboxes.timeout_msg'), "warning")
            messagebox.showwarning(
                t('messageboxes.timeout_title'),
                t('messageboxes.timeout_msg')
            )
            self._taskbar_progress.reset()
        elif cancelled:
            self._taskbar_progress.reset()
            self._progress_lbl.configure(text=t('content.rip_prog_stop').format(success=success, total=total))
            self._log.log(t('log.stop_sum').format(success=success), "warning")
            messagebox.showinfo(
                t('messageboxes.stop_title'),
                t('messageboxes.stop_msg').format(success=success, folder=out_folder)
            )
        elif errors == 0:
            self._progress_var.set(100)
            self._progress_lbl.configure(text=t('content.rip_prog_done').format(success=success, total=total))
            self._progress_pct.configure(text="100%")
            self._taskbar_progress.set_value(100, 100)
            self._log.log(
                t('log.done_ok').format(success=success, folder=out_folder),
                "success"
            )
            # Auto-open output folder if checked
            if self._auto_open_folder.get():
                try:
                    os.startfile(out_folder)
                except Exception as e:
                    self._log.log(t('log.open_err').format(err=e), "warning")

            # Only prompt to eject disc
            if messagebox.askyesno(
                t('messageboxes.eject_title'),
                t('messageboxes.eject_msg').format(success=success)
            ):
                self._eject_disc()
            self._taskbar_progress.reset()
        else:
            self._taskbar_progress.set_error()
            self._log.log(
                t('log.done_err').format(errors=errors, success=success, folder=out_folder),
                "warning"
            )
            messagebox.showwarning(
                t('messageboxes.err_title'),
                t('messageboxes.err_msg').format(success=success, errors=errors)
            )
            self._taskbar_progress.reset()

    # ── Canvas scroll helpers ─────────────────
    def _on_list_configure(self, _):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._on_global_mousewheel(event)

    def _on_global_mousewheel(self, event):
        """Global mousewheel scroll handler: scrolls only the canvas under the mouse pointer."""
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            widget = None
        if not widget:
            return
        w = widget
        while w:
            if isinstance(w, tk.Canvas) and getattr(w, "_can_scroll", False):
                w.yview_scroll(-1 * (event.delta // 120), "units")
                return "break"
            w = getattr(w, "master", None)

    # ── Unsupported Disc Dialog ───────────────
    def _show_unsupported_disc_dialog(self, drive_path, disc_type):
        """Show modal dialog warning user that the detected disc is not a VCD."""
        if getattr(self, "_unsupported_dlg_open", False):
            return
        self._unsupported_dlg_open = True

        dlg = tk.Toplevel(self)
        dlg.title(t('messageboxes.unsupported_disc_title'))
        dlg.configure(bg=COLORS["bg_panel"])
        dlg.resizable(False, False)
        self._set_window_icon(dlg)

        # Center dialog relative to main window
        try:
            self.update_idletasks()
            w, h = scale_val(480), scale_val(240)
            x = max(0, self.winfo_x() + (self.winfo_width() - w) // 2)
            y = max(0, self.winfo_y() + (self.winfo_height() - h) // 2)
            dlg.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        dlg.grab_set()

        def on_close():
            self._unsupported_dlg_open = False
            try:
                dlg.destroy()
            except Exception:
                pass

        dlg.protocol("WM_DELETE_WINDOW", on_close)

        content = tk.Frame(dlg, bg=COLORS["bg_panel"], padx=scale_val(24), pady=scale_val(20))
        content.pack(fill="both", expand=True)

        # Top row: warning icon + title & type badge
        top_row = tk.Frame(content, bg=COLORS["bg_panel"])
        top_row.pack(fill="x", pady=(0, scale_val(10)))

        icon_lbl = tk.Label(
            top_row, text="⚠", font=FONTS["title"],
            bg=COLORS["bg_panel"], fg=COLORS["warning"]
        )
        icon_lbl.pack(side="left", padx=(0, scale_val(14)), anchor="n")

        title_col = tk.Frame(top_row, bg=COLORS["bg_panel"])
        title_col.pack(side="left", fill="x", expand=True)

        t_lbl = tk.Label(
            title_col, text=t('messageboxes.unsupported_disc_title'),
            font=FONTS["subhead"], bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
            anchor="w"
        )
        t_lbl.pack(anchor="w")

        clean_drive = drive_path.rstrip("\\") if drive_path else ""
        badge_text = f"Drive: {clean_drive}  •  Format: {disc_type}"
        badge_lbl = tk.Label(
            title_col, text=badge_text,
            font=FONTS["small"], bg=COLORS["accent_dim"], fg=COLORS["text_primary"],
            padx=scale_val(8), pady=scale_val(2)
        )
        badge_lbl.pack(anchor="w", pady=(scale_val(4), 0))

        # Message body
        msg_lbl = tk.Label(
            content, text=t('messageboxes.unsupported_disc_msg'),
            font=FONTS["body"], bg=COLORS["bg_panel"], fg=COLORS["text_secondary"],
            wraplength=scale_val(420), justify="left", anchor="w"
        )
        msg_lbl.pack(fill="x", pady=(0, 16))

        # Button row
        btn_row = tk.Frame(content, bg=COLORS["bg_panel"])
        btn_row.pack(fill="x", side="bottom")

        def do_eject():
            on_close()
            self._eject_disc(drive_path)

        def do_ok():
            on_close()

        # Eject Disc button (accent color)
        btn_eject = tk.Button(
            btn_row, text=f"⏏  {t('messageboxes.btn_eject')}",
            font=FONTS["body"], bg=COLORS["accent"],
            fg=COLORS["text_primary"], relief="flat", bd=0,
            padx=18, pady=7, cursor="hand2",
            activebackground=COLORS["accent_hover"],
            activeforeground=COLORS["text_primary"],
            command=do_eject
        )
        btn_eject.pack(side="right", padx=(8, 0))

        # OK button (card style)
        btn_ok = tk.Button(
            btn_row, text=t('messageboxes.btn_ok'),
            font=FONTS["body"], bg=COLORS["bg_card"],
            fg=COLORS["text_primary"], relief="flat", bd=0,
            padx=20, pady=7, cursor="hand2",
            activebackground=COLORS["bg_hover"],
            activeforeground=COLORS["text_primary"],
            command=do_ok
        )
        btn_ok.pack(side="right")

        dlg.bind("<Return>", lambda e: do_ok())
        dlg.bind("<Escape>", lambda e: do_ok())

    def _clear_all_action(self):
        """Clear loaded video files list and reset progress indicators."""
        if self._ripping:
            self._stop_rip()

        self._videos.clear()
        self._cards.clear()
        self._selected_indices.clear()
        self._batch_base_name = "Track"

        self._clear_list()
        if hasattr(self, "_empty_frame") and self._empty_frame.winfo_exists():
            self._empty_frame.pack(fill="both", expand=True, pady=100)

        self._video_count_badge.configure(text=t('content.badge_empty'))
        self._sel_count_lbl.configure(
            text=t('selection.count').format(n=0, total=0),
            fg=COLORS["text_muted"]
        )

        # Reset main ripping progress
        self._progress_var.set(0)
        self._progress_lbl.configure(text="")
        self._progress_pct.configure(text="")
        self._progress_bar.pack_forget()

        # Reset scan progress if active
        if hasattr(self, "_scan_progress_var"):
            self._scan_progress_var.set(0)
        if hasattr(self, "_scan_progress_lbl"):
            self._scan_progress_lbl.configure(text="")
        if hasattr(self, "_scan_progress_pct"):
            self._scan_progress_pct.configure(text="")
        if hasattr(self, "_scan_progress_frame"):
            self._scan_progress_frame.pack_forget()
        if hasattr(self, "_scan_progress_bar"):
            self._scan_progress_bar.pack_forget()

        # Reset Windows taskbar progress
        if hasattr(self, "_taskbar_progress"):
            self._taskbar_progress.reset()

        self._log.log(t('log.cleared_all'), "info")

    # ── Drive eject & Reset ───────────────────
    def _clear_disc_info(self):
        """Reset and clear all scanned disc tracks and drive info UI."""
        self._taskbar_progress.reset()
        self._videos.clear()
        self._cards.clear()
        self._selected_indices.clear()
        self._vcd_path.set("")
        self._batch_base_name = "Track"
        self._last_non_vcd_drive = None

        self._clear_list()
        if hasattr(self, "_empty_frame") and self._empty_frame.winfo_exists():
            self._empty_frame.pack(fill="both", expand=True, pady=100)

        self._drive_lbl.configure(text=t('header.no_disc'), fg=COLORS["text_muted"])
        self._detect_icon.configure(text="💿")
        self._detect_label.configure(text=t('drive.insert_vcd'), fg=COLORS["text_muted"])
        self._detected_drive_lbl.configure(text="")
        self._video_count_badge.configure(text=t('content.badge_empty'))
        self._sel_count_lbl.configure(text=t('selection.count').format(n=0, total=0))

        self._log.log(t('log.cleared'), "info")

    def _eject_disc(self, drive_to_eject=None):
        """Eject the disc from the detected or specified optical drive."""
        if self._ripping:
            self._stop_rip()

        # Determine drive letter
        drive_letter = None
        target = drive_to_eject or self._vcd_path.get()
        if target and len(target) >= 2 and target[1] == ':':
            drive_letter = target[0].upper()
        else:
            # Try to find an optical drive
            cd_drives = get_cd_drives()
            if cd_drives:
                drive_letter = cd_drives[0][0].upper()
        
        if not drive_letter:
            messagebox.showinfo(t('messageboxes.no_drive_title'), t('messageboxes.no_drive_msg'))
            return
        
        self._log.log(t('messageboxes.ejecting').format(drive=drive_letter), "info")
        
        def do_eject_bg():
            ejected = False
            # Strategy 1: Win32 DeviceIoControl (most reliable)
            try:
                import ctypes
                from ctypes import wintypes
                GENERIC_READ = 0x80000000
                FILE_SHARE_READ = 0x00000001
                FILE_SHARE_WRITE = 0x00000002
                OPEN_EXISTING = 3
                IOCTL_STORAGE_EJECT_MEDIA = 0x2D4808
                INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
                
                handle = ctypes.windll.kernel32.CreateFileW(
                    f"\\\\.\\{drive_letter}:",
                    GENERIC_READ,
                    FILE_SHARE_READ | FILE_SHARE_WRITE,
                    None, OPEN_EXISTING, 0, None
                )
                if handle != INVALID_HANDLE_VALUE:
                    bytes_returned = wintypes.DWORD(0)
                    result = ctypes.windll.kernel32.DeviceIoControl(
                        handle, IOCTL_STORAGE_EJECT_MEDIA,
                        None, 0, None, 0,
                        ctypes.byref(bytes_returned), None
                    )
                    ctypes.windll.kernel32.CloseHandle(handle)
                    if result:
                        ejected = True
                        self.after(0, lambda: self._log.log(t('log.eject_win32').format(drive=drive_letter), "success"))
            except Exception as e:
                self.after(0, lambda err=e: self._log.log(t('log.eject_win32_fail').format(err=err), "warning"))
            
            # Strategy 2: PowerShell Shell.Application COM
            if not ejected:
                try:
                    ps_cmd = (
                        f"(New-Object -ComObject Shell.Application)"
                        f".Namespace(17).ParseName('{drive_letter}:').InvokeVerb('Eject')"
                    )
                    proc = subprocess.run(
                        ["powershell", "-NoProfile", "-NonInteractive",
                         "-Command", ps_cmd],
                        env=get_subprocess_env(),
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if proc.returncode == 0:
                        ejected = True
                        self.after(0, lambda: self._log.log(t('log.eject_ps').format(drive=drive_letter), "success"))
                    else:
                        raise RuntimeError(proc.stderr.strip() if proc.stderr else "Eject verb failed")
                except Exception as e:
                    self.after(0, lambda err=e: (
                        self._log.log(t('log.eject_ps_fail').format(err=err), "error"),
                        messagebox.showwarning(
                            t('messageboxes.eject_fail_title'),
                            t('messageboxes.eject_fail_msg').format(drive=drive_letter, err=err)
                        )
                    ))
            
            # Always clear disc info and reset non-VCD state on UI thread
            self.after(0, self._clear_disc_info)

        threading.Thread(target=do_eject_bg, daemon=True).start()

    def _set_window_icon(self, window):
        """Set app icon on a Tk or Toplevel window using the multi-resolution CompactDisc.ico and sync title bar dark mode."""
        global _APP_ICON_PHOTO, _APP_ICON_ICO_PATH
        try:
            hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
            set_window_dark_mode(hwnd, i18n.get_effective_theme() == "dark")
        except Exception:
            pass

        try:
            if _APP_ICON_ICO_PATH is None:
                candidates = []
                if getattr(sys, "_MEIPASS", None):
                    candidates.append(os.path.join(sys._MEIPASS, "CompactDisc.ico"))
                base_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
                exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else base_dir
                candidates.append(os.path.join(exe_dir, "CompactDisc.ico"))
                candidates.append(os.path.join(exe_dir, "_internal", "CompactDisc.ico"))
                candidates.append(os.path.join(base_dir, "CompactDisc.ico"))
                candidates.append(os.path.abspath("CompactDisc.ico"))
                for c in candidates:
                    if c and os.path.isfile(c):
                        _APP_ICON_ICO_PATH = os.path.abspath(c)
                        break
                else:
                    _APP_ICON_ICO_PATH = False

            ico_applied = False
            if _APP_ICON_ICO_PATH:
                try:
                    if isinstance(window, tk.Tk):
                        window.iconbitmap(default=_APP_ICON_ICO_PATH)
                    else:
                        window.iconbitmap(_APP_ICON_ICO_PATH)
                    ico_applied = True
                except Exception:
                    pass

                try:
                    hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2) or window.winfo_id()
                    IMAGE_ICON = 1
                    LR_LOADFROMFILE = 0x00000010
                    LR_DEFAULTSIZE = 0x00000040
                    WM_SETICON = 0x0080
                    ICON_SMALL = 0
                    ICON_BIG = 1

                    # Load large icon (32x32 / 48x48) for Alt-Tab and Taskbar
                    hicon_big = ctypes.windll.user32.LoadImageW(
                        None, _APP_ICON_ICO_PATH, IMAGE_ICON, 0, 0,
                        LR_LOADFROMFILE | LR_DEFAULTSIZE
                    )
                    if hicon_big:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)

                    # Load small icon (16x16) for Title bar
                    cx_sm = ctypes.windll.user32.GetSystemMetrics(49) or 16
                    cy_sm = ctypes.windll.user32.GetSystemMetrics(50) or 16
                    hicon_sm = ctypes.windll.user32.LoadImageW(
                        None, _APP_ICON_ICO_PATH, IMAGE_ICON, cx_sm, cy_sm,
                        LR_LOADFROMFILE
                    )
                    if hicon_sm:
                        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_sm)
                    ico_applied = True
                except Exception:
                    pass

            # Only fallback to PNG iconphoto if ICO could not be loaded
            if not ico_applied:
                if _APP_ICON_PHOTO is None:
                    _base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
                    _png = os.path.join(_base, "CompactDisc.png")
                    if not os.path.isfile(_png):
                        _png = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CompactDisc.png")
                    if os.path.isfile(_png):
                        try:
                            from PIL import Image, ImageTk
                            _APP_ICON_PHOTO = ImageTk.PhotoImage(Image.open(_png))
                        except Exception:
                            _APP_ICON_PHOTO = False
                    else:
                        _APP_ICON_PHOTO = False
                if _APP_ICON_PHOTO:
                    try:
                        window.iconphoto(False, _APP_ICON_PHOTO)
                        window._icon_photo_ref = _APP_ICON_PHOTO
                    except Exception:
                        pass
        except Exception:
            pass

    def _batch_rename(self):
        """Open a batch rename dialog for all scanned files."""
        if not self._videos:
            messagebox.showinfo(t('batch.no_files_title'), t('batch.no_files_msg'))
            return

        dlg = tk.Toplevel(self)
        dlg.title(t('batch.title'))
        dlg.configure(bg=COLORS["bg_panel"])
        dlg.geometry(f"{scale_val(650)}x{scale_val(600)}")
        self._set_window_icon(dlg)
        dlg.grab_set()

        # Title
        tk.Label(
            dlg, text=t('batch.header'),
            font=FONTS["heading"], bg=COLORS["bg_panel"],
            fg=COLORS["text_primary"]
        ).pack(padx=24, pady=(20, 4), anchor="w")

        tk.Label(
            dlg, text=t('batch.inst'),
            font=FONTS["body"], bg=COLORS["bg_panel"],
            fg=COLORS["text_secondary"]
        ).pack(padx=24, pady=(0, 8), anchor="w")

        # ── Sequential Numbering Section ──────────────────
        seq_frame = tk.Frame(dlg, bg=COLORS["bg_card"],
                             highlightbackground=COLORS["border"], highlightthickness=1)
        seq_frame.pack(fill="x", padx=24, pady=(0, 10))

        seq_enabled = tk.BooleanVar(value=self._batch_seq_enabled)
        base_var = tk.StringVar(value=self._batch_base_name)
        start_var = tk.StringVar(value=self._batch_start_index)

        def _save_batch_state(*_):
            self._batch_seq_enabled = seq_enabled.get()
            self._batch_base_name = base_var.get()
            self._batch_start_index = start_var.get()

        seq_enabled.trace_add("write", _save_batch_state)
        base_var.trace_add("write", _save_batch_state)
        start_var.trace_add("write", _save_batch_state)

        # Checkbox row
        seq_chk = tk.Checkbutton(
            seq_frame, text=t('batch.seq_enable'),
            variable=seq_enabled,
            font=FONTS["body"], bg=COLORS["bg_card"],
            fg=COLORS["accent"], activebackground=COLORS["bg_card"],
            activeforeground=COLORS["accent"], selectcolor=COLORS["bg_dark"],
            cursor="hand2"
        )
        seq_chk.pack(anchor="w", padx=12, pady=(10, 6))

        # Config row (Base Name + Start Index)
        cfg_row = tk.Frame(seq_frame, bg=COLORS["bg_card"])
        cfg_row.pack(fill="x", padx=12, pady=(0, 10))

        tk.Label(cfg_row, text=t('batch.seq_base'), font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]
                 ).pack(side="left", padx=(0, 4))
        base_ent = tk.Entry(cfg_row, textvariable=base_var, font=FONTS["body"],
                            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                            insertbackground=COLORS["accent"], relief="flat",
                            bd=4, width=14)
        base_ent.pack(side="left", padx=(0, 14))

        tk.Label(cfg_row, text=t('batch.seq_start'), font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]
                 ).pack(side="left", padx=(0, 4))
        start_ent = tk.Entry(cfg_row, textvariable=start_var, font=FONTS["body"],
                             bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                             insertbackground=COLORS["accent"], relief="flat",
                             bd=4, width=5)
        start_ent.pack(side="left")

        # ── Scrollable file list ──────────────────────────
        scroll_frame = tk.Frame(dlg, bg=COLORS["bg_panel"])
        scroll_frame.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        canvas = tk.Canvas(scroll_frame, bg=COLORS["bg_panel"], highlightthickness=0)
        canvas._can_scroll = True
        vsb = ttk.Scrollbar(scroll_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=COLORS["bg_panel"])
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas.find_all()[0], width=e.width) if canvas.find_all() else None)

        total = len(self._videos)
        pad_width = 3 if total > 99 else 2

        entry_vars = []     # full-name entries (manual mode)
        suffix_vars = []    # suffix entries (seq mode)
        row_frames = []
        manual_widgets = []   # (track_lbl, name_entry)
        seq_widgets = []      # (num_lbl, suffix_lbl, suffix_entry)

        for i, info in enumerate(self._videos):
            row = tk.Frame(inner, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"], highlightthickness=1)
            row.pack(fill="x", pady=3)
            row_frames.append(row)

            # ── Manual mode widgets ──
            trk_lbl = tk.Label(
                row, text=t('batch.track').format(n=i+1),
                font=FONTS["badge"], bg=COLORS["bg_card"],
                fg=COLORS["text_muted"], width=8
            )
            current_stem = info.get("custom_stem", Path(info["filename"]).stem)
            name_var = tk.StringVar(value=current_stem)
            entry_vars.append(name_var)
            name_ent = tk.Entry(
                row, textvariable=name_var, font=FONTS["body"],
                bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                insertbackground=COLORS["accent"], relief="flat", bd=6
            )
            manual_widgets.append((trk_lbl, name_ent))

            # ── Sequential mode widgets ──
            try:
                start_idx = int(start_var.get())
            except ValueError:
                start_idx = 1
            num_text = str(start_idx + i).zfill(pad_width)
            num_lbl = tk.Label(
                row, text=num_text,
                font=FONTS["badge"], bg=COLORS["bg_card"],
                fg=COLORS["cyan"], width=5
            )
            suf_lbl = tk.Label(
                row, text=t('batch.seq_suffix'),
                font=FONTS["small"], bg=COLORS["bg_card"],
                fg=COLORS["text_muted"]
            )
            suf_var = tk.StringVar(value="")
            suffix_vars.append(suf_var)
            suf_ent = tk.Entry(
                row, textvariable=suf_var, font=FONTS["body"],
                bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                insertbackground=COLORS["accent"], relief="flat", bd=6
            )
            seq_widgets.append((num_lbl, suf_lbl, suf_ent))

        def _update_seq_numbers(*_):
            """Recalculate sequential number labels."""
            try:
                start_idx = int(start_var.get())
            except ValueError:
                start_idx = 1
            pw = 3 if total > 99 else 2
            for i in range(total):
                num_lbl_i = seq_widgets[i][0]
                num_lbl_i.configure(text=str(start_idx + i).zfill(pw))

        def _toggle_mode(*_):
            """Switch between manual and sequential layouts."""
            is_seq = seq_enabled.get()
            for i in range(total):
                trk_lbl, name_ent = manual_widgets[i]
                num_lbl, suf_lbl, suf_ent = seq_widgets[i]
                # Hide all first
                for w in (trk_lbl, name_ent, num_lbl, suf_lbl, suf_ent):
                    w.pack_forget()
                if is_seq:
                    num_lbl.pack(side="left", padx=(10, 6), pady=8)
                    suf_lbl.pack(side="left", padx=(0, 4), pady=8)
                    suf_ent.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)
                else:
                    trk_lbl.pack(side="left", padx=(10, 6), pady=8)
                    name_ent.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)
            # Enable/disable config fields
            state = "normal" if is_seq else "disabled"
            base_ent.configure(state=state)
            start_ent.configure(state=state)
            if is_seq:
                _update_seq_numbers()

        # Bind toggle & number updates
        seq_enabled.trace_add("write", _toggle_mode)
        start_var.trace_add("write", _update_seq_numbers)

        # Initialize in manual mode
        _toggle_mode()

        # ── Button row ────────────────────────────────────
        btn_row = tk.Frame(dlg, bg=COLORS["bg_panel"])
        btn_row.pack(fill="x", padx=24, pady=(4, 20))

        def apply_all():
            if seq_enabled.get():
                base = base_var.get().strip()
                try:
                    start_idx = int(start_var.get())
                except ValueError:
                    start_idx = 1
                pw = 3 if total > 99 else 2
                for i in range(total):
                    num = str(start_idx + i).zfill(pw)
                    suffix = suffix_vars[i].get().strip()
                    if base and suffix:
                        raw_stem = f"{base} {num} - {suffix}"
                    elif base:
                        raw_stem = f"{base} {num}"
                    elif suffix:
                        raw_stem = f"{num} - {suffix}"
                    else:
                        raw_stem = num
                    new_stem = sanitize_filename(raw_stem, fallback=f"Track_{num}")
                    if i < len(self._videos):
                        self._videos[i]["custom_stem"] = new_stem
                        if i < len(self._cards):
                            self._cards[i]._filename_lbl.configure(text=f"📼  {new_stem}")
            else:
                for i, var in enumerate(entry_vars):
                    raw_stem = var.get().strip()
                    if raw_stem and i < len(self._videos):
                        new_stem = sanitize_filename(raw_stem, fallback=f"Track_{i+1}")
                        self._videos[i]["custom_stem"] = new_stem
                        if i < len(self._cards):
                            self._cards[i]._filename_lbl.configure(text=f"📼  {new_stem}")
            self._log.log(t('log.batch_renamed').format(total=total), "success")
            dlg.destroy()

        tk.Button(
            btn_row, text=t('batch.apply_all'),
            font=FONTS["body"], bg=COLORS["accent"],
            fg=COLORS["text_primary"], relief="flat", bd=0,
            padx=20, pady=8, cursor="hand2",
            command=apply_all
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            btn_row, text=t('batch.cancel'),
            font=FONTS["body"], bg=COLORS["bg_card"],
            fg=COLORS["text_muted"], relief="flat", bd=0,
            padx=20, pady=8, cursor="hand2",
            command=dlg.destroy
        ).pack(side="left")

        dlg.bind("<Escape>", lambda e: dlg.destroy())

    # ── FFmpeg warning ────────────────────────
    def _show_ffmpeg_warning(self):
        self._log.log(
            t('log.ffmpeg_dl'), "error"
        )
        self._log.log(
            t('log.ffmpeg_hint'), "warning"
        )

    def _toggle_console(self):
        """Show or hide the console log window."""
        if self._log_window.state() == "withdrawn" or self._log_window.state() == "iconic":
            self._log_window.deiconify()
            self._log_window.lift()
        else:
            self._log_window.withdraw()

    def _refresh_ui(self):
        self.title(t('header.title'))
        self._title_lbl.configure(text=t('header.title'))
        self._console_btn.configure(text=t('header.console'))
        if hasattr(self, "_clear_all_btn"):
            self._clear_all_btn.configure(text=t('header.clear_all'))
        if hasattr(self, "_clear_all_tip"):
            self._clear_all_tip.text = t('header.clear_all_tip')
        self._about_btn.configure(text=t('header.about'))
        self._batch_rename_btn.configure(text=t('header.batch_rename'))
        self._eject_btn.configure(text=t('header.eject_disc'))
        
        d = self._vcd_path.get()
        if d:
            drive_letter = d[0].upper()
            self._drive_lbl.configure(text=t('header.vcd_on').format(drive=drive_letter))
            self._detected_drive_lbl.configure(text=t('drive.drive_label').format(drive=drive_letter))
            self._detect_label.configure(text=t('drive.folder_selected') if is_vcd_folder(d) else t('drive.detect_vcd'))
        else:
            self._drive_lbl.configure(text=t('header.no_disc'))
            self._detect_label.configure(text=t('drive.insert_vcd'))
            
        self._source_section_lbl.configure(text=t('source.title'))
        self._browse_btn.set_text(t('source.browse'), icon="📁")
        self._scan_btn.set_text(t('source.scan'), icon="🔍")
        
        self._sel_section_lbl.configure(text=t('selection.title'))
        self._sel_all_btn.set_text(t('selection.all'), icon="☑")
        self._sel_none_btn.set_text(t('selection.none'), icon="☐")
        self._update_sel_count()
        
        self._format_section_lbl.configure(text=t('format.title'))
        self._video_mode_rb.configure(text=t('format.video_mode'))
        self._audio_mode_rb.configure(text=t('format.audio_mode'))
        self._video_fmt_lbl.configure(text=t('format.video_lbl'))
        self._audio_fmt_lbl.configure(text=t('format.audio_lbl'))
        
        for fmt, lbl in self._fmt_desc_lbls.items():
            lbl.configure(text=t(f"format.{fmt.lower()}_desc"))
        for fmt, lbl in self._audio_desc_lbls.items():
            lbl.configure(text=t(f"format.{fmt.lower()}_desc"))
            
        self._dat_mode_lbl.configure(text=t('format.dat_mode_lbl'))
        self._dat_raw_rb.configure(text=t('format.dat_raw'))
        self._dat_mp4_rb.configure(text=t('format.dat_mp4'))
        self._res_title_lbl.configure(text=t('format.res_title'))
        self._res_orig_rb.configure(text=t('format.res_orig'))
        self._res_1080p_rb.configure(text=t('format.res_1080p'))
        
        self._output_section_lbl.configure(text=t('output.title'))
        self._choose_folder_btn.set_text(t('output.choose'), icon="💾")
        self._auto_open_chk.configure(text=t('output.auto_open'))
        
        self._rip_btn.set_text(t('rip.start'), icon="⚡")
        self._stop_btn.set_text(t('rip.stop'), icon="⏹")
        
        self._content_title.configure(text=t('content.title'))
        total = len(self._videos)
        if total == 0:
            self._video_count_badge.configure(text=t('content.badge_empty'))
        else:
            self._video_count_badge.configure(text=t('content.badge').format(n=total))
            
        if hasattr(self, "_empty_title_lbl") and self._empty_title_lbl.winfo_exists():
            self._empty_title_lbl.configure(text=t('content.empty_title'))
            self._empty_sub_lbl.configure(text=t('content.empty_sub'))
            
        self._console_title_lbl.configure(text=t('console.title'))
        self._console_clear_btn.configure(text=t('console.clear'))
        self._log_window.title(f"{t('console.title').strip()} — {t('header.title')}")
        if hasattr(self, "_about_dialog") and self._about_dialog and self._about_dialog.winfo_exists():
            if hasattr(self._about_dialog, "update_lang"):
                self._about_dialog.update_lang()

    def on_close(self):
        try:
            self._taskbar_progress.reset()
        except Exception:
            pass
        self._log_window.destroy()
        if self._poll_job:
            self.after_cancel(self._poll_job)
        release_single_instance_lock()
        self.destroy()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    # Single-instance lock check — executed before initializing heavy GUI
    if not acquire_single_instance_lock():
        activate_existing_window()
        sys.exit(0)

    app = VCDRipperApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
