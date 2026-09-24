# VCD Ripper Pro

<p align="center">
  <img src="CompactDisc.png" alt="VCD Ripper Pro Logo" width="120"/>
</p>

<p align="center">
  <strong>A modern, premium VCD video extraction tool for Windows</strong><br/>
  Extract videos from VCD discs — with a sleek dark UI and zero fuss.
</p>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-1.2.4-6C63FF?style=flat-square"/>
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows-blue?style=flat-square"/>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-22C55E?style=flat-square"/>
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-F59E0B?style=flat-square"/>
</p>

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🎬 **Direct DAT Extraction** | Copy raw `.dat` files from VCD directly — no re-encoding, fastest possible speed |
| 🎞 **Video Conversion** | Convert to **MPG**, **MP4** (H.264+AAC), or **MOV** using FFmpeg |
| 📐 **1440×1080 Upscale** | When exporting to MP4 or MOV, optionally upscale to **1440×1080** (4:3 at 1080p) using Lanczos — ideal for VCD's low-res 352×240 source |
| 🎵 **Audio Only Mode** | Extract audio as **WAV** (lossless) or **MP3** (compressed) |
<<<<<<< HEAD
| ✏ **File Rename** | Rename output files before ripping via an inline rename dialog |
| ✏ **Batch Rename** | Rename all output files at once via a dedicated batch rename dialog |
| 🔄 **Auto-Scan** | Automatically scans for VCD tracks when a disc is inserted — no manual scan needed |
| ☑ **Batch Selection** | Select all / none with one click; defaults to all-selected after scan |
| ⏹ **Stop Anytime** | Cancel an in-progress rip at any time |
| 📋 **Console Log** | Live log of every operation with timestamps |
| ⏏ **Eject Disc** | Eject button in the header bar; auto-detects drive letter with multi-strategy eject for broad Windows compatibility |
| 📂 **Auto-Open Folder** | Option to automatically open output folder after ripping completes |
| 📊 **Taskbar Progress** | Real-time Rip progress bar on Windows taskbar icon (green for in-progress, yellow for stopped, red for errors) |
| 🌓 **Appearance Themes** | Switch between **System** (auto-detects Windows dark/light theme), **Light Mode**, and **Dark Mode** |
| ✏ **File Rename** | Rename output files before ripping |
| ☑ **Batch Selection** | Select all / none with one click |
| ⏹ **Stop Anytime** | Cancel an in-progress rip at any time |
| 📋 **Console Log** | Live log of every operation with timestamps |
| 💿 **Auto Disc Eject** | After ripping completes, prompts to automatically eject the physical disc |
| 💾 **Portable** | No installation required — run from any folder on any Windows PC |

---

## 🖥 System Requirements

| Requirement | Minimum |
|---|---|
| **OS** | Windows 7 / 8 / 10 / 11 (64-bit) |
| **CPU** | Any x86-64 processor |
| **RAM** | 256 MB |
| **Disk** | ~150 MB (including FFmpeg) |
| **Python** *(source only)* | 3.9 or later |

> **Portable build**: No Python installation needed — all dependencies are bundled.

---

## 🚀 Getting Started

### Option A — Portable Build (Recommended, No Installation)

1. Download the latest **`VCD_Ripper_Pro_Portable.zip`** from the [Releases](../../releases) page.
2. Extract the ZIP to any folder.
3. Double-click **`VCD Ripper Pro.exe`** to launch.
4. **Keep the folder structure intact** — the `_internal\` runtime and `ffmpeg\` folders must stay alongside the `.exe`.

### Option B — Run from Source

#### Prerequisites

- Python 3.9+
- FFmpeg (download from [ffmpeg.org](https://ffmpeg.org/download.html))

#### Install dependencies

```bash
pip install pillow
```

#### Launch

```bash
python vcd_ripper.py
```

---

## 📖 Usage Guide

1. **Left Panel — Source & Selection**:
   - Insert your VCD disc — the app **auto-detects and scans** tracks automatically.
   - Alternatively, click **Browse Folder** to target a VCD folder manually.
   - Select tracks via checkmarks (or **All** / **None**).
2. **Center Panel — Track List**:
   - *(Optional)* Click the **✏ icon** on any track card to rename the output file.
   - *(Optional)* Use **✏ Batch Rename** in the header to rename all files at once.
3. **Right Panel — Export & Control**:
   - Choose **Output Format** (**Video** → DAT/MPG/MP4/MOV, or **Audio Only** → WAV/MP3).
   - *(Optional for MP4/MOV)* Toggle **1440×1080** Lanczos upscale.
   - Click **Choose Output Folder** to pick destination directory.
   - *(Optional)* Enable **Open output folder after ripped** to auto-open the folder.
   - Click **⚡ Start Ripping** (or **⏹ Stop Ripping** to cancel).
4. **Header Bar**:
   - **⏏ Eject Disc** — eject the optical drive (auto-detects the correct drive).

---

## 🗂 Project Structure

```
VCD Ripper Pro/
├── vcd_ripper.py          # Main application source
├── CompactDisc.png        # App logo (1024×1024)
├── CompactDisc.ico        # App icon (multi-resolution)
├── LICENSE                # MIT License
├── README.md              # This file
├── .gitignore             # Git ignore rules
└── ffmpeg/
    └── bin/
        ├── ffmpeg.exe     # FFmpeg engine (video/audio conversion)
        └── ffprobe.exe    # Media analysis tool
```

---

## 🔧 Building the Portable EXE

Requires [PyInstaller](https://pyinstaller.org):

```bash
pip install pyinstaller pillow
python -m PyInstaller --noconsole --onedir --clean -y \
  --name "VCDRipperPro" \
  --icon "CompactDisc.ico" \
  --add-data "CompactDisc.ico;." \
  --add-data "CompactDisc.png;." \
  vcd_ripper.py
```

Then copy `ffmpeg/` into the `dist/VCDRipperPro/` folder.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

© 2026 **jjsiew2014-art** — Free to use, modify, and distribute with attribution.
