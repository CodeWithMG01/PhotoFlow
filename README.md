# PhotoFlow 📸

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](#testing)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

A modern, local-first desktop application designed for **high-fidelity photo conversion** (HEIC/HEIF/HIF to JPG) and **smart facial recognition photo filtering**—processed entirely offline on your local machine with zero cloud uploads.

---

## ✨ Features

### 👤 Smart Face Filter (New)
* **Multi-Person Permutation Recognition**: Identifies photos containing **Person 1**, **Person 2**, or **both**, whether they appear alone, together, or within larger group photos.
* **Local Neural Face Embeddings**: Powered by OpenCV's state-of-the-art **YuNet** face detector and **SFace** facial recognizer (128-dimensional biometric embeddings).
* **Safe Organization**:
  * **Copy Mode (Default)**: Preserves original folders untouched and copies matched photos into `Matched_Photos/`.
  * **Separate Mode**: Organizes your collection by moving target photos to `Matched_Photos/` and all other photos to `Other_Photos/`.
* **Universal Format Support**: Scans and filters `.heic`, `.heif`, `.hif`, `.jpg`, `.jpeg`, `.png`, `.webp`, and `.bmp`.

### 🎨 High-Fidelity HEIC Conversion Pipeline
* **Display P3 Color Profile Retention**: Preserves wide-gamut color profiles from Apple devices so colors never appear dull, washed out, or shifted.
* **Full Chroma Resolution (4:4:4)**: Disables default JPEG chroma downsampling (`subsampling=0`), keeping fine lines, sharp text, and saturated colors crisp.
* **Full EXIF & Geotag Preservation**: Retains GPS coordinates, capture dates (`DateTimeOriginal`), exposure settings, lens details, and camera models.
* **Smart Orientation Correction**: Automatically normalizes photo orientation based on EXIF tags without risk of double-rotation.
* **Alpha Channel Transparency**: Composites transparent graphics and iOS subject cutouts over a clean white background instead of rendering black artifacts.
* **Filesystem Timestamp Matching**: Duplicates original file modification and access times (`os.utime`), keeping your photo library sorted chronologically.

### 🖥️ Desktop Application
* **Modern Tabbed Interface**: Built with CustomTkinter, seamlessly switching between the **HEIC Converter** and the **Face Filter**.
* **Multi-Threaded Concurrency**: Processes high-resolution photo batches rapidly in the background without freezing the UI.
* **100% Private & Offline**: Works completely offline. Your photos never leave your device.

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

### Using the Face Filter:
1. Click the **"Face Filter"** tab at the top.
2. Select your photo collection folder.
3. Click **Choose** next to **Person 1** and select a clear reference photo of their face.
4. *(Optional)* Click **Choose** next to **Person 2** to select a second person's face.
5. Choose your output location and action (**Copy** or **Separate**).
6. Click **FILTER PHOTOS BY FACE**.

### Using the HEIC Converter:
1. Click the **"HEIC Converter"** tab.
2. Select your folder of `.heic` / `.heif` / `.hif` photos.
3. Adjust your target JPEG quality.
4. Click **CONVERT PHOTOS**.

---

## 🧪 Testing

PhotoFlow includes a full test suite built with `pytest`:

```bash
pytest
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
