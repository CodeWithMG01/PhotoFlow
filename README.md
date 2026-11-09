# PhotoFlow 📸

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](#testing)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)]()

A modern, local-first desktop application designed to convert **HEIC**, **HEIF**, and **HIF** photo collections to **JPG without compromising on image quality or metadata**.

Most standard HEIC converters discard vital camera metadata, downsample colors, and strip wide-gamut color profiles. **PhotoFlow** preserves full color fidelity, orientation, GPS coordinates, and camera profiles—all processed entirely on your local machine with zero cloud uploads.

---

## ✨ Features

### High-Fidelity Conversion Pipeline
* **Display P3 Color Profile Retention**: Preserves wide-gamut color profiles from Apple devices so colors never appear dull, washed out, or shifted.
* **Full Chroma Resolution (4:4:4)**: Disables default JPEG chroma downsampling (`subsampling=0`), keeping fine lines, sharp text, and saturated colors crisp.
* **Full EXIF & Geotag Preservation**: Retains GPS coordinates, capture dates (`DateTimeOriginal`), exposure settings, lens details, and camera models.
* **Smart Orientation Correction**: Automatically normalizes photo orientation based on EXIF tags without risk of double-rotation.
* **Alpha Channel Transparency**: Composites transparent graphics and iOS subject cutouts over a clean white background instead of rendering black artifacts.
* **Filesystem Timestamp Matching**: Duplicates original file modification and access times (`os.utime`), keeping your photo library sorted chronologically.
* **Broad Camera Compatibility**: Supports `.heic` and `.heif` (Apple / Android) as well as `.hif` (Canon EOS, Sony Alpha, and Nikon mirrorless cameras).

### Desktop Application
* **Modern Dark Mode UI**: Clean, responsive interface built with CustomTkinter that smoothly adapts across display scaling settings.
* **Multi-Threaded Concurrency**: Leverages multi-core CPUs via a background `ThreadPoolExecutor` to process high-resolution batches rapidly without freezing the UI.
* **Custom Output Paths**: Easily specify custom output folders or keep the organized `Converted_JPG` subfolder.
* **Real-Time Progress & Cancellation**: Live progress bar, photo counter, and graceful cancellation support.
* **100% Private & Offline**: Works completely offline. Your photos never leave your device.

---

## 🗺️ Roadmap / Planned Features

* [ ] Automatic photo reorganization into `Year/Month` folder structures.
* [ ] Perceptual hash duplicate photo detection.
* [ ] Thumbnail gallery and side-by-side comparison preview.

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10 or higher
* `pip` package manager

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/PhotoFlow.git
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

1. Click **Browse** under **1. Select photo folder** to pick your folder of HEIC/HEIF images.
2. *(Optional)* Click **Browse** under **2. Output location** to pick a custom destination.
3. Adjust the **JPG image quality** slider (default: `95%`).
4. Click **CONVERT PHOTOS**.

---

## 🧪 Testing

PhotoFlow includes a full test suite built with `pytest`:

```bash
pytest
```

---

## 📁 Project Structure

```text
PhotoFlow/
├── .github/
│   └── workflows/
│       └── test.yml          # Automated CI test pipeline
├── assets/
│   └── .gitkeep
├── src/
│   └── photoflow/
│       ├── __init__.py       # Package definition
│       ├── __main__.py       # Entry point for python -m photoflow
│       ├── converter.py      # Core conversion pipeline & concurrency
│       └── main.py           # CustomTkinter GUI application
├── tests/
│   ├── test_app.py           # UI & extension validation tests
│   └── test_converter.py     # Conversion, EXIF, ICC, and timestamp tests
├── .gitignore                # Git ignore rules
├── LICENSE                   # MIT License
├── pyproject.toml            # Project packaging specification
├── README.md                 # Project documentation
└── requirements.txt          # Python dependencies
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
