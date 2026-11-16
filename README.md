# PhotoFlow 📸

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](#testing)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

A modern, local-first desktop application designed for **high-fidelity photo conversion** (HEIC/HEIF/HIF to JPG), **Apple video conversion** (MOV to MP4), **EXIF-based date organization**, and **smart facial recognition filtering**—processed entirely offline on your local machine with zero cloud uploads.

---

## ✨ Features

### 🎬 Apple MOV to Windows MP4 Converter (New)
* **100% Native Windows Compatibility**: Converts Apple `.mov` videos (encoded in HEVC/H.265 or ProRes) into universal H.264 `.mp4` with AAC audio.
* **No Paid Codecs Required**: Videos play smoothly in Windows Media Player, PowerPoint, and web browsers without needing Microsoft Store HEVC extensions.
* **Instant Start (`+faststart`)**: Moves video index atoms to the front so videos play instantly without waiting to buffer.
* **Preserves Video Timestamps**: Maintains original recording dates and timestamps (`os.utime`).

### 📅 Smart Date-Based Photo & Video Organizer
* **True Shutter & Video Timestamp**: Reads internal camera hardware timestamps directly from EXIF (`DateTimeOriginal`) and QuickTime container atoms (`moov/mvhd`).
* **Google Photos JSON Sidecar Reader**: Reads `photoTakenTime` from companion `.json` files (e.g. `IMG_1234.jpg.json` / `IMG_1234.mov.json`) and moves the sidecar with the photo.
* **iPhone Live Photo Pairing**: Automatically detects paired `.HEIC` and `.mov` clips and organizes them side-by-side in the same date folder.
* **Intelligent Filename Detection**: Extracts capture dates from Android (`PXL_202407...`, `IMG_202407...`), WhatsApp, and camera timestamps.
* **Flexible Directory Structures**:
  * `Year / Month (e.g. 2024 / 2024-08 August)`
  * `Year / Month / Day (e.g. 2024 / 2024-08 / 2024-08-20)`
  * `Daily Folders (e.g. 2024-08-20)`
  * `Year Only (e.g. 2024)`

### 👤 Local Face Filter & Trip Cleaner
* **Trip Cleaner Mode (Clean Vacation Albums)**:
  * **Keep Family & Couples**: Keeps every photo containing **You (Person 1)** or **Your Husband (Person 2)**, whether solo, duo, or in group shots.
  * **Preserve Scenery & Landscapes**: Intelligently identifies photos with **0 faces** (landscapes, mountains, food, monuments) and **keeps them untouched** in your main folder.
  * **Remove Other People's Solo Photos**: Detects when a photo only contains another individual's solo portrait (1 face, neither Person 1 nor Person 2) and moves it into `Removed_Other_People/`.
  * **Non-Destructive**: Photos are safely moved rather than permanently deleted, allowing easy review. Companion `.json` sidecars are kept in sync.
* **Standard Filter Mode**:
  * **Multi-Person Permutation Recognition**: Extracts photos containing **Person 1**, **Person 2**, or **both**, whether they appear alone, together, or within larger group photos into `Matched_Photos/`.
* **Local Biometric Face Embeddings**: Powered by OpenCV's state-of-the-art **YuNet** face detector and **SFace** facial recognizer (128-dimensional biometric embeddings), running completely offline on your CPU with zero cloud transmission.

### 🎨 High-Fidelity HEIC Conversion Pipeline
* **Display P3 Color Profile Retention**: Preserves wide-gamut color profiles from Apple devices so colors never appear dull, washed out, or shifted.
* **Full Chroma Resolution (4:4:4)**: Disables default JPEG chroma downsampling (`subsampling=0`), keeping fine lines, sharp text, and saturated colors crisp.
* **Full EXIF & Geotag Preservation**: Retains GPS coordinates, capture dates, exposure settings, lens details, and camera models.
* **Smart Orientation Correction**: Automatically normalizes photo orientation based on EXIF tags without risk of double-rotation.
* **Alpha Channel Transparency**: Safely blends transparent graphics and iOS subject cutouts over a clean white background.

### 🖥️ Desktop Application
* **Modern Tabbed Interface**: Built with CustomTkinter, seamlessly switching between the **HEIC Converter**, **Video Converter**, **Face Filter**, and **Date Organizer**.
* **Multi-Threaded Concurrency**: Processes high-resolution photo and video batches rapidly in the background without freezing the UI.
* **100% Private & Offline**: Works completely offline. Your photos and videos never leave your device.

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10 or higher
* `pip` package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/CodeWithMG01/PhotoFlow.git
   cd PhotoFlow
   ```

2. **Create and activate a virtual environment:**
   * **Windows (PowerShell):**
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

---

## 💻 Usage

Launch the PhotoFlow desktop application:

```bash
python -m photoflow
```

1. **HEIC Converter**: Select a folder to convert Apple `.heic` / `.heif` / `.hif` photos to JPEG with full color fidelity.
2. **Video Converter**: Select a folder of Apple `.mov` videos to batch convert to universal `.mp4` for Windows laptops.
3. **Face Filter & Trip Cleaner**: Choose reference photos for Person 1 (You) & Person 2 (Husband) to automatically keep all your photos and scenery while filtering out other people's solo shots into a separate folder.
4. **Date Organizer**: Organize your media library into Year/Month/Day folders using internal hardware capture timestamps.

---

## 🧪 Testing

PhotoFlow includes a full test suite built with `pytest`:

```bash
pytest
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
